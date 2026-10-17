"""Servidor local do AL-IAdo: conversa, biblioteca e fontes, acessível só por 127.0.0.1.

Importado apenas por `aliado web`; o restante do pacote não carrega Starlette.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
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

from aliado import routing
from aliado.interfaces.web.conversations import ConversationStore
from aliado.interfaces.web.gpvs_runs import gpvs_routes
from aliado.interfaces.web.obsidian import ObsidianSync, build_notes, write_vault
from aliado.interfaces.web.rendering import render_markdown
from aliado.interfaces.web.science import science_routes
from aliado.knowledge import figures, reading
from aliado.knowledge.coverage import make_plan
from aliado.knowledge.metadata import reference
from aliado.knowledge.rewrite import rewrite_kind
from aliado.knowledge.stopwords import plain
from aliado.llm.providers.base import ProviderError, ProviderNotConfiguredError
from aliado.llm.usage_log import record_usage
from aliado.memory.reviewer import needs_review
from aliado.memory.store import TRAIL_QUESTION, TRAIL_STRONG, trail_pages
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
# Modelo que descreve as figuras e tabelas (lote 29), escolhido pelo pesquisador no piloto de 03/10/2026,
# e os nomes mostrados no aviso antes de enviar.
FIGURE_ALIAS = "flash"
MODEL_NAMES = {"flash": "Flash", "flash_lite": "Flash-Lite"}
# Leitura dos documentos numa pergunta. "auto" (lote 31) é o padrão: o roteador escolhe o degrau da escada.
# Os outros fixam um degrau: trechos, páginas inteiras, o documento citado ou fixado, e a leitura ampla do lote 30.
READING_MODES = ("auto", "trechos", "paginas", "documento", "integral")
RUNG_OF = {"trechos": routing.PASSAGES, "paginas": routing.PAGES, "documento": routing.DOCUMENT,
           "integral": routing.WIDE}
MODE_OF = {rung: mode for mode, rung in RUNG_OF.items()}
# Tipos de pergunta cuja resposta vem dos documentos: deixam trilha e, sem citação, sobem um degrau.
LIBRARY_INTENTS = {"fato", "sintese", "metodo", "visual", "documento"}
# A trilha é achada pela consulta de busca, que diz o assunto. Sem ela, uma pergunta com menos palavras que
# isto não deixa nem segue trilha ("Traga outra fonte." serve a qualquer assunto).
TRAIL_WORDS = 5
# Quantas páginas de uma resposta anterior voltam ao modelo; e quantas das páginas de uma leitura ficam
# reservadas para as de respostas parecidas, sem tirar o lugar das que a busca achou.
TRAIL_PAGES = 6
RESERVED_PAGES = 3
# Teto de tokens de documentos nos degraus das páginas e do documento.
DOCUMENT_BUDGET = 60_000
# Na escolha automática, o documento citado só vai inteiro se couber nesta parte do teto sem confirmação.
DOCUMENT_SHARE = 0.6
# Custo de uma página inteira com a sua linha na lista, para a estimativa do botão "Ler mais fundo".
PAGE_ESTIMATE = reading.PAGE_TOKENS + 55


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
    # Espelho para o Obsidian (lote 28): pasta das notas, refeitas a cada mudança; None desliga.
    obsidian_dir: Path | None = None
    # Descrição de figuras e tabelas (lote 29): pedido com a imagem da página -> resultado; e o nome do
    # modelo, para o aviso antes de enviar. Só por pedido do usuário, nunca sozinha.
    figure_reader: Callable[[object], object] | None = None
    figure_model: str | None = None
    # Leitura integral (lote 30): o modo e o teto de tokens que valem quando a página não diz outro; e o que
    # ficou no serviço de arquivos do Google: () -> lista dos envios, e () -> apaga de lá e limpa o registro.
    reading_mode: str = "auto"
    reading_budget: int = reading.DEFAULT_BUDGET
    # Escada de leitura (lote 31): acima de `ceiling` tokens estimados, uma leitura pede confirmação; depois de
    # `daily_warning` tokens no dia, toda leitura acima dos trechos pede.
    ceiling: int = 30_000
    daily_warning: int = 300_000
    uploaded_files: Callable[[], list[dict]] | None = None
    forget_files: Callable[[], dict] | None = None

    def __post_init__(self):
        self.data_dir = Path(self.data_dir).resolve()
        self.library_dir = Path(self.library_dir).resolve()
        self.usage_log = Path(self.usage_log or self.data_dir / "uso" / "chamadas.jsonl")
        self.results_dir = Path(self.results_dir or self.data_dir / "resultados").resolve()
        self.gpvs_dir = Path(self.gpvs_dir).resolve()
        self.reference_dir = Path(self.reference_dir).resolve()
        if self.obsidian_dir is not None:
            self.obsidian_dir = Path(self.obsidian_dir).resolve()
            # No Windows, "Conversas" e "conversas" são a mesma pasta: o espelho não pode cair sobre os dados,
            # nem dentro nem em volta de uma pasta que o AL-IAdo usa.
            owned = [self.data_dir / name for name in (
                "conversas", "memoria", "uploads-temporarios", "uso", "resultados", "ciencia", "bibliotecas", "gpvs",
                "models", "tools", "memory-review", "avaliacao-busca")] + [
                self.usage_log.parent, self.library_dir, self.results_dir, self.gpvs_dir, self.reference_dir]
            if self.obsidian_dir == self.data_dir or self.obsidian_dir in self.data_dir.parents or any(
                    self.obsidian_dir == folder or folder in self.obsidian_dir.parents
                    or self.obsidian_dir in folder.parents for folder in owned):
                raise ValueError("A pasta do Obsidian precisa ser uma pasta própria, separada dos dados do AL-IAdo.")


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


def _local_day(stamp: str) -> str:
    """O dia de um registro no horário deste computador: o "hoje" da tela vira à meia-noite daqui."""
    try:
        return datetime.fromisoformat(stamp).astimezone().date().isoformat()
    except ValueError:
        return stamp[:10]


def _usage_totals(path: Path) -> dict:
    today = datetime.now().astimezone().date().isoformat()
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
        if _local_day(str(entry.get("timestamp", ""))) == today:
            totals["hoje"] += tokens
    return totals


def _trail(question: str, sources, status: str | None, key: str | None = None) -> list[dict] | None:
    """As páginas que uma resposta conferida citou: a trilha da pergunta (lote 31). Sem a consulta de busca,
    que diz o assunto, uma pergunta curta não deixa trilha."""
    if status != "citation_ids_verified" or (not key and len(question.split()) < TRAIL_WORDS):
        return None
    pages = [{"sha256": source.get("sha256"), "page": source.get("page"),
              "title": source.get("referencia") or source.get("title")} for source in sources or ()]
    return [page for page in pages if page["sha256"] and page["page"] is not None] or None


def _mentions(library_, terms: list[str], cards: dict, named, total: int) -> dict | None:
    """A contagem exata dos termos da pergunta (lote 31), enxuta para o modelo. O nome de um autor citado não
    é assunto; um termo que aparece em mais da metade dos documentos vai só com o número."""
    skip = {plain(word) for title in named
            for word in re.findall(r"[^\W\d_]+", (cards.get(title) or {}).get("referencia") or "")}
    wanted = [term for term in terms if plain(term) not in skip]
    if not wanted:
        return None
    try:
        found = library_.mentions(wanted)
    except (ValueError, sqlite3.DatabaseError):
        return None
    view = {}
    for term, entry in found.items():
        if total and entry["documentos"] > total / 2:
            view[term] = {"documentos": entry["documentos"], "de": total}
            continue
        names = [(item["referencia"] or item["title"], item) for item in entry["onde"]]
        view[term] = {"documentos": entry["documentos"], "de": total, "onde": [
            f"{name}: {item['locais']} página(s)" + (f" ({', '.join(map(str, item['paginas']))})" if item["paginas"] else "")
            + (", só em figura" if item["so_em_figura"] else "") for name, item in names[:8]]}
        if names[8:]:
            view[term]["outros"] = [name for name, _ in names[8:]]
    return view or None


def _passage_tokens(hits) -> int:
    return sum(len(hit.get("passagem") or hit.get("text") or "") for hit in hits) // reading.CHARS_PER_TOKEN


def _deeper(rung: int, result, library_, budget: int) -> dict | None:
    """O degrau seguinte da escada e quanto ele custaria, para o botão "Ler mais fundo" (lote 31)."""
    if library_ is None or not routing.PASSAGES <= rung < routing.WIDE or result.provider == "local":
        return None
    used = (result.usage.input_tokens if result.usage else 0) or 0
    read = getattr(result, "reading", None) or {}
    sent = read.get("tokens_estimados") or 0 if read else _passage_tokens([*result.sources, *result.retrieved])
    base = max(used - sent, 0)
    if rung == routing.PASSAGES:
        return {"leitura": "paginas", "tokens": base + reading.TOP_PAGES * PAGE_ESTIMATE}
    if rung == routing.PAGES:
        top = next((hit.get("document_id") for hit in [*result.sources, *result.retrieved] if hit.get("document_id")), None)
        try:
            record = library_.pages(top) if top else None
        except (ValueError, AttributeError):
            record = None
        if record:
            cost = sum(reading.page_cost(unit["text"], record["pdf"]) for unit in record["units"])
            return {"leitura": "documento", "tokens": base + min(cost, DOCUMENT_BUDGET), "documentos": [top],
                    "titulo": record["referencia"] or record["title"]}
    return {"leitura": "integral", "tokens": base + budget, "ate": True}


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
                    answer=answer["content"], skill=question.get("skill"), created_at=answer.get("created_at"),
                    key=answer.get("consulta_biblioteca"),
                    pages=_trail(question["content"], answer.get("sources"), answer.get("validation_status"),
                                 answer.get("consulta_biblioteca")) if
                    not answer.get("cobertura") or answer["cobertura"].get("completa") else None)
    memory.fill_missing_vectors()
    return added


def create_app(settings: WebSettings) -> Starlette:
    # A página é lida do disco a cada carga, e este programa só muda quando é reiniciado. Com a hora em que
    # ele começou, a página sabe se é mais nova do que ele e pede o reinício (lote 30).
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    store = ConversationStore(settings.data_dir / "conversas")
    uploads = settings.data_dir / "uploads-temporarios"
    worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aliado-biblioteca")
    lock = threading.Lock()
    library_jobs: set[str] = set()  # envios, fichas e figuras; enquanto correm, nenhum documento é apagado
    figure_jobs: dict[str, dict] = {}  # documento -> tarefa de descrição das figuras em andamento e o seu "parar"
    upload_order: list[str] = []  # envios na ordem de chegada; o lote mais recente alimenta o pop-up da página
    skills = {item.name: item.description for item in list_skills()}
    aliases = {model["alias"] for model in settings.models}
    if settings.memory is not None:
        # Conversas anteriores ao lote 18 entram na memória de conversas uma vez, sem travar a abertura.
        worker.submit(_index_conversations, store, settings.memory)

    def export_obsidian() -> dict:
        # Tudo é lido antes de gravar: uma falha de leitura deixa o cofre anterior como estava.
        memories = settings.memory.list() if settings.memory is not None else []
        return write_vault(settings.obsidian_dir, build_notes(store.snapshot(), _documents(), memories))

    sync = ObsidianSync(export_obsidian) if settings.obsidian_dir is not None else None

    def obsidian() -> None:
        """Pede a atualização das notas do Obsidian; a rodada corre em fila própria, fora do pedido."""
        if sync is not None:
            sync.request()

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
            "leitura": {"modo": settings.reading_mode, "teto": settings.reading_budget, "tetos": list(reading.BUDGETS),
                        "modos": list(READING_MODES), "limite": settings.ceiling, "aviso_diario": settings.daily_warning},
            "iniciado": started,
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
                obsidian()
                return JSONResponse({"apagada": True})
            if request.method == "PATCH":
                body = await request.json()
                if "fixados" in body:
                    # Só entram documentos que estão na biblioteca; a ordem dada é a ordem de leitura.
                    known = {document["id"] for document in await run_in_threadpool(_documents)}
                    wanted = body["fixados"]
                    data = store.pin(request.path_params["cid"],
                                     [item for item in wanted if item in known] if isinstance(wanted, list) else wanted)
                if "title" in body or "fixados" not in body:
                    data = store.rename(request.path_params["cid"], body.get("title"))
                    obsidian()
            else:
                data = store.get(request.path_params["cid"])
        except (ValueError, AttributeError) as exc:
            return _error(str(exc), 404 if "encontrada" in str(exc) else 400)
        pinned = await run_in_threadpool(_pinned, data)
        return JSONResponse(data | {"messages": [_view(m) for m in data["messages"]], "fixados": pinned})

    # Lote 33: os nomes dos resultados para o roteador, tirados do último resumo montado; o resumo só é montado
    # para isso uma vez, e depois é refeito apenas quando uma pergunta precisa dos resultados.
    known_vocabulary: dict = {}

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
        # "auto" (lote 31): o roteador escolhe a skill, o modelo ou a leitura; um nome fixa a escolha.
        if skill not in {"nenhuma", "auto"} and skill not in skills or support and support not in skills:
            return _error("Skill desconhecida.")
        if alias != "auto" and alias not in aliases or not aliases:
            return _error("Modelo não configurado. Confira o .env.")
        if "resultados" not in body:
            use_results = skill in {RESULTS_SKILL, "auto"}
        mode = body.get("leitura") or settings.reading_mode
        budget = body.get("teto") or settings.reading_budget
        if mode not in READING_MODES or budget not in reading.BUDGETS:
            return _error("Modo de leitura ou teto desconhecido.")
        confirmed = body.get("confirmado") if isinstance(body.get("confirmado"), str) else None
        asked = [item for item in body.get("documentos") or () if isinstance(item, str)] \
            if isinstance(body.get("documentos"), list) else []
        pinned = [item for item in data.get("fixados") or () if isinstance(item, str)]
        history = store.history(data)
        last_user = next((m for m in reversed(data["messages"]) if m.get("role") == "user"), None)
        last_reply = next((m for m in reversed(data["messages"]) if m.get("role") == "assistant"), None)
        # A rota da resposta anterior: uma mensagem curta continua o assunto e a leitura dela.
        before = (last_reply or {}).get("rota") or {}
        # Uma leitura cara, escolhida por você, não é herdada sozinha: a continuação vai até as páginas.
        previous = {"rung": min(before.get("rung", routing.PASSAGES if (last_user or {}).get("biblioteca")
                                           else routing.NONE), routing.PAGES),
                    "results": bool(before.get("results"))} if last_reply else None
        words = len(text.split())

        def line(payload: dict) -> str:
            return json.dumps(payload, ensure_ascii=False) + "\n"

        def events():
            # Gerador síncrono: o Starlette o consome numa thread, sem travar o servidor.
            source = settings.library_factory() if use_library or pinned else None
            try:
                documents = source.documents() if hasattr(source, "documents") else []
                cards = source.cards() if hasattr(source, "cards") else {}
            except (ValueError, OSError, sqlite3.DatabaseError):
                documents, cards = [], {}  # sem o catálogo, a rota sai só das regras e da mensagem
            # Roteador local (lote 31): sem custo, decide o que a mensagem precisa antes de qualquer chamada paga.
            found = routing.route(
                text, encoder=getattr(source, "encoder", None), cards=cards, skills=list(skills),
                current_skill=(last_user or {}).get("skill") if skill == "auto" else skill,
                library=source is not None, results=use_results, previous=previous, vocabulary=vocabulary())
            reasons = list(found.reasons)
            # Escolhas aprendidas (lote 33): numa mensagem muito parecida com outra, vale a escolha que você fez nela.
            auto_model, auto_skill, auto_rung, learned = found.model, found.skill or "nenhuma", found.rung, []
            lessons = lessons_for(text)
            if "model" in lessons and lessons["model"]["value"] in aliases:
                auto_model = lessons["model"]["value"]
                learned.append(lessons["model"] | {"campo": "modelo"})
            if "skill" in lessons and lessons["skill"]["value"] in {"nenhuma", *skills}:
                auto_skill = lessons["skill"]["value"]
                learned.append(lessons["skill"] | {"campo": "skill"})
            # Só quando o roteador já vai à biblioteca: um seletor fixado na tela fica guardado entre as sessões, e um
            # "Oi" enviado com ele não pode passar a ler páginas no modo automático.
            if "rung" in lessons and source is not None and found.rung > routing.NONE:
                # Nunca a leitura ampla; o documento inteiro, só quando a mensagem cita um documento.
                auto_rung = min(int(lessons["rung"]["value"]), routing.DOCUMENT if found.named else routing.PAGES)
                learned.append(lessons["rung"] | {"campo": "leitura"})
            chosen = auto_skill if skill == "auto" else skill
            memory_skill = None if chosen == "nenhuma" else chosen
            # O modelo que a escolha automática usaria; um alias que não está configurado cai no primeiro que está.
            auto_model = auto_model if auto_model in aliases else sorted(aliases)[0]
            model = alias if alias != "auto" else auto_model
            rung = auto_rung if mode == "auto" else RUNG_OF[mode] if source is not None else routing.NONE
            ids = {document.get("title"): document["id"] for document in documents if document.get("id")}
            known = set(ids.values())
            named = [ids[title] for title in found.named if title in ids]
            fixed = list(dict.fromkeys([*pinned, *(item for item in asked if item in known)]))
            focus = []
            if rung == routing.DOCUMENT and mode == "auto" and not fixed:
                try:
                    cost = sum(reading.page_cost(unit["text"], record["pdf"])
                               for record in map(source.pages, named) for unit in record["units"])
                except (ValueError, AttributeError):
                    cost = 0
                if cost > settings.ceiling * DOCUMENT_SHARE:
                    # Um livro citado pelo autor não vai inteiro sem você pedir: vão as páginas mais próximas.
                    rung, focus = routing.PAGES, named
                    reasons.append("o documento citado é grande: foram lidas as páginas dele mais próximas da pergunta")
            if rung == routing.PASSAGES and fixed:
                rung = routing.DOCUMENT  # os fixados na conversa vão inteiros, e o resto, por trechos
            by_passages = bool(use_web and (fixed or rung > routing.PASSAGES))
            if use_web:
                # Com a busca na web ligada, o pedido segue por trechos (lote 30).
                rung = min(rung, routing.PASSAGES)
            searches = rung > routing.NONE and use_library
            # Reescrita seletiva (lote 33): sem chamada quando a mensagem já diz o assunto; o plano, só com partes.
            preparation = rewrite_kind(text, history, intent=found.intent) if searches else None
            rewritten, rewrite_tokens = rewrite(plan=preparation == "plano") if preparation in {"simples", "plano"} else (None, 0)
            search_query = rewritten.get("consulta") if isinstance(rewritten, dict) else rewritten
            plan = make_plan(text, history, rewritten) if preparation == "plano" else None
            search_plan = plan if plan and len(plan["unidades"]) > 1 else None
            # Trilhas (lote 31): uma pergunta já respondida leva de volta às páginas que a resposta citou.
            trail, priority, reserve, strong, asked_again = None, [], [], False, False
            follows = mode == "auto" and rung in {routing.PASSAGES, routing.PAGES} and found.intent in LIBRARY_INTENTS \
                and (search_query or words >= TRAIL_WORDS) and settings.memory is not None
            if follows:
                try:
                    matches = settings.memory.trail(search_query or text, question=text, limit=5)
                except (ValueError, OSError, sqlite3.DatabaseError, AttributeError):
                    matches = []

                def same(match: dict) -> bool:
                    # O mesmo assunto e o mesmo pedido: só assim as páginas de antes respondem à pergunta de agora.
                    return match["similaridade"] >= TRAIL_STRONG and match.get("pergunta_parecida", 1.0) >= TRAIL_QUESTION
                by_sha = {document["sha256"]: document["id"] for document in documents
                          if document.get("sha256") and document.get("id")}

                def located(pages) -> list[tuple]:
                    # Documento apagado sai da trilha: só valem as páginas de arquivos que estão na biblioteca.
                    return [(by_sha[page["sha256"]], page["page"]) for page in pages if page["sha256"] in by_sha]

                best = next((match for match in matches if same(match)), None)
                if last_reply and any(match["message_id"] == last_reply.get("id") and same(match) for match in matches):
                    # A mesma pergunta, feita de novo logo em seguida: a resposta não bastou.
                    rung, priority, asked_again = routing.PAGES, located(trail_pages(matches))[:TRAIL_PAGES], True
                    reasons.append("a pergunta foi refeita em seguida: leitura mais funda")
                elif best and located(best["pages"]) and not search_plan and not best.get("fraca"):
                    # Lote 31: uma parte só e uma resposta que bastou: parte das páginas dela, sem nova busca.
                    strong, trail, priority = True, best, located(best["pages"])[:TRAIL_PAGES]
                    reasons.append("pergunta muito parecida com uma já respondida: partiu das páginas daquela resposta")
                elif best and located(best["pages"]):
                    # Lote 33: com mais partes, ou depois de uma reclamação, as páginas de antes só apoiam a busca.
                    trail, reserve = best, located(best["pages"])[:RESERVED_PAGES]
                    reasons.append("páginas de uma resposta anterior apoiam uma nova busca")
                elif rung == routing.PAGES:
                    reserve = located(trail_pages(matches))[:RESERVED_PAGES]

            def reading_of(step: int, *, from_trail: bool = False, first: list | None = None,
                           kept: list | None = None) -> dict | None:
                """As opções de leitura de um degrau; None é o pedido por trechos (ou sem biblioteca)."""
                if from_trail:
                    return {"budget": DOCUMENT_BUDGET, "fixed": [], "whole": False, "search": False,
                            "pages": TRAIL_PAGES, "priority": first or []}
                if step == routing.PAGES:
                    return {"budget": DOCUMENT_BUDGET, "fixed": fixed, "whole": False, "search": use_library,
                            "pages": reading.TOP_PAGES, "priority": first or []} | ({"reserve": kept} if kept else {}) \
                        | ({"focus": focus} if focus else {})
                if step == routing.DOCUMENT:
                    return {"budget": DOCUMENT_BUDGET, "fixed": list(dict.fromkeys([*fixed, *named])), "whole": False,
                            "search": use_library, "top": 1}
                if step == routing.WIDE:
                    return {"budget": budget, "fixed": fixed, "whole": True, "search": use_library}
                return None

            memories, recalled = [], []
            if settings.memory is not None:
                try:
                    memories = settings.memory.relevant(text, skill=memory_skill)
                    # Numa pergunta à biblioteca, uma conversa anterior basta; na conversa solta, vão até três.
                    recalled = settings.memory.recall(text, exclude_conversation=cid,
                                                      **({"limit": 1} if rung > routing.NONE else {}))
                except (ValueError, OSError, sqlite3.DatabaseError):
                    memories, recalled = [], []  # a conversa segue sem memória em vez de falhar
            if trail:
                recalled = [item for item in recalled if item["message_id"] != trail["message_id"]]
            digest, missing = results_for_request() if found.results else (None, [])
            mentions = None
            if rung > routing.NONE and found.intent in {"acervo", "documento"} and hasattr(source, "mentions"):
                mentions = _mentions(source, routing.terms(f"{text} {search_query or ''}"), cards, found.named,
                                     len({document.get("title") for document in documents}))
            today = _usage_totals(settings.usage_log)["hoje"]
            over = today >= settings.daily_warning

            def options(step: int, read: dict | None, *, alias_: str, limit: int | None) -> dict:
                extra = ({"results": digest} if digest else {}) | ({"reading": read} if read else {})
                extra |= {} if found.catalog or step == routing.NONE else {"catalog": False}
                extra |= {} if found.references else {"references": False}
                extra |= {"reasoning_level": found.reasoning} if found.reasoning and alias_ == found.model else {}
                extra |= {"mentions": mentions} if mentions else {}
                extra |= {"search_plan": search_plan} if search_plan else {}
                if limit is not None:
                    extra |= {"ceiling": limit, "salt": "dia" if over else ""} | ({"confirmed": confirmed} if confirmed else {})
                return {"model_alias": alias_, "skill_name": memory_skill, "supporting_skill_name": support,
                        "library": source if step > routing.NONE else None, "history": history, "memories": memories,
                        "web_search": use_web, "recalled": recalled, "search_query": search_query} | extra

            def run(call: dict, before: str | None = None):
                """Uma chamada ao modelo em fluxo; devolve ("final", resultado) ou ("confirmar", estimativa)."""
                final = None
                for kind, value in settings.stream(text, **call):
                    if kind == "confirmar":
                        return kind, value
                    if before is not None:
                        yield before
                        before = None
                    if kind == "inicio":
                        continue  # o pedido passou pelo teto e seguiu ao modelo
                    if kind == "texto":
                        yield line({"tipo": "texto", "texto": value})
                    else:
                        final = value
                return "final", final

            # Acima do teto, uma leitura pede confirmação; depois do aviso diário, toda leitura acima dos trechos.
            limit = None if rung <= routing.PASSAGES else 0 if over else settings.ceiling
            first = reading_of(rung, from_trail=strong, first=priority, kept=reserve)
            call = options(rung, first, alias_=model, limit=limit) | ({"trail": trail} if trail and trail[
                "conversation_id"] != cid else {})
            attempts, result = [], None
            recorded = False
            try:
                kind, result = yield from run(call)
                if kind == "confirmar":
                    yield line({"tipo": "confirmar", "tokens": result["tokens"], "chave": result.get("chave"),
                                "limite": settings.ceiling, "motivo": "dia" if over else "teto", "hoje": today,
                                "aviso_diario": settings.daily_warning, "lembrar": not over,
                                "modo": MODE_OF.get(rung, "trechos"), "leitura": result.get("leitura")})
                    return
                # Lote 33: a segunda chamada só vale se houver o que ler de novo: partes sem citação com material
                # que a busca achou e não enviou, ou, saindo dos trechos, as páginas inteiras do que foi enviado.
                gaps = [unit for unit in ((result.coverage or {}).get("unidades") or ()) if not unit["citados"]
                        and (unit["estado"] == "nao_enviado" or (unit["estado"] == "sem_citacao" and rung == routing.PASSAGES))]
                partial = bool(result is not None and result.coverage and not result.coverage["completa"] and gaps)
                climbs = (result is not None and mode == "auto" and not use_web and not result.truncated
                          and result.validation_status not in OUT_OF_CONTEXT and found.intent in LIBRARY_INTENTS
                          and (partial or (not search_plan and not over and result.validation_status == "uncited"
                                           and (rung == routing.PASSAGES or strong))))
                if climbs:
                    # A resposta não citou nenhum documento, ou deixou partes sem citação: sobe um degrau, se couber.
                    spent = (result.usage.total_tokens if result.usage else 0) or 0
                    stronger = model if alias != "auto" else routing.STRONG if routing.STRONG in aliases else model
                    daily = _usage_totals(settings.usage_log)["hoje"] + spent >= settings.daily_warning
                    second = options(routing.PAGES, reading_of(routing.PAGES), alias_=stronger,
                                     limit=0 if daily else max(settings.ceiling - spent - rewrite_tokens, 0))
                    second.pop("confirmed", None)
                    if partial:
                        missing_units = [u for u in result.coverage["unidades"] if not u["citados"]]
                        names = [u["nome"] for u in missing_units]
                        second["supplement"] = {"sem_citacao": names, "resposta_anterior": result.content}
                        # As lacunas ganham a primeira vaga, mas as partes atendidas também são recuperadas
                        # para a resposta consolidada citar apenas fontes enviadas nesta chamada.
                        second["search_plan"] = search_plan | {"unidades": sorted(search_plan["unidades"],
                            key=lambda u: u["nome"] not in names)}
                    notice = ("Completando a pesquisa nas partes sem citação…" if partial
                              else "Os trechos não bastaram: lendo as páginas inteiras…")
                    try:
                        kind, better = yield from run(second, before=line({"tipo": "recomeco", "texto": notice}))
                    except (ProviderError, ValueError, OSError):
                        kind, better = "falhou", None
                        if result.coverage:
                            result = replace(result, coverage=result.coverage | {"complemento": "falhou"})
                    if kind == "confirmar" and result.coverage:
                        result = replace(result, coverage=result.coverage | {
                            "complemento": "confirmacao_necessaria", "tokens_complemento": better["tokens"]})
                    if kind == "final" and better is not None:
                        first_read = "páginas de uma resposta anterior" if strong else routing.RUNG_NAMES[rung]
                        if result.provider != "local":
                            try:
                                record_usage(result, settings.usage_log)
                                recorded = True
                            except OSError:
                                pass
                        old_covered = {u["id"] for u in (result.coverage or {}).get("unidades", []) if u["citados"]}
                        new_covered = {u["id"] for u in (better.coverage or {}).get("unidades", []) if u["citados"]}
                        usable = not better.truncated and better.validation_status not in OUT_OF_CONTEXT \
                            and better.results_status != UNVERIFIED_RESULTS and old_covered <= new_covered
                        if usable:
                            attempts.append({"leitura": first_read, "tokens": spent})
                            result, rung, model, strong, trail = better, routing.PAGES, stronger, False, None
                            recorded = False
                            reasons.append("a primeira leitura deixou partes sem citação: completou a pesquisa" if partial
                                           else "a primeira leitura não achou a resposta: subiu um degrau")
                        else:
                            # A primeira já foi contabilizada: a última etapa registra a tentativa rejeitada, e a rota
                            # mostra quanto ela custou (lote 33).
                            attempts.append({"leitura": routing.RUNG_NAMES[routing.PAGES], "descartada": True,
                                             "tokens": (better.usage.total_tokens if better.usage else 0) or 0})
                            if better.provider != "local":
                                try:
                                    record_usage(better, settings.usage_log)
                                except OSError:
                                    pass
                            if result.coverage:
                                result = replace(result, coverage=result.coverage | {"complemento": "sem_melhora"})
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
            if result.provider != "local" and not recorded:
                try:
                    record_usage(result, settings.usage_log)
                except OSError:
                    pass
            # Resposta cortada pelo teto de tamanho (lote 27): aparece com aviso e fica fora do histórico.
            in_context = (result.validation_status not in OUT_OF_CONTEXT and result.provider != "local"
                          and result.results_status != UNVERIFIED_RESULTS and not result.truncated)
            user = {"role": "user", "content": text.strip(), "in_context": in_context,
                    "skill": chosen, "apoio": support, "biblioteca": use_library, "web": use_web,
                    "resultados": use_results, "leitura": mode, "teto": budget}
            # A rota (lote 31): o que o roteador decidiu, o que foi escolha sua e o que foi lido de fato.
            route_view = found.view() | {
                "rung": rung, "leitura": "páginas de uma resposta anterior" if strong else routing.RUNG_NAMES[rung],
                "skill": memory_skill, "model": model, "reasons": reasons, "results": bool(digest),
                "automatico": {"modelo": alias == "auto", "skill": skill == "auto", "leitura": mode == "auto"},
                "tentativas": attempts,
                # Lote 33: como a busca foi preparada: sem reescrita, reescrita simples ou uma busca por parte do pedido.
                "busca": "plano" if search_plan else "simples" if preparation == "plano" else preparation,
                "partes": [unit["nome"] for unit in search_plan["unidades"]] if search_plan else [],
                # Lote 33: as escolhas suas que esta resposta repetiu, com a mensagem e a data de cada uma.
                "aprendido": [{"campo": lesson["campo"], "data": lesson["created_at"],
                               "pergunta": " ".join(lesson["question"].split())[:200]} for lesson in learned
                              if (lesson["campo"] == "modelo" and alias == "auto") or (lesson["campo"] == "skill" and skill == "auto")
                              or (lesson["campo"] == "leitura" and mode == "auto")],
                "trilha": {"data": trail["created_at"], "pergunta": " ".join(trail["question"].split())[:200],
                           "conversa": trail["conversation_id"]} if trail else None}
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
                     # Lote 30: os documentos lidos inteiros ou em blocos; e se a web fez a leitura cair para trechos.
                     "leitura": getattr(result, "reading", None),
                     "leitura_por_trechos": by_passages,
                     "cobertura": result.coverage,
                     "rota": route_view,
                     "aprofundar": None if use_web else _deeper(rung, result, source, budget),
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
                        created_at=stored["messages"][-1].get("created_at"),
                        # A trilha: as páginas citadas, quando a pergunta é das que os documentos respondem.
                        **({"pages": pages, "key": search_query} if found.intent in LIBRARY_INTENTS
                            and (result.coverage is None or result.coverage.get("completa")) and (
                            pages := _trail(text, result.sources, result.validation_status, search_query)) else {}))
                except (OSError, sqlite3.DatabaseError):
                    pass  # a resposta já foi guardada; a memória de conversas não deve derrubá-la
            learn(auto_model, auto_skill, auto_rung, asked_again, found.complaint)
            obsidian()  # antes do aviso de fim: vale mesmo se a página for fechada em seguida
            yield line({"tipo": "fim", "conversa": {k: stored[k] for k in ("id", "title", "updated_at")},
                        "mensagens": [_view(m) for m in stored["messages"][-2:]]})
            if in_context and settings.memory is not None and settings.reviewer is not None and needs_review(
                    text, explicit=bool(EXPLICIT_MEMORY.match(text)), history=history):
                yield line(review(stored, memories, result))

        def results_for_request() -> tuple[dict | None, list[str]]:
            """O resumo dos resultados e o que faltou, em palavras; uma falha aqui não derruba a conversa."""
            if not use_results or settings.results_digest is None:
                return None, []
            try:
                digest = results_digest()
            except Exception:  # o resumo é opcional: qualquer falha dele deixa a conversa seguir
                return None, ["os resultados da pesquisa (não foi possível montá-los)"]
            return (digest if digest.get("blocos") else None), list(digest.get("faltando") or ())

        built: dict = {}

        def results_digest() -> dict:
            """O resumo dos resultados, montado no máximo uma vez por mensagem."""
            if "resumo" not in built:
                built["resumo"] = settings.results_digest()
                known_vocabulary["nomes"] = routing.results_vocabulary(built["resumo"])
            return built["resumo"]

        def vocabulary() -> dict | None:
            """Os nomes dos resultados para o roteador (lote 33); sem o resumo, o roteador usa os de sempre."""
            if "nomes" in known_vocabulary or settings.results_digest is None:
                return known_vocabulary.get("nomes")
            try:
                results_digest()
            except Exception:  # o resumo é opcional, como em results_for_request
                return None
            return known_vocabulary.get("nomes")

        def lessons_for(question: str) -> dict:
            """As escolhas aprendidas para a mensagem (lote 33); uma falha da memória não derruba a rota."""
            if settings.memory is None or not hasattr(settings.memory, "route_lessons"):
                return {}
            try:
                return settings.memory.route_lessons(question)
            except (ValueError, OSError, sqlite3.DatabaseError):
                return {}

        def learn(auto_model: str, auto_skill: str, auto_rung: int, asked_again: bool, complaint: bool) -> None:
            """Aprendizado com o uso (lote 33), local e sem tokens. Uma escolha fixada na tela que difere da automática
            fica guardada para a mensagem; a pergunta refeita, o "Ler mais fundo" e a reclamação enfraquecem a trilha
            da resposta anterior, e a pergunta dela fica guardada com a leitura mais funda."""
            memory = settings.memory
            if memory is None or not hasattr(memory, "learn_route"):
                return
            again = bool(last_user and " ".join(last_user["content"].split()) == " ".join(text.split()))
            # Só o que você escolheu nesta mensagem: um campo ausente do pedido não é escolha.
            chosen_rung = RUNG_OF.get(mode) if body.get("leitura") else None
            lessons = []
            if body.get("modelo") and alias != "auto" and alias != auto_model:
                lessons.append((text, "model", alias, "escolha"))
            if body.get("skill") and skill != "auto" and skill != auto_skill:
                lessons.append((text, "skill", skill, "escolha"))
            if chosen_rung is not None and chosen_rung != routing.WIDE and chosen_rung != auto_rung:
                lessons.append((text, "rung", str(chosen_rung), "refeita" if again else "escolha"))
            if asked_again:
                lessons.append((text, "rung", str(routing.PAGES), "refeita"))
            complained = complaint and last_user is not None
            if complained:
                lessons.append((last_user["content"], "rung", str(routing.PAGES), "reclamacao"))
            try:
                for question, field_, value, origin in lessons:
                    memory.learn_route(question=question, field=field_, value=value, origin=origin, conversation_id=cid)
                if last_reply and last_reply.get("id") and (again or asked_again or complained):
                    memory.weaken_trail(last_reply["id"])
            except (ValueError, OSError, sqlite3.DatabaseError):
                pass  # o aprendizado é um extra: a resposta já foi guardada

        def rewrite(*, plan: bool = False) -> tuple[str | dict | None, int]:
            """Consulta da busca pelo modelo mais barato; sem ela, a busca segue pela própria pergunta. Com `plan`,
            vem também o plano por partes (lote 33: só quando o pedido tem partes)."""
            if settings.query_rewriter is None:
                return None, 0
            try:
                query, rewrite_result = settings.query_rewriter(question=text, history=history,
                                                                **({"plan": True} if plan else {}))
            except (ProviderError, ValueError, KeyError, TypeError):
                return None, 0
            try:
                record_usage(rewrite_result, settings.usage_log)
            except OSError:
                pass
            return query, (rewrite_result.usage.total_tokens or 0) if rewrite_result.usage else 0

        def review(stored: dict, memories: list[dict], result) -> dict:
            """Revisor depois da resposta: a conversa já está salva, e uma falha aqui não a afeta."""
            reply_id = stored["messages"][-1]["id"]
            try:
                memory_skill = stored["messages"][-2].get("skill")
                memory_skill = None if memory_skill == "nenhuma" else memory_skill
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
            if views:
                obsidian()
            return {"tipo": "memoria", "mensagem": reply_id, "criadas": views}

        return StreamingResponse(events(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    def _documents() -> list[dict]:
        if not (settings.library_dir / "catalog.sqlite3").exists():
            return []
        return settings.library_factory().documents()

    def _pinned(data: dict) -> list[dict]:
        """Os documentos fixados na conversa que ainda estão na biblioteca, com o nome a mostrar."""
        wanted = [item for item in data.get("fixados") or () if isinstance(item, str)]
        if not wanted:
            return []
        known = {document["id"]: document for document in _documents()}
        return [{"id": item, "title": known[item]["title"], "referencia": known[item].get("referencia")}
                for item in wanted if item in known]

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
                summary = getattr(library_, "figures_summary", dict)()
                return [{k: d.get(k) for k in ("id", "title", "version", "status", "issues", "created_at",
                                               "ficha", "ficha_origem", "referencia")}
                        | {"ficha_pendente": d["title"] in pending, "figuras": summary.get(d.get("sha256"))}
                        for d in _documents()]
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
                obsidian()  # uma versão nova que não pôde ser lida também aparece na nota do documento
                return
            # O documento já pode ser buscado e citado: fica pronto aqui (lote 27). As fichas chamam o
            # modelo e vão para o fim da fila, depois da indexação dos outros arquivos enviados.
            with lock:
                settings.jobs[job].update(outcome)
            obsidian()
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
                obsidian()

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
                obsidian()
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
        obsidian()
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
            obsidian()
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
                obsidian()

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
        obsidian()
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
        obsidian()
        return JSONResponse({"apagado": result["title"], "versoes": result["versions"], "trechos": result["chunks"],
                             "anotacoes_revogadas": revoked, "sobras": result["leftovers"]})

    async def document_figures(request: Request):
        """Descrição das figuras e tabelas de um documento pelo modelo (lote 29).

        GET diz quantas páginas há e se uma leitura está em andamento; POST começa, uma chamada por página
        com conteúdo visual ainda não lida; DELETE pede para parar antes das páginas que não começaram."""
        doc = request.path_params["doc"]
        library_ = settings.library_factory()
        if request.method == "DELETE":
            with lock:
                running = figure_jobs.get(doc)
            if running is None:
                return _error("Nenhuma descrição de figuras em andamento neste documento.", 404)
            running["parar"].set()
            return JSONResponse({"parando": True})
        try:
            target = await run_in_threadpool(library_.figure_pages, doc)
        except ValueError as exc:
            return _error(str(exc), 404)
        pending = sum(1 for page in target["pages"] if not page["read"])
        if request.method == "GET":
            with lock:
                running = figure_jobs.get(doc)
            return JSONResponse({"paginas": len(target["pages"]), "por_ler": pending,
                                 "tarefa": running["tarefa"] if running else None,
                                 "modelo": settings.figure_model, "disponivel": settings.figure_reader is not None,
                                 "tokens_por_pagina": figures.TOKENS_PER_PAGE})
        if settings.figure_reader is None:
            return _error("A descrição de figuras não está configurada.")
        if not pending:
            return _error("Não há páginas por descrever neste documento.")
        job, stop = uuid.uuid4().hex, threading.Event()
        with lock:
            if doc in figure_jobs:
                return _error("As figuras deste documento já estão sendo descritas.", 409)
            figure_jobs[doc] = {"tarefa": job, "parar": stop}
            settings.jobs[job] = {"estado": "processando", "etapa": "descrevendo", "atual": 0, "total": pending,
                                  "documento": doc}
            library_jobs.add(job)

        def progress(stage: str, current: int, total: int) -> None:
            with lock:
                settings.jobs[job].update({"etapa": stage, "atual": current, "total": total})

        def record(result) -> None:
            record_usage(result, settings.usage_log)

        def run():
            outcome: dict = {}
            try:
                counts = figures.describe(library_, doc, settings.figure_reader, progress=progress,
                                          stopped=stop.is_set, record=record, reindex=False)
                outcome = {"resultado": counts}
                if counts["lidas"]:
                    progress("indexando", 0, 1)
                    try:
                        # A extração nova é gravada pela fila da biblioteca, como os envios.
                        worker.submit(library_.reindex, doc).result()
                    except Exception:
                        outcome["aviso"] = ("As descrições foram guardadas, mas o índice não pôde ser refeito agora. "
                                            "Elas entram na busca na próxima reindexação do documento.")
            except Exception:
                # Erro não previsto: a tarefa termina, em vez de ficar presa e bloquear o apagar.
                outcome = {"erro": "Não foi possível descrever as figuras agora. Tente de novo."}
            finally:
                with lock:
                    figure_jobs.pop(doc, None)
                    settings.jobs[job].update({"estado": "concluido"} | outcome)
                obsidian()

        threading.Thread(target=run, name="aliado-figuras", daemon=True).start()
        return JSONResponse({"tarefa": job, "total": pending}, 202)

    async def google_files(request: Request):
        """O que a leitura integral deixou no serviço de arquivos do Google (lote 30): quantos e até quando.

        DELETE apaga de lá o que este computador enviou; os documentos da biblioteca não mudam."""
        if settings.uploaded_files is None:
            return JSONResponse({"disponivel": False, "arquivos": 0, "bytes": 0, "expira": None})
        if request.method == "DELETE":
            if settings.forget_files is None:
                return _error("O serviço de arquivos não está configurado.")
            try:
                counts = await run_in_threadpool(settings.forget_files)
            except ProviderError:
                return _error("O serviço de arquivos do Google não respondeu. Tente de novo em instantes.", 502)
            return JSONResponse(counts)
        listed = await run_in_threadpool(settings.uploaded_files)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        alive = [item for item in listed if str(item.get("expira") or "") > now]
        return JSONResponse({"disponivel": True, "arquivos": len(alive),
                             "bytes": sum(item.get("bytes") or 0 for item in alive),
                             "expira": max((item["expira"] for item in alive), default=None)})

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
        if request.path_params["kind"] == "figuras":
            return await document_figures(request)
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
        Route("/api/biblioteca/arquivos", google_files, methods=["GET", "DELETE"]),
        Route("/api/biblioteca/{doc}", delete_document, methods=["DELETE"]),
        Route("/api/biblioteca/{doc}/{kind:str}", document, methods=["GET", "POST", "DELETE"]),
        Route("/api/memoria", memory_list, methods=["GET", "POST"]),
        Route("/api/memoria/{mid}/{acao}", memory_action, methods=["GET", "POST"]),
        *science_routes(settings, worker, lock),
        *gpvs_routes(settings, lock),
        Mount("/static", StaticFiles(directory=STATIC), name="static"),
    ]
    app = Starlette(routes=routes, middleware=[Middleware(LocalOnly, port=settings.port)])
    app.state.worker = worker
    app.state.obsidian = sync
    obsidian()  # ao abrir o servidor: o cofre começa em dia com os dados
    return app


def default_settings(*, data_dir: Path, library_dir: Path, port: int, results_dir: Path | None = None,
                     gpvs_dir: Path = Path("data/gpvs"), obsidian: bool = True) -> WebSettings:
    """Gateway e biblioteca reais; o .env já deve ter sido carregado explicitamente."""
    from aliado.agent import Agent
    from aliado.knowledge.embeddings import LocalEncoder
    from aliado.knowledge.library import DocumentLibrary
    from aliado.knowledge.metadata import extract_card
    from aliado.knowledge.reranking import LocalReranker
    from aliado.knowledge.rewrite import rewrite_query
    from aliado.llm.providers.gateway import build_default_gateway
    from aliado.llm.usage_log import FILES_LOG_NAME
    from aliado.memory.reviewer import check_memory, reading_card, review_exchange
    from aliado.memory.store import MemoryStore
    from aliado.science import digest

    # O registro do que for enviado ao serviço de arquivos fica ao lado do registro de uso (lote 30).
    gateway = build_default_gateway(files=Path(data_dir) / "uso" / FILES_LOG_NAME)
    google = gateway.registry.provider("google")
    agent = Agent(gateway)
    models = [{"alias": m["alias"], "model_id": m["model_id"]}
              for m in gateway.registry.status()["models"]
              if m["provider"] == "google" and m["configured"]]
    # Um só modelo de busca local, carregado sob demanda, serve à biblioteca e à memória.
    encoder = LocalEncoder()
    library = DocumentLibrary(library_dir, encoder=encoder, reranker=LocalReranker())
    memory = MemoryStore(Path(data_dir) / "memoria", encoder=encoder)
    aliases = [m["alias"] for m in models]
    # Revisor e ficha usam o modelo mais barato configurado.
    helper_alias = "flash_lite" if "flash_lite" in aliases else (aliases[0] if aliases else "flash_lite")

    def execute(request):
        return gateway.execute(request, provider="google", model_alias=helper_alias)

    # Descrição das figuras (lote 29): o modelo escolhido no piloto, ou o de AL_IADO_FIGURE_MODEL.
    wanted = os.getenv("AL_IADO_FIGURE_MODEL", FIGURE_ALIAS)
    figure_alias = wanted if wanted in aliases else (helper_alias if aliases else None)

    def read_figures(request):
        return gateway.execute(request, provider="google", model_alias=figure_alias)

    def stream(question, **kwargs):
        return agent.stream_answer(question, provider="google", append_sources=False, **kwargs)

    settings = WebSettings(data_dir=data_dir, library_dir=library_dir, port=port, stream=stream,
                       models=models, library_factory=lambda: library, memory=memory,
                       reviewer=lambda **kwargs: review_exchange(execute, **kwargs),
                       card_maker=lambda **kwargs: reading_card(execute, **kwargs),
                       checker=lambda memory_: check_memory(execute, memory_),
                       card_extractor=lambda **kwargs: extract_card(execute, **kwargs),
                       query_rewriter=lambda **kwargs: rewrite_query(execute, plan=True, **kwargs),
                       results_dir=results_dir, gpvs_dir=gpvs_dir,
                       results_digest=lambda: digest.cached(settings.results_dir, settings.reference_dir),
                       obsidian_dir=Path(data_dir) / "obsidian" if obsidian else None,
                       figure_reader=read_figures if figure_alias else None,
                       figure_model=MODEL_NAMES.get(figure_alias, figure_alias),
                       uploaded_files=google.uploaded, forget_files=google.forget_uploads)
    return settings
