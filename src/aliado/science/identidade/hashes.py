"""Os hashes que identificam os arquivos e as configurações de uma rodada (lote 54: as cópias espalhadas viraram
estes dois)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """SHA-256 do conteúdo de um arquivo, lido em blocos de 1 MiB."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def config_digest(data: dict) -> str:
    """SHA-256 de uma configuração em JSON, com as chaves em ordem: as mesmas escolhas dão o mesmo valor."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()


def arrays_digest(arrays: dict) -> str:
    """SHA-256 do conteúdo de matrizes (nome, tipo, formato e bytes, na ordem dos nomes). O mesmo conteúdo dá o mesmo
    valor mesmo regravado: o arquivo compactado guarda a hora da gravação, e o hash dele mudaria a cada vez."""
    digest = hashlib.sha256()
    for name in sorted(arrays):
        array = arrays[name]
        digest.update(f"{name}|{array.dtype.str}|{array.shape}|".encode("utf-8"))
        digest.update(array.tobytes())
    return digest.hexdigest()
