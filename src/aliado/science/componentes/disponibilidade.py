"""Confiabilidade por componente e disponibilidade dos 4 grupos da FMECA (lote 25).

As taxas vêm dos cenários exponenciais de cada grupo, um por base de tempo (horas de operação ou
de calendário), e os tempos de reparo, de `reparos.json`. Curvas e disponibilidade saem do serviço
RAM (`evaluate_scenario`), sem ajuste empírico. O reparo corre em horas de calendário: na
disponibilidade, o MTBF é 8.760 / (λ · horas por ano), em horas de calendário, e a parada por
falha é o tempo para detectar mais o de reparar. Sem dependências externas.
"""

from __future__ import annotations

from aliado.science.componentes.reparos import validate_repairs
from aliado.science.confiabilidade.cenarios import evaluate_scenario

CALENDAR_HOURS = 8760.0
BASES = ("operation", "calendar")


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
            "Cada grupo é analisado isoladamente, sem a topologia do equipamento.",
            "Disponibilidade estacionária: MTBF / (MTBF + parada por falha), com o MTBF em horas de calendário.",
            "Horas paradas por ano = falhas por ano × parada por falha.",
        ],
    }
