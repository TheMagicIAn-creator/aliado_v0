"""Servidor local do AL-IAdo: conversa, biblioteca e fontes, acessível só por 127.0.0.1.

Importado apenas por `aliado web`; o restante do pacote não carrega Starlette.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from aliado.interfaces.web.conversations import ConversationStore
from aliado.interfaces.web.gpvs_runs import gpvs_routes
from aliado.interfaces.web.rendering import render_markdown
from aliado.interfaces.web.science import science_routes
from aliado.knowledge.metadata import reference
from aliado.llm.providers.base import ProviderError, ProviderNotConfiguredError
from aliado.llm.usage_log import record_usage
from aliado.skills.library import list_skills, load_skill

STATIC = Path(__file__).resolve().parent / "static"
MAX_QUESTION_CHARS = 20_000
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
UPLOAD_SUFFIXES = {".pdf", ".md", ".json"}
UPLOAD_BATCH = re.compile(r"[0-9a-f]{8,32}")  # identificador do lote de envios, gerado pela página
# Respostas locais que não devem voltar ao modelo como histórico.
OUT_OF_CONTEXT = {"insufficient_evidence", "invalid_citations", "invalid_result_refs"}
# Resposta com número que não está no resultado citado (lote 26): aparece com aviso e fica fora do histórico.
UNVERIFIED_RESULTS = "numeros_nao_conferidos"
RESULTS_SKILL = "pesquisa-inversores"
# "Lembre que…", "lembre-se de que…", "lembra que…": pedido explícito de anotação.
EXPLICIT_MEMORY = re.compile(r"^\s*lembr[ae](?:-se)?(?:\s+de)?\s+que\b", re.IGNORECASE)
MEMORY_VIEW_KEYS = ("id", "kind", "text", "origin", "status", "skill", "source", "diverges_skill",
                    "conflict_with", "supersedes", "superseded_by", "created_at")


def _memory_view(memory: dict) -> dict:
    return {key: memory.get(key) for key in MEMORY_VIEW_KEYS}


def _pdf_pages(markdown: str) -> int:
    return max((int(n) for n in re.findall(r"^## página PDF (\d+)", markdown, re.MULTILINE)), default=0)
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
       "font-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")


@dataclass
class WebSettings:
    data_dir: Path
    library_dir: Path
    port: int
    # Gera ("texto", pedaço) e termina com ("final", LLMResult); ver Agent.stream_answer.
    stream: Callable[..., Iterator[tuple[str, object]]]
    models: list[dict]
    library_factory: Callable[[], object]
    usage_log: Path | None = None
    jobs: dict = field(default_factory=dict)
    # Memória (lote 11): armazenamento, revisor da troca e ficha de leitura; opcionais.
    memory: object | None = None
    reviewer: Callable[..., tuple[list[dict], object]] | None = None
    card_maker: Callable[..., tuple[list[dict], object]] | None = None
    # Busca na web (lote 12): conferência de uma anotação; devolve (veredito, resultado).
    checker: Callable[[dict], tuple[dict, object]] | None = None
    # Ficha do documento (lote 19): (título=, text=) -> (ficha conferida, resultado).
    card_extractor: Callable[..., tuple[dict, object]] | None = None
    # Consulta da busca (lote 22): (question=, history=) -> (consulta reescrita, resultado).
    query_rewriter: Callable[..., tuple[str, object]] | None = None
    # Aba Ciência (lote 20): resultados, dados do GPVS e referências da pesquisa (FMECA e cenários).
    results_dir: Path | None = None
    gpvs_dir: Path = Path("data/gpvs")
    reference_dir: Path = Path("docs/pesquisa-inversores")
    # GPVS pela interface (lote 21): (args, on_line, on_process) -> (código, stdout); padrão, subprocesso.
    gpvs_command: Callable[..., tuple[int, str]] | None = None
    # Resultados no chat (lote 26): () -> resumo com os blocos [R1]…; montado sob demanda, em cache.
    results_digest: Callable[[], dict] | None = None

    def __post_init__(self):
        self.data_dir = Path(self.data_dir).resolve()
        self.library_dir = Path(self.library_dir).resolve()
        self.usage_log = Path(self.usage_log or self.data_dir / "uso" / "chamadas.jsonl")
        self.results_dir = Path(self.results_dir or self.data_dir / "resultados").resolve()
        self.gpvs_dir = Path(self.gpvs_dir).resolve()
        self.reference_dir = Path(self.reference_dir).resolve()


class LocalOnly(BaseHTTPMiddleware):
    """Recusa hosts externos (DNS rebinding) e mutações sem o cabeçalho próprio (CSRF)."""

    def __init__(self, app, port: int):
        super().__init__(app)
        self.hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.origins = {f"http://{host}" for host in self.hosts}

    async def dispatch(self, request: Request, call_next):
        if request.headers.get("host") not in self.hosts:
            return JSONResponse({"erro": "Acesso permitido apenas pelo endereço local."}, 403)
        if request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("origin")
            if (origin and origin not in self.origins) or request.headers.get("x-aliado") != "1":
                return JSONResponse({"erro": "Pedido recusado pela proteção local."}, 403)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            # Conferir a versão a cada carga (barato localmente): uma atualização aparece na hora.
            response.headers.setdefault("Cache-Control", "no-cache")
        if not request.url.path.endswith("/original"):
            response.headers.setdefault("Content-Security-Policy", CSP)
        return response


def _error(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"erro": message}, status)


def _view(message: dict) -> dict:
    """Mensagem pronta para a tela; o HTML é gerado na leitura a partir do texto guardado."""
    view = dict(message)
    if message["role"] == "assistant":
        results = message.get("result_sources") or ()
        view["html"] = render_markdown(message["content"], message.get("sources") or (),
                                       message.get("web_sources") or (), results)
        if results:
            # A tabela de cada bloco citado, pronta para a janela de fontes.
            view["result_sources"] = [dict(block) | {"html": render_markdown(block.get("texto", ""))} for block in results]
    return view


def _usage_totals(path: Path) -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    totals = {"hoje": 0, "total": 0, "chamadas": 0}
    if not path.is_file():
        return totals
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        tokens = entry.get("total_tokens") or 0
        totals["total"] += tokens
        totals["chamadas"] += 1
        if str(entry.get("timestamp", "")).startswith(today):
            totals["hoje"] += tokens
    return totals


def _index_conversations(store: ConversationStore, memory) -> int:
    """Guarda na memória de conversas as trocas exibidas que ainda não estão lá (conversas antigas)
    e calcula os vetores que faltam em anotações e trocas antigas."""
    added = 0
    for item in store.list():
        try:
            messages = store.get(item["id"])["messages"]
        except ValueError:
            continue
        for question, answer in zip(messages, messages[1:]):
            if (question.get("role"), answer.get("role")) == ("user", "assistant") and \
                    question.get("in_context", True) and answer.get("in_context", True):
                added += memory.remember_exchange(
                    conversation_id=item["id"], message_id=answer["id"], question=question["content"],
                    answer=answer["content"], skill=question.get("skill"), created_at=answer.get("created_at"))
    memory.fill_missing_vectors()
    return added


def create_app(settings: WebSettings) -> Starlette:
    store = ConversationStore(settings.data_dir / "conversas")
    uploads = settings.data_dir / "uploads-temporarios"
    worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aliado-biblioteca")
    lock = threading.Lock()
    library_jobs: set[str] = set()  # envios e fichas; enquanto correm, nenhum documento é apagado
    upload_order: list[str] = []  # envios na ordem de chegada; o lote mais recente alimenta o pop-up da página
    skills = {item.name: item.description for item in list_skills()}
    aliases = {model["alias"] for model in settings.models}
    if settings.memory is not None:
        # Conversas anteriores ao lote 18 entram na memória de conversas uma vez, sem travar a abertura.
        worker.submit(_index_conversations, store, settings.memory)

    async def index(request: Request):
        return FileResponse(STATIC / "index.html")

    async def state(request: Request):
        documents = await run_in_threadpool(_documents)
        return JSONResponse({
            "skills": [{"name": name, "description": text} for name, text in skills.items()],
            "modelos": settings.models,
            "biblioteca": {"documentos": len(documents)},
            # Só diz se há de onde tirar os resultados; o resumo é montado na primeira pergunta.
            "resultados": {"disponivel": settings.results_digest is not None, "skill": RESULTS_SKILL},
            "uso": _usage_totals(settings.usage_log),
        })

    async def conversations(request: Request):
        if request.method == "POST":
            return JSONResponse(store.create(), 201)
        return JSONResponse(store.list())

    async def conversation(request: Request):
        try:
            if request.method == "DELETE":
                store.delete(request.path_params["cid"])
                if settings.memory is not None:
                    try:
                        # A conversa apagada deixa de ser relembrada; as anotações dela ficam.
                        settings.memory.forget_conversation(request.path_params["cid"])
                    except (OSError, sqlite3.DatabaseError):
                        pass
                return JSONResponse({"apagada": True})
            if request.method == "PATCH":
                body = await request.json()
                data = store.rename(request.path_params["cid"], body.get("title"))
            else:
                data = store.get(request.path_params["cid"])
        except (ValueError, AttributeError) as exc:
            return _error(str(exc), 404 if "encontrada" in str(exc) else 400)
        return JSONResponse(data | {"messages": [_view(m) for m in data["messages"]]})

    async def message(request: Request):
        cid = request.path_params["cid"]
        try:
            data = store.get(cid)
        except ValueError as exc:
            return _error(str(exc), 404)
        try:
            body = await request.json()
        except ValueError:
            return _error("Pedido inválido.")
        if not isinstance(body, dict):
            return _error("Pedido inválido.")
        text = body.get("texto")
        skill = body.get("skill") or "pesquisa-inversores"
        support = body.get("apoio") or None
        alias = body.get("modelo")
        use_library = bool(body.get("biblioteca"))
        use_web = bool(body.get("web"))
        # Sem o campo, os resultados entram só na skill do mestrado.
        use_results = bool(body["resultados"]) if "resultados" in body else skill == RESULTS_SKILL
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_QUESTION_CHARS:
            return _error("Escreva uma pergunta de até 20 mil caracteres.")
        if skill != "nenhuma" and skill not in skills or support and support not in skills:
            return _error("Skill desconhecida.")
        if alias not in aliases:
            return _error("Modelo não configurado. Confira o .env.")
        library = settings.library_factory() if use_library else None
        history = store.history(data)

        def line(payload: dict) -> str:
            return json.dumps(payload, ensure_ascii=False) + "\n"

        memory_skill = None if skill == "nenhuma" else skill

        def events():
            # Gerador síncrono: o Starlette o consome numa thread, sem travar o servidor.
            result = None
            memories, recalled = [], []
            if settings.memory is not None:
                try:
                    memories = settings.memory.relevant(text, skill=memory_skill)
                    recalled = settings.memory.recall(text, exclude_conversation=cid)
                except (ValueError, OSError, sqlite3.DatabaseError):
                    memories, recalled = [], []  # a conversa segue sem memória em vez de falhar
            search_query = rewrite() if library is not None else None
            digest, missing = results_for_request()
            extra = {"results": digest} if digest else {}
            try:
                for kind, value in settings.stream(
                        text, model_alias=alias, skill_name=memory_skill,
                        supporting_skill_name=support, library=library, history=history,
                        memories=memories, web_search=use_web, recalled=recalled,
                        search_query=search_query, **extra):
                    if kind == "texto":
                        yield line({"tipo": "texto", "texto": value})
                    else:
                        result = value
            except ProviderNotConfiguredError:
                yield line({"tipo": "erro", "erro": "Configure a chave do Gemini no .env e reinicie."})
                return
            except ProviderError:
                # Mensagens de SDK podem conter URLs ou credenciais; não são repassadas.
                yield line({"tipo": "erro", "erro": "O Gemini não respondeu. Tente de novo em instantes."})
                return
            except ValueError as exc:
                yield line({"tipo": "erro", "erro": f"Pedido inválido: {exc}"})
                return
            if result is None:
                yield line({"tipo": "erro", "erro": "A resposta não foi concluída."})
                return
            if result.provider != "local":
                try:
                    record_usage(result, settings.usage_log)
                except OSError:
                    pass
            # Resposta cortada pelo teto de tamanho (lote 27): aparece com aviso e fica fora do histórico.
            in_context = (result.validation_status not in OUT_OF_CONTEXT and result.provider != "local"
                          and result.results_status != UNVERIFIED_RESULTS and not result.truncated)
            user = {"role": "user", "content": text.strip(), "in_context": in_context,
                    "skill": skill, "apoio": support, "biblioteca": use_library, "web": use_web,
                    "resultados": use_results}
            reply = {"role": "assistant", "content": result.content, "in_context": in_context,
                     "provider": result.provider, "model": result.model,
                     "usage": asdict(result.usage) if result.usage else None,
                     "sources": list(result.sources), "validation_status": result.validation_status,
                     # Lote 27: o que a busca trouxe e a resposta não citou, para a janela de fontes.
                     "recuperados": [dict(hit) for hit in result.retrieved],
                     "web_sources": [dict(s) for s in result.web_sources],
                     "web_queries": list(result.web_queries),
                     "consulta_biblioteca": search_query,
                     "result_sources": [dict(block) for block in result.result_sources],
                     "results_status": result.results_status,
                     "numeros_nao_conferidos": list(result.unverified_numbers),
                     "numeros_sem_marca": result.unmarked_numbers,
                     "cortada": result.truncated,
                     "resultados_faltando": missing,
                     "memorias_usadas": [{"id": m["id"], "kind": m["kind"], "origin": m["origin"],
                                          "text": m["text"]} for m in memories],
                     "conversas_lembradas": [{"conversation_id": r["conversation_id"],
                                              "created_at": r["created_at"],
                                              "question": " ".join(r["question"].split())[:200]}
                                             for r in recalled]}
            try:
                stored = store.append(cid, user, reply)
            except ValueError:
                yield line({"tipo": "erro", "erro": "A conversa foi apagada durante a resposta."})
                return
            if in_context and settings.memory is not None:
                try:
                    settings.memory.remember_exchange(
                        conversation_id=cid, message_id=stored["messages"][-1]["id"], question=text,
                        answer=result.content, skill=memory_skill,
                        created_at=stored["messages"][-1].get("created_at"))
                except (OSError, sqlite3.DatabaseError):
                    pass  # a resposta já foi guardada; a memória de conversas não deve derrubá-la
            yield line({"tipo": "fim", "conversa": {k: stored[k] for k in ("id", "title", "updated_at")},
                        "mensagens": [_view(m) for m in stored["messages"][-2:]]})
            if in_context and settings.memory is not None and settings.reviewer is not None:
                yield line(review(stored, memories, result))

        def results_for_request() -> tuple[dict | None, list[str]]:
            """O resumo dos resultados e o que faltou, em palavras; uma falha aqui não derruba a conversa."""
            if not use_results or settings.results_digest is None:
                return None, []
            try:
                digest = settings.results_digest()
            except Exception:  # o resumo é opcional: qualquer falha dele deixa a conversa seguir
                return None, ["os resultados da pesquisa (não foi possível montá-los)"]
            return (digest if digest.get("blocos") else None), list(digest.get("faltando") or ())

        def rewrite() -> str | None:
            """Consulta da busca pelo modelo mais barato; sem ela, a busca segue pela própria pergunta."""
            if settings.query_rewriter is None:
                return None
            try:
                query, rewrite_result = settings.query_rewriter(question=text, history=history)
            except (ProviderError, ValueError, KeyError, TypeError):
                return None
            try:
                record_usage(rewrite_result, settings.usage_log)
            except OSError:
                pass
            return query

        def review(stored: dict, memories: list[dict], result) -> dict:
            """Revisor depois da resposta: a conversa já está salva, e uma falha aqui não a afeta."""
            reply_id = stored["messages"][-1]["id"]
            try:
                skill_text = load_skill(memory_skill).instructions if memory_skill else ""
                notes, review_result = settings.reviewer(
                    question=text, answer=result.content, skill=memory_skill, skill_text=skill_text,
                    sources=list(result.sources) + [
                        {"citation_id": f"W{n}", "title": s.get("title") or s.get("domain") or "web",
                         "url": s.get("uri"), "text": ""} for n, s in enumerate(result.web_sources, 1)],
                    existing=memories,
                    explicit=bool(EXPLICIT_MEMORY.match(text)))
            except (ProviderError, ValueError, KeyError, TypeError):
                return {"tipo": "memoria", "criadas": [], "aviso": "O revisor de memória não respondeu."}
            try:
                record_usage(review_result, settings.usage_log)
            except OSError:
                pass
            origin = {"conversation_id": cid, "message_id": reply_id, "conversation_title": stored["title"],
                      "trecho": " ".join(text.split())[:240]}
            created = []
            for note in notes:
                try:
                    created.append(settings.memory.add(
                        kind=note["kind"], text=note["text"], origin=note["origin"], skill=memory_skill,
                        source=note["source"] | origin, supersedes=note["supersedes"],
                        diverges_skill=note["diverges_skill"]))
                except ValueError:
                    continue
            views = [_memory_view(memory) for memory in created]
            try:
                store.annotate(cid, reply_id, memorias_criadas=views)
            except ValueError:
                pass  # conversa apagada nesse meio-tempo; as anotações continuam na memória
            return {"tipo": "memoria", "mensagem": reply_id, "criadas": views}

        return StreamingResponse(events(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    def _documents() -> list[dict]:
        if not (settings.library_dir / "catalog.sqlite3").exists():
            return []
        return settings.library_factory().documents()

    def _document_card(library_, title: str) -> dict:
        """Ficha do documento pelo Flash-Lite, conferida no texto; grava mesmo vazia (tentativa feita)."""
        card, card_result = settings.card_extractor(title=title, text=library_.opening_text(title))
        try:
            record_usage(card_result, settings.usage_log)
        except OSError:
            pass
        library_.set_card(title, card, edited=False)
        return card

    async def library(request: Request):
        if request.method == "GET":
            def listing():
                library_ = settings.library_factory()
                pending = set(library_.titles_without_card()) if settings.card_extractor else set()
                return [{k: d.get(k) for k in ("id", "title", "version", "status", "issues", "created_at",
                                               "ficha", "ficha_origem", "referencia")}
                        | {"ficha_pendente": d["title"] in pending} for d in _documents()]
            return JSONResponse(await run_in_threadpool(listing))
        form = await request.form(max_files=1, max_fields=4)
        upload = form.get("arquivo")
        if upload is None or not getattr(upload, "filename", None):
            return _error("Envie um arquivo PDF, Markdown ou JSON.")
        card_skill = form.get("skill")
        card_skill = card_skill if isinstance(card_skill, str) and card_skill in skills else None
        # A página manda o mesmo lote para os arquivos escolhidos juntos; o pop-up soma por lote.
        batch = form.get("lote")
        batch = batch if isinstance(batch, str) and UPLOAD_BATCH.fullmatch(batch) else uuid.uuid4().hex
        name = Path(upload.filename).name
        if Path(name).suffix.lower() not in UPLOAD_SUFFIXES:
            return _error("Formato não aceito. Envie PDF, Markdown ou JSON.")
        job = uuid.uuid4().hex
        folder = uploads / job
        folder.mkdir(parents=True, exist_ok=False)
        target = folder / name
        size = 0
        with target.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    handle.close()
                    shutil.rmtree(folder, ignore_errors=True)
                    return _error("Arquivo acima de 100 MB.", 413)
                handle.write(chunk)
        with lock:
            settings.jobs[job] = {"estado": "na fila", "arquivo": name, "lote": batch}
            library_jobs.add(job)
            upload_order.append(job)

        def progress(stage: str, current: int, total: int) -> None:
            with lock:
                settings.jobs[job].update({"etapa": stage, "atual": current, "total": total})

        def run():
            with lock:
                settings.jobs[job]["estado"] = "processando"
            result = library_ = None
            try:
                library_ = settings.library_factory()
                result = library_.add(target, title=name, progress=progress)
                if result.get("duplicate") and result.get("status") == "failed":
                    # Reenviar um documento que falhou é um pedido de nova tentativa.
                    result = library_.add(target, title=name, reprocess=True, progress=progress)
                indexed = result.get("status") in {"ready", "partial"}
                outcome = {"indexado": indexed, "resultado": {k: result[k] for k in (
                    "id", "title", "version", "status", "issues", "duplicate") if k in result}
                    | {"trechos": result.get("chunks")}}
            except ValueError as exc:
                outcome = {"estado": "falhou", "erro": str(exc)}  # mensagens escritas pelo projeto
            except OSError:
                # O texto do sistema traz código de erro e caminho de pasta: a tela recebe uma frase simples.
                outcome = {"estado": "falhou", "erro": "Não foi possível ler ou gravar o arquivo. Confira o espaço "
                                                       "em disco e tente enviar de novo."}
            except Exception:
                # Erro não previsto: a tarefa termina com falha, em vez de ficar presa e bloquear o apagar.
                outcome = {"estado": "falhou", "erro": "Erro inesperado ao processar o documento. Tente enviar de novo."}
            finally:
                # A biblioteca guarda a própria cópia do original; o arquivo temporário sai.
                shutil.rmtree(folder, ignore_errors=True)
            if not outcome.get("indexado") or result.get("duplicate"):
                with lock:
                    settings.jobs[job].update({"estado": "concluido"} | outcome)
                return
            # O documento já pode ser buscado e citado: fica pronto aqui (lote 27). As fichas chamam o
            # modelo e vão para o fim da fila, depois da indexação dos outros arquivos enviados.
            with lock:
                settings.jobs[job].update(outcome)
            try:
                worker.submit(cards, library_, result)
            except RuntimeError:  # o executor já foi encerrado: as fichas saem agora
                cards(library_, result)

        def cards(library_, result: dict) -> None:
            extra: dict = {}
            try:
                extra |= document_card(library_, result)
                extra |= reading_card(library_, result)
            except Exception:
                # Uma falha inesperada nas fichas não pode deixar a tarefa presa: ela bloquearia o apagar.
                extra.setdefault("aviso_ficha", "A ficha de leitura não pôde ser criada agora.")
            finally:
                with lock:
                    current = settings.jobs[job]
                    current.update({"estado": "concluido", "resultado": current["resultado"] | extra})

        def document_card(library_, result: dict) -> dict:
            """Ficha do documento (título, autores, ano e DOI); só na primeira versão de um título."""
            if settings.card_extractor is None or result["title"] not in library_.titles_without_card():
                return {}
            progress("ficha do documento", 0, 1)
            try:
                card = _document_card(library_, result["title"])
            except (ProviderError, ValueError, OSError, KeyError, TypeError):
                return {"aviso_ficha_documento": "A ficha do documento não pôde ser criada agora."}
            return {"referencia": reference(card)}

        def reading_card(library_, result: dict) -> dict:
            """Ficha de leitura na memória: fatos inferidos com página, depois da indexação."""
            if settings.memory is None or settings.card_maker is None:
                return {}
            progress("ficha", 0, 1)
            try:
                markdown = library_.document_files(result["id"])["markdown"].read_text(encoding="utf-8")
                notes, card_result = settings.card_maker(
                    title=result["title"], markdown=markdown, document_id=result["id"],
                    pages=_pdf_pages(markdown))
            except (ProviderError, ValueError, OSError, KeyError, TypeError):
                return {"fichas": 0, "aviso_ficha": "A ficha de leitura não pôde ser criada agora."}
            try:
                record_usage(card_result, settings.usage_log)
            except OSError:
                pass
            created = 0
            for note in notes:
                try:
                    settings.memory.add(kind=note["kind"], text=note["text"], origin=note["origin"],
                                        skill=card_skill, source=note["source"])
                    created += 1
                except ValueError:
                    continue
            return {"fichas": created}

        worker.submit(run)
        return JSONResponse({"tarefa": job, "estado": "na fila", "arquivo": name}, 202)

    def _memory_required():
        if settings.memory is None:
            raise ValueError("Memória não configurada.")
        return settings.memory

    async def memory_list(request: Request):
        try:
            memory = _memory_required()
            if request.method == "POST":
                body = await request.json()
                if not isinstance(body, dict):
                    raise ValueError("Pedido inválido.")
                skill_ = body.get("skill")
                created = await run_in_threadpool(
                    memory.add, kind=body.get("tipo"), text=body.get("texto"), origin="comando",
                    skill=skill_ if skill_ in skills else None,
                    source={"manual": True, "conversation_id": body.get("conversa")})
                return JSONResponse(_memory_view(created), 201)
            status = request.query_params.get("estado") or None
            origin = request.query_params.get("origem") or None
            items = await run_in_threadpool(memory.list, status=status, origin=origin)
            everything = await run_in_threadpool(memory.list)
        except ValueError as exc:
            return _error(str(exc))
        counts = {name: 0 for name in ("ativa", "conflito", "superada", "revogada", "inferido")}
        for item in everything:
            counts[item["status"]] += 1
            if item["origin"] == "inferido" and item["status"] == "ativa":
                counts["inferido"] += 1
        return JSONResponse({"itens": [_memory_view(m) for m in items], "contagem": counts})

    async def memory_action(request: Request):
        action, memory_id = request.path_params["acao"], request.path_params["mid"]
        try:
            memory = _memory_required()
            if action == "historico" and request.method == "GET":
                chain = await run_in_threadpool(memory.history, memory_id)
                return JSONResponse([_memory_view(m) for m in chain])
            if request.method != "POST":
                return _error("Recurso não encontrado.", 404)
            if action == "conferir":
                return await check(memory, memory_id)
            if action == "revogar":
                changed = await run_in_threadpool(memory.revoke, memory_id)
            elif action == "editar":
                body = await request.json()
                changed = await run_in_threadpool(memory.edit, memory_id, (body or {}).get("texto"))
            elif action in {"aceitar", "manter"}:
                changed = await run_in_threadpool(memory.resolve, memory_id, accept=action == "aceitar")
            else:
                return _error("Recurso não encontrado.", 404)
        except ValueError as exc:
            return _error(str(exc), 404 if "encontrada" in str(exc) else 400)
        return JSONResponse(_memory_view(changed))

    async def check(memory, memory_id: str):
        """Confere a anotação na web e aplica as regras de conflito a uma correção."""
        if settings.checker is None:
            return _error("Busca na web não configurada.", 400)
        target = await run_in_threadpool(memory.get, memory_id)
        if target["status"] not in {"ativa", "conflito"}:
            return _error("Só anotações ativas ou em conflito podem ser conferidas.")
        try:
            verdict, result = await run_in_threadpool(settings.checker, target)
        except ProviderError:
            return _error("A busca na web não respondeu. Tente de novo em instantes.", 502)
        try:
            record_usage(result, settings.usage_log)
        except OSError:
            pass
        created = None
        if verdict["veredito"] == "contradiz" and verdict["correcao"]:
            # Correção vinda da web é dedução: supera outra dedução, mas contra a sua vira conflito.
            created = await run_in_threadpool(
                memory.add, kind=target["kind"], text=verdict["correcao"], origin="inferido",
                skill=target["skill"], supersedes=memory_id,
                source={"conferida_de": memory_id, "web": verdict["fontes"][:5],
                        "title": (verdict["fontes"][0].get("title") or verdict["fontes"][0].get("domain"))
                        if verdict["fontes"] else None,
                        "url": verdict["fontes"][0].get("uri") if verdict["fontes"] else None})
        return JSONResponse(verdict | {"criada": _memory_view(created) if created else None,
                                       "buscas": len(result.web_queries)})

    async def complete_cards(request: Request):
        """Fichas dos documentos que nunca tiveram uma: uma chamada ao Flash-Lite por documento."""
        if settings.card_extractor is None:
            return _error("A ficha do documento não está configurada.")
        library_ = settings.library_factory()
        titles = await run_in_threadpool(library_.titles_without_card)
        job = uuid.uuid4().hex
        with lock:
            settings.jobs[job] = {"estado": "processando", "etapa": "fichas", "atual": 0, "total": len(titles)}
            library_jobs.add(job)

        def run():
            counts = {"fichas": 0, "sem_dados": 0, "falhas": 0}
            try:
                for index, title in enumerate(titles, 1):
                    try:
                        # Um envio pode ter criado esta ficha enquanto a tarefa esperava: não paga duas vezes.
                        if title in library_.titles_without_card():
                            counts["fichas" if _document_card(library_, title) else "sem_dados"] += 1
                    except Exception:
                        # Erro previsto ou não: conta como falha, sem registro gravado, e a próxima rodada
                        # tenta de novo. A tarefa presa bloquearia o apagar de documentos.
                        counts["falhas"] += 1
                    with lock:
                        settings.jobs[job]["atual"] = index
            finally:
                with lock:
                    settings.jobs[job].update({"estado": "concluido", "resultado": counts})

        worker.submit(run)
        return JSONResponse({"tarefa": job, "total": len(titles)}, 202)

    async def edit_card(request: Request):
        body = await request.json()
        if not isinstance(body, dict):
            return _error("Pedido inválido.")
        library_ = settings.library_factory()
        try:
            files = await run_in_threadpool(library_.document_files, request.path_params["doc"])
            saved = await run_in_threadpool(lambda: library_.set_card(files["title"], body, edited=True))
        except ValueError as exc:
            return _error(str(exc), 404)
        return JSONResponse(saved)

    async def delete_document(request: Request):
        """Apaga de vez um documento e revoga as deduções tiradas dele (decisão de 30/09/2026)."""
        with lock:
            busy = any(settings.jobs.get(job, {}).get("estado") in {"na fila", "processando"}
                       for job in library_jobs)
        if busy:
            return _error("Espere terminar o envio ou as fichas em andamento para apagar um documento.", 409)
        library_ = settings.library_factory()
        try:
            # Pelo mesmo executor dos envios: nunca apaga enquanto um documento está sendo gravado.
            result = await asyncio.wrap_future(worker.submit(library_.delete, request.path_params["doc"]))
        except ValueError as exc:
            return _error(str(exc), 404)
        revoked = 0
        if settings.memory is not None:
            try:
                revoked = len(await run_in_threadpool(settings.memory.revoke_from_documents, result["ids"]))
            except (OSError, sqlite3.DatabaseError):
                revoked = None  # o documento já saiu; as deduções podem ser revogadas na aba Memória
        return JSONResponse({"apagado": result["title"], "versoes": result["versions"], "trechos": result["chunks"],
                             "anotacoes_revogadas": revoked, "sobras": result["leftovers"]})

    async def job_status(request: Request):
        with lock:
            # Cópia tirada com a trava: a tarefa continua sendo atualizada por outra thread.
            job = dict(settings.jobs.get(request.path_params["job"]) or {})
        return JSONResponse(job) if job else _error("Tarefa não encontrada.", 404)

    async def upload_jobs(request: Request):
        """Envios do lote mais recente, na ordem de chegada: alimenta o pop-up e o traz de volta ao recarregar."""
        with lock:
            batch = settings.jobs[upload_order[-1]]["lote"] if upload_order else None
            items = [{"id": job} | settings.jobs[job] for job in upload_order
                     if settings.jobs[job]["lote"] == batch]
        return JSONResponse({"lote": batch, "tarefas": items})

    async def document(request: Request):
        if request.path_params["kind"] == "ficha" and request.method == "POST":
            return await edit_card(request)
        if request.path_params["kind"] not in {"original", "markdown"} or request.method != "GET":
            return _error("Recurso não encontrado.", 404)
        try:
            files = await run_in_threadpool(settings.library_factory().document_files,
                                            request.path_params["doc"])
        except ValueError as exc:
            if request.path_params["kind"] == "original":
                # O original abre numa aba nova: uma página curta em vez de JSON.
                return HTMLResponse("<!doctype html><meta charset='utf-8'><title>Documento indisponível</title>"
                                    "<p style='font-family:sans-serif'>Este documento não está na biblioteca: "
                                    "ele pode ter sido apagado.</p>", 404)
            return _error(str(exc), 404)
        if request.path_params["kind"] == "original":
            media = "application/pdf" if files["original"].suffix == ".pdf" else "text/plain; charset=utf-8"
            return FileResponse(files["original"], media_type=media,
                                headers={"Content-Disposition": "inline"})
        markdown = files["markdown"].read_text(encoding="utf-8")
        return JSONResponse({"titulo": files["title"], "html": render_markdown(markdown)})

    routes = [
        Route("/", index),
        Route("/api/estado", state),
        Route("/api/conversas", conversations, methods=["GET", "POST"]),
        Route("/api/conversas/{cid}", conversation, methods=["GET", "PATCH", "DELETE"]),
        Route("/api/conversas/{cid}/mensagens", message, methods=["POST"]),
        Route("/api/biblioteca", library, methods=["GET", "POST"]),
        Route("/api/biblioteca/tarefas", upload_jobs),
        Route("/api/biblioteca/tarefas/{job}", job_status),
        Route("/api/biblioteca/fichas", complete_cards, methods=["POST"]),
        Route("/api/biblioteca/{doc}", delete_document, methods=["DELETE"]),
        Route("/api/biblioteca/{doc}/{kind:str}", document, methods=["GET", "POST"]),
        Route("/api/memoria", memory_list, methods=["GET", "POST"]),
        Route("/api/memoria/{mid}/{acao}", memory_action, methods=["GET", "POST"]),
        *science_routes(settings, worker, lock),
        *gpvs_routes(settings, lock),
        Mount("/static", StaticFiles(directory=STATIC), name="static"),
    ]
    app = Starlette(routes=routes, middleware=[Middleware(LocalOnly, port=settings.port)])
    app.state.worker = worker
    return app


def default_settings(*, data_dir: Path, library_dir: Path, port: int, results_dir: Path | None = None,
                     gpvs_dir: Path = Path("data/gpvs")) -> WebSettings:
    """Gateway e biblioteca reais; o .env já deve ter sido carregado explicitamente."""
    from aliado.agent import Agent
    from aliado.knowledge.embeddings import LocalEncoder
    from aliado.knowledge.library import DocumentLibrary
    from aliado.knowledge.metadata import extract_card
    from aliado.knowledge.rewrite import rewrite_query
    from aliado.llm.providers.gateway import build_default_gateway
    from aliado.memory.reviewer import check_memory, reading_card, review_exchange
    from aliado.memory.store import MemoryStore
    from aliado.science import digest

    gateway = build_default_gateway()
    agent = Agent(gateway)
    models = [{"alias": m["alias"], "model_id": m["model_id"]}
              for m in gateway.registry.status()["models"]
              if m["provider"] == "google" and m["configured"]]
    # Um só modelo de busca local, carregado sob demanda, serve à biblioteca e à memória.
    encoder = LocalEncoder()
    library = DocumentLibrary(library_dir, encoder=encoder)
    memory = MemoryStore(Path(data_dir) / "memoria", encoder=encoder)
    aliases = [m["alias"] for m in models]
    # Revisor e ficha usam o modelo mais barato configurado.
    helper_alias = "flash_lite" if "flash_lite" in aliases else (aliases[0] if aliases else "flash_lite")

    def execute(request):
        return gateway.execute(request, provider="google", model_alias=helper_alias)

    def stream(question, **kwargs):
        return agent.stream_answer(question, provider="google", append_sources=False, **kwargs)

    settings = WebSettings(data_dir=data_dir, library_dir=library_dir, port=port, stream=stream,
                       models=models, library_factory=lambda: library, memory=memory,
                       reviewer=lambda **kwargs: review_exchange(execute, **kwargs),
                       card_maker=lambda **kwargs: reading_card(execute, **kwargs),
                       checker=lambda memory_: check_memory(execute, memory_),
                       card_extractor=lambda **kwargs: extract_card(execute, **kwargs),
                       query_rewriter=lambda **kwargs: rewrite_query(execute, **kwargs),
                       results_dir=results_dir, gpvs_dir=gpvs_dir,
                       results_digest=lambda: digest.cached(settings.results_dir, settings.reference_dir))
    return settings
