"""Interface local: rotas, proteção, fluxo, conversas, citações e biblioteca, sem rede nem Gemini real."""

from __future__ import annotations

import json
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


def test_results_switch_reaches_the_agent_and_defaults_to_the_research_skill(env):
    client, built = env["client"], []
    env["settings"].results_digest = lambda: built.append(1) or RESULTS_DIGEST
    state = client.get("/api/estado").json()["resultados"]
    assert state == {"disponivel": True, "skill": "pesquisa-inversores"} and not built  # o estado não monta o resumo
    cid = new_conversation(client)
    ask(client, cid, resultados=True)
    assert env["calls"][-1]["results"] is RESULTS_DIGEST and len(built) == 1
    ask(client, cid)  # sem o campo, vale ligado na skill do mestrado
    assert env["calls"][-1]["results"] is RESULTS_DIGEST
    ask(client, cid, skill="engenharia")
    assert "results" not in env["calls"][-1]
    ask(client, cid, resultados=False)
    assert "results" not in env["calls"][-1]
    stored = client.get(f"/api/conversas/{cid}").json()["messages"]
    assert [m["resultados"] for m in stored if m["role"] == "user"] == [True, True, False, False]


def test_cited_results_are_stored_rendered_and_unverified_numbers_leave_the_history(env):
    client = env["client"]
    env["settings"].results_digest = lambda: RESULTS_DIGEST
    env["reply"].update(pieces=["O Denso detectou 10 de 14 [R1]."], sources=(), status=None,
                        extra={"result_sources": (RESULT_BLOCK,), "results_status": "conferido"})
    cid = new_conversation(client)
    reply = fim(ask(client, cid)[1])["mensagens"][1]
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
    assert [m["content"] for m in env["calls"][-1]["history"]] == ["Qual a taxa?", "O Denso detectou 10 de 14 [R1]."]
    env["reply"].update(pieces=["Aviso local."], status="invalid_result_refs", extra={"results_status": "invalid_result_refs"})
    assert fim(ask(client, cid, "De novo")[1])["mensagens"][1]["in_context"] is False


def test_a_failing_digest_does_not_break_the_conversation(env):
    client = env["client"]

    cid = new_conversation(client)
    for error in (OSError("disco"), TypeError("float() de None"), ZeroDivisionError()):
        def broken(error=error):
            raise error

        env["settings"].results_digest = broken
        reply = fim(ask(client, cid)[1])["mensagens"][1]
        assert "results" not in env["calls"][-1] and "não foi possível" in reply["resultados_faltando"][0]
    env["settings"].results_digest = lambda: {"cabecalho": "c", "blocos": [], "faltando": ["tudo"]}
    reply = fim(ask(client, cid)[1])["mensagens"][1]
    assert "results" not in env["calls"][-1] and reply["resultados_faltando"] == ["tudo"]
    env["settings"].results_digest = None
    assert client.get("/api/estado").json()["resultados"]["disponivel"] is False
    assert fim(ask(client, cid)[1])["mensagens"][1]["resultados_faltando"] == []
