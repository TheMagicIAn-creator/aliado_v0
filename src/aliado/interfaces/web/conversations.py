"""Conversas locais em JSON, uma por arquivo; base para a memória do lote 11."""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

_ID = re.compile(r"[0-9a-f]{32}")
MAX_TITLE = 80


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ConversationStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        # Uma leitura e uma gravação do mesmo arquivo nunca se cruzam: no Windows, trocar um arquivo que
        # outra thread está lendo falha, e a resposta em andamento se perderia (lote 28).
        self._lock = threading.RLock()

    def _file(self, conversation_id: str) -> Path:
        if not isinstance(conversation_id, str) or not _ID.fullmatch(conversation_id):
            raise ValueError("Conversa não encontrada.")
        return self.root / f"{conversation_id}.json"

    def _write(self, data: dict) -> None:
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            target = self._file(data["id"])
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            # Troca atômica: uma falha no meio da escrita não corrompe a conversa anterior.
            os.replace(temporary, target)

    def create(self, title: str = "Nova conversa") -> dict:
        data = {"id": uuid.uuid4().hex, "title": title.strip()[:MAX_TITLE] or "Nova conversa",
                "created_at": _now(), "updated_at": _now(), "messages": []}
        self._write(data)
        return data

    def get(self, conversation_id: str) -> dict:
        path = self._file(conversation_id)
        with self._lock:
            if not path.is_file():
                raise ValueError("Conversa não encontrada.")
            return json.loads(path.read_text(encoding="utf-8"))

    def snapshot(self) -> list[dict]:
        """Todas as conversas, inteiras, da mais antiga à mais nova; a lixeira fica de fora."""
        if not self.root.is_dir():
            return []
        items = []
        for path in sorted(self.root.glob("*.json")):
            if not _ID.fullmatch(path.stem):
                continue
            # A trava vale por arquivo: quem grava uma conversa espera no máximo a leitura de uma.
            with self._lock:
                if path.is_file():  # pode ter sido apagada desde a listagem
                    items.append(json.loads(path.read_text(encoding="utf-8")))
        return sorted(items, key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")))

    def list(self) -> list[dict]:
        items = [{key: data[key] for key in ("id", "title", "created_at", "updated_at")}
                 | {"messages": len(data["messages"])} for data in self.snapshot()]
        return sorted(items, key=lambda item: item["updated_at"], reverse=True)

    def rename(self, conversation_id: str, title: str) -> dict:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Informe um título.")
        with self._lock:
            data = self.get(conversation_id)
            data["title"], data["updated_at"] = title.strip()[:MAX_TITLE], _now()
            self._write(data)
        return data

    def delete(self, conversation_id: str) -> None:
        """Tira a conversa da lista, movendo-a para a lixeira local (recuperável à mão).

        A memória do lote 11 guarda o próprio conteúdo e a referência à origem, e não
        depende deste arquivo: apagar a conversa não apaga a memória gerada.
        """
        path = self._file(conversation_id)
        with self._lock:
            if not path.is_file():
                raise ValueError("Conversa não encontrada.")
            trash = self.root / "lixeira"
            trash.mkdir(parents=True, exist_ok=True)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["deleted_at"] = _now()
            target = trash / f"{conversation_id}.json"
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            path.unlink()

    def append(self, conversation_id: str, *messages: dict) -> dict:
        with self._lock:
            data = self.get(conversation_id)
            if not data["messages"] and data["title"] == "Nova conversa":
                first = next((m["content"] for m in messages if m.get("role") == "user"), "")
                data["title"] = " ".join(first.split())[:MAX_TITLE] or data["title"]
            for message in messages:
                data["messages"].append({"id": uuid.uuid4().hex, "created_at": _now(), **message})
            data["updated_at"] = _now()
            self._write(data)
        return data

    def annotate(self, conversation_id: str, message_id: str, **fields) -> dict:
        """Acrescenta metadados a uma mensagem (ex.: memórias criadas pelo revisor)."""
        with self._lock:
            data = self.get(conversation_id)
            for message in data["messages"]:
                if message["id"] == message_id:
                    message.update(fields)
                    self._write(data)
                    return message
        raise ValueError("Mensagem não encontrada.")

    @staticmethod
    def history(data: dict) -> list[dict]:
        """Apenas turnos válidos seguem ao modelo; avisos locais e falhas ficam de fora."""
        return [{"role": m["role"], "content": m["content"]} for m in data["messages"]
                if m.get("role") in {"user", "assistant"} and m.get("in_context", True)
                and isinstance(m.get("content"), str) and m["content"].strip()]
