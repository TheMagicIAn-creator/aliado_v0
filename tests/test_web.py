"""Interface local: rotas, proteção, fluxo, conversas, citações e biblioteca, sem rede nem Gemini real."""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("starlette")
from starlette.testclient import TestClient  # noqa: E402

from aliado.interfaces.web.app import WebSettings, create_app  # noqa: E402
from aliado.interfaces.web.conversations import ConversationStore  # noqa: E402
from aliado.interfaces.web.rendering import render_markdown  # noqa: E402
from aliado.llm.contracts import LLMResult, LLMUsage  # noqa: E402
from aliado.llm.providers.base import ProviderError  # noqa: E402
from aliado.memory.store import MemoryStore  # noqa: E402

BASE = "http://127.0.0.1:8765"
HEADERS = {"x-aliado": "1"}
SOURCE = {"citation_id": "Kabc", "document_id": "d1", "title": "Baschel 2018", "version": 1,
          "locator": "página 5", "page": 5, "method": "text", "status": "ready", "text": "IGBT..."}


class FakeLibrary:
    def __init__(self, root: Path):
        self.root = root
        self.added = []
        self.original = root / "original.pdf"
        self.markdown = root / "content.md"

    def documents(self):
        return [{"id": "d1", "title": "Baschel 2018", "version": 1, "status": "partial",
                 "issues": ["OCR na página 2"], "created_at": "2026-09-26T00:00:00+00:00"}]

    def add(self, path, *, title=None, reprocess=False, progress=None):
        assert Path(path).is_file()
        self.added.append((Path(path).read_bytes(), title))
        if progress:
            for step in (("lendo", 1, 2), ("ocr", 2, 2), ("indexando", 0, 7)):
                progress(*step)
        if title == "falhou.pdf" and not reprocess:
            return {"id": "d3", "title": title, "version": 1, "status": "failed", "issues": ["OCR"],
                    "duplicate": True}
        return {"id": "d2", "title": title, "version": 1, "status": "ready", "issues": [],
                "duplicate": False, "chunks": 7}

    def document_files(self, doc_id):
        if doc_id not in {"d1", "d2"}:
            raise ValueError("Documento não encontrado na biblioteca.")
        return {"title": "Baschel 2018", "original": self.original, "markdown": self.markdown}


@pytest.fixture
def env(tmp_path):
    calls = []
    library = FakeLibrary(tmp_path)
    library.original.write_bytes(b"%PDF-1.4 fake")
    library.markdown.write_text("# Baschel\n\nTaxa $\\lambda$ e <b>html</b>", encoding="utf-8")
    (tmp_path / "biblioteca").mkdir()
    (tmp_path / "biblioteca" / "catalog.sqlite3").write_bytes(b"")
    reply = {"pieces": ["A taxa é ", "8,9e-6/h [Kabc]."], "sources": (SOURCE,), "provider": "google",
             "status": "citation_ids_verified", "error": None, "content": None}

    def stream(question, **kwargs):
        calls.append({"question": question, **kwargs})
        if reply["error"]:
            raise reply["error"]
        # Lote 31: acima do teto, o agente devolve a estimativa em vez de chamar o modelo.
        if reply.get("confirm") is not None and kwargs.get("ceiling") is not None \
                and reply["confirm"] > kwargs["ceiling"] and kwargs.get("confirmed") != "chave1":
            yield "confirmar", {"tokens": reply["confirm"], "chave": "chave1", "leitura": None}
            return
        if reply.get("statuses"):
            reply["status"] = reply["statuses"].pop(0)
        for piece in reply["pieces"]:
            yield "texto", piece
        content = reply["content"] or "".join(reply["pieces"])
        web = {"web_sources": ({"uri": "https://exemplo.org/a", "title": "Exemplo", "domain": "exemplo.org"},),
               "web_queries": ("taxa IGBT",)} if kwargs.get("web_search") else {}
        yield "final", LLMResult(content, reply["provider"], "gemini-teste", "critical_reasoning",
                                 usage=LLMUsage(100, 20, 320, 200), sources=reply["sources"],
                                 validation_status=reply["status"], **web, **reply.get("extra", {}))

    memory = MemoryStore(tmp_path / "dados" / "memoria")
    review = {"notes": [{"kind": "preferencia", "text": "Prefiro respostas curtas.", "origin": "feedback",
                         "source": {}, "supersedes": None, "diverges_skill": False}],
              "calls": [], "error": None}

    def reviewer(**kwargs):
        review["calls"].append(kwargs)
        if review["error"]:
            raise review["error"]
        return review["notes"], LLMResult("{}", "google", "lite", "memoria-revisor", usage=LLMUsage(10, 5, 15))

    def card_maker(**kwargs):
        review["calls"].append(kwargs)
        return ([{"kind": "fato", "text": "Reparo de duas horas.", "origin": "inferido",
                  "source": {"document_id": kwargs["document_id"], "title": kwargs["title"], "page": 1,
                             "ficha": True}}],
                LLMResult("{}", "google", "lite", "memoria-ficha", usage=LLMUsage(40, 10, 50)))

    verdict = {"veredito": "contradiz", "correcao": "Correção vinda da web.", "explicacao": "Fontes dizem outra coisa.",
               "fontes": [{"uri": "https://exemplo.org/a", "title": "Exemplo", "domain": "exemplo.org"}]}

    def checker(memory_):
        review["calls"].append({"conferir": memory_["id"]})
        return dict(verdict), LLMResult("x", "google", "lite", "memoria-conferencia", usage=LLMUsage(5, 5, 10),
                                        web_sources=tuple(verdict["fontes"]), web_queries=("q",))

    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765,
                           stream=stream, models=[{"alias": "flash", "model_id": "gemini-teste"}],
                           library_factory=lambda: library, memory=memory, reviewer=reviewer,
                           card_maker=card_maker, checker=checker)
    client = TestClient(create_app(settings), base_url=BASE)
    return {"client": client, "calls": calls, "reply": reply, "library": library,
            "settings": settings, "tmp": tmp_path, "memory": memory, "review": review, "verdict": verdict}


def new_conversation(client) -> str:
    return client.post("/api/conversas", headers=HEADERS).json()["id"]


def ask(client, cid, text="Qual a taxa?", **extra):
    """Envia a pergunta; devolve a resposta e os eventos do fluxo (vazio em erros de validação)."""
    body = {"texto": text, "skill": "pesquisa-inversores", "modelo": "flash", "biblioteca": True} | extra
    response = client.post(f"/api/conversas/{cid}/mensagens", json=body, headers=HEADERS)
    events = []
    if response.headers.get("content-type", "").startswith("application/x-ndjson"):
        events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    return response, events


def fim(events):
    return next(e for e in events if e["tipo"] == "fim")


def test_page_and_static_files_are_served_with_protective_headers(env):
    client = env["client"]
    page = client.get("/")
    assert page.status_code == 200 and "AL-IAdo" in page.text
    assert 'id="font"' in page.text  # fonte do texto na barra do topo (lote 22)
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert page.headers["x-content-type-options"] == "nosniff"
    for path in ("/static/app.js", "/static/app.css", "/static/vendor/katex/katex.min.js"):
        assert client.get(path).status_code == 200


def test_foreign_host_and_cross_site_mutations_are_refused(env):
    client = env["client"]
    assert client.get("/api/estado", headers={"host": "evil.example:8765"}).status_code == 403
    assert client.post("/api/conversas").status_code == 403
    assert client.post("/api/conversas", headers={**HEADERS, "origin": "http://evil.example"}).status_code == 403
    assert client.post("/api/conversas", headers={**HEADERS, "origin": BASE}).status_code == 201


def test_state_lists_skills_models_library_and_usage(env):
    data = env["client"].get("/api/estado").json()
    assert {"pesquisa-inversores", "engenharia", "confiabilidade"} <= {s["name"] for s in data["skills"]}
    assert data["modelos"] == [{"alias": "flash", "model_id": "gemini-teste"}]
    assert data["biblioteca"]["documentos"] == 1
    assert data["uso"] == {"hoje": 0, "total": 0, "chamadas": 0}


def test_answer_streams_text_before_final_message(env):
    cid = new_conversation(env["client"])
    response, events = ask(env["client"], cid)
    assert response.status_code == 200
    assert [e["tipo"] for e in events] == ["texto", "texto", "fim", "memoria"]
    assert "".join(e["texto"] for e in events[:2]) == "A taxa é 8,9e-6/h [Kabc]."
    assert response.headers["cache-control"] == "no-store"


def test_conversation_keeps_history_citations_and_usage_without_text(env):
    client, calls = env["client"], env["calls"]
    cid = new_conversation(client)
    user, reply = fim(ask(client, cid)[1])["mensagens"]
    assert user["content"] == "Qual a taxa?"
    assert 'class="cite" data-cite="1"' in reply["html"]
    assert reply["sources"][0]["document_id"] == "d1"
    assert reply["usage"]["reasoning_tokens"] == 200
    assert calls[0]["history"] == [] and calls[0]["library"] is env["library"]
    assert calls[0]["skill_name"] == "pesquisa-inversores" and calls[0]["model_alias"] == "flash"
    ask(client, cid, "E em 20 anos?", biblioteca=False)
    assert [m["role"] for m in calls[1]["history"]] == ["user", "assistant"]
    assert calls[1]["library"] is None
    listed = client.get("/api/conversas").json()
    assert listed[0]["title"] == "Qual a taxa?" and listed[0]["messages"] == 4
    log = [json.loads(line) for line in env["settings"].usage_log.read_text(encoding="utf-8").splitlines()]
    assert [e["task_type"] for e in log] == ["critical_reasoning", "memoria-revisor"] * 2
    assert "taxa" not in json.dumps(log) and log[0]["reasoning_tokens"] == 200
    assert client.get("/api/estado").json()["uso"]["total"] == 670
    stored = client.get(f"/api/conversas/{cid}").json()
    assert stored["messages"][1]["html"] == reply["html"]


def test_model_html_is_escaped_and_math_preserved(env):
    env["reply"].update(pieces=["<script>alert(1)</script> custo R$ 5,00 e $\\lambda t$ [Kzzz]"], sources=())
    cid = new_conversation(env["client"])
    html = fim(ask(env["client"], cid)[1])["mensagens"][1]["html"]
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "$\\lambda t$" in html and "R$ 5,00" in html and "[Kzzz]" in html


def test_local_answers_stay_out_of_model_history(env):
    client, calls = env["client"], env["calls"]
    env["reply"].update(provider="local", status="insufficient_evidence", sources=(), pieces=[],
                        content="Não encontrei trechos suficientes.")
    cid = new_conversation(client)
    assert [e["tipo"] for e in ask(client, cid)[1]] == ["fim"]
    env["reply"].update(provider="google", status=None, pieces=["ok"], content=None)
    ask(client, cid, "Outra pergunta", biblioteca=False)
    assert calls[1]["history"] == []
    assert len(env["settings"].usage_log.read_text(encoding="utf-8").splitlines()) == 2  # resposta + revisor


@pytest.mark.parametrize("change,status", [
    ({"texto": " "}, 400), ({"skill": "desconhecida"}, 400), ({"apoio": "desconhecida"}, 400),
    ({"modelo": "sol"}, 400), ({"texto": "x" * 20_001}, 400),
])
def test_invalid_messages_are_rejected_without_calling_the_model(env, change, status):
    cid = new_conversation(env["client"])
    assert ask(env["client"], cid, **change)[0].status_code == status
    assert env["calls"] == []


def test_unknown_or_malformed_conversation_ids_are_not_found(env):
    client = env["client"]
    assert client.get("/api/conversas/" + "0" * 32).status_code == 404
    assert client.get("/api/conversas/..%2F..%2Fsegredo").status_code == 404
    assert ask(client, "../../x")[0].status_code == 404


def test_provider_errors_do_not_leak_details_or_store_messages(env):
    client = env["client"]
    env["reply"]["error"] = ProviderError("token=segredo-que-nao-pode-aparecer")
    cid = new_conversation(client)
    response, events = ask(client, cid)
    assert events == [{"tipo": "erro", "erro": "O Gemini não respondeu. Tente de novo em instantes."}]
    assert "segredo" not in response.text
    assert client.get(f"/api/conversas/{cid}").json()["messages"] == []


def test_deleted_conversation_goes_to_local_trash(env):
    client = env["client"]
    cid = new_conversation(client)
    ask(client, cid)
    assert client.delete(f"/api/conversas/{cid}").status_code == 403  # sem o cabeçalho próprio
    assert client.delete(f"/api/conversas/{cid}", headers=HEADERS).json() == {"apagada": True}
    assert client.get(f"/api/conversas/{cid}").status_code == 404
    assert client.get("/api/conversas").json() == []
    trashed = json.loads((env["settings"].data_dir / "conversas" / "lixeira" / f"{cid}.json").read_text(encoding="utf-8"))
    assert trashed["deleted_at"] and len(trashed["messages"]) == 2
    assert client.delete(f"/api/conversas/{cid}", headers=HEADERS).status_code == 404


def upload(client, name, content=b"%PDF-1.4 conteudo"):
    response = client.post("/api/biblioteca", headers=HEADERS, files={"arquivo": (name, content, "application/pdf")})
    assert response.status_code == 202
    job = response.json()["tarefa"]
    for _ in range(50):
        status = client.get(f"/api/biblioteca/tarefas/{job}").json()
        if status["estado"] in {"concluido", "falhou"}:
            return status
        time.sleep(0.05)
    raise AssertionError("Tarefa não terminou")


def test_upload_reports_progress_and_removes_temporary_copy(env):
    client, library = env["client"], env["library"]
    status = upload(client, "Sarquis 2020.pdf")
    assert status["estado"] == "concluido" and status["resultado"]["trechos"] == 7
    assert status["etapa"] == "ficha" and status["resultado"]["fichas"] == 1
    assert library.added == [(b"%PDF-1.4 conteudo", "Sarquis 2020.pdf")]
    retried = upload(client, "falhou.pdf")
    assert retried["resultado"]["status"] == "ready" and len(library.added) == 3
    assert not any((env["settings"].data_dir / "uploads-temporarios").iterdir())
    refused = client.post("/api/biblioteca", headers=HEADERS, files={"arquivo": ("script.exe", b"MZ", "application/octet-stream")})
    assert refused.status_code == 400
    assert client.post("/api/biblioteca", files={"arquivo": ("a.pdf", b"x", "application/pdf")}).status_code == 403


def test_memory_is_used_learned_and_survives_conversation_deletion(env):
    client, memory, review = env["client"], env["memory"], env["review"]
    cid = new_conversation(client)
    events = ask(client, cid, "Responda curto, por favor.")[1]
    learned = events[-1]
    assert learned["tipo"] == "memoria" and learned["criadas"][0]["kind"] == "preferencia"
    note = memory.list()[0]
    assert note["origin"] == "feedback" and note["source"]["conversation_id"] == cid
    assert note["source"]["trecho"] == "Responda curto, por favor."
    stored = client.get(f"/api/conversas/{cid}").json()["messages"][1]
    assert stored["memorias_criadas"][0]["id"] == note["id"]
    assert review["calls"][0]["skill"] == "pesquisa-inversores" and review["calls"][0]["skill_text"]
    review["notes"] = []
    second = new_conversation(client)
    ask(client, second, "Outra pergunta")
    assert [m["id"] for m in env["calls"][-1]["memories"]] == [note["id"]]  # usada na conversa nova
    assert fim(ask(client, second, "E agora?")[1])["mensagens"][1]["memorias_usadas"][0]["id"] == note["id"]
    client.delete(f"/api/conversas/{cid}", headers=HEADERS)
    assert memory.get(note["id"])["status"] == "ativa"  # apagar a conversa não apaga a memória


def test_explicit_request_and_reviewer_failure(env):
    client, review = env["client"], env["review"]
    cid = new_conversation(client)
    ask(client, cid, "Lembre-se de que prefiro tabelas.")
    assert review["calls"][-1]["explicit"] is True
    review["error"] = ProviderError("chave=segredo")
    events = ask(client, cid, "Outra")[1]
    assert fim(events)["mensagens"][1]["content"]  # a resposta vale mesmo se o revisor falhar
    assert events[-1] == {"tipo": "memoria", "criadas": [], "aviso": "O revisor de memória não respondeu."}


def test_memory_routes_list_create_revoke_edit_and_resolve(env):
    client, memory = env["client"], env["memory"]
    assert client.post("/api/memoria", json={"texto": "x", "tipo": "fato"}).status_code == 403
    assert client.post("/api/memoria", headers=HEADERS, json={"texto": "x", "tipo": "outro"}).status_code == 400
    created = client.post("/api/memoria", headers=HEADERS,
                          json={"texto": "IGBT usa 8,9e-6/h.", "tipo": "decisao", "skill": "pesquisa-inversores"})
    assert created.status_code == 201 and created.json()["origin"] == "comando"
    mid = created.json()["id"]
    guess = memory.add(kind="decisao", text="IGBT usa 16,6e-6/h.", origin="inferido", supersedes=mid)
    listed = client.get("/api/memoria").json()
    assert listed["contagem"]["conflito"] == 1 and listed["contagem"]["ativa"] == 1
    assert client.get("/api/memoria?estado=conflito").json()["itens"][0]["id"] == guess["id"]
    assert client.post(f"/api/memoria/{guess['id']}/manter", headers=HEADERS).json()["status"] == "revogada"
    edited = client.post(f"/api/memoria/{mid}/editar", headers=HEADERS, json={"texto": "IGBT usa 8,90e-6/h."}).json()
    assert edited["origin"] == "feedback" and edited["supersedes"] == mid
    chain = client.get(f"/api/memoria/{edited['id']}/historico").json()
    assert [m["id"] for m in chain] == [mid, edited["id"]]
    assert client.post(f"/api/memoria/{edited['id']}/revogar", headers=HEADERS).json()["status"] == "revogada"
    assert client.post(f"/api/memoria/{edited['id']}/apagar", headers=HEADERS).status_code == 404
    assert client.post("/api/memoria/" + "0" * 32 + "/revogar", headers=HEADERS).status_code == 404


def test_document_markdown_and_original_are_served_safely(env):
    client = env["client"]
    listed = client.get("/api/biblioteca").json()
    assert listed[0]["status"] == "partial" and listed[0]["issues"] == ["OCR na página 2"]
    markdown = client.get("/api/biblioteca/d1/markdown").json()
    assert markdown["titulo"] == "Baschel 2018" and "&lt;b&gt;" in markdown["html"]
    original = client.get("/api/biblioteca/d1/original")
    assert original.status_code == 200 and original.content == b"%PDF-1.4 fake"
    assert original.headers["content-type"] == "application/pdf"
    assert client.get("/api/biblioteca/zz/markdown").status_code == 404
    assert client.get("/api/biblioteca/d1/segredo").status_code == 404


def test_conversation_store_renames_deletes_and_writes_atomically(tmp_path):
    store = ConversationStore(tmp_path)
    data = store.create()
    store.append(data["id"], {"role": "user", "content": "  Primeira   pergunta  "},
                 {"role": "assistant", "content": "Resposta", "in_context": True})
    assert store.get(data["id"])["title"] == "Primeira pergunta"
    assert store.rename(data["id"], "Taxas")["title"] == "Taxas"
    assert not list(tmp_path.glob("*.tmp"))
    with pytest.raises(ValueError):
        store.rename(data["id"], " ")
    with pytest.raises(ValueError):
        store.get("../fora")
    store.delete(data["id"])
    assert store.list() == [] and (tmp_path / "lixeira" / f"{data['id']}.json").is_file()


def test_rendering_numbers_only_known_citations():
    html = render_markdown("Uma [Kb] e outra [Ka] e [Kx].", [{"citation_id": "Ka"}, {"citation_id": "Kb"}])
    assert html.index('data-cite="2"') < html.index('data-cite="1"')  # número pela ordem das fontes
    assert 'aria-label="Fonte 2">2</button>' in html and "[Kx]" in html


def test_cli_web_rejects_invalid_port_without_starting(capsys):
    from aliado.cli import main

    assert main(["web", "--porta", "80", "--sem-navegador"]) == 2
    assert "Porta" in capsys.readouterr().err


def test_web_switch_reaches_agent_and_web_sources_render(env):
    client = env["client"]
    env["reply"].update(pieces=["A taxa é constante.[W1] E o PDF diz 8,9e-6/h [Kabc]."])
    cid = new_conversation(client)
    reply = fim(ask(client, cid, web=True)[1])["mensagens"][1]
    assert env["calls"][-1]["web_search"] is True
    assert reply["web_sources"][0]["uri"] == "https://exemplo.org/a" and reply["web_queries"] == ["taxa IGBT"]
    assert 'class="cite cite-web" data-web="1"' in reply["html"] and 'data-cite="1"' in reply["html"]
    assert env["review"]["calls"][-1]["sources"][-1] == {"citation_id": "W1", "title": "Exemplo",
                                                       "url": "https://exemplo.org/a", "text": ""}
    ask(client, cid, "Sem web")
    assert env["calls"][-1]["web_search"] is False


def test_check_route_corrects_inference_and_opens_conflict_for_user_note(env):
    client, memory = env["client"], env["memory"]
    guess = memory.add(kind="fato", text="MTTR de 2 h.", origin="inferido")
    corrected = client.post(f"/api/memoria/{guess['id']}/conferir", headers=HEADERS).json()
    assert corrected["veredito"] == "contradiz" and corrected["buscas"] == 1
    assert corrected["criada"]["status"] == "ativa" and memory.get(guess["id"])["status"] == "superada"
    assert corrected["criada"]["source"]["url"] == "https://exemplo.org/a"
    mine = memory.add(kind="decisao", text="Usar MTTR de 4 h.", origin="feedback")
    conflict = client.post(f"/api/memoria/{mine['id']}/conferir", headers=HEADERS).json()
    assert conflict["criada"]["status"] == "conflito" and memory.get(mine["id"])["status"] == "ativa"
    env["verdict"].update(veredito="confirma", correcao="")
    confirmed = client.post(f"/api/memoria/{mine['id']}/conferir", headers=HEADERS).json()
    assert confirmed["criada"] is None
    assert client.post(f"/api/memoria/{guess['id']}/conferir", headers=HEADERS).status_code == 400  # superada
    assert client.post(f"/api/memoria/{mine['id']}/conferir").status_code == 403
    log = env["settings"].usage_log.read_text(encoding="utf-8")
    assert '"task_type": "memoria-conferencia"' in log and '"web_queries": 1' in log


class WordEncoder:
    """Vetores por grupos de palavras, para testar a memória de conversas sem o modelo local."""

    groups = (("igbt",), ("reparo", "mttr"), ("nome", "rodolfo"))

    def encode(self, texts):
        return [[1.0 if any(w in t.lower() for w in g) else 0.0 for g in self.groups] + [0.01] for t in texts]


def test_conversation_memory_is_recalled_in_new_conversations_and_forgotten_on_delete(env):
    client, calls, memory = env["client"], env["calls"], env["memory"]
    memory.encoder = WordEncoder()
    first = new_conversation(client)
    ask(client, first, "Qual a taxa do IGBT?", biblioteca=False)
    assert memory.exchange_count() == 1
    second = new_conversation(client)
    _, events = ask(client, second, "E o IGBT, qual era mesmo?", biblioteca=False)
    assert [item["conversation_id"] for item in calls[-1]["recalled"]] == [first]
    assert fim(events)["mensagens"][-1]["conversas_lembradas"][0]["conversation_id"] == first
    ask(client, second, "Mais sobre o IGBT?", biblioteca=False)
    assert all(item["conversation_id"] != second for item in calls[-1]["recalled"])  # já está no histórico
    assert client.delete(f"/api/conversas/{first}", headers=HEADERS).status_code == 200
    ask(client, second, "IGBT de novo?", biblioteca=False)
    assert calls[-1]["recalled"] == []


def test_existing_conversations_are_indexed_once(env):
    from aliado.interfaces.web.app import _index_conversations
    from aliado.interfaces.web.conversations import ConversationStore

    env["memory"].encoder = WordEncoder()
    client = env["client"]
    ask(client, new_conversation(client), "Taxa do IGBT?", biblioteca=False)
    store = ConversationStore(env["tmp"] / "dados" / "conversas")
    assert _index_conversations(store, env["memory"]) == 0  # guardada na hora da resposta
    fresh = MemoryStore(env["tmp"] / "outra", encoder=WordEncoder())
    assert _index_conversations(store, fresh) == 1 and _index_conversations(store, fresh) == 0


def test_uncited_reply_is_shown_and_kept_in_context(env):
    client, reply = env["client"], env["reply"]
    reply.update(status="uncited", sources=())
    cid = new_conversation(client)
    ask(client, cid)
    last = client.get(f"/api/conversas/{cid}").json()["messages"][-1]
    assert last["validation_status"] == "uncited" and last["in_context"] is True


def test_page_and_static_files_are_revalidated_after_updates(env):
    client = env["client"]
    for path in ("/", "/static/app.js", "/static/app.css"):
        assert client.get(path).headers["cache-control"] == "no-cache", path



RESULT_BLOCK = {"citation_id": "R1", "titulo": "Avaliação oficial", "fonte": "Avaliação oficial de 27/09/2026",
                "data": "2026-09-27", "estatuto": "oficial", "secao": "resumo", "texto": "| Denso | 10 de 14 |\n|---|---|",
                "notas": [{"nome": "Ensaios detectados", "texto": "Ensaios com alarme a partir do início da falha."}]}
RESULTS_DIGEST = {"cabecalho": "c", "blocos": [RESULT_BLOCK], "faltando": ["a reanálise com o início observado das falhas"]}
# Lote 31: os resultados só seguem quando a pergunta é sobre eles.
RESULTS_QUESTION = "Quais foram os nossos resultados no GPVS?"


def test_results_switch_reaches_the_agent_and_defaults_to_the_research_skill(env):
    client, built = env["client"], []
    env["settings"].results_digest = lambda: built.append(1) or RESULTS_DIGEST
    state = client.get("/api/estado").json()["resultados"]
    assert state == {"disponivel": True, "skill": "pesquisa-inversores"} and not built  # o estado não monta o resumo
    cid = new_conversation(client)
    ask(client, cid, RESULTS_QUESTION, resultados=True)
    assert env["calls"][-1]["results"] is RESULTS_DIGEST and len(built) == 1
    ask(client, cid, RESULTS_QUESTION)  # sem o campo, vale ligado na skill do mestrado
    assert env["calls"][-1]["results"] is RESULTS_DIGEST
    ask(client, cid, RESULTS_QUESTION, skill="engenharia")
    assert "results" not in env["calls"][-1]
    ask(client, cid, RESULTS_QUESTION, resultados=False)
    assert "results" not in env["calls"][-1]
    # Lote 31: ligado, o resumo só segue quando a pergunta é sobre os resultados.
    ask(client, cid, "Obrigado, ficou claro.", resultados=True)
    assert "results" not in env["calls"][-1] and len(built) == 2
    stored = client.get(f"/api/conversas/{cid}").json()["messages"]
    assert [m["resultados"] for m in stored if m["role"] == "user"] == [True, True, False, False, True]


def test_cited_results_are_stored_rendered_and_unverified_numbers_leave_the_history(env):
    client = env["client"]
    env["settings"].results_digest = lambda: RESULTS_DIGEST
    env["reply"].update(pieces=["O Denso detectou 10 de 14 [R1]."], sources=(), status=None,
                        extra={"result_sources": (RESULT_BLOCK,), "results_status": "conferido"})
    cid = new_conversation(client)
    reply = fim(ask(client, cid, RESULTS_QUESTION)[1])["mensagens"][1]
    assert 'class="cite cite-result" data-result="R1"' in reply["html"] and reply["results_status"] == "conferido"
    assert reply["result_sources"][0]["citation_id"] == "R1" and "<table>" in reply["result_sources"][0]["html"]
    assert reply["resultados_faltando"] == RESULTS_DIGEST["faltando"] and reply["in_context"] is True
    assert reply["result_sources"][0]["notas"][0]["nome"] == "Ensaios detectados" and reply["numeros_sem_marca"] == 0
    assert all("R1" not in str(source) for source in env["review"]["calls"][-1]["sources"])  # o revisor não recebe os blocos
    env["reply"].update(pieces=["A sensibilidade é 0,45 [R1]."],
                        extra={"result_sources": (RESULT_BLOCK,), "results_status": "numeros_nao_conferidos",
                               "unverified_numbers": ("0,45",)})
    flagged = fim(ask(client, cid, "E a sensibilidade?")[1])["mensagens"]
    assert [m["in_context"] for m in flagged] == [False, False] and flagged[1]["numeros_nao_conferidos"] == ["0,45"]
    ask(client, cid, "Continue")
    assert [m["content"] for m in env["calls"][-1]["history"]] == [RESULTS_QUESTION, "O Denso detectou 10 de 14 [R1]."]
    env["reply"].update(pieces=["Aviso local."], status="invalid_result_refs", extra={"results_status": "invalid_result_refs"})
    assert fim(ask(client, cid, "De novo")[1])["mensagens"][1]["in_context"] is False


def test_a_failing_digest_does_not_break_the_conversation(env):
    client = env["client"]

    cid = new_conversation(client)
    for error in (OSError("disco"), TypeError("float() de None"), ZeroDivisionError()):
        def broken(error=error):
            raise error

        env["settings"].results_digest = broken
        reply = fim(ask(client, cid, RESULTS_QUESTION)[1])["mensagens"][1]
        assert "results" not in env["calls"][-1] and "não foi possível" in reply["resultados_faltando"][0]
    env["settings"].results_digest = lambda: {"cabecalho": "c", "blocos": [], "faltando": ["tudo"]}
    reply = fim(ask(client, cid, RESULTS_QUESTION)[1])["mensagens"][1]
    assert "results" not in env["calls"][-1] and reply["resultados_faltando"] == ["tudo"]
    env["settings"].results_digest = None
    assert client.get("/api/estado").json()["resultados"]["disponivel"] is False
    assert fim(ask(client, cid)[1])["mensagens"][1]["resultados_faltando"] == []


def wait_job(client, job, until=lambda status: status["estado"] in {"concluido", "falhou"}):
    for _ in range(100):
        status = client.get(f"/api/biblioteca/tarefas/{job}").json()
        if until(status):
            return status
        time.sleep(0.05)
    raise AssertionError("A tarefa não chegou ao estado esperado")


def post_file(client, name, batch=None):
    response = client.post("/api/biblioteca", headers=HEADERS, data={"lote": batch} if batch else None,
                           files={"arquivo": (name, b"%PDF-1.4 conteudo", "application/pdf")})
    assert response.status_code == 202
    return response.json()["tarefa"]


def test_document_is_marked_ready_before_its_cards(env):
    client, settings, library = env["client"], env["settings"], env["library"]
    release, maker = threading.Event(), settings.card_maker

    def slow_maker(**kwargs):
        release.wait(5)
        return maker(**kwargs)

    settings.card_maker = slow_maker
    job = post_file(client, "Sarquis 2020.pdf")
    ready = wait_job(client, job, lambda status: status.get("indexado"))
    # Já pode ser buscado e citado: pronto para a tela, com as fichas ainda por fazer.
    assert ready["estado"] == "processando" and ready["resultado"]["trechos"] == 7
    assert "fichas" not in ready["resultado"]
    release.set()
    done = wait_job(client, job)
    assert done["estado"] == "concluido" and done["indexado"] is True and done["resultado"]["fichas"] == 1
    # Extração que falhou: termina sem ficar pronta e sem pedir fichas.
    cards = len(env["review"]["calls"])
    library.add = lambda path, **kwargs: {"id": "d9", "title": kwargs["title"], "version": 1, "status": "failed",
                                          "issues": ["PDF sem texto."], "duplicate": False, "chunks": 0}
    failed = wait_job(client, post_file(client, "vazio.pdf"))
    assert failed["estado"] == "concluido" and failed["indexado"] is False
    assert failed["resultado"]["status"] == "failed" and len(env["review"]["calls"]) == cards


def test_queued_uploads_are_indexed_before_the_cards(env):
    client, settings, library = env["client"], env["settings"], env["library"]
    order, release = [], threading.Event()
    add, maker = library.add, settings.card_maker

    def slow_add(path, **kwargs):
        release.wait(5)
        order.append(("indexa", kwargs["title"]))
        return add(path, **kwargs)

    def noting_maker(**kwargs):
        order.append(("ficha", kwargs["title"]))
        return maker(**kwargs)

    library.add, settings.card_maker = slow_add, noting_maker
    jobs = [post_file(client, name, "abcdef0123456789") for name in ("a.pdf", "b.pdf")]
    release.set()
    for job in jobs:
        assert wait_job(client, job)["resultado"]["fichas"] == 1
    # As fichas chamam o modelo: só vêm depois de todos os arquivos enviados estarem indexados.
    assert order == [("indexa", "a.pdf"), ("indexa", "b.pdf"), ("ficha", "a.pdf"), ("ficha", "b.pdf")]


def test_upload_jobs_route_lists_only_the_current_batch(env):
    client, settings = env["client"], env["settings"]
    assert client.get("/api/biblioteca/tarefas").json() == {"lote": None, "tarefas": []}
    first = [post_file(client, name, "0123456789abcdef") for name in ("a.pdf", "b.pdf")]
    for job in first:
        wait_job(client, job)
    settings.jobs["ciencia"] = {"estado": "processando", "etapa": "treino"}  # tarefa de outra aba: fica de fora
    listing = client.get("/api/biblioteca/tarefas").json()
    assert listing["lote"] == "0123456789abcdef" and [job["id"] for job in listing["tarefas"]] == first
    assert [job["arquivo"] for job in listing["tarefas"]] == ["a.pdf", "b.pdf"]
    assert all(job["estado"] == "concluido" and job["indexado"] for job in listing["tarefas"])
    assert "uploads-temporarios" not in json.dumps(listing)  # nenhum caminho do computador
    other = post_file(client, "c.pdf", "../../etc")  # lote inválido: o servidor cria o dele
    wait_job(client, other)
    listing = client.get("/api/biblioteca/tarefas").json()
    assert [job["id"] for job in listing["tarefas"]] == [other] and re.fullmatch(r"[0-9a-f]{32}", listing["lote"])


def test_job_fails_instead_of_hanging_on_an_unexpected_error(env):
    client, library = env["client"], env["library"]

    def broken(path, **kwargs):
        raise KeyError("campo que faltou")  # fora dos erros previstos para a leitura do documento

    library.add = broken
    done = wait_job(client, post_file(client, "estranho.pdf"))
    assert done["estado"] == "falhou" and "Erro inesperado" in done["erro"] and "KeyError" not in done["erro"]
    assert not any((env["settings"].data_dir / "uploads-temporarios").iterdir())


def test_job_ends_when_the_cards_fail_unexpectedly(env):
    client, settings = env["client"], env["settings"]

    def broken(**kwargs):
        raise RuntimeError("falha fora das previstas para a ficha")

    settings.card_maker = broken
    done = wait_job(client, post_file(client, "Sarquis 2020.pdf"))
    # A tarefa presa em "processando" bloquearia o apagar de documentos até reiniciar.
    assert done["estado"] == "concluido" and done["resultado"]["trechos"] == 7
    assert "não pôde ser criada" in done["resultado"]["aviso_ficha"]


def test_complete_cards_does_not_pay_twice_for_a_card_made_meanwhile(env):
    client, settings, library = env["client"], env["settings"], env["library"]
    calls, pending = [], iter([["Baschel 2018"]])
    settings.card_extractor = lambda **kwargs: calls.append(kwargs["title"])
    # Na hora do clique falta a ficha; quando a tarefa roda, um envio já a criou.
    library.titles_without_card = lambda: next(pending, [])
    job = client.post("/api/biblioteca/fichas", headers=HEADERS).json()
    assert job["total"] == 1
    assert wait_job(client, job["tarefa"])["resultado"] == {"fichas": 0, "sem_dados": 0, "falhas": 0} and calls == []


def test_reply_stores_what_the_search_brought_and_the_answer_did_not_cite(env):
    client = env["client"]
    other = SOURCE | {"citation_id": "Kxyz", "title": "IEEE 493", "page": 134, "passagem": "RCM is a logical framework."}
    env["reply"].update(extra={"retrieved": (other,)})
    cid = new_conversation(client)
    reply = fim(ask(client, cid)[1])["mensagens"][1]
    assert [source["citation_id"] for source in reply["sources"]] == ["Kabc"] and reply["recuperados"] == [other]
    stored = client.get(f"/api/conversas/{cid}").json()["messages"][1]
    assert stored["recuperados"][0]["passagem"] == "RCM is a logical framework."


def test_page_starts_on_the_welcome_screen_and_has_the_upload_popup(env):
    client = env["client"]
    # O fim de linha do arquivo depende do sistema: as travas de mais de uma linha valem nos dois.
    page, script = client.get("/").text, client.get("/static/app.js").text.replace("\r\n", "\n")
    assert 'id="upload-pop"' in page and 'id="uploads"' not in page and 'id="upload-status" role="status"' in page
    # A última conversa não fica mais guardada no navegador: abrir ou recarregar cai na apresentação.
    assert "aliado.conversation" not in script and "restoreUploads()" in script
    assert "/api/biblioteca/tarefas" in script and "showChat(); uploadFiles" not in script
    assert "A busca também trouxe" in script and "documentos que a busca trouxe" in script
    # A janela de fontes: a passagem ampliada nos dois grupos, o link só quando sobrou documento sem citar, o
    # grupo dos não citados, e o texto dos documentos sempre como texto (nunca como HTML).
    assert script.count("text: flowText(source.passagem || source.text)") == 2
    assert "if (brought.size > cited.size && !read.length) {" in script and "if (retrieved.length) {" in script
    assert script.count("innerHTML") == 2  # só HTML gerado no servidor: a resposta e a tabela do resultado
    # O reenvio de um documento que já estava na biblioteca, indexado em parte, diz isso em vez da contagem.
    assert "já estava na biblioteca, indexado só em parte" in script and "message.cortada" in script
    # Uma trava por correção da tela (a suíte não roda o JavaScript): se alguma sair, o teste acusa.
    for pinned in (
        "const UPLOAD_PARALLEL = 3;",
        "uploads.hidden = false;\n  uploads.minimized = false;",
        'uploadStatus(item) === "andamento") || items.find((item) => !uploadIndexed(item))',
        '" · com falha"',
        "const noCards = items.filter(cardWarning).length;",
        "uploads.earlier = kept;",
        "if (key !== uploads.issuesKey) {",
        "if (inside) focusAfterUploads();",
        'statuses[0] === "parcial" ? cardNotes(',
        'title.classList.toggle("is-summary", !single || failed > 0);',
        "error instanceof TypeError",
        "if (response.status === 404) return null;",
        "catch { continue; }",
        "item.messages || item.id === state.conversation?.id",
        '{ kind: "retrieved" }',
        'focus?.kind === "retrieved"',
        "O que a busca na biblioteca trouxe",
        'class: "source-peek"',
        'count === 1 ? "1 trecho"',
        "renderMemoryPanel(message);\n            }",
        '.replace(/([^\\n])\\n(?!\\n)/g, "$1 ")',
        '["ficha", "ficha do documento"].includes(item.job?.etapa)) || pending[0]',
    ):
        assert pinned in script, pinned
    assert script.count("raiseUploads();") == 3
    styles = client.get("/static/app.css").text
    assert ".source-card, .source-retrieved { scroll-margin-top" in styles
    assert ".upload-pop-title.is-summary { white-space: normal; overflow-wrap: anywhere; }" in styles
    # O aviso fica no canto inferior direito, e a área da aba termina acima dele, para não cobrir nenhum botão.
    assert ".upload-pop { position: fixed; right: 16px; bottom: 16px;" in styles
    assert (".app.has-upload-pop .messages, .app.has-upload-pop .library { margin-bottom: var(--upload-space, 0px); }"
            in styles)
    assert 'app.style.setProperty("--upload-space"' in script and 'app.classList.remove("has-upload-pop");' in script
    assert "placeUploads();  // devolve o espaço reservado" in script
    assert 'new ResizeObserver(placeUploads).observe($("composer"));' in script  # a caixa de mensagem cresce


def test_resent_partial_document_comes_back_as_a_duplicate_without_a_count(env):
    client, library = env["client"], env["library"]
    library.add = lambda path, **kwargs: {"id": "d1", "title": kwargs["title"], "version": 1, "status": "partial",
                                          "issues": ["Página 2: sem texto utilizável; conferir original."],
                                          "duplicate": True}
    done = wait_job(client, post_file(client, "Baschel 2018.pdf"))
    # A duplicata não traz a contagem de trechos: a página mostra "já estava na biblioteca, indexado só em parte".
    assert done["estado"] == "concluido" and done["indexado"] is True
    assert done["resultado"]["duplicate"] is True and done["resultado"]["status"] == "partial"
    assert done["resultado"]["trechos"] is None and "fichas" not in done["resultado"]


def test_file_errors_reach_the_screen_in_plain_words(env):
    client, library = env["client"], env["library"]

    def broken(path, **kwargs):
        raise OSError(2, "No such file or directory", "C:\\dados\\uploads-temporarios\\a.md")

    library.add = broken
    job = post_file(client, "a.pdf")
    done = wait_job(client, job)
    listed = client.get("/api/biblioteca/tarefas").json()["tarefas"][0]
    for shown in (done["erro"], listed["erro"]):
        assert shown.startswith("Não foi possível ler ou gravar o arquivo")
        assert "Errno" not in shown and "uploads-temporarios" not in shown and ":\\" not in shown
    # Mensagem escrita pelo projeto continua chegando como está.
    library.add = lambda path, **kwargs: (_ for _ in ()).throw(ValueError("PDF protegido; forneça uma cópia acessível."))
    assert wait_job(client, post_file(client, "b.pdf"))["erro"] == "PDF protegido; forneça uma cópia acessível."


def test_complete_cards_ends_even_with_an_unexpected_error(env):
    client, settings, library = env["client"], env["settings"], env["library"]
    library.titles_without_card = lambda: ["Baschel 2018"]

    def broken(**kwargs):
        raise RuntimeError("erro fora dos previstos para a ficha")

    settings.card_extractor = broken
    library.opening_text = lambda title: "texto"
    job = client.post("/api/biblioteca/fichas", headers=HEADERS).json()
    done = wait_job(client, job["tarefa"])
    # A tarefa presa em andamento manteria o botão girando e bloquearia o apagar de documentos.
    assert done["estado"] == "concluido" and done["resultado"] == {"fichas": 0, "sem_dados": 0, "falhas": 1}


def test_cut_answer_is_flagged_and_stays_out_of_the_history(env):
    client = env["client"]
    env["reply"].update(pieces=["A definição é a frase que fic"], sources=(), status="uncited", extra={"truncated": True})
    cid = new_conversation(client)
    messages = fim(ask(client, cid)[1])["mensagens"]
    assert messages[1]["cortada"] is True and [m["in_context"] for m in messages] == [False, False]
    env["reply"].update(pieces=["Resposta inteira."], extra={})
    whole = fim(ask(client, cid, "De novo")[1])["mensagens"]
    assert whole[1]["cortada"] is False and whole[1]["in_context"] is True
    assert [m["content"] for m in env["calls"][-1]["history"]] == []  # a resposta cortada não voltou ao modelo


def test_reading_mode_budget_and_fixed_documents_reach_the_agent(env):
    """Lote 30: o modo, o teto e os documentos fixados seguem ao agente. Desde o lote 31, a leitura ampla é uma
    escolha ("integral"), e não o padrão."""
    client, calls, library = env["client"], env["calls"], env["library"]
    assert client.get("/api/estado").json()["leitura"] == {
        "modo": "auto", "teto": 400_000, "tetos": [150_000, 400_000, 900_000], "limite": 30_000,
        "modos": ["auto", "trechos", "paginas", "documento", "integral"], "aviso_diario": 300_000}
    cid = new_conversation(client)
    env["reply"]["extra"] = {"reading": {"teto": 400_000, "tokens_estimados": 9000, "fora": [],
                                         "documentos": [{"titulo": "Baschel et al., 2018", "paginas": 16, "total": 16,
                                                         "inteiro": True, "blocos": "1–16", "fixado": False}]}}
    user, reply = fim(ask(client, cid, leitura="integral")[1])["mensagens"]
    assert calls[-1]["reading"] == {"budget": 400_000, "fixed": [], "whole": True, "search": True}
    assert (user["leitura"], user["teto"]) == ("integral", 400_000)
    assert reply["leitura"]["documentos"][0]["paginas"] == 16 and reply["leitura_por_trechos"] is False
    # "Só trechos" é o pedido de sempre; o teto escolhido na página vale para a pergunta.
    ask(client, cid, leitura="trechos")
    assert "reading" not in calls[-1] and calls[-1]["library"] is library
    ask(client, cid, leitura="integral", teto=150_000)
    assert calls[-1]["reading"]["budget"] == 150_000
    assert ask(client, cid, leitura="tudo")[0].status_code == 400 and ask(client, cid, teto=123)[0].status_code == 400
    # Fixar na conversa: só documentos que estão na biblioteca, e o título da conversa não muda.
    pinned = "a" * 32
    library.documents = lambda: [{"id": pinned, "title": "baschel.pdf", "version": 1, "status": "ready", "issues": [],
                                  "sha256": "f" * 64,
                                  "created_at": "2026-10-03T00:00:00+00:00", "referencia": "Baschel et al., 2018"}]
    data = client.patch(f"/api/conversas/{cid}", json={"fixados": [pinned, "b" * 32]}, headers=HEADERS).json()
    assert data["fixados"] == [{"id": pinned, "title": "baschel.pdf", "referencia": "Baschel et al., 2018"}]
    assert data["title"] == "Qual a taxa?" and client.get(f"/api/conversas/{cid}").json()["fixados"] == data["fixados"]
    assert client.patch(f"/api/conversas/{cid}", json={"fixados": "tudo"}, headers=HEADERS).status_code == 400
    assert client.patch(f"/api/conversas/{cid}", json={"fixados": ["x"]}, headers=HEADERS).json()["fixados"] == []
    client.patch(f"/api/conversas/{cid}", json={"fixados": [pinned]}, headers=HEADERS)
    # Com a biblioteca desligada, o fixado continua indo inteiro, sem busca.
    ask(client, cid, "Qual é a taxa de falha dos ventiladores de refrigeração do inversor central?", biblioteca=False)
    assert calls[-1]["reading"] == {"budget": 60_000, "fixed": [pinned], "whole": False, "search": False, "top": 1}
    assert calls[-1]["library"] is library and calls[-1]["search_query"] is None
    # No modo de trechos, o fixado vai inteiro e a busca segue por trechos.
    ask(client, cid, leitura="trechos")
    assert calls[-1]["reading"] == {"budget": 60_000, "fixed": [pinned], "whole": False, "search": True, "top": 1}
    # Com a busca na web, o pedido segue por trechos, e a resposta guarda esse aviso.
    env["reply"]["extra"] = {}
    _, reply = fim(ask(client, cid, web=True)[1])["mensagens"]
    assert "reading" not in calls[-1] and reply["leitura_por_trechos"] is True and reply["leitura"] is None
    # Soltar o documento volta ao pedido sem fixados; renomear continua funcionando.
    assert client.patch(f"/api/conversas/{cid}", json={"fixados": []}, headers=HEADERS).json()["fixados"] == []
    assert client.patch(f"/api/conversas/{cid}", json={"title": "Taxas"}, headers=HEADERS).json()["title"] == "Taxas"
    assert client.patch(f"/api/conversas/{cid}", json={}, headers=HEADERS).status_code == 400
    with pytest.raises(ValueError):
        ConversationStore(env["tmp"] / "dados" / "conversas").pin(cid, [f"{n:032x}" for n in range(13)])


def test_google_files_route_counts_and_forgets(env):
    """Lote 30: o que a leitura integral deixou no serviço de arquivos do Google, e o botão de apagar."""
    from datetime import datetime, timedelta, timezone

    client, settings = env["client"], env["settings"]
    assert client.get("/api/biblioteca/arquivos").json() == {"disponivel": False, "arquivos": 0, "bytes": 0, "expira": None}
    now = datetime.now(timezone.utc)
    later, past = ((now + delta).isoformat(timespec="seconds") for delta in (timedelta(hours=40), timedelta(hours=-1)))
    forgotten = []
    settings.uploaded_files = lambda: [{"chave": "a:1-3", "bytes": 10, "expira": later},
                                       {"chave": "b:1-2", "bytes": 5, "expira": past}]
    settings.forget_files = lambda: forgotten.append(1) or {"apagados": 2, "falhas": 0}
    # Só o que ainda está no prazo conta; a resposta não traz chave nem endereço.
    assert client.get("/api/biblioteca/arquivos").json() == {"disponivel": True, "arquivos": 1, "bytes": 10, "expira": later}
    assert client.delete("/api/biblioteca/arquivos").status_code == 403 and forgotten == []
    assert client.delete("/api/biblioteca/arquivos", headers=HEADERS).json() == {"apagados": 2, "falhas": 0}

    def broken():
        raise ProviderError("https://exemplo.test/?key=segredo", transient=True)

    settings.forget_files = broken
    failed = client.delete("/api/biblioteca/arquivos", headers=HEADERS)
    assert failed.status_code == 502 and "segredo" not in failed.text


def test_library_tab_gave_place_to_the_documents_panel(env):
    """Lote 30: a aba Biblioteca saiu; os documentos ficam num painel do chat, com a leitura e os fixados."""
    client = env["client"]
    page, script = client.get("/").text, client.get("/static/app.js").text.replace("\r\n", "\n")
    assert 'id="nav-library"' not in page and 'id="library-view"' not in page and "Biblioteca</span></button>" not in page
    for wanted in ('id="docs-panel"', 'id="docs-open"', 'id="docs-files"', 'id="pinned"', 'id="reading-mode"',
                   'id="reading-budget"', '<option value="auto">Leitura automática</option>', '<option value="integral">Leitura ampla</option>',
                   '<option value="trechos">Só trechos</option>', 'id="library-add"', 'id="library-cards"'):
        assert wanted in page, wanted
    assert "openLibrary" not in script and "nav-library" not in script and "/markdown" not in script
    # Uma trava por comportamento da tela (a suíte não roda o JavaScript).
    for pinned in (
        'leitura: $("reading-mode").value, teto: Number($("reading-budget").value),',
        "if (waiting.length) await setPins(waiting);",
        'json: { fixados: list.map((doc) => doc.id) }',
        "pinDocument({ id: sent.id, title: sent.title, referencia: sent.referencia });",
        "(state.conversation?.id || null) === item.conversation",
        'uploadFiles([...$("file").files], attachToConversation)',
        'uploadFiles([...event.dataTransfer.files], !$("chat-view").hidden)',
        '{ kind: "reading" }',
        "Não couberam no teto:",
        'api("/api/biblioteca/arquivos", { method: "DELETE" })',
        "por até 48 horas",
        "com a busca na web, a leitura foi por trechos",
        '$("budget-box").hidden = !(whole || (!state.router && pins().length)) || !state.readingAvailable;',
        "‹ Todos os documentos",
    ):
        assert pinned in script, pinned


def test_page_asks_for_a_restart_when_the_server_is_older(env):
    """Lote 30: a página é lida do disco a cada carga; se o programa em execução é anterior a ela, a tela avisa.

    Em 04/10/2026 a tela nova rodou com o programa antigo: mostrava "Documentos inteiros", e as respostas
    saíram por trechos, sem aviso."""
    from datetime import datetime, timezone

    client = env["client"]
    started = datetime.fromisoformat(client.get("/api/estado").json()["iniciado"])
    assert started.tzinfo is not None and abs((datetime.now(timezone.utc) - started).total_seconds()) < 600
    page, script = client.get("/").text, client.get("/static/app.js").text.replace("\r\n", "\n")
    assert 'id="restart-note"' in page and "hidden>O AL-IAdo em execução é anterior a" in page
    assert client.head("/static/app.js").headers.get("last-modified")  # a data que a página compara
    for pinned in (
        "let stale = !data.leitura?.modos || !data.iniciado;",
        'fetch("/static/app.js", { method: "HEAD", cache: "no-store" })',
        "changed > Date.parse(data.iniciado) + 2000",
        '$("restart-note").hidden = !stale;',
        "state.readingAvailable = Boolean(data.leitura);",
        '$("reading-box").hidden = !library || !state.readingAvailable;',
    ):
        assert pinned in script, pinned



# --- Lote 31: roteador, escada de leitura, confirmação e trilhas ---

from datetime import datetime, timezone  # noqa: E402

LIBRARY_QUESTION = "Com base na literatura, o que são autoencoders e para que servem?"


def two_models(env):
    """O mesmo servidor, com os dois modelos configurados."""
    env["settings"].models = [{"alias": "flash", "model_id": "gemini-grande"}, {"alias": "flash_lite", "model_id": "gemini-pequeno"}]
    return TestClient(create_app(env["settings"]), base_url=BASE)


def test_router_chooses_model_skill_and_reading_and_the_reply_keeps_the_route(env):
    client, calls = two_models(env), env["calls"]
    cid = new_conversation(client)
    auto = {"skill": "auto", "modelo": "auto", "leitura": "auto"}
    _, reply = fim(ask(client, cid, "Obrigado, era isso.", **auto)[1])["mensagens"]
    assert calls[-1]["library"] is None and calls[-1]["model_alias"] == "flash_lite" and calls[-1]["skill_name"] is None
    assert calls[-1]["reasoning_level"] == "low" and calls[-1]["references"] is False and "reading" not in calls[-1]
    assert "ceiling" not in calls[-1] and "results" not in calls[-1]
    route = reply["rota"]
    assert (route["rung"], route["leitura"], route["model"], route["skill"]) == (0, "sem a biblioteca", "flash_lite", None)
    assert route["automatico"] == {"modelo": True, "skill": True, "leitura": True} and route["reasons"]
    assert reply["aprofundar"] is None
    # Figura ou tabela: páginas inteiras, com o modelo maior; o teto sem confirmação acompanha o pedido.
    ask(client, cid, "O que mostra a Figura 2 do artigo sobre os inversores?", **auto)
    assert calls[-1]["reading"] == {"budget": 60_000, "fixed": [], "whole": False, "search": True, "pages": 10, "priority": []}
    assert calls[-1]["model_alias"] == "flash" and calls[-1]["ceiling"] == 30_000 and calls[-1]["catalog"] is False
    assert calls[-1]["library"] is env["library"]
    # Pergunta sobre o acervo: trechos, o catálogo completo e o modelo menor.
    ask(client, cid, "Quais documentos temos na biblioteca sobre inversores?", **auto)
    assert "reading" not in calls[-1] and "catalog" not in calls[-1] and calls[-1]["model_alias"] == "flash_lite"
    # Um nome nos seletores fixa a escolha, e a rota registra de quem ela foi.
    _, reply = fim(ask(client, cid, "Obrigado, era isso.", skill="engenharia", modelo="flash", leitura="auto")[1])["mensagens"]
    assert calls[-1]["model_alias"] == "flash" and calls[-1]["skill_name"] == "engenharia" and "reasoning_level" not in calls[-1]
    assert reply["rota"]["automatico"] == {"modelo": False, "skill": False, "leitura": True}
    stored = client.get(f"/api/conversas/{cid}").json()["messages"]
    assert [m["skill"] for m in stored if m["role"] == "user"][:2] == ["nenhuma", "pesquisa-inversores"]
    assert ask(client, cid, modelo="outro")[0].status_code == 400 and ask(client, cid, skill="outra")[0].status_code == 400
    assert ask(client, cid, leitura="tudo")[0].status_code == 400


def test_a_reading_above_the_ceiling_asks_first_and_the_daily_warning_asks_every_time(env):
    client, calls = env["client"], env["calls"]
    cid = new_conversation(client)
    env["reply"]["confirm"] = 46_000
    _, events = ask(client, cid, leitura="documento")
    assert [event["tipo"] for event in events] == ["confirmar"]
    assert (events[0]["tokens"], events[0]["chave"], events[0]["limite"], events[0]["motivo"], events[0]["lembrar"]) == (
        46_000, "chave1", 30_000, "teto", True)
    assert events[0]["modo"] == "documento" and client.get(f"/api/conversas/{cid}").json()["messages"] == []  # nada gravado
    assert calls[-1]["ceiling"] == 30_000 and calls[-1]["reading"]["top"] == 1
    assert fim(ask(client, cid, leitura="documento", confirmado="chave1")[1])["mensagens"][1]["rota"]["rung"] == 3
    # Por trechos, não há teto a conferir: é o modo barato.
    ask(client, cid, leitura="trechos")
    assert "ceiling" not in calls[-1] and "reading" not in calls[-1]
    # Depois do aviso diário, toda leitura acima dos trechos pergunta, e a chave não é reaproveitada.
    env["reply"]["confirm"] = 9_000
    assert [event["tipo"] for event in ask(client, cid, leitura="paginas")[1]][:3] == ["texto", "texto", "fim"]
    log = env["settings"].usage_log
    log.write_text(log.read_text(encoding="utf-8") + json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(), "total_tokens": 300_000}) + "\n", encoding="utf-8")
    _, events = ask(client, cid, leitura="paginas")
    assert (events[0]["tipo"], events[0]["motivo"], events[0]["lembrar"]) == ("confirmar", "dia", False)
    assert events[0]["hoje"] >= 300_000 and (calls[-1]["ceiling"], calls[-1]["salt"]) == (0, "dia")
    assert fim(ask(client, cid, leitura="trechos")[1])  # os trechos seguem sem perguntar


def test_an_answer_without_citations_climbs_one_rung_inside_the_ceiling(env):
    client, calls = env["client"], env["calls"]
    cid = new_conversation(client)
    env["reply"].update(statuses=["uncited", "citation_ids_verified"])
    _, events = ask(client, cid, LIBRARY_QUESTION, leitura="auto")
    kinds = [event["tipo"] for event in events]
    assert kinds.count("recomeco") == 1 and kinds.index("recomeco") > kinds.index("texto") and kinds[-2] == "fim"
    first, second = calls[-2:]
    assert "reading" not in first and second["reading"]["pages"] == 10 and second["ceiling"] == 30_000 - 320
    route = fim(events)["mensagens"][1]["rota"]
    assert route["rung"] == 2 and route["tentativas"] == [{"leitura": "trechos", "tokens": 320}]
    assert "subiu um degrau" in route["reasons"][-1]
    usage = [json.loads(line)["task_type"] for line in env["settings"].usage_log.read_text(encoding="utf-8").splitlines()]
    assert usage.count("critical_reasoning") == 2  # as duas chamadas ficam no registro de uso
    # Com o degrau fixado por você, a resposta sem citação fica como veio.
    before = len(calls)
    env["reply"].update(statuses=["uncited"])
    reply = fim(ask(client, cid, LIBRARY_QUESTION, leitura="trechos")[1])["mensagens"][1]
    assert len(calls) == before + 1 and reply["validation_status"] == "uncited" and reply["rota"]["tentativas"] == []
    # Se a subida passar do teto, vale a primeira resposta.
    env["reply"].update(statuses=["uncited"], confirm=31_000)
    reply = fim(ask(client, new_conversation(client), LIBRARY_QUESTION, leitura="auto")[1])["mensagens"][1]
    assert reply["rota"]["rung"] == 1 and reply["aprofundar"]["leitura"] == "paginas"


def test_an_answered_question_leaves_a_trail_that_a_similar_one_follows(env):
    from test_routing import Words

    client, calls, library = env["client"], env["calls"], env["library"]
    env["settings"].memory = memory = MemoryStore(env["tmp"] / "trilhas", encoder=Words())
    sha = "a" * 64
    library.documents = lambda: [{"id": "d1", "title": "Baschel 2018", "version": 1, "status": "ready", "issues": [],
                                  "sha256": sha, "created_at": "2026-10-03T00:00:00+00:00"}]
    env["reply"]["sources"] = (SOURCE | {"sha256": sha, "page": 5},)
    first = new_conversation(client)
    reply = fim(ask(client, first, LIBRARY_QUESTION, leitura="auto")[1])["mensagens"][1]
    assert "reading" not in calls[-1] and reply["rota"]["trilha"] is None
    assert memory.trail(LIBRARY_QUESTION)[0]["pages"] == [{"sha256": sha, "page": 5, "title": "Baschel 2018"}]
    # A mesma pergunta, em outra conversa: sem busca, com a troca anterior e as páginas que ela citou.
    second = new_conversation(client)
    reply = fim(ask(client, second, "O que são autoencoders e para que servem, com base na literatura?", leitura="auto")[1])["mensagens"][1]
    assert calls[-1]["reading"] == {"budget": 60_000, "fixed": [], "whole": False, "search": False, "pages": 6,
                                    "priority": [("d1", 5)]}
    assert calls[-1]["trail"]["question"] == LIBRARY_QUESTION and "ceiling" not in calls[-1]
    assert reply["rota"]["trilha"]["conversa"] == first and reply["rota"]["leitura"] == "páginas de uma resposta anterior"
    assert "já respondida" in reply["rota"]["reasons"][-1]
    # Refeita logo em seguida, na mesma conversa: a resposta não bastou, e a leitura sobe para as páginas.
    ask(client, second, "O que são autoencoders e para que servem, com base na literatura?", leitura="auto")
    assert calls[-1]["reading"]["pages"] == 10 and calls[-1]["reading"]["search"] is True and "trail" not in calls[-1]
    assert calls[-1]["reading"]["priority"] == [("d1", 5)]
    # Outro assunto não pega trilha; pergunta curta, também não; e o documento apagado sai das trilhas.
    ask(client, new_conversation(client), "Com base na literatura, qual é o tempo de reparo do transformador?", leitura="auto")
    assert "reading" not in calls[-1] and "trail" not in calls[-1]
    library.documents = lambda: []
    ask(client, new_conversation(client), LIBRARY_QUESTION, leitura="auto")
    assert "reading" not in calls[-1] and "trail" not in calls[-1]


def test_a_large_named_document_goes_by_its_own_pages_without_asking(env):
    client, calls, library = env["client"], env["calls"], env["library"]
    library.documents = lambda: [{"id": "d1", "title": "livro.pdf", "version": 1, "status": "ready", "issues": [],
                                  "sha256": "a" * 64, "created_at": "2026-10-03T00:00:00+00:00"}]
    library.cards = lambda: {"livro.pdf": {"ficha": {"titulo": "Manual de confiabilidade", "autores": ["Lafraia, J."]},
                                           "referencia": "Lafraia, 2001"}}
    pages = {"pdf": True, "title": "livro.pdf", "referencia": "Lafraia, 2001", "units": [{"text": "x" * 300}] * 369}
    library.pages = lambda doc_id: pages
    cid = new_conversation(client)
    reply = fim(ask(client, cid, "De acordo com Lafraia, o que é a disponibilidade?", leitura="auto")[1])["mensagens"][1]
    assert calls[-1]["reading"] == {"budget": 60_000, "fixed": [], "whole": False, "search": True, "pages": 10,
                                    "priority": [], "focus": ["d1"]}
    assert reply["rota"]["rung"] == 2 and "é grande" in reply["rota"]["reasons"][-1]
    # Um documento citado que cabe no teto vai inteiro.
    pages["units"] = pages["units"][:12]
    ask(client, cid, "De acordo com Lafraia, o que é a mantenabilidade?", leitura="auto")
    assert calls[-1]["reading"] == {"budget": 60_000, "fixed": ["d1"], "whole": False, "search": True, "top": 1}


def test_reply_offers_the_next_rung_with_its_cost(env):
    client = env["client"]
    cid = new_conversation(client)
    reply = fim(ask(client, cid, LIBRARY_QUESTION, leitura="trechos")[1])["mensagens"][1]
    assert reply["aprofundar"] == {"leitura": "paginas", "tokens": 100 - len("IGBT...") // 3 + 10 * (560 + 55)}
    reply = fim(ask(client, cid, LIBRARY_QUESTION, leitura="documento", documentos=["d1", "x"])[1])["mensagens"][1]
    assert env["calls"][-1]["reading"]["fixed"] == ["d1"]  # o documento pedido pelo botão, se está na biblioteca
    assert reply["aprofundar"]["leitura"] == "integral" and reply["aprofundar"]["ate"] is True
    assert fim(ask(client, cid, LIBRARY_QUESTION, leitura="integral")[1])["mensagens"][1]["aprofundar"] is None
    assert fim(ask(client, cid, LIBRARY_QUESTION, leitura="trechos", web=True)[1])["mensagens"][1]["aprofundar"] is None


def test_page_has_the_automatic_choices_the_route_line_and_the_confirmation(env):
    client = env["client"]
    page, script = client.get("/").text, client.get("/static/app.js").text.replace("\r\n", "\n")
    for wanted in ('<option value="auto">Leitura automática</option>', '<option value="paginas">Páginas inteiras</option>',
                   '<option value="documento">Documento inteiro</option>'):
        assert wanted in page, wanted
    for pinned in (
        'state.router = Boolean(data.leitura?.modos);',
        'el("option", { value: "auto", text: "Modelo automático" })',
        '"auto": "Skill automática",',
        'store.get("aliado.rota.skill", "auto")',
        'else if (event.tipo === "confirmar") { final = event; handlers.onConfirm?.(event); }',
        'else if (event.tipo === "recomeco") handlers.onRestart?.(event);',
        'submitQuestion(text, { ...extra, confirmado: event.chave });',
        'submitQuestion(text, { leitura: "trechos" })',
        'submitQuestion(question.content, { leitura: deeper.leitura, documentos: deeper.documentos });',
        '...(remembered ? { confirmado: remembered } : {}), ...extra,',
        'text: "partiu de uma resposta anterior"',
        "Ler mais fundo (",
    ):
        assert pinned in script, pinned
