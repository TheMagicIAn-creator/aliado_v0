"""As tabelas de reparo: os tempos de detecção e de reparo de cada grupo da FMECA, com fontes e hipóteses."""

from __future__ import annotations

import json
import math
from pathlib import Path

REPAIR_FIELDS = {"nome", "decidida_em", "criterio", "grupos", "cenarios", "ressalvas"}
SCENARIO_FIELDS = {"id", "nome", "tipo", "deteccao_horas", "reparo_horas", "fontes", "hipoteses", "ressalvas"}


def _check_fields(value, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label}: campos esperados {', '.join(sorted(expected))}.")


def _hours(value, label: str, *, positive: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
            or value < 0 or (positive and value == 0):
        raise ValueError(f"{label}: informe horas {'maiores que zero' if positive else 'não negativas'}.")
    return float(value)


def _texts(value, label: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(t, str) and t.strip() for t in value):
        raise ValueError(f"{label}: informe uma lista não vazia de textos.")
    return list(value)


def validate_repairs(data: dict, groups: list[str]) -> dict:
    """Os cenários de reparo cobrem exatamente os grupos da FMECA, com horas válidas e fontes."""
    _check_fields(data, REPAIR_FIELDS, "reparos")
    if sorted(data["grupos"]) != sorted(groups):
        raise ValueError("reparos: os grupos devem ser os mesmos da FMECA: " + ", ".join(groups) + ".")
    if not isinstance(data["cenarios"], list) or not data["cenarios"]:
        raise ValueError("reparos: informe ao menos um cenário.")
    seen = set()
    for scenario in data["cenarios"]:
        _check_fields(scenario, SCENARIO_FIELDS, f"cenário {scenario.get('id', '?') if isinstance(scenario, dict) else '?'}")
        if scenario["id"] in seen:
            raise ValueError(f"cenário {scenario['id']}: identificador repetido.")
        seen.add(scenario["id"])
        _hours(scenario["deteccao_horas"], f"{scenario['id']}.deteccao_horas", positive=False)
        if not isinstance(scenario["reparo_horas"], dict) or sorted(scenario["reparo_horas"]) != sorted(groups):
            raise ValueError(f"{scenario['id']}.reparo_horas: um tempo para cada grupo da FMECA.")
        for group, value in scenario["reparo_horas"].items():
            _hours(value, f"{scenario['id']}.reparo_horas.{group}", positive=True)
        for key in ("fontes", "hipoteses"):
            _texts(scenario[key], f"{scenario['id']}.{key}")
    return data


def load_repairs(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))
