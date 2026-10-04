"""Biblioteca local por projeto: originais imutáveis, catálogo e busca híbrida."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import sqlite3
import subprocess
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from aliado.knowledge import chunking, figures
from aliado.knowledge.embeddings import ENCODE_BATCH, LocalEncoder
from aliado.knowledge.extraction import TesseractOCR, extract_document
from aliado.knowledge.metadata import MAX_CHARS, clean_card, named_documents, reference
from aliado.knowledge.stopwords import STOPWORDS, plain

# Busca híbrida (lote 19). Valores fixados antes da medição com as perguntas de referência:
# a parte por palavras ignora palavras vazias e pesa a metade da parte por significado, e cada
# documento ocupa no máximo 2 dos resultados (4 se a pergunta o cita pelo autor ou pelo título).
SEARCH_SETTINGS = {
    "palavras_vazias": "português e inglês",
    "rrf_k": 60,
    "peso_significado": 1.0,
    "peso_palavras": 0.5,
    "peso_documento_citado": 1.0,
    "por_documento": 2,
    "por_documento_citado": 4,
    # Lote 29: as descrições automáticas de figuras, escritas em português, ganhavam de todo o acervo em
    # inglês na lista por palavras de uma pergunta em português. Elas concorrem só pelo significado e
    # chegam junto com a legenda achada no texto.
    "descricoes_por_palavras": False,
}
# Indexação em fatias (lote 27), para a tela acompanhar o avanço. Só múltiplos do lote interno do
# encoder dão vetores idênticos aos de uma chamada única.
INDEX_SLICE = 2 * ENCODE_BATCH
# Menor sobreposição, em caracteres, para dois trechos vizinhos serem unidos numa passagem.
MIN_OVERLAP = 12
# Quantos trechos de cada lado a passagem de uma descrição de figura ou tabela alcança (lote 29).
DESCRIPTION_REACH = 12
# Como as seções de figuras aparecem no Markdown da extração; as de texto seguem como "native" e "ocr".
METHOD_NAMES = {figures.FIGURE_TEXT: "texto reconhecido na figura", figures.DESCRIPTION: "descrição automática"}


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _diverse(candidates: list[tuple[float, dict]], limit: int, named: set[str]) -> list[tuple[float, dict]]:
    """Os melhores candidatos com teto por documento; só completa além do teto se faltar candidato."""
    chosen, spare, per_document = [], [], Counter()
    for pair in candidates:
        title = pair[1]["title"]
        cap = SEARCH_SETTINGS["por_documento_citado" if title in named else "por_documento"]
        if per_document[title] < cap:
            per_document[title] += 1
            chosen.append(pair)
            if len(chosen) == limit:
                return chosen
        elif len(spare) < limit:
            spare.append(pair)
    return sorted(chosen + spare[:limit - len(chosen)], key=lambda pair: (-pair[0], pair[1]["id"]))


def _overlap(left: str, right: str, minimum: int = MIN_OVERLAP, split=None) -> int | None:
    """Quantos caracteres do fim de `left` repetem o começo de `right`; None se não der para saber.

    Os trechos são fatias do mesmo texto, com cerca de 20 tokens em comum: o fim do primeiro repete o
    começo do segundo. Sem essa repetição, os textos não são vizinhos.
    - Um só tamanho serve: é a sobreposição.
    - Dois tamanhos servem: é prosa em que a parte comum começa e termina com o mesmo termo. Vale o
      maior, e só se `split` (a divisão que criou os trechos) devolver os dois trechos a partir da união.
    - Três ou mais servem: o texto é repetitivo (pontilhado de sumário, células iguais de uma tabela), e
      escolher um tamanho cortaria repetições. Os trechos não são unidos.
    """
    sizes = [size for size in range(min(len(left), len(right)), minimum - 1, -1) if left.endswith(right[:size])]
    if len(sizes) == 1:
        return sizes[0]
    if len(sizes) == 2 and split is not None:
        try:
            if split(left + right[sizes[0]:]) == [left, right]:
                return sizes[0]
        except ValueError:  # encoder indisponível: sem desempate, sem união
            return None
    return None


def _join(left: str, right: str, minimum: int = MIN_OVERLAP, split=None) -> str | None:
    """Une dois trechos vizinhos sem repetir a parte comum; None se a sobreposição não for segura."""
    size = _overlap(left, right, minimum, split)
    return None if size is None else left + right[size:]


def _space(fingerprint: str) -> str:
    """A parte do registro do encoder que identifica os vetores, sem a regra de divisão em trechos.

    Os trechos por frase (lote 29) e os de tamanho fixo usam o mesmo modelo: os vetores se comparam, e a
    busca aceita os dois no mesmo índice."""
    return fingerprint.rsplit(":", 1)[0]


def _vector(values) -> list[float]:
    if not values or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise ValueError("Vetor inválido no índice documental.")
    norm = math.sqrt(sum(v * v for v in values))
    if not norm or not math.isfinite(norm):
        raise ValueError("Vetor vazio ou fora da faixa numérica.")
    return [v / norm for v in values]


class DocumentLibrary:
    def __init__(self, root: str | Path, *, encoder=None, ocr=None):
        self.root = Path(root).resolve()
        self.encoder = encoder if encoder is not None else LocalEncoder()
        self.ocr = ocr

    @contextmanager
    def _connect(self, *, create=False):
        path = self.root / "catalog.sqlite3"
        if create:
            self.root.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(path)
        else:
            connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            if create:
                if connection.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
                    raise ValueError("Versão desconhecida do catálogo documental.")
                connection.executescript("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY, title TEXT NOT NULL, sha256 TEXT NOT NULL,
                        version INTEGER NOT NULL, original TEXT NOT NULL, created_at TEXT NOT NULL,
                        active_run TEXT, UNIQUE(title, version));
                    CREATE TABLE IF NOT EXISTS runs (
                        id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
                        status TEXT NOT NULL, issues TEXT NOT NULL, encoder TEXT NOT NULL,
                        json_path TEXT NOT NULL, json_sha TEXT NOT NULL,
                        md_path TEXT NOT NULL, md_sha TEXT NOT NULL, created_at TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS chunks (
                        id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                        text TEXT NOT NULL, locator TEXT NOT NULL, page INTEGER,
                        method TEXT NOT NULL, vector TEXT NOT NULL);
                    CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
                        id UNINDEXED, text, tokenize='unicode61 remove_diacritics 2');
                    -- Lote 19: ficha por documento lógico; a edição do usuário vale sobre a
                    -- inferida, que continua guardada.
                    CREATE TABLE IF NOT EXISTS document_cards (
                        title TEXT PRIMARY KEY, inferred TEXT, edited TEXT, updated_at TEXT NOT NULL);
                    -- Lote 29: uma linha por página com figura, desenho, tabela ou legenda, pelo conteúdo
                    -- do arquivo. O texto reconhecido nas figuras e a descrição do modelo valem para toda
                    -- extração do mesmo arquivo.
                    CREATE TABLE IF NOT EXISTS page_figures (
                        sha256 TEXT NOT NULL, page INTEGER NOT NULL, signals TEXT NOT NULL, local_text TEXT,
                        reading TEXT, model TEXT, read_at TEXT, usage TEXT, PRIMARY KEY (sha256, page));
                    PRAGMA user_version=1;
                """)
            elif connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("Versão desconhecida do catálogo documental.")
            yield connection
        finally:
            connection.close()

    def _path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Caminho fora da biblioteca documental.")
        return path

    @property
    def search_settings(self) -> dict:
        return dict(SEARCH_SETTINGS)

    def documents(self) -> list[dict]:
        if not (self.root / "catalog.sqlite3").exists():
            return []
        with self._connect() as db:
            rows = db.execute("""SELECT d.*, r.status, r.issues FROM documents d
                JOIN runs r ON d.active_run=r.id ORDER BY d.title, d.version""").fetchall()
        cards = self.cards()
        return [{**dict(row), "issues": json.loads(row["issues"])}
                | {key: cards.get(row["title"], {}).get(key) for key in ("ficha", "ficha_origem", "referencia")}
                for row in rows]

    def cards(self) -> dict[str, dict]:
        """Fichas por documento lógico: a edição do usuário vale sobre a inferida."""
        if not (self.root / "catalog.sqlite3").exists():
            return {}
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='document_cards'").fetchone():
                return {}  # catálogo anterior ao lote 19, ainda sem fichas
            rows = db.execute("SELECT * FROM document_cards").fetchall()
        cards = {}
        for row in rows:
            edited = json.loads(row["edited"]) if row["edited"] is not None else None
            card = edited if edited is not None else json.loads(row["inferred"] or "{}")
            if card:
                cards[row["title"]] = {"ficha": card, "ficha_origem": "sua" if edited is not None else "inferida",
                                       "referencia": reference(card)}
        return cards

    def titles_without_card(self) -> list[str]:
        """Documentos que nunca tiveram ficha tentada; uma tentativa vazia não se repete sozinha."""
        titles = list(dict.fromkeys(document["title"] for document in self.documents()))
        if not titles:
            return []
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='document_cards'").fetchone():
                return titles
            tried = {row["title"] for row in db.execute("SELECT title FROM document_cards")}
        return [title for title in titles if title not in tried]

    def set_card(self, title: str, card: dict, *, edited: bool) -> dict:
        """Grava a ficha inferida ou a sua edição, sem apagar a outra."""
        if not any(document["title"] == title for document in self.documents()):
            raise ValueError("Documento não encontrado na biblioteca.")
        column = "edited" if edited else "inferred"
        with self._connect(create=True) as db, db:
            db.execute(f"""INSERT INTO document_cards (title, {column}, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(title) DO UPDATE SET {column}=excluded.{column}, updated_at=excluded.updated_at""",
                       (title, json.dumps(clean_card(card), ensure_ascii=False),
                        datetime.now(timezone.utc).isoformat()))
        return self.cards().get(title, {"ficha": {}, "ficha_origem": "sua" if edited else "inferida",
                                        "referencia": None})

    def opening_text(self, title: str, limit: int = MAX_CHARS) -> str:
        """Começo do texto extraído da versão ativa, de onde a ficha é tirada e conferida."""
        if not (self.root / "catalog.sqlite3").exists():
            raise ValueError("Documento não encontrado na biblioteca.")
        with self._connect() as db:
            row = db.execute("""SELECT r.json_path FROM documents d JOIN runs r ON r.id=d.active_run
                WHERE d.title=? ORDER BY d.version DESC LIMIT 1""", (title,)).fetchone()
        if row is None:
            raise ValueError("Documento não encontrado na biblioteca.")
        sections = json.loads(self._path(row["json_path"]).read_text(encoding="utf-8"))["sections"]
        text = ""
        for section in sections:
            if section["method"] not in figures.TEXT_METHODS:
                continue  # texto de figura e descrição automática não são o começo do documento
            text += section["text"] + "\n"
            if len(text) >= limit:
                break
        return text[:limit]

    def add(self, source: str | Path, *, title: str | None = None,
            force_ocr=False, reprocess=False, progress=None) -> dict:
        """`progress(etapa, atual, total)`: etapas lendo/ocr por página e indexando por trecho."""
        source = Path(source).resolve()
        if source.suffix.lower() not in {".pdf", ".md", ".json"} or not source.is_file():
            raise ValueError("Selecione um arquivo PDF, Markdown ou JSON existente.")
        if "memory-review" in source.parts:
            raise ValueError("A revisão privada de memórias não integra a biblioteca documental.")
        if source.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("Documento excede o limite local de 100 MiB.")
        title = (title or source.name).strip()
        if not title or len(title) > 250:
            raise ValueError("Identificador do documento deve ter entre 1 e 250 caracteres.")
        raw = source.read_bytes()
        sha = _hash(raw)
        records = self.documents()
        same_name = [d for d in records if d["title"] == title]
        latest = max(same_name, key=lambda d: d["version"], default=None)
        existing = latest if latest and latest["sha256"] == sha else None
        if not same_name:
            current_versions = {d["title"]: d["version"] for d in records}
            existing = next((d for d in reversed(records) if d["sha256"] == sha and
                             d["version"] == current_versions[d["title"]]), None)
        if existing and not (reprocess or force_ocr):
            path = self._path(existing["original"])
            if not path.is_file() or _hash(path.read_bytes()) != sha:
                raise ValueError("Original armazenado ausente ou alterado; execute biblioteca verificar.")
            return {**existing, "duplicate": True}
        doc_id = existing["id"] if existing else uuid.uuid4().hex
        version = existing["version"] if existing else (latest["version"] + 1 if latest else 1)
        title = existing["title"] if existing else title
        original = existing["original"] if existing else f"originals/{sha}/source{source.suffix.lower()}"
        original_path = self._path(original)
        original_path.parent.mkdir(parents=True, exist_ok=True)
        if original_path.exists():
            if _hash(original_path.read_bytes()) != sha:
                raise ValueError("Original armazenado diverge do hash; execute biblioteca verificar.")
        else:
            with original_path.open("xb") as handle:
                handle.write(raw)
        run_id = uuid.uuid4().hex
        issues, chunks, sections, record = [], [], [], {}
        pages = 0
        try:
            extraction = extract_document(original_path, ocr=self.ocr, force_ocr=force_ocr,
                                          progress=progress)
            issues.extend(extraction.issues)
            pages, sections = extraction.pages, extraction.to_dict()["sections"]
            sections = self._with_figures(original_path, sha, sections, progress)
            chunks, record = self._chunks(sections)
            self._encode(chunks, progress)
        except (ValueError, OSError, RuntimeError, ImportError) as exc:
            issues.append(f"Processamento incompleto ({type(exc).__name__}); confira formato, OCR e modelo local e reprocesse.")
        return self._store(doc_id=doc_id, title=title, sha=sha, version=version, original=original, run_id=run_id,
                           sections=sections, chunks=chunks, issues=issues, pages=pages, record=record,
                           force_ocr=bool(force_ocr), new=not existing)

    def reindex(self, doc_id: str, *, progress=None) -> dict:
        """Refaz os trechos de um documento a partir do texto de página já guardado (lote 29).

        Não lê o arquivo de novo nem repete o reconhecimento de texto das páginas: aproveita as seções de
        texto da extração ativa, as figuras já lidas e o vetor de todo trecho que não mudou. A extração
        anterior continua guardada. Vale para a versão mais recente do documento."""
        if not (self.root / "catalog.sqlite3").exists():
            raise ValueError("Documento não encontrado na biblioteca.")
        with self._connect() as db:
            row = db.execute("""SELECT d.*, r.json_path, r.json_sha,
                    (SELECT MAX(v.version) FROM documents v WHERE v.title=d.title) AS latest
                    FROM documents d JOIN runs r ON r.id=d.active_run WHERE d.id=?""", (doc_id,)).fetchone()
            if row is None:
                raise ValueError("Documento não encontrado na biblioteca.")
            if row["version"] != row["latest"]:
                raise ValueError("Só a versão mais recente do documento é reindexada.")
            known = {item["text"]: json.loads(item["vector"]) for item in db.execute(
                "SELECT text, vector FROM chunks WHERE run_id=?", (row["active_run"],))}
        original_path, json_path = self._path(row["original"]), self._path(row["json_path"])
        if not original_path.is_file() or _hash(original_path.read_bytes()) != row["sha256"]:
            raise ValueError("Original armazenado ausente ou alterado; execute biblioteca verificar.")
        if not json_path.is_file() or _hash(json_path.read_bytes()) != row["json_sha"]:
            raise ValueError("Extração guardada ausente ou alterada; execute biblioteca verificar.")
        previous = json.loads(json_path.read_text(encoding="utf-8"))
        sections = [section for section in previous["sections"] if section["method"] in figures.TEXT_METHODS]
        if not sections:
            raise ValueError("Documento sem texto guardado; envie o arquivo de novo.")
        # As pendências da leitura das páginas continuam valendo; as do processamento são refeitas agora.
        issues = [issue for issue in previous["issues"] if issue.startswith("Página ")]
        chunks, record = [], {}
        try:
            sections = self._with_figures(original_path, row["sha256"], sections, progress)
            chunks, record = self._chunks(sections)
            self._encode(chunks, progress, known)
        except (ValueError, OSError, RuntimeError, ImportError) as exc:
            issues.append(f"Processamento incompleto ({type(exc).__name__}); confira formato, OCR e modelo local e reprocesse.")
        return self._store(doc_id=row["id"], title=row["title"], sha=row["sha256"], version=row["version"],
                           original=row["original"], run_id=uuid.uuid4().hex, sections=sections, chunks=chunks,
                           issues=issues, pages=previous.get("pages", 0), record=record,
                           force_ocr=bool(previous.get("force_ocr")), new=False)

    def _figure_rows(self, sha: str) -> dict[int, dict]:
        """O que a biblioteca guarda das páginas com conteúdo visual de um arquivo, por página."""
        if not (self.root / "catalog.sqlite3").exists():
            return {}
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='page_figures'").fetchone():
                return {}  # catálogo anterior ao lote 29
            rows = db.execute("SELECT * FROM page_figures WHERE sha256=? ORDER BY page", (sha,)).fetchall()
        load = lambda value: json.loads(value) if value else None  # noqa: E731
        return {row["page"]: {"signals": json.loads(row["signals"]), "local_text": load(row["local_text"]),
                              "reading": load(row["reading"]), "model": row["model"], "read_at": row["read_at"],
                              "usage": load(row["usage"])} for row in rows}

    def figure_pages(self, doc_id: str, *, scan: bool = False, progress=None) -> dict:
        """As páginas com conteúdo visual da versão ativa de um documento e o que já foi lido de cada uma.

        Serve à descrição pelo modelo: traz o arquivo original e o texto guardado de cada página, de onde a
        conferência tira os rótulos e as legendas. Com `scan`, procura antes as páginas e reconhece o texto
        das figuras, sem refazer a extração: é o que falta a um documento indexado antes do lote 29."""
        if not (self.root / "catalog.sqlite3").exists():
            raise ValueError("Documento não encontrado na biblioteca.")
        with self._connect() as db:
            row = db.execute("""SELECT d.id, d.title, d.sha256, d.original, r.json_path FROM documents d
                JOIN runs r ON r.id=d.active_run WHERE d.id=?""", (doc_id,)).fetchone()
        if row is None:
            raise ValueError("Documento não encontrado na biblioteca.")
        sections = json.loads(self._path(row["json_path"]).read_text(encoding="utf-8"))["sections"]
        text = {section["page"]: section["text"] for section in sections
                if section["method"] in figures.TEXT_METHODS and section.get("page")}
        if scan:
            self._with_figures(self._path(row["original"]), row["sha256"],
                               [section for section in sections if section["method"] in figures.TEXT_METHODS], progress)
        pages = [{"page": number, "signals": item["signals"], "local_text": item["local_text"],
                  "read": item["reading"] is not None, "model": item["model"], "read_at": item["read_at"]}
                 for number, item in self._figure_rows(row["sha256"]).items()]
        return {"id": row["id"], "title": row["title"], "sha256": row["sha256"],
                "original": self._path(row["original"]), "text": text, "pages": pages}

    def save_figure_reading(self, sha: str, page: int, reading: dict, *, model: str, usage: dict | None = None) -> None:
        """Guarda a descrição do modelo para uma página, já conferida; vale para toda extração do arquivo."""
        with self._connect(create=True) as db, db:
            saved = db.execute("UPDATE page_figures SET reading=?, model=?, read_at=?, usage=? WHERE sha256=? AND page=?",
                               (json.dumps(reading, ensure_ascii=False), model,
                                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                json.dumps(usage, ensure_ascii=False) if usage else None, sha, page)).rowcount
        if not saved:
            raise ValueError("Página sem registro de figuras; reindexe o documento.")

    def figures_summary(self) -> dict[str, dict]:
        """Por arquivo (SHA-256): páginas com conteúdo visual, com texto reconhecido nas figuras e já descritas."""
        if not (self.root / "catalog.sqlite3").exists():
            return {}
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='page_figures'").fetchone():
                return {}
            rows = db.execute("SELECT sha256, local_text, reading, model, read_at FROM page_figures").fetchall()
        summary: dict[str, dict] = {}
        for row in rows:
            entry = summary.setdefault(row["sha256"], {"paginas": 0, "com_texto": 0, "descritas": 0, "itens": 0,
                                                       "modelo": None, "data": None})
            entry["paginas"] += 1
            entry["com_texto"] += bool(row["local_text"] and json.loads(row["local_text"]).get("texto"))
            if row["reading"]:
                entry["descritas"] += 1
                entry["itens"] += len(json.loads(row["reading"]).get("itens") or [])
                if entry["data"] is None or row["read_at"] > entry["data"]:
                    entry["modelo"], entry["data"] = row["model"], row["read_at"]
        return summary

    def _with_figures(self, original: Path, sha: str, sections: list[dict], progress=None) -> list[dict]:
        """As seções de texto, cada página seguida das suas seções de figuras (lote 29).

        Procura as páginas com conteúdo visual e, nas que têm figura embutida, reconhece o texto dentro
        dela. O resultado fica guardado pelo conteúdo do arquivo e não é refeito. Uma falha aqui não
        derruba a indexação do texto: as figuras ficam para a próxima vez."""
        if original.suffix.lower() != ".pdf" or not sections:
            return sections
        try:
            signals = figures.page_signals(original, sections)
            rows = self._figure_rows(sha)
            reader = self.ocr if self.ocr is not None else TesseractOCR()
            ready = callable(getattr(reader, "extract_region", None)) and getattr(reader, "available", lambda: True)()
            text = {section["page"]: section["text"] for section in sections}
            pending = [number for number, signal in signals.items() if ready and signal["imagens"]
                       and not signal["digitalizada"] and (rows.get(number) or {}).get("local_text") is None]
            found = {}
            for position, number in enumerate(pending, 1):
                if progress:
                    progress("figuras", position, len(pending))
                try:
                    found[number] = figures.figure_text(reader, original, number, signals[number], text.get(number, ""))
                except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired):
                    continue  # figura que o reconhecimento não leu: é tentada de novo na próxima vez
            if signals or rows:
                with self._connect(create=True) as db, db:
                    # Página que deixou de ter sinal sai do registro, a menos que já tenha sido descrita.
                    for number in set(rows) - set(signals):
                        db.execute("DELETE FROM page_figures WHERE sha256=? AND page=? AND reading IS NULL", (sha, number))
                    for number, signal in signals.items():
                        db.execute("""INSERT INTO page_figures (sha256, page, signals) VALUES (?, ?, ?)
                            ON CONFLICT(sha256, page) DO UPDATE SET signals=excluded.signals""",
                                   (sha, number, json.dumps(signal, ensure_ascii=False)))
                    for number, local in found.items():
                        db.execute("UPDATE page_figures SET local_text=? WHERE sha256=? AND page=?",
                                   (json.dumps(local, ensure_ascii=False), sha, number))
                rows = self._figure_rows(sha)
        except (ImportError, OSError, ValueError, RuntimeError, sqlite3.Error):
            return sections  # sem pdfium, PDF que ele não abre ou catálogo ocupado: segue só com o texto
        result, placed = [], set()
        for section in sections:
            result.append(section)
            row = rows.get(section["page"])
            if row and section["page"] not in placed:
                placed.add(section["page"])
                result += figures.page_sections(section["page"], row["local_text"], row["reading"])
        for number, row in rows.items():  # página sem texto próprio, só com a figura
            if number not in placed:
                result += figures.page_sections(number, row["local_text"], row["reading"])
        return result

    def _chunk(self, text: str, section: dict, kind: str | None = None) -> dict:
        return {"id": "K" + uuid.uuid4().hex[:16], "text": text, "locator": chunking.marked(section["locator"], kind),
                "page": section["page"], "method": section["method"]}

    def _chunks(self, sections: list[dict]) -> tuple[list[dict], dict]:
        """Os trechos das seções, ainda sem vetor, e o registro do que a limpeza tirou.

        Com um encoder que informa a posição dos tokens, as páginas dos PDFs são limpas e todo texto é
        dividido em frases inteiras (lote 29). Sem isso, vale a divisão do próprio encoder, como antes."""
        if chunking.scheme(self.encoder) is None:
            return [self._chunk(piece, section) for section in sections
                    for piece in self.encoder.split(section["text"])], {}
        pages = [section for section in sections if section["method"] in figures.TEXT_METHODS and section.get("page")]
        parts, cleaning = (chunking.clean_pages([section["text"] for section in pages],
                                                [section["page"] for section in pages]) if pages else ([], {}))
        by_page = {id(section): part for section, part in zip(pages, parts)}
        chunks, seen, repeated = [], set(), 0
        for section in sections:
            if section["method"] == figures.DESCRIPTION:
                # A descrição de uma figura é uma coisa só: trechos cheios, e o primeiro com a legenda.
                found = [(piece, None) for piece in chunking.filled(section["text"], self.encoder, section.get("head", 0))]
            else:
                whole = [(0, len(section["text"]), None)]
                found = chunking.pieces(section["text"], by_page.get(id(section), whole), self.encoder)
            for piece, kind in found:
                key = " ".join(piece.split())
                if key in seen:  # repetido palavra por palavra no mesmo documento: entra uma vez
                    repeated += 1
                    continue
                seen.add(key)
                chunks.append(self._chunk(piece, section, kind))
        record = {"trechos_repetidos": repeated}
        if pages:
            numbers = [section["page"] for section in pages]
            record |= {"linhas_de_borda": cleaning["linhas_de_borda"], "padroes_de_borda": cleaning["padroes_de_borda"],
                       "paginas_de_sumario": [numbers[index] for index in cleaning["sumario"]],
                       "paginas_com_referencias": [numbers[index] for index in cleaning["referencias"]],
                       "glifos": cleaning["glifos"]}
        return chunks, record

    def _encode(self, chunks: list[dict], progress=None, known: dict[str, list[float]] | None = None) -> None:
        """Põe o vetor em cada trecho; o de um trecho que não mudou vem da extração anterior (`known`)."""
        if not chunks:
            return
        known = known or {}
        pending = [chunk for chunk in chunks if chunk["text"] not in known]
        texts, vectors = [chunk["text"] for chunk in pending], []
        for start in range(0, len(texts), INDEX_SLICE):
            if progress:
                progress("indexando", start, len(texts))
            vectors.extend(self.encoder.encode(texts[start:start + INDEX_SLICE]))
        if progress:
            progress("indexando", len(texts), len(texts))
        if len(vectors) != len(pending):
            raise ValueError("Encoder retornou quantidade incorreta de vetores.")
        reused = [known[chunk["text"]] for chunk in chunks if chunk["text"] in known]
        if len({len(vector) for vector in vectors + reused}) != 1:
            raise ValueError("Dimensões incompatíveis de vetores.")
        fresh = iter(vectors)
        for chunk in chunks:
            chunk["vector"] = _vector(known[chunk["text"]] if chunk["text"] in known else next(fresh))

    def _index_id(self) -> str:
        """O registro do encoder gravado na extração: os vetores e, nos trechos por frase, o esquema."""
        scheme = chunking.scheme(self.encoder)
        return f"{_space(self.encoder.fingerprint)}:{scheme}" if scheme else self.encoder.fingerprint

    def _store(self, *, doc_id: str, title: str, sha: str, version: int, original: str, run_id: str,
               sections: list[dict], chunks: list[dict], issues: list[str], pages: int, record: dict,
               force_ocr: bool, new: bool) -> dict:
        """Grava a extração (JSON e Markdown), os trechos e o índice por palavras, e a torna a ativa."""
        # Vetores incompletos nunca entram na busca. O original e a extração ficam preservados.
        indexed = [c for c in chunks if "vector" in c]
        if not indexed and not issues:
            issues.append("Documento sem trechos indexáveis; confira o original.")
        status = "failed" if not indexed else ("partial" if issues else "ready")
        now = datetime.now(timezone.utc).isoformat()
        encoder = self._index_id()
        metadata = {"schema_version": 1, "id": doc_id, "title": title, "sha256": sha,
                    "version": version, "original": original, "run_id": run_id,
                    "created_at": now, "status": status, "issues": issues, "pages": pages,
                    "encoder": encoder, "sections": sections, "chunks": indexed,
                    "force_ocr": force_ocr}
        if record:
            metadata["limpeza"] = record
        folder = self._path(f"extracted/{doc_id}/v{version}/{run_id}")
        folder.mkdir(parents=True, exist_ok=False)
        json_path, md_path = folder / "metadata.json", folder / "content.md"
        json_path.write_text(_json(metadata), encoding="utf-8")
        markdown = [f"# {title}", "", f"SHA-256: {sha} | Versão: {version} | Estado: {status}",
                    "", "Texto extraído automaticamente; confira fórmulas, tabelas e OCR no original."]
        for section in sections:
            method = METHOD_NAMES.get(section["method"], section["method"])
            markdown.extend(["", f"## {section['locator']} ({method})", "", section["text"]])
        if issues:
            markdown.extend(["", "## Pendências da extração", "", *[f"- {item}" for item in issues]])
        md_path.write_text("\n".join(markdown) + "\n", encoding="utf-8")
        with self._connect(create=True) as db, db:
            # Atualiza somente o índice derivado; originais, versões, runs e chunks permanecem.
            db.execute("""DELETE FROM chunk_fts WHERE id IN (
                SELECT c.id FROM chunks c JOIN runs r ON r.id=c.run_id
                JOIN documents d ON d.id=r.document_id WHERE d.title=?)""", (title,))
            if new:
                db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, NULL)",
                           (doc_id, title, sha, version, original, now))
            db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (run_id, doc_id, status, _json(issues), encoder,
                        json_path.relative_to(self.root).as_posix(), _hash(json_path.read_bytes()),
                        md_path.relative_to(self.root).as_posix(), _hash(md_path.read_bytes()), now))
            for chunk in indexed:
                db.execute("INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (chunk["id"], run_id, chunk["text"], chunk["locator"], chunk["page"],
                            chunk["method"], _json(chunk["vector"])))
                db.execute("INSERT INTO chunk_fts VALUES (?, ?)", (chunk["id"], chunk["text"]))
            db.execute("UPDATE documents SET active_run=? WHERE id=?", (run_id, doc_id))
        return {k: metadata[k] for k in ("id", "title", "sha256", "version", "run_id", "status", "issues")} | {
            "duplicate": False, "chunks": len(indexed), "original": str(self._path(original)),
        }

    def delete(self, doc_id: str) -> dict:
        """Apaga de vez um documento: todas as versões do título, extrações, índice e ficha.

        Um original só sai quando nenhum outro documento o usa. Sem cópia: não tem volta."""
        if not (self.root / "catalog.sqlite3").exists():
            raise ValueError("Documento não encontrado na biblioteca.")
        with self._connect(create=True) as db, db:
            row = db.execute("SELECT title FROM documents WHERE id=?", (doc_id,)).fetchone()
            if row is None:
                raise ValueError("Documento não encontrado na biblioteca.")
            title = row["title"]
            documents = db.execute("SELECT id, original FROM documents WHERE title=? ORDER BY version",
                                   (title,)).fetchall()
            ids = [document["id"] for document in documents]
            marks = ",".join("?" * len(ids))
            runs = [run["id"] for run in db.execute(f"SELECT id FROM runs WHERE document_id IN ({marks})", ids)]
            chunks = 0
            if runs:
                run_marks = ",".join("?" * len(runs))
                db.execute(f"""DELETE FROM chunk_fts WHERE id IN (
                    SELECT id FROM chunks WHERE run_id IN ({run_marks}))""", runs)
                chunks = db.execute(f"DELETE FROM chunks WHERE run_id IN ({run_marks})", runs).rowcount
                db.execute(f"DELETE FROM runs WHERE id IN ({run_marks})", runs)
            db.execute(f"DELETE FROM documents WHERE id IN ({marks})", ids)
            db.execute("DELETE FROM document_cards WHERE title=?", (title,))
            # As figuras lidas valem pelo conteúdo do arquivo: saem quando nenhum documento o usa mais.
            db.execute("DELETE FROM page_figures WHERE sha256 NOT IN (SELECT sha256 FROM documents)")
            in_use = {document["original"] for document in db.execute("SELECT original FROM documents")}
        folders = [self._path(f"extracted/{document_id}") for document_id in ids]
        folders += [self._path(original).parent for original in {d["original"] for d in documents} - in_use]
        leftovers = []
        for folder in folders:
            # Só pastas próprias do documento, nunca a raiz nem as pastas de topo da biblioteca.
            if folder.parent.parent != self.root or not folder.exists():
                continue
            try:
                shutil.rmtree(folder)
            except OSError:
                leftovers.append(folder.relative_to(self.root).as_posix())
        return {"title": title, "ids": ids, "versions": len(ids), "chunks": chunks, "leftovers": leftovers}

    def document_files(self, doc_id: str) -> dict:
        """Original e Markdown da extração ativa, para exibição local; nunca caminhos externos."""
        if not (self.root / "catalog.sqlite3").exists():
            raise ValueError("Documento não encontrado na biblioteca.")
        with self._connect() as db:
            row = db.execute("""SELECT d.title, d.original, r.md_path FROM documents d
                JOIN runs r ON r.id=d.active_run WHERE d.id=?""", (doc_id,)).fetchone()
        if row is None:
            raise ValueError("Documento não encontrado na biblioteca.")
        return {"title": row["title"], "original": self._path(row["original"]),
                "markdown": self._path(row["md_path"])}

    def search(self, query: str, *, limit=6, min_similarity=0.30) -> list[dict]:
        if not query.strip() or not 1 <= limit <= 20:
            raise ValueError("Consulta vazia ou limite fora de 1–20.")
        if not (self.root / "catalog.sqlite3").exists():
            return []
        cards = self.cards()
        named = named_documents(query, cards)
        with self._connect() as db:
            rows = db.execute("""SELECT c.*, c.rowid AS position, d.id AS document_id, d.title, d.version, d.sha256,
                    d.original, r.encoder, r.status FROM chunks c JOIN runs r ON c.run_id=r.id
                    JOIN documents d ON d.id=r.document_id WHERE d.active_run=r.id
                    AND d.version=(SELECT MAX(v.version) FROM documents v WHERE v.title=d.title)
                    ORDER BY c.id""").fetchall()
            if not rows:
                return []
            if any(_space(row["encoder"]) != _space(self.encoder.fingerprint) for row in rows):
                raise ValueError("Encoder do índice mudou; reprocesse os documentos antes da busca.")
            if not chunking.asks_support(query):
                # Sumário e lista de referências: cheios de palavras-chave e vazios de conteúdo (lote 29).
                rows = [row for row in rows if not chunking.support(row["locator"])]
                if not rows:
                    return []
            # Palavras vazias ("de", "the", "segundo") puxariam qualquer texto no mesmo idioma.
            words = [word for word in dict.fromkeys(re.findall(r"[^\W_]+", query, re.UNICODE))
                     if plain(word) not in STOPWORDS][:40]
            lexical = db.execute("""SELECT id FROM chunk_fts WHERE chunk_fts MATCH ? ORDER BY bm25(chunk_fts)""",
                                 (" OR ".join('"' + word + '"' for word in words),)).fetchall() if words else []
        query_parts = self.encoder.split(query)
        if not query_parts:
            return []
        encoded = self.encoder.encode(query_parts)
        q = _vector([sum(values) / len(encoded) for values in zip(*encoded)])
        semantic = []
        for row in rows:
            vector = _vector(json.loads(row["vector"]))
            if len(q) != len(vector):
                raise ValueError("Dimensões incompatíveis no índice documental.")
            semantic.append((row["id"], sum(a * b for a, b in zip(q, vector))))
        semantic.sort(key=lambda pair: (-pair[1], pair[0]))
        scores = dict(semantic)
        titles = {row["id"]: row["title"] for row in rows}
        described_ids = set() if SEARCH_SETTINGS["descricoes_por_palavras"] else {
            row["id"] for row in rows if row["method"] == figures.DESCRIPTION}
        lexical_ids = [row["id"] for row in lexical if row["id"] in titles and row["id"] not in described_ids]
        lexical_ranks = {key: rank for rank, key in enumerate(lexical_ids, 1)}
        semantic_ranks = {key: rank for rank, (key, _) in enumerate(semantic, 1)}
        # Documento citado pelo autor ou pelo título: seus trechos formam uma terceira lista.
        named_ranks = {key: rank for rank, key in enumerate(
            (key for key, _ in semantic if titles[key] in named), 1)}
        k, weights = SEARCH_SETTINGS["rrf_k"], SEARCH_SETTINGS
        candidates = []
        for row in rows:
            key = row["id"]
            if key not in lexical_ranks and key not in named_ranks and scores[key] < min_similarity:
                continue
            score = weights["peso_significado"] / (k + semantic_ranks[key])
            if key in lexical_ranks:
                score += weights["peso_palavras"] / (k + lexical_ranks[key])
            if key in named_ranks:
                score += weights["peso_documento_citado"] / (k + named_ranks[key])
            candidates.append((score, row))
        candidates.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
        # O começo da descrição de cada figura ou tabela, por extração, página e rótulo (lote 29).
        described: dict[tuple, sqlite3.Row] = {}
        for row in rows:
            if row["method"] == figures.DESCRIPTION:
                for label in figures.captions(row["locator"].rsplit(" · ", 1)[-1]):
                    key = (row["run_id"], row["page"], label)
                    if key not in described or row["position"] < described[key]["position"]:
                        described[key] = row
        checked = set()

        def hit(row, score: float) -> dict:
            original = self._path(row["original"])
            if original not in checked:
                if not original.is_file() or _hash(original.read_bytes()) != row["sha256"]:
                    raise ValueError("Original ausente ou alterado; execute biblioteca verificar.")
                checked.add(original)
            return {"citation_id": row["id"], "document_id": row["document_id"],
                    "title": row["title"], "version": row["version"],
                    "sha256": row["sha256"], "original": str(original), "locator": row["locator"],
                    "page": row["page"], "method": row["method"], "status": row["status"],
                    "text": row["text"], "score": score, "similarity": scores[row["id"]],
                    "referencia": cards.get(row["title"], {}).get("referencia")}

        chosen = _diverse(candidates, limit, named)
        hits, taken = [], {row["id"] for _, row in chosen}
        for score, row in chosen:
            hits.append(hit(row, score))
            if row["method"] not in figures.TEXT_METHODS:
                continue
            # A legenda achada no texto leva à descrição da figura: sozinha, ela diz que a figura existe,
            # mas não o que mostra. Um trecho que é só a legenda dá lugar à descrição, que já a traz.
            labels = figures.captions(row["text"])
            for label in labels:
                description = described.get((row["run_id"], row["page"], label))
                if description is None or description["id"] in taken:
                    continue
                taken.add(description["id"])
                alone = len(labels) == 1 and figures.squash(row["text"]) in figures.squash(description["text"])
                hits[-1 if alone else len(hits):] = [hit(description, score)]
        return hits[:limit]

    def expand(self, hits: list[dict], *, neighbours: int = 1) -> list[dict]:
        """Os mesmos resultados, com `passagem`: o trecho unido ao anterior e ao seguinte da mesma página.

        Um trecho tem cerca de 68 palavras e pode cortar uma definição no meio da frase (lote 27). A ordem
        dos trechos de uma extração é a de gravação. Um vizinho só entra se for da mesma extração e do
        mesmo localizador (a mesma página), se o texto realmente se sobrepuser e se ele não for outro
        resultado nem já tiver sido usado. `text` continua sendo o trecho indexado, o que a busca achou.
        Numa página com texto repetido na extração, o resultado cujo trecho já vai inteiro na passagem
        de outro melhor colocado não é ampliado, para o mesmo parágrafo não seguir duas vezes.
        """
        expanded = [dict(hit) | {"passagem": hit["text"]} for hit in hits]
        if not hits or neighbours < 1 or not (self.root / "catalog.sqlite3").exists():
            return expanded
        ids = [hit["citation_id"] for hit in hits]
        split = getattr(self.encoder, "split", None)  # a divisão que criou os trechos desempata a união
        # A linha vizinha na ordem de gravação, numa busca direta pela posição: os trechos de uma extração
        # são gravados em sequência. A extração e o localizador são conferidos depois, sem varrer a tabela.
        nearest = {-1: "rowid < ? ORDER BY rowid DESC", 1: "rowid > ? ORDER BY rowid"}
        with self._connect() as db:
            rows = {row["id"]: row for row in db.execute(
                f"""SELECT c.id, c.rowid AS position, c.run_id, c.locator, c.method, r.encoder FROM chunks c
                    JOIN runs r ON r.id=c.run_id WHERE c.id IN ({','.join('?' * len(ids))})""", ids)}
            used = set(ids)
            done = []  # (extração e localizador, passagem) dos resultados melhor colocados
            for hit in expanded:  # na ordem da busca: o melhor resultado escolhe os vizinhos primeiro
                row = rows.get(hit["citation_id"])
                if row is None:
                    continue
                place = (row["run_id"], row["locator"])
                if any(where == place and hit["text"] in passage for where, passage in done):
                    continue
                # Trechos por frase (lote 29) são fatias seguidas do texto, sem parte comum: unem-se com
                # uma quebra de linha. Os de tamanho fixo se unem pela parte que repetem.
                sentences = row["encoder"].rsplit(":", 1)[-1].startswith("frases")
                for direction, condition in nearest.items():
                    position, edge = row["position"], hit["text"]  # o trecho da ponta, que encosta no vizinho
                    # A descrição de uma figura ou tabela é uma coisa só: vai inteira, e não só os vizinhos.
                    for _ in range(DESCRIPTION_REACH if row["method"] == figures.DESCRIPTION else neighbours):
                        neighbour = db.execute(
                            f"SELECT id, rowid AS position, text, run_id, locator FROM chunks WHERE {condition} LIMIT 1",
                            (position,)).fetchone()
                        if (neighbour is None or (neighbour["run_id"], neighbour["locator"]) != place
                                or neighbour["id"] in used):
                            break
                        if sentences:
                            hit["passagem"] = (f"{neighbour['text']}\n{hit['passagem']}" if direction < 0
                                               else f"{hit['passagem']}\n{neighbour['text']}")
                        else:
                            size = (_overlap(neighbour["text"], edge, split=split) if direction < 0
                                    else _overlap(edge, neighbour["text"], split=split))
                            if size is None:
                                break
                            hit["passagem"] = (neighbour["text"] + hit["passagem"][size:] if direction < 0
                                               else hit["passagem"] + neighbour["text"][size:])
                        used.add(neighbour["id"])
                        position, edge = neighbour["position"], neighbour["text"]
                done.append((place, hit["passagem"]))
        return expanded

    def verify(self) -> dict:
        issues = []
        documents = self.documents()
        if not documents:
            return {"ok": True, "documents": 0, "runs": 0, "issues": []}
        for doc in documents:
            path = self._path(doc["original"])
            if not path.is_file() or _hash(path.read_bytes()) != doc["sha256"]:
                issues.append(f"Original ausente ou alterado: {doc['id']}.")
        with self._connect() as db:
            runs = db.execute("SELECT * FROM runs").fetchall()
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                issues.append("Falha na integridade SQLite.")
            for run in runs:
                for kind in ("json", "md"):
                    path = self._path(run[f"{kind}_path"])
                    if not path.is_file() or _hash(path.read_bytes()) != run[f"{kind}_sha"]:
                        issues.append(f"Artefato {kind} ausente ou alterado: {run['id']}.")
                path = self._path(run["json_path"])
                if path.is_file() and _hash(path.read_bytes()) == run["json_sha"]:
                    expected = json.loads(path.read_text(encoding="utf-8"))["chunks"]
                    stored = db.execute("SELECT * FROM chunks WHERE run_id=? ORDER BY id", (run["id"],)).fetchall()
                    actual = [{k: row[k] for k in ("id", "text", "locator", "page", "method")} |
                              {"vector": json.loads(row["vector"])} for row in stored]
                    if sorted(expected, key=lambda c: c["id"]) != actual:
                        issues.append(f"Trechos ou vetores divergentes: {run['id']}.")
                if run["status"] != "ready" and any(d["active_run"] == run["id"] for d in documents):
                    issues.append(f"Extração {run['status']}: {run['id']}.")
            drift = db.execute("""SELECT COUNT(*) FROM chunks c JOIN runs r ON r.id=c.run_id
                JOIN documents d ON d.id=r.document_id LEFT JOIN chunk_fts f ON c.id=f.id
                WHERE d.active_run=r.id
                AND d.version=(SELECT MAX(v.version) FROM documents v WHERE v.title=d.title)
                AND (f.id IS NULL OR f.text != c.text)""").fetchone()[0]
            if drift:
                issues.append("Índice lexical diverge dos trechos armazenados.")
        return {"ok": not issues, "documents": len(documents), "runs": len(runs), "issues": issues}
