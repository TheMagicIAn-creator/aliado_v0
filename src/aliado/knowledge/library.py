"""Biblioteca local por projeto: originais imutáveis, catálogo e busca híbrida."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from aliado.knowledge.embeddings import LocalEncoder
from aliado.knowledge.extraction import extract_document
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
}


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
        issues, chunks, sections = [], [], []
        pages = 0
        try:
            extraction = extract_document(original_path, ocr=self.ocr, force_ocr=force_ocr,
                                          progress=progress)
            issues.extend(extraction.issues)
            pages, sections = extraction.pages, extraction.to_dict()["sections"]
            for section in extraction.sections:
                for piece in self.encoder.split(section.text):
                    chunks.append({"id": "K" + uuid.uuid4().hex[:16], "text": piece,
                                   "locator": section.locator, "page": section.page,
                                   "method": section.method})
            if chunks:
                if progress:
                    progress("indexando", 0, len(chunks))
                vectors = self.encoder.encode([c["text"] for c in chunks])
                if len(vectors) != len(chunks):
                    raise ValueError("Encoder retornou quantidade incorreta de vetores.")
                dimensions = {len(vector) for vector in vectors}
                if len(dimensions) != 1:
                    raise ValueError("Dimensões incompatíveis de vetores.")
                for chunk, vector in zip(chunks, vectors):
                    chunk["vector"] = _vector(vector)
        except (ValueError, OSError, RuntimeError, ImportError) as exc:
            issues.append(f"Processamento incompleto ({type(exc).__name__}); confira formato, OCR e modelo local e reprocesse.")
        # Vetores incompletos nunca entram na busca. O original e a extração ficam preservados.
        indexed = [c for c in chunks if "vector" in c]
        if not indexed and not issues:
            issues.append("Documento sem trechos indexáveis; confira o original.")
        status = "failed" if not indexed else ("partial" if issues else "ready")
        now = datetime.now(timezone.utc).isoformat()
        metadata = {"schema_version": 1, "id": doc_id, "title": title, "sha256": sha,
                    "version": version, "original": original, "run_id": run_id,
                    "created_at": now, "status": status, "issues": issues, "pages": pages,
                    "encoder": self.encoder.fingerprint, "sections": sections, "chunks": indexed,
                    "force_ocr": bool(force_ocr)}
        folder = self._path(f"extracted/{doc_id}/v{version}/{run_id}")
        folder.mkdir(parents=True, exist_ok=False)
        json_path, md_path = folder / "metadata.json", folder / "content.md"
        json_path.write_text(_json(metadata), encoding="utf-8")
        markdown = [f"# {title}", "", f"SHA-256: {sha} | Versão: {version} | Estado: {status}",
                    "", "Texto extraído automaticamente; confira fórmulas, tabelas e OCR no original."]
        for section in sections:
            markdown.extend(["", f"## {section['locator']} ({section['method']})", "", section["text"]])
        if issues:
            markdown.extend(["", "## Pendências da extração", "", *[f"- {item}" for item in issues]])
        md_path.write_text("\n".join(markdown) + "\n", encoding="utf-8")
        with self._connect(create=True) as db, db:
            # Atualiza somente o índice derivado; originais, versões, runs e chunks permanecem.
            db.execute("""DELETE FROM chunk_fts WHERE id IN (
                SELECT c.id FROM chunks c JOIN runs r ON r.id=c.run_id
                JOIN documents d ON d.id=r.document_id WHERE d.title=?)""", (title,))
            if not existing:
                db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, NULL)",
                           (doc_id, title, sha, version, original, now))
            db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (run_id, doc_id, status, _json(issues), self.encoder.fingerprint,
                        json_path.relative_to(self.root).as_posix(), _hash(json_path.read_bytes()),
                        md_path.relative_to(self.root).as_posix(), _hash(md_path.read_bytes()), now))
            for chunk in indexed:
                db.execute("INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (chunk["id"], run_id, chunk["text"], chunk["locator"], chunk["page"],
                            chunk["method"], _json(chunk["vector"])))
                db.execute("INSERT INTO chunk_fts VALUES (?, ?)", (chunk["id"], chunk["text"]))
            db.execute("UPDATE documents SET active_run=? WHERE id=?", (run_id, doc_id))
        return {k: metadata[k] for k in ("id", "title", "sha256", "version", "run_id", "status", "issues")} | {
            "duplicate": False, "chunks": len(indexed), "original": str(original_path),
        }

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
            rows = db.execute("""SELECT c.*, d.id AS document_id, d.title, d.version, d.sha256, d.original,
                    r.encoder, r.status FROM chunks c JOIN runs r ON c.run_id=r.id
                    JOIN documents d ON d.id=r.document_id WHERE d.active_run=r.id
                    AND d.version=(SELECT MAX(v.version) FROM documents v WHERE v.title=d.title)
                    ORDER BY c.id""").fetchall()
            if not rows:
                return []
            if any(row["encoder"] != self.encoder.fingerprint for row in rows):
                raise ValueError("Encoder do índice mudou; reprocesse os documentos antes da busca.")
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
        lexical_ids = [row["id"] for row in lexical if row["id"] in titles]
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
        hits, checked = [], set()
        for score, row in _diverse(candidates, limit, named):
            original = self._path(row["original"])
            if original not in checked:
                if not original.is_file() or _hash(original.read_bytes()) != row["sha256"]:
                    raise ValueError("Original ausente ou alterado; execute biblioteca verificar.")
                checked.add(original)
            hits.append({"citation_id": row["id"], "document_id": row["document_id"],
                         "title": row["title"], "version": row["version"],
                         "sha256": row["sha256"], "original": str(original), "locator": row["locator"],
                         "page": row["page"], "method": row["method"], "status": row["status"],
                         "text": row["text"], "score": score, "similarity": scores[row["id"]],
                         "referencia": cards.get(row["title"], {}).get("referencia")})
        return hits

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
