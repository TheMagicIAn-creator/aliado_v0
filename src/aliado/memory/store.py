"""Memória persistente local: anotações com origem, versões e conflitos, nunca apagadas.

Regras aprovadas pelo pesquisador (lote 11):
- origem "feedback"/"comando" (o próprio usuário) vale na hora; "inferido" vale marcado;
- feedback supera qualquer anotação; inferido supera inferido; inferido contra feedback
  vira conflito, e a anotação do usuário continua valendo até a decisão;
- correções e edições criam versões novas; a anterior fica "superada";
- a memória guarda o próprio conteúdo e a origem: apagar a conversa não a afeta.

Lote 18: "perfil" guarda quem é o usuário e o seu contexto, e vale sempre, como as
preferências. A memória de conversas guarda cada troca exibida para ser relembrada por
semelhança; a troca de uma conversa apagada é esquecida (a anotação que saiu dela fica).
"""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

KINDS = ("perfil", "preferencia", "correcao", "fato", "decisao")
ALWAYS_KINDS = ("perfil", "preferencia")
ORIGINS = ("feedback", "comando", "inferido")
USER_ORIGINS = {"feedback", "comando"}
STATUSES = ("ativa", "conflito", "superada", "revogada")
MAX_TEXT = 600
MAX_PREFERENCES = 10
MAX_PROFILE = 15
MAX_QUESTION = 500
MAX_ANSWER = 1500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize(vector) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values] if norm and math.isfinite(norm) else []


class MemoryStore:
    def __init__(self, root: str | Path, *, encoder=None):
        self.root = Path(root).resolve()
        self.encoder = encoder

    @contextmanager
    def _db(self):
        self.root.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.root / "memoria.sqlite3")
        connection.row_factory = sqlite3.Row
        try:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, text TEXT NOT NULL,
                    origin TEXT NOT NULL, status TEXT NOT NULL, skill TEXT,
                    source TEXT NOT NULL, supersedes TEXT, superseded_by TEXT,
                    conflict_with TEXT, diverges_skill INTEGER NOT NULL DEFAULT 0,
                    vector TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS exchanges (
                    message_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
                    question TEXT NOT NULL, answer TEXT NOT NULL, skill TEXT,
                    created_at TEXT NOT NULL, vector TEXT, forgotten INTEGER NOT NULL DEFAULT 0);
            """)
            # Uma transação por operação: tudo ou nada (ex.: nova versão + antiga superada).
            with connection:
                yield connection
        finally:
            connection.close()

    def _embedding(self, text: str) -> list[float]:
        """Vetor do texto; textos longos são divididos em partes de até 128 tokens e somados.

        O encoder local recusa mais de 128 tokens, e anotações ou perguntas longas ficavam
        sem vetor, invisíveis à busca por semelhança (corrigido no lote 18).
        """
        if self.encoder is None or not str(text or "").strip():
            return []
        try:
            parts = self.encoder.split(text) if hasattr(self.encoder, "split") else [text]
            vectors = self.encoder.encode(parts or [text])
            return _normalize([sum(values) for values in zip(*vectors)])
        except (ValueError, OSError, RuntimeError, ImportError, IndexError):
            # Sem o modelo local, a anotação vale mesmo assim; a busca recorre à ordem recente.
            return []

    def _vector(self, text: str) -> str | None:
        vector = self._embedding(text)
        return json.dumps(vector) if vector else None

    def _exchange_vector(self, question: str, answer: str) -> str | None:
        """Pergunta e resposta com o mesmo peso, para uma resposta longa não apagar o assunto."""
        parts = [vector for vector in (self._embedding(question), self._embedding(answer)) if vector]
        if not parts:
            return None
        return json.dumps(_normalize([sum(values) for values in zip(*parts)]))

    def fill_missing_vectors(self) -> int:
        """Calcula os vetores que faltam (anotações e trocas antigas); devolve quantos ganharam vetor."""
        if self.encoder is None:
            return 0
        with self._db() as db:
            notes = db.execute("SELECT id, text FROM memories WHERE vector IS NULL").fetchall()
            exchanges = db.execute("SELECT message_id, question, answer FROM exchanges WHERE vector IS NULL").fetchall()
        filled = 0
        for row in notes:
            vector = self._vector(row["text"])
            if vector:
                with self._db() as db:
                    db.execute("UPDATE memories SET vector=? WHERE id=?", (vector, row["id"]))
                filled += 1
        for row in exchanges:
            vector = self._exchange_vector(row["question"], row["answer"])
            if vector:
                with self._db() as db:
                    db.execute("UPDATE exchanges SET vector=? WHERE message_id=?", (vector, row["message_id"]))
                filled += 1
        return filled

    @staticmethod
    def _row(row: sqlite3.Row) -> dict:
        data = {key: row[key] for key in row.keys() if key != "vector"}
        data["source"] = json.loads(data["source"])
        data["diverges_skill"] = bool(data["diverges_skill"])
        return data

    def get(self, memory_id: str) -> dict:
        with self._db() as db:
            row = db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if row is None:
            raise ValueError("Anotação não encontrada.")
        return self._row(row)

    def add(self, *, kind: str, text: str, origin: str, skill: str | None = None,
            source: dict | None = None, supersedes: str | None = None,
            diverges_skill: bool = False) -> dict:
        if kind not in KINDS or origin not in ORIGINS:
            raise ValueError("Tipo ou origem de anotação inválidos.")
        text = " ".join(str(text or "").split())[:MAX_TEXT]
        if not text:
            raise ValueError("A anotação precisa de texto.")
        if kind in ALWAYS_KINDS:
            skill = None  # perfil e preferências valem em todas as especializações
        # Só uma decisão do próprio usuário pode divergir de uma skill.
        diverges_skill = bool(diverges_skill and kind == "decisao" and origin in USER_ORIGINS)
        memory_id, now = uuid.uuid4().hex, _now()
        status, conflict_with = "ativa", None
        with self._db() as db:
            if supersedes:
                target = db.execute("SELECT * FROM memories WHERE id=?", (supersedes,)).fetchone()
                if target is None or target["status"] not in {"ativa", "conflito"}:
                    supersedes = None
                elif origin == "inferido" and target["origin"] in USER_ORIGINS:
                    status, conflict_with, supersedes = "conflito", target["id"], None
            db.execute("INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                memory_id, kind, text, origin, status, skill, json.dumps(source or {}, ensure_ascii=False),
                supersedes, None, conflict_with, int(diverges_skill), self._vector(text), now, now))
            if supersedes:
                db.execute("UPDATE memories SET status='superada', superseded_by=?, updated_at=? WHERE id=?",
                           (memory_id, now, supersedes))
            if conflict_with:
                db.execute("UPDATE memories SET conflict_with=?, updated_at=? WHERE id=?",
                           (memory_id, now, conflict_with))
        return self.get(memory_id)

    def list(self, *, status: str | None = None, origin: str | None = None) -> list[dict]:
        query, params = "SELECT * FROM memories WHERE 1=1", []
        if status:
            if status not in STATUSES:
                raise ValueError("Estado desconhecido.")
            query += " AND status=?"
            params.append(status)
        if origin:
            query += " AND origin=?"
            params.append(origin)
        with self._db() as db:
            rows = db.execute(query + " ORDER BY created_at DESC, id", params).fetchall()
        return [self._row(row) for row in rows]

    def history(self, memory_id: str) -> list[dict]:
        """Cadeia de versões, da mais antiga à mais recente, passando pela anotação pedida."""
        current = self.get(memory_id)
        chain = [current]
        while chain[0]["supersedes"]:
            chain.insert(0, self.get(chain[0]["supersedes"]))
        while chain[-1]["superseded_by"]:
            chain.append(self.get(chain[-1]["superseded_by"]))
        return chain

    def revoke(self, memory_id: str) -> dict:
        memory = self.get(memory_id)
        if memory["status"] in {"superada", "revogada"}:
            raise ValueError("Só anotações ativas ou em conflito podem ser revogadas.")
        with self._db() as db:
            db.execute("UPDATE memories SET status='revogada', updated_at=? WHERE id=?", (_now(), memory_id))
            # Revogar um lado do conflito libera o outro.
            db.execute("UPDATE memories SET conflict_with=NULL WHERE conflict_with=?", (memory_id,))
        return self.get(memory_id)

    def edit(self, memory_id: str, text: str) -> dict:
        """Edição do usuário: nova versão com origem feedback, sem apagar a anterior."""
        memory = self.get(memory_id)
        if memory["status"] not in {"ativa", "conflito"}:
            raise ValueError("Só anotações ativas ou em conflito podem ser editadas.")
        return self.add(kind=memory["kind"], text=text, origin="feedback", skill=memory["skill"],
                        source=memory["source"] | {"editada_de": memory_id}, supersedes=memory_id,
                        diverges_skill=memory["diverges_skill"])

    def resolve(self, memory_id: str, *, accept: bool) -> dict:
        """Decide um conflito: aceitar a anotação nova (supera a antiga) ou mantê-la de fora."""
        memory = self.get(memory_id)
        if memory["status"] != "conflito" or not memory["conflict_with"]:
            raise ValueError("Esta anotação não está em conflito.")
        if not accept:
            return self.revoke(memory_id)
        now, old = _now(), memory["conflict_with"]
        with self._db() as db:
            db.execute("UPDATE memories SET status='ativa', conflict_with=NULL, supersedes=?, updated_at=? "
                       "WHERE id=?", (old, now, memory_id))
            db.execute("UPDATE memories SET status='superada', superseded_by=?, conflict_with=NULL, "
                       "updated_at=? WHERE id=?", (memory_id, now, old))
        return self.get(memory_id)

    def relevant(self, question: str, *, skill: str | None, limit: int = 8,
                 min_similarity: float = 0.30) -> list[dict]:
        """Perfil e preferências sempre; demais anotações ativas por semelhança, na skill ativa ou globais."""
        with self._db() as db:
            rows = db.execute("SELECT * FROM memories WHERE status='ativa' ORDER BY created_at DESC").fetchall()
        profile = [row for row in rows if row["kind"] == "perfil"][:MAX_PROFILE]
        preferences = [row for row in rows if row["kind"] == "preferencia"][:MAX_PREFERENCES]
        others = [row for row in rows if row["kind"] not in ALWAYS_KINDS and row["skill"] in (None, skill)]
        query = json.loads(self._vector(question) or "[]")
        if query and any(row["vector"] for row in others):
            scored = []
            for row in others:
                vector = json.loads(row["vector"] or "[]")
                if len(vector) == len(query):
                    similarity = sum(a * b for a, b in zip(query, vector))
                    if similarity >= min_similarity:
                        scored.append((similarity, row))
            scored.sort(key=lambda pair: -pair[0])
            chosen = [row for _, row in scored[:limit]]
        else:
            chosen = others[:limit]
        return [self._row(row) for row in profile + preferences + chosen]

    # Memória de conversas (lote 18)

    def remember_exchange(self, *, conversation_id: str, message_id: str, question: str, answer: str,
                          skill: str | None = None, created_at: str | None = None) -> bool:
        """Guarda uma troca exibida (pergunta e resposta); devolve False se já estava guardada."""
        question = str(question or "").strip()[:MAX_QUESTION]
        answer = str(answer or "").strip()[:MAX_ANSWER]
        if not question or not answer:
            return False
        with self._db() as db:
            if db.execute("SELECT 1 FROM exchanges WHERE message_id=?", (message_id,)).fetchone():
                return False
            db.execute("INSERT INTO exchanges VALUES (?,?,?,?,?,?,?,0)", (
                message_id, conversation_id, question, answer, skill, created_at or _now(),
                self._exchange_vector(question, answer)))
        return True

    def recall(self, question: str, *, exclude_conversation: str | None = None, limit: int = 3,
               min_similarity: float = 0.40) -> list[dict]:
        """Trocas de outras conversas mais parecidas com a pergunta; as esquecidas ficam de fora."""
        query = json.loads(self._vector(question) or "[]")
        if not query:
            return []
        with self._db() as db:
            rows = db.execute("SELECT * FROM exchanges WHERE forgotten=0 AND conversation_id IS NOT ?",
                              (exclude_conversation,)).fetchall()
        scored = []
        for row in rows:
            vector = json.loads(row["vector"] or "[]")
            if len(vector) == len(query):
                similarity = sum(a * b for a, b in zip(query, vector))
                if similarity >= min_similarity:
                    scored.append((similarity, row))
        scored.sort(key=lambda pair: -pair[0])
        return [{key: row[key] for key in row.keys() if key not in {"vector", "forgotten"}}
                | {"similaridade": round(similarity, 3)} for similarity, row in scored[:limit]]

    def forget_conversation(self, conversation_id: str) -> int:
        """A conversa apagada deixa de ser relembrada; devolve quantas trocas saíram."""
        with self._db() as db:
            cursor = db.execute("UPDATE exchanges SET forgotten=1 WHERE conversation_id=? AND forgotten=0",
                                (conversation_id,))
        return cursor.rowcount

    def exchange_count(self) -> int:
        with self._db() as db:
            return db.execute("SELECT COUNT(*) FROM exchanges WHERE forgotten=0").fetchone()[0]
