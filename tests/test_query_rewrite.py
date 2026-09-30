"""Lote 22: consulta da biblioteca reescrita a partir da conversa, pelo modelo mais barato."""

from __future__ import annotations

import json

import pytest

from aliado.agent import prepare_request
from aliado.knowledge.evaluation import evaluate_search
from aliado.knowledge.rewrite import rewrite_query
from aliado.llm.contracts import LLMResult, LLMUsage
from aliado.llm.providers.base import ProviderError

HISTORY = [{"role": "user", "content": "Traga o conceito de MCC conforme uma literatura."},
           {"role": "assistant", "content": "Segundo Lafraia (2001), a MCC " + "é um processo. " * 100}]
QUESTION = "Traga a definição com base na literatura. Uma citação direta."
QUERY = "definição de Manutenção Centrada na Confiabilidade (MCC); reliability centered maintenance (RCM) definition"


def executor(answer, calls):
    def execute(request):
        calls.append(request)
        return LLMResult("{}", "google", "lite", request.task_type, structured_data=answer,
                         usage=LLMUsage(120, 30, 150))
    return execute


def test_rewrite_uses_recent_conversation_and_returns_the_query():
    calls = []
    query, result = rewrite_query(executor({"consulta": f"  {QUERY}  "}, calls), question=QUESTION,
                                  history=[{"role": "user", "content": "antiga"}] * 3 + HISTORY)
    assert query == QUERY and result.usage.total_tokens == 150
    request = calls[0]
    payload = json.loads(request.messages[1]["content"])
    assert request.task_type == "biblioteca-consulta" and request.structured_output["required"] == ["consulta"]
    assert payload["mensagem"] == QUESTION and len(payload["conversa"]) == 4
    assert payload["conversa"][-2]["texto"].startswith("Traga o conceito de MCC")
    assert len(payload["conversa"][-1]["texto"]) == 700  # respostas longas entram cortadas
    assert "português e em inglês" in request.messages[0]["content"]


@pytest.mark.parametrize("answer", [{}, {"consulta": "   "}, {"consulta": "x" * 401}])
def test_empty_or_long_query_is_refused(answer):
    with pytest.raises(ValueError):
        rewrite_query(executor(answer, []), question=QUESTION)


class Library:
    def __init__(self, empty_for=()):
        self.queries, self.limits, self.empty_for = [], [], set(empty_for)

    def documents(self):
        return [{"title": "manual.pdf", "version": 1, "status": "ready"}]

    def search(self, query, limit=6):
        self.queries.append(query)
        self.limits.append(limit)
        if query in self.empty_for:
            return []
        return [{"citation_id": "K1", "document_id": "d1", "title": "manual.pdf", "version": 1, "sha256": "s",
                 "locator": "página 181", "page": 181, "method": "text", "status": "ready", "text": "MCC é…"}]


def test_the_rewritten_query_drives_the_search_and_falls_back_without_hits():
    library = Library()
    request = prepare_request(QUESTION, library=library, history=HISTORY, search_query=QUERY)
    assert library.queries == [QUERY] and request.metadata["search_query"] == QUERY
    # Mais opções de fontes: 10 trechos no chat, e o pedido de mostrar a opção de cada fonte.
    assert library.limits == [10]
    assert any("opção de cada fonte" in m["content"] for m in request.messages if m["role"] == "developer")
    empty = Library(empty_for={QUERY})
    request = prepare_request(QUESTION, library=empty, history=HISTORY, search_query=QUERY)
    assert empty.queries == [QUERY, QUESTION] and request.metadata["search_query"] == QUESTION
    plain = Library()
    prepare_request(QUESTION, library=plain, history=HISTORY)
    assert plain.queries == [QUESTION]  # sem reescrita, a regra antiga continua


def test_evaluation_can_measure_with_the_rewritten_query():
    library = Library()
    questions = [{"id": "P1", "pergunta": QUESTION, "esperados": ["manual.pdf"], "idioma": "pt",
                  "idioma_documento": "pt", "tipo": "conteudo"}]
    result = evaluate_search(library, questions, rewrite=lambda question: QUERY)
    assert library.queries == [QUERY] and result["detalhe"][0]["consulta"] == QUERY
    assert result["consulta_reescrita"] is True and result["resumo"]["acertos"] == 1
    assert "consulta" not in evaluate_search(Library(), questions)["detalhe"][0]


@pytest.fixture
def web(tmp_path):
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    from aliado.interfaces.web.app import WebSettings, create_app

    calls, rewrites = [], {"error": None, "calls": []}
    (tmp_path / "biblioteca").mkdir()

    def stream(question, **kwargs):
        calls.append(kwargs)
        yield "texto", "Resposta."
        yield "final", LLMResult("Resposta.", "google", "flash", "critical_reasoning", usage=LLMUsage(10, 5, 15),
                                 validation_status="uncited")

    def rewriter(**kwargs):
        rewrites["calls"].append(kwargs)
        if rewrites["error"]:
            raise rewrites["error"]
        return QUERY, LLMResult("{}", "google", "lite", "biblioteca-consulta", usage=LLMUsage(100, 20, 120))

    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765,
                           stream=stream, models=[{"alias": "flash", "model_id": "teste"}],
                           library_factory=Library, query_rewriter=rewriter)
    client = TestClient(create_app(settings), base_url="http://127.0.0.1:8765")
    return {"client": client, "calls": calls, "rewrites": rewrites, "settings": settings}


def ask(client, cid, **extra):
    body = {"texto": QUESTION, "skill": "pesquisa-inversores", "modelo": "flash", "biblioteca": True} | extra
    response = client.post(f"/api/conversas/{cid}/mensagens", json=body, headers={"x-aliado": "1"})
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_chat_rewrites_with_the_library_on_records_usage_and_keeps_the_query(web):
    client = web["client"]
    cid = client.post("/api/conversas", headers={"x-aliado": "1"}).json()["id"]
    events = ask(client, cid)
    fim = next(event for event in events if event["tipo"] == "fim")
    assert web["calls"][-1]["search_query"] == QUERY
    assert web["rewrites"]["calls"][-1]["question"] == QUESTION
    assert fim["mensagens"][-1]["consulta_biblioteca"] == QUERY
    log = web["settings"].usage_log.read_text(encoding="utf-8").splitlines()
    assert [json.loads(entry)["task_type"] for entry in log] == ["biblioteca-consulta", "critical_reasoning"]

    ask(client, cid, biblioteca=False)
    assert len(web["rewrites"]["calls"]) == 1 and web["calls"][-1]["search_query"] is None

    web["rewrites"]["error"] = ProviderError("fora do ar", transient=True)
    events = ask(client, cid)
    assert any(event["tipo"] == "fim" for event in events)  # sem consulta, a resposta segue
    assert web["calls"][-1]["search_query"] is None
