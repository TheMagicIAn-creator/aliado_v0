"""O início nominal da falha: o meio do registro, porque os CSVs não trazem canal de disparo (lote 51: as três
cópias, em `evaluation`, `reanalysis` e `summary`, viraram esta)."""

from __future__ import annotations


def nominal_onset(item: dict) -> int:
    """Primeira janela da falha nominal num ensaio preparado: a da transição ou, sem ela, a do pós-falha."""
    return int(item["transicao"][0]) if len(item["transicao"]) else int(item["pos_falha"][0])
