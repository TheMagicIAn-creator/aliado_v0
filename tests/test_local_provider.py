"""Modelo local (lote 38): o adapter do Ollama, a cascata do gateway e o agente, com um cliente falso.

Nada vai à rede: nem Ollama, nem Gemini."""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest

from aliado.agent import Agent
from aliado.llm.contracts import LLMRequest, LLMResult, LLMStreamChunk
from aliado.llm.providers import ModelRegistration, ProviderGateway
from aliado.llm.providers.local import (
    CITE_RULE,
    ESCALATE,
    TEXT_NOTE,
    LocalLimit,
    LocalOutOfReach,
    LocalProvider,
    LocalUnavailable,
)

CLOUD = frozenset({"text", "structured_output", "web_search", "multimodal"})


class Completions:
    """O `client.chat.completions` do SDK: guarda os pedidos e devolve as respostas na ordem."""

    def __init__(self, *replies):
        self.calls, self.replies = [], list(replies)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return iter(reply) if isinstance(reply, list) else reply


def local(*replies):
    completions = Completions(*replies)
    return LocalProvider(client=SimpleNamespace(chat=SimpleNamespace(completions=completions))), completions


def usage():
    return SimpleNamespace(prompt_tokens=30, completion_tokens=5, total_tokens=35)


def answer(content, finish="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)],
                           usage=usage())


def piece(text, finish=None):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text), finish_reason=finish)],
                           usage=None)


def events(*texts, finish="stop"):
    """O fluxo do Ollama: os pedaços, o fim e, por último, o uso."""
    return [*(piece(text) for text in texts), piece("", finish), SimpleNamespace(choices=[], usage=usage())]


def ask(content="Qual a taxa?", **kwargs):
    return LLMRequest(task_type="critical_reasoning", messages=[
        {"role": "developer", "content": "Responda em português."}, {"role": "user", "content": content}], **kwargs)


def parts(*items):
    return LLMRequest(task_type="multimodal_analysis", multimodal=True, messages=[{"role": "user", "content": list(items)}])


def pdf(pages: int) -> bytes:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument.new()
    for _ in range(pages):
        document.new_page(200, 300)
    buffer = io.BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


class Gemini:
    """O Gemini falso: conta as chamadas e responde com o modelo pedido."""

    name, configured = "google", True

    def __init__(self):
        self.calls = []

    def generate(self, request, *, model_id):
        self.calls.append(model_id)
        return LLMResult("Resposta do Gemini.", self.name, model_id, request.task_type)

    def stream(self, request, *, model_id):
        self.calls.append(model_id)
        yield LLMStreamChunk("Resposta do Gemini.", self.name, model_id, request.task_type)


def cascade(*replies, local_model="aliado-local"):
    """O gateway com o Gemini falso e o adapter local de verdade sobre o cliente falso."""
    provider, completions = local(*replies)
    gemini, gateway = Gemini(), ProviderGateway()
    gateway.register_provider("google", gemini)
    gateway.register_provider("ollama", provider)
    gateway.register_model(ModelRegistration("google", "flash_lite", "gemini-lite", capabilities=CLOUD))
    gateway.register_model(ModelRegistration("google", "flash", "gemini-flash", capabilities=CLOUD))
    gateway.register_model(ModelRegistration("ollama", "local", local_model, capabilities=CLOUD - {"web_search"}))
    return gateway, gemini, completions


def test_local_request_has_one_system_with_the_help_rule_and_thinks_unless_the_route_is_light():
    """PRV-01: as instruções vão num `system` só, com o pedido de ajuda no fim; raciocínio baixo desliga o pensar."""
    provider, completions = local(answer("A taxa é 8,9e-6/h."), answer("Outra."))
    result = provider.generate(ask(reasoning_level="low"), model_id="aliado-local")
    sent = completions.calls[0]
    assert [message["role"] for message in sent["messages"]] == ["system", "user"]
    assert sent["messages"][0]["content"].startswith("Responda em português.") and ESCALATE in sent["messages"][0]["content"]
    assert sent["model"] == "aliado-local" and sent["reasoning_effort"] == "none" and sent["max_tokens"] < 16_384
    assert (result.provider, result.content, result.usage.total_tokens) == ("ollama", "A taxa é 8,9e-6/h.", 35)
    provider.generate(ask(), model_id="aliado-local")
    assert "reasoning_effort" not in completions.calls[1]


def test_local_reads_images_and_pdf_pages_as_base64_images():
    """PRV-01: imagem e páginas de PDF vão ao Ollama como imagens em base64, que é o que ele aceita."""
    provider, completions = local(answer("Uma figura."), answer("Duas páginas."))
    provider.generate(parts({"type": "text", "text": "Descreva."},
                            {"type": "image", "mime_type": "image/png", "data": b"\x89PNG falso"}), model_id="m")
    sent = completions.calls[0]["messages"][1]["content"]
    assert sent[0] == {"type": "text", "text": "Descreva."}
    assert sent[1]["image_url"]["url"].startswith("data:image/png;base64,")
    provider.generate(parts({"type": "document", "mime_type": "application/pdf", "data": lambda: pdf(2),
                             "pages": [3, 4]}), model_id="m")
    pages = completions.calls[1]["messages"][1]["content"]
    assert len(pages) == 2 and all(page["image_url"]["url"].startswith("data:image/jpeg;base64,") for page in pages)


def test_pdf_parts_with_their_text_go_as_text_with_the_reading_note_and_the_citation_rule():
    """PRV-06: a parte em PDF que traz o texto das páginas vai como texto, sem abrir o PDF e sem o limite de 4
    páginas; o local recebe a nota da leitura e, com fontes citáveis, a regra de citação."""
    provider, completions = local(answer("A taxa é baixa [Kabc1]."), answer("Oi."))
    pages = "\n\n".join(f"=== [Kabc{number}] página PDF {number} ===\nTexto da página {number}." for number in range(1, 11))
    part = {"type": "document", "mime_type": "application/pdf", "data": lambda: pytest.fail("PDF aberto"),
            "pages": list(range(1, 11)), "text": pages}
    provider.generate(LLMRequest(task_type="critical_reasoning", multimodal=True,
                                 metadata={"citations": [{"citation_id": "Kabc1"}]},
                                 messages=[{"role": "developer", "content": "Regras."},
                                           {"role": "user", "content": [{"type": "text", "text": "Documento."}, part]}]),
                      model_id="m")
    sent = completions.calls[0]["messages"]
    assert sent[1]["content"] == [{"type": "text", "text": "Documento."}, {"type": "text", "text": pages}]
    assert TEXT_NOTE in sent[0]["content"] and CITE_RULE in sent[0]["content"]
    provider.generate(ask(), model_id="m")  # sem documento e sem fontes, nenhuma das duas
    assert TEXT_NOTE not in completions.calls[1]["messages"][0]["content"]
    assert CITE_RULE not in completions.calls[1]["messages"][0]["content"]


def test_the_local_notes_show_no_identifier_to_copy():
    """PRV-06: no lote 45, o local copiou o exemplo [K12ab34p5] e o [K...] das notas em 4 respostas, que foram
    descartadas; as notas não mostram mais nenhum identificador, só pedem o que veio copiado sem mudança."""
    import re

    for note in (TEXT_NOTE, CITE_RULE):
        assert not re.search(r"\[K[^\]]*\]", note)
    assert "sem acrescentar a página" in CITE_RULE


class Response:
    """O fluxo do SDK, que o adapter fecha quando para de ler (lote 46)."""

    def __init__(self, items):
        self.items, self.closed = items, False

    def __iter__(self):
        return iter(self.items)

    def close(self):
        self.closed = True


def test_stopping_the_local_stream_early_closes_the_ollama_response():
    """PRV-02: quando a conversa para de ler o local (a marca não conferiu), o fluxo HTTP é fechado e o Ollama
    deixa de gerar o resto."""
    response = Response(events("x" * 200, " resto", " fim."))
    provider, _ = local(response)
    stream = provider.stream(ask(), model_id="m")
    assert next(stream).content == "x" * 200 and not response.closed
    stream.close()
    assert response.closed


def test_the_light_route_and_page_readings_go_without_reasoning():
    """PRV-07: vão sem raciocínio o pedido de raciocínio baixo (a reescrita da busca e a rota leve do roteador) e,
    desde o lote 48, a leitura de páginas inteiras ou do documento. Os trechos seguem com ele, porque sem raciocínio o
    local deixou de citar no lote 41."""
    provider, completions = local(answer("Leve."), answer("Trechos."), answer("Páginas."))
    citations = [{"citation_id": "Kabc1"}]
    provider.generate(ask(reasoning_level="low"), model_id="m")
    provider.generate(ask(metadata={"citations": citations}), model_id="m")
    provider.generate(ask(metadata={"citations": citations, "reading": {"tokens_estimados": 900}}), model_id="m")
    assert completions.calls[0]["reasoning_effort"] == "none" and completions.calls[2]["reasoning_effort"] == "none"
    assert "reasoning_effort" not in completions.calls[1]


def test_structured_output_goes_as_json_schema_without_the_help_rule():
    provider, completions = local(answer('{"status": "ok"}'))
    result = provider.generate(ask(structured_output={"type": "object"}), model_id="m")
    sent = completions.calls[0]
    assert result.structured_data == {"status": "ok"}
    assert sent["response_format"]["json_schema"]["schema"] == {"type": "object"}
    assert ESCALATE not in sent["messages"][0]["content"]


def test_local_limit_on_help_request_invalid_json_or_empty_answer_but_not_on_a_cut_answer():
    """PRV-02: o local pede ajuda, erra o JSON ou não responde nada; a resposta cortada no teto não é limite."""
    provider, _ = local(answer(f"{ESCALATE}"), answer("não é JSON"), answer(""), answer("", finish="length"))
    with pytest.raises(LocalLimit, match="pediu ajuda"):
        provider.generate(ask(), model_id="m")
    with pytest.raises(LocalLimit, match="inválida"):
        provider.generate(ask(structured_output={"type": "object"}), model_id="m")
    with pytest.raises(LocalLimit, match="nada"):
        provider.generate(ask(), model_id="m")
    assert provider.generate(ask(), model_id="m").truncated


def test_local_stream_holds_the_start_until_it_knows_it_is_not_a_help_request():
    """PRV-02: no fluxo, o pedido de ajuda é reconhecido antes de qualquer pedaço chegar à tela."""
    provider, _ = local(events("[ESC", "ALAR]"), events("[", "K1] A taxa", " é baixa.", finish="length"))
    with pytest.raises(LocalLimit):
        next(provider.stream(ask(), model_id="m"))
    chunks = list(provider.stream(ask(), model_id="m"))
    assert "".join(chunk.content for chunk in chunks) == "[K1] A taxa é baixa."
    assert chunks[-1].usage.total_tokens == 35 and any(chunk.truncated for chunk in chunks)


def test_help_request_after_a_label_still_hands_over():
    """PRV-02: na Etapa 3, o modelo escreveu um rótulo antes do [ESCALAR]; ainda assim ele passa a vez, antes da tela."""
    label = "**Resposta ao usuário:** "
    provider, _ = local(answer(f"{label}{ESCALATE} Não tenho acesso a esses resultados."),
                        events(label, "[ESC", "ALAR] Não tenho acesso a esses resultados."))
    with pytest.raises(LocalLimit, match="pediu ajuda"):
        provider.generate(ask(), model_id="m")
    with pytest.raises(LocalLimit, match="pediu ajuda"):
        next(provider.stream(ask(), model_id="m"))


def test_what_the_local_cannot_take_is_out_of_reach_before_any_call():
    """PRV-03: mais de 4 páginas de PDF, mais que o contexto local ou busca na web: nem chega ao Ollama."""
    provider, completions = local()
    unread = {"type": "document", "mime_type": "application/pdf", "data": lambda: pytest.fail("PDF aberto"),
              "pages": [1, 2, 3, 4, 5]}
    for request, reason in ((parts(unread), "páginas"), (ask("x" * 60_000), "contexto"), (ask(web_search=True), "web")):
        with pytest.raises(LocalOutOfReach, match=reason):
            provider.generate(request, model_id="m")
    assert completions.calls == []


def test_ollama_down_or_model_missing_is_a_clear_error():
    """PRV-04: Ollama fechado ou modelo não baixado: a mensagem diz o que conferir."""
    httpx = pytest.importorskip("httpx")
    openai = pytest.importorskip("openai")
    refused = openai.APIConnectionError(request=httpx.Request("POST", "http://localhost:11434/v1/chat/completions"))
    missing = type("NotFound", (Exception,), {"status_code": 404})()
    provider, _ = local(refused, missing)
    with pytest.raises(LocalUnavailable, match="abra o Ollama"):
        provider.generate(ask(), model_id="m")
    with pytest.raises(LocalUnavailable, match="não foi baixado"):
        list(provider.stream(ask(), model_id="m"))


def test_local_model_answers_first_and_without_it_everything_goes_to_gemini(monkeypatch):
    """PRV-01: ligado, o local responde e o Gemini não é chamado; sem ele ou com local=False, tudo segue como antes."""
    gateway, gemini, _ = cascade(answer("Resposta local."))
    result = gateway.execute(ask(), provider="google", model_alias="flash_lite")
    assert (result.provider, result.content, result.route_reason, gemini.calls) == ("ollama", "Resposta local.", None, [])
    for gateway, gemini, completions, options in ((*cascade(local_model=None), {}), (*cascade(), {"local": False})):
        assert gateway.execute(ask(), provider="google", model_alias="flash_lite", **options).provider == "google"
        assert completions.calls == [] and gemini.calls == ["gemini-lite"]
    from aliado.llm.providers.gateway import build_default_gateway

    monkeypatch.setenv("AL_IADO_LOCAL_MODEL", "aliado-local")
    models = {(model["provider"], model["alias"]): model for model in build_default_gateway().status()["models"]}
    assert models[("ollama", "local")]["configured"] and "web_search" not in models[("ollama", "local")]["capabilities"]


def test_local_limit_escalates_once_to_gemini_flash_and_says_so():
    """PRV-02: no limite do local, responde o Gemini Flash (mesmo com o Flash-Lite pedido), uma vez e marcado."""
    gateway, gemini, _ = cascade(answer(ESCALATE), events(ESCALATE))
    result = gateway.execute(ask(), provider="google", model_alias="flash_lite")
    assert (result.provider, result.model, result.escalation_used) == ("google", "gemini-flash", True)
    assert "pediu ajuda" in result.route_reason and "Gemini Flash respondeu" in result.route_reason
    chunks = list(gateway.stream(ask(), provider="google", model_alias="flash_lite"))
    assert [chunk.provider for chunk in chunks] == ["google"] and chunks[0].fallback_used and chunks[0].route_reason
    assert gemini.calls == ["gemini-flash", "gemini-flash"]


def test_what_the_local_cannot_take_goes_straight_to_the_requested_model():
    """PRV-03: sem escalada, o pedido vai direto ao modelo pedido, e a rota diz por quê."""
    gateway, gemini, completions = cascade()
    result = gateway.execute(ask(web_search=True), provider="google", model_alias="flash_lite")
    assert (result.provider, result.model, result.escalation_used) == ("google", "gemini-lite", False)
    assert "busca na web" in result.route_reason and completions.calls == []
    chunks = list(gateway.stream(ask("x" * 60_000), provider="google", model_alias="flash_lite"))
    assert chunks[0].route_reason.startswith("o modelo local não alcança") and not chunks[0].fallback_used
    assert gemini.calls == ["gemini-lite", "gemini-lite"]


def test_ollama_down_raises_without_calling_gemini():
    """PRV-04: com o Ollama fora do ar, o erro sobe e nada vai ao Gemini."""
    gateway, gemini, _ = cascade(ConnectionError("recusada"), ConnectionError("recusada"))
    with pytest.raises(LocalUnavailable, match="abra o Ollama"):
        gateway.execute(ask(), provider="google", model_alias="flash")
    with pytest.raises(LocalUnavailable):
        list(gateway.stream(ask(), provider="google", model_alias="flash"))
    assert gemini.calls == []


def test_agent_records_who_answered_and_why():
    """A resposta guarda quem respondeu de fato: o local, ou o Gemini com o motivo; `local=False` pula o local."""
    gateway, gemini, _ = cascade(events("Resposta ", "local."), events(ESCALATE))
    agent = Agent(gateway)
    *_, (kind, result) = agent.stream_answer("Oi?", provider="google", model_alias="flash_lite")
    assert (kind, result.provider, result.content) == ("final", "ollama", "Resposta local.")
    *_, (_, result) = agent.stream_answer("Oi?", provider="google", model_alias="flash_lite")
    assert (result.provider, result.escalation_used) == ("google", True) and "Gemini Flash" in result.route_reason
    *_, (_, result) = agent.stream_answer("Oi?", provider="google", model_alias="flash_lite", local=False)
    assert (result.provider, result.route_reason) == ("google", None) and gemini.calls == ["gemini-flash", "gemini-lite"]
