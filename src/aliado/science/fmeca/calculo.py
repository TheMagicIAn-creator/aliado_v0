"""FMECA por notas ordinais e, separada, a leitura pelas taxas de falha (lote 16).

O NPR (S × O × D, notas de 1 a 10 no critério da IEC 60812) é calculado, nunca aceito pronto.
A leitura pelas taxas usa os cenários exponenciais do serviço RAM. As duas não se fundem:
nenhuma nota é derivada de taxa e nenhuma taxa de nota. Sem dependências externas.
"""

from __future__ import annotations

import math

from aliado.science.confiabilidade.cenarios import evaluate_scenario
from aliado.science.fmeca.tabela import ITEM_FIELDS, NOTES, TABLE_FIELDS, _check_fields, _note


def _rate_reading(scenario: dict, horizons: list[float]) -> dict:
    """MTBF, chance de falhar e falhas esperadas de um cenário exponencial com taxa horária."""
    evaluated = evaluate_scenario(scenario)  # valida o cenário como o serviço RAM
    if scenario["kind"] != "exponential" or "time_base" not in scenario:
        raise ValueError(f"{scenario['name']}: a leitura pelas taxas exige exponencial com taxa em 1/h.")
    hourly = float(scenario["parameters"]["rate"])
    hours = float(scenario["time_base"]["hours_per_year"])
    yearly = hourly * hours
    return {
        "cenario": scenario["name"], "base": scenario["time_base"]["basis"], "horas_por_ano": hours,
        "taxa_por_hora": hourly, "mtbf_horas": 1 / hourly, "mtbf_anos": evaluated["summary"]["mttf"],
        "horizontes": {str(t): {"chance_de_falhar": -math.expm1(-yearly * t), "falhas_esperadas": yearly * t}
                       for t in horizons},
        "fontes": list(scenario["sources"]),
    }


def _positions(values: dict[str, float]) -> dict[str, int]:
    """Posição por valor decrescente; empates dividem a mesma posição."""
    ordered = sorted(values.values(), reverse=True)
    return {key: ordered.index(value) + 1 for key, value in values.items()}


def evaluate_fmeca(table: dict, scenarios: dict[str, dict]) -> dict:
    """NPR e prioridades pelas notas; leitura pelas taxas; posições lado a lado e pares discordantes."""
    _check_fields(table, TABLE_FIELDS, "tabela")
    horizons = table["horizontes_anos"]
    if not isinstance(horizons, list) or not horizons or any(
            isinstance(t, bool) or not isinstance(t, (int, float)) or t <= 0 for t in horizons):
        raise ValueError("horizontes_anos: lista de anos positivos.")
    items, seen = [], set()
    for raw in table["itens"]:
        _check_fields(raw, ITEM_FIELDS, f"item {raw.get('id', '?') if isinstance(raw, dict) else '?'}")
        if raw["id"] in seen:
            raise ValueError(f"item {raw['id']}: identificador repetido.")
        seen.add(raw["id"])
        notes = {note: _note(raw[note], f"{raw['id']}.{note}") for note in NOTES}
        readings = [_rate_reading(scenarios[name], horizons) for name in raw["cenarios"]]
        rates = {reading["taxa_por_hora"] for reading in readings}
        if len(rates) > 1:
            raise ValueError(f"{raw['id']}: os cenários do item usam taxas diferentes.")
        items.append({"id": raw["id"], "nome": raw["nome"], "item_na_fonte": raw["item_na_fonte"], **notes,
                      "npr": notes["S"] * notes["O"] * notes["D"], "ressalvas": list(raw["ressalvas"]),
                      "taxa_por_hora": rates.pop() if rates else None, "leitura_pelas_taxas": readings})
    by_npr = _positions({item["id"]: item["npr"] for item in items})
    by_occurrence = _positions({item["id"]: item["O"] for item in items})
    rated = {item["id"]: item["taxa_por_hora"] for item in items if item["taxa_por_hora"] is not None}
    by_rate = _positions(rated)
    for item in items:
        item["posicoes"] = {"npr": by_npr[item["id"]], "ocorrencia": by_occurrence[item["id"]],
                            "taxa": by_rate.get(item["id"])}
    discordant = [
        {"maior_O": a["id"], "menor_O": b["id"], "O": [a["O"], b["O"]], "taxas": [a["taxa_por_hora"], b["taxa_por_hora"]]}
        for a in items for b in items
        if a["id"] in rated and b["id"] in rated and a["O"] > b["O"] and a["taxa_por_hora"] < b["taxa_por_hora"]
    ]
    return {
        "schema_version": 1, "nome": table["nome"], "decidida_em": table["decidida_em"],
        "criterio": table["criterio"], "fonte_notas": table["fonte_notas"], "horizontes_anos": horizons,
        "itens": sorted(items, key=lambda item: (item["posicoes"]["npr"], item["id"])),
        "pares_discordantes_O_taxa": discordant,
        "ressalvas": list(table["ressalvas"]),
        "limites": [
            "O NPR multiplica notas ordinais: combinações diferentes podem dar o mesmo valor, e a ordem não mede o risco em escala.",
            "Falhas esperadas = λ × horas: cada falha é reparada ou trocada por componente equivalente, com a mesma taxa constante.",
            "Chance de falhar = 1 − exp(−λt), sem reparo: ao menos uma falha até o horizonte.",
            "Componentes analisados isoladamente, sem topologia de sistema.",
            "A disponibilidade de cada grupo fica na confiabilidade por componente, com os tempos de reparo do "
            "IEEE 493-2007 e de Baschel et al. (2018) (decisão de 30/09/2026).",
        ],
    }
