"""A tabela da FMECA decidida pelo pesquisador: os campos, as notas de 1 a 10 e os cenários de taxa citados."""

from __future__ import annotations

import json
from pathlib import Path

NOTES = ("S", "O", "D")
TABLE_FIELDS = {"nome", "decidida_em", "criterio", "fonte_notas", "horizontes_anos", "itens", "ressalvas"}
ITEM_FIELDS = {"id", "nome", "item_na_fonte", "S", "O", "D", "cenarios", "ressalvas"}


def _check_fields(value, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label}: campos esperados {', '.join(sorted(expected))}.")


def _note(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 10:
        raise ValueError(f"{label}: nota inteira de 1 a 10.")
    return value


def load_table(path: str | Path) -> tuple[dict, dict[str, dict]]:
    """Tabela da FMECA e os cenários citados, com caminhos relativos ao arquivo da tabela."""
    path = Path(path)
    table = json.loads(path.read_text(encoding="utf-8-sig"))
    _check_fields(table, TABLE_FIELDS, "tabela")
    scenarios = {}
    for item in table["itens"]:
        for name in item.get("cenarios", []):
            scenarios[name] = json.loads((path.parent / name).read_text(encoding="utf-8-sig"))
    return table, scenarios
