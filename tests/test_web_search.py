"""Busca na web (lote 12): adapter, gateway, agente, renderização, uso e conferência, sem rede."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from aliado.agent import Agent, _mark_web, prepare_request
from aliado.llm.contracts import LLMRequest, LLMResult, LLMStreamChunk, LLMUsage
from aliado.llm.providers import ModelRegistration, ProviderGateway
from aliado.llm.providers.base import ProviderError
from aliado.llm.providers.gemini import GeminiProvider
from aliado.llm.usage_log import record_usage, usage_line
from aliado.memory.reviewer import check_memory, review_exchange


def grounded(text, *, supports=(("taxa constante", (0,)),)):
    chunks = [SimpleNamespace(web=SimpleNamespace(uri="https://exemplo.org/a", title="Exemplo A", domain="exemplo.org")),
              SimpleNamespace(web=None),
              SimpleNamespace(web=SimpleNamespace(uri="https://outro.edu/b", title="", domain="outro.edu"))]
    metadata = SimpleNamespace(
        grounding_chunks=chunks, web_search_queries=["taxa de falha IGBT"],
        grounding_supports=[SimpleNamespace(segment=SimpleNamespace(text=t), grounding_chunk_indices=list(i))
                            for t, i in supports])
    return SimpleNamespace(text=text, usage_metadata=None, candidates=[SimpleNamespace(grounding_metadata=metadata)])


def test_gemini_enables_search_only_when_asked_and_reads_sources():
    calls = []

    class Models:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return grounded("Usa-se taxa constante.", supports=[("taxa constante", [0, 2]), ("sem fonte", [1])])

    provider = GeminiProvider(client=SimpleNamespace(models=Models()))
    plain = LLMRequest(task_type="t", messages=[{"content": "oi"}])
    provider.generate(plain, model_id="m")
    assert "tools" not in calls[0]["config"]
    result = provider.generate(LLMRequest(task_type="t", messages=[{"content": "oi"}], web_search=True), model_id="m")
    assert calls[1]["config"]["tools"] == [{"google_search": {}}]
    assert [s["uri"] for s in result.web_sources] == ["https://exemplo.org/a", "https://outro.edu/b"]
    assert result.web_queries == ("taxa de falha IGBT",)
    # O índice 2 do provedor é a segunda fonte da web; o trecho sem fonte web é descartado.
    assert result.web_supports == ({"text": "taxa constante", "sources": [1, 2]},)
    with pytest.raises(ValueError):
        provider.generate(LLMRequest(task_type="t", messages=[{"content": "oi"}], web_search=True,
                                     structured_output={"type": "object"}), model_id="m")


def test_gemini_stream_carries_grounding_in_last_chunk():
    class Models:
        def generate_content_stream(self, **_kwargs):
            return iter([SimpleNamespace(text="Taxa ", usage_metadata=None, candidates=[]),
                         grounded("constante.")])

    chunks = list(GeminiProvider(client=SimpleNamespace(models=Models())).stream(
        LLMRequest(task_type="t", messages=[{"content": "oi"}], web_search=True), model_id="m"))
    assert chunks[0].web_sources == () and chunks[-1].web_queries == ("taxa de falha IGBT",)


def test_gateway_refuses_web_search_on_models_without_it():
    gateway = ProviderGateway()
    gateway.register_provider("fake", SimpleNamespace(configured=True, generate=lambda *a, **k: None))
    gateway.register_model(ModelRegistration("fake", "m", "id"))
    with pytest.raises(ProviderError):
        gateway.execute(LLMRequest(task_type="t", messages=[{"content": "oi"}], web_search=True),
                        provider="fake", model_alias="m")


def test_web_markers_follow_supported_text():
    content = "A taxa é constante. Depois, a vida útil é de 20 anos."
    marked = _mark_web(content, [{"text": "A taxa é constante.", "sources": [1]},
                                 {"text": "a vida útil é de 20 anos", "sources": [2, 1]},
                                 {"text": "trecho inexistente", "sources": [3]}])
    assert marked == "A taxa é constante.[W1] Depois, a vida útil é de 20 anos[W2][W1]."


def test_prepare_request_marks_web_and_adds_rules():
    request = prepare_request("Qual a taxa?", web_search=True)
    assert request.web_search and request.metadata["web_search"]
    assert any("Busca na web habilitada" in m["content"] for m in request.messages)
    assert not prepare_request("Qual a taxa?").web_search


class Library:
    def __init__(self, hits):
        self.hits = hits

    def search(self, question):
        return self.hits


HIT = {"citation_id": "Kok", "document_id": "d1", "title": "Doc", "version": 1, "sha256": "x", "locator": "p1",
       "page": 1, "method": "text", "status": "ready", "text": "t", "original": "o"}


def stream_agent(text, *, web=True):
    web_meta = {"web_sources": ({"uri": "https://exemplo.org", "title": "Ex", "domain": "exemplo.org"},),
                "web_queries": ("q",), "web_supports": ({"text": text.split(".")[0], "sources": [1]},)} if web else {}

    def stream(request, **kwargs):
        yield LLMStreamChunk(text, "google", "m", request.task_type)
        yield LLMStreamChunk("", "google", "m", request.task_type, usage=LLMUsage(1, 1, 2), **web_meta)

    return Agent(SimpleNamespace(stream=stream))


def final(agent, **kwargs):
    return list(agent.stream_answer("Q?", provider="google", model_alias="flash", **kwargs))[-1][1]


def test_library_and_web_together_accept_web_only_but_block_invented_pdf_citation():
    result = final(stream_agent("A taxa é constante. Mais texto."), library=Library([HIT]), web_search=True)
    assert result.validation_status == "web_grounded" and "[W1]" in result.content
    assert result.web_queries == ("q",)
    both = final(stream_agent("A taxa é constante [Kok]. Mais."), library=Library([HIT]), web_search=True,
                 append_sources=False)
    assert both.validation_status == "citation_ids_verified" and both.sources[0]["citation_id"] == "Kok"
    invented = final(stream_agent("A taxa é constante [Kfalso]. Mais."), library=Library([HIT]), web_search=True)
    assert invented.validation_status == "invalid_citations"
    no_web = final(stream_agent("Sem fonte nenhuma.", web=False), library=Library([HIT]), web_search=True)
    assert no_web.validation_status == "invalid_citations"


def test_empty_library_does_not_block_when_web_is_on():
    assert final(stream_agent("Resposta da web."), library=Library([]), web_search=True).provider == "google"
    assert final(stream_agent("x"), library=Library([])).provider == "local"


def test_usage_log_counts_searches_without_storing_queries(tmp_path):
    result = LLMResult("ok", "google", "m", "t", usage=LLMUsage(1, 1, 2), web_queries=("consulta sigilosa", "outra"))
    entry = record_usage(result, tmp_path / "uso.jsonl")
    assert entry["web_queries"] == 2 and "sigilosa" not in (tmp_path / "uso.jsonl").read_text(encoding="utf-8")
    assert "buscas na web: 2" in usage_line(result)


def test_reviewer_accepts_web_fact_with_link():
    payload = {"anotacoes": [{"tipo": "fato", "texto": "Fato da web.", "origem": "inferido", "citacao": "W1"}]}

    def execute(request):
        return LLMResult(json.dumps(payload), "google", "m", request.task_type, structured_data=payload)

    notes, _ = review_exchange(execute, question="Q", answer="A", skill=None,
                               sources=[{"citation_id": "W1", "title": "Ex", "url": "https://exemplo.org", "text": ""}])
    assert notes[0]["source"] == {"citation_id": "W1", "title": "Ex", "url": "https://exemplo.org"}


@pytest.mark.parametrize("content,sources,expected", [
    ("VEREDITO: contradiz\nCORRECAO: O MTTR é 4 h.\nEXPLICACAO: A norma diz 4 h.", True, "contradiz"),
    ("**VEREDITO:** confirma\nEXPLICACAO: ok", True, "confirma"),
    ("VEREDITO: contradiz\nCORRECAO: nova", False, "inconclusivo"),  # sem fonte, sem conferência
    ("sem formato", True, "inconclusivo"),
])
def test_check_memory_parses_verdict_and_requires_sources(content, sources, expected):
    requests = []

    def execute(request):
        requests.append(request)
        web = ({"uri": "https://exemplo.org", "title": "Ex", "domain": "exemplo.org"},) if sources else ()
        return LLMResult(content, "google", "m", request.task_type, web_sources=web, web_queries=("q",))

    verdict, _ = check_memory(execute, {"kind": "fato", "text": "O MTTR é 2 h."})
    assert verdict["veredito"] == expected
    assert requests[0].web_search and not requests[0].structured_output
    assert bool(verdict["correcao"]) == (expected == "contradiz")
