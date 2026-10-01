"""Confiabilidade por componente e disponibilidade dos 4 grupos da FMECA (lote 25).

As taxas vêm dos cenários exponenciais de cada grupo, um por base de tempo (horas de operação ou
de calendário), e os tempos de reparo, de `reparos.json`. Curvas e disponibilidade saem do serviço
RAM (`evaluate_scenario`), sem ajuste empírico. O reparo corre em horas de calendário: na
disponibilidade, o MTBF é 8.760 / (λ · horas por ano), em horas de calendário, e a parada por
falha é o tempo para detectar mais o de reparar. Sem dependências externas.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from aliado.science.ram import evaluate_scenario

CALENDAR_HOURS = 8760.0
REPAIR_FIELDS = {"nome", "decidida_em", "criterio", "grupos", "cenarios", "ressalvas"}
SCENARIO_FIELDS = {"id", "nome", "tipo", "deteccao_horas", "reparo_horas", "fontes", "hipoteses", "ressalvas"}
BASES = ("operation", "calendar")


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


def _availability(mtbf_hours: float, downtime_hours: float, name: str) -> float:
    result = evaluate_scenario({
        "name": name, "kind": "availability_inherent", "time_unit": "h",
        "parameters": {"mtbf": mtbf_hours, "mttr": downtime_hours},
        "sources": ["Taxa do cenário do grupo e tempo de reparo de reparos.json."],
        "assumptions": ["Taxa constante; o reparo devolve o componente ao estado de novo."],
    })
    return result["summary"]["availability_inherent"]


def _base(scenario: dict, repairs: dict, group: str, horizon: float, points: int) -> dict:
    """Taxas, curvas e disponibilidade de um grupo numa base de tempo."""
    if scenario["kind"] != "exponential" or "time_base" not in scenario:
        raise ValueError(f"{scenario['name']}: a confiabilidade por componente exige exponencial com taxa em 1/h.")
    times = [round(horizon * index / (points - 1), 6) for index in range(points)]
    curve = evaluate_scenario(scenario | {"times": sorted(set(times) | {1.0})})
    hourly = float(scenario["parameters"]["rate"])
    hours = float(scenario["time_base"]["hours_per_year"])
    yearly = hourly * hours
    at = {row["time"]: row for row in curve["rows"]}
    availability = {}
    for repair in repairs["cenarios"]:
        downtime = repair["deteccao_horas"] + repair["reparo_horas"][group]
        mtbf_calendar = CALENDAR_HOURS / yearly
        availability[repair["id"]] = {
            "parada_horas": downtime, "mtbf_calendario_horas": mtbf_calendar,
            "disponibilidade": _availability(mtbf_calendar, downtime, f"{scenario['name']} · {repair['nome']}"),
            "horas_paradas_por_ano": yearly * downtime,
        }
    return {
        "cenario": scenario["name"], "horas_por_ano": hours, "taxa_por_hora": hourly, "taxa_por_ano": yearly,
        "mtbf_anos": curve["summary"]["mttf"], "falhas_por_ano": yearly, "falhas_no_horizonte": yearly * horizon,
        "f_1_ano": at[1.0]["failure_probability"], "f_horizonte": at[float(horizon)]["failure_probability"],
        "curva": [{"t": row["time"], "r": row["reliability"], "f": row["failure_probability"]} for row in curve["rows"]],
        "disponibilidade": availability, "fontes": list(scenario["sources"]), "hipoteses": list(scenario["assumptions"]),
    }


def component_view(table: dict, scenarios: dict[str, dict], repairs: dict, *, points: int = 41) -> dict:
    """Um bloco por grupo da FMECA, com as duas bases de tempo e os cenários de reparo."""
    groups = [item["id"] for item in table["itens"]]
    validate_repairs(repairs, groups)
    horizon = float(max(table["horizontes_anos"]))
    items = []
    for item in table["itens"]:
        by_basis = {}
        for name in item["cenarios"]:
            scenario = scenarios[name]
            basis = scenario.get("time_base", {}).get("basis")
            if basis in by_basis:
                raise ValueError(f"{item['id']}: dois cenários na mesma base de tempo.")
            by_basis[basis] = _base(scenario, repairs, item["id"], horizon, points)
        if sorted(by_basis) != sorted(BASES):
            raise ValueError(f"{item['id']}: faltam os cenários de operação e de calendário.")
        items.append({"id": item["id"], "nome": item["nome"], "bases": {basis: by_basis[basis] for basis in BASES}})
    return {
        "horizonte_anos": horizon,
        "grupos": items,
        "reparo": [{key: repair[key] for key in ("id", "nome", "tipo", "deteccao_horas", "fontes", "hipoteses", "ressalvas")}
                   for repair in repairs["cenarios"]],
        "ressalvas": list(repairs["ressalvas"]),
        "limites": [
            "Taxa de falha constante (vida exponencial), sem mortalidade infantil nem desgaste.",
            "Cada grupo é analisado isoladamente, sem topologia do inversor.",
            "Disponibilidade estacionária: MTBF / (MTBF + parada por falha), com o MTBF em horas de calendário.",
            "Horas paradas por ano = falhas por ano × parada por falha.",
        ],
    }
