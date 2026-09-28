"""FMECA por notas ordinais e, separada, a leitura pelas taxas de falha (lote 16).

O NPR (S × O × D, notas de 1 a 10 no critério da IEC 60812) é calculado, nunca aceito pronto.
A leitura pelas taxas usa os cenários exponenciais do serviço RAM. As duas não se fundem:
nenhuma nota é derivada de taxa e nenhuma taxa de nota. Sem dependências externas.
"""

from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path

from aliado.science.ram import evaluate_scenario

NOTES = ("S", "O", "D")
TABLE_FIELDS = {"nome", "decidida_em", "criterio", "fonte_notas", "horizontes_anos", "itens", "ressalvas"}
ITEM_FIELDS = {"id", "nome", "item_na_fonte", "S", "O", "D", "cenarios", "ressalvas"}
BASIS_NAMES = {"operation": "operação", "calendar": "calendário"}


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
            "Disponibilidade não calculada: não há fonte de tempo de reparo (decisão de 27/09/2026).",
        ],
    }


def _percent(probability: float) -> str:
    return "> 99.9%" if probability > 0.999 else f"{100 * probability:.1f}%"


def _name(items: list[dict], item_id: str) -> str:
    return next(item["nome"] for item in items if item["id"] == item_id)


def _markdown(result: dict) -> str:
    items = result["itens"]
    lines = [
        f"# {result['nome']}", "",
        f"Decidida em {result['decidida_em']}. {result['criterio']} Notas: {result['fonte_notas']}", "",
        "## 1. Criticidade pelas notas (NPR)", "",
        "| Prioridade | Grupo | Item na fonte | S | O | D | NPR |", "|---:|---|---|---:|---:|---:|---:|",
        *[f"| {item['posicoes']['npr']} | {item['nome']} | {item['item_na_fonte']} | {item['S']} | {item['O']} | "
          f"{item['D']} | {item['npr']} |" for item in items],
        "", "## 2. Leitura pelas taxas de falha (separada; não altera as notas)", "",
    ]
    horizons = [str(t) for t in result["horizontes_anos"]]
    header = " | ".join(f"Chance de falhar em {t} ano(s) | Falhas esperadas em {t} ano(s)" for t in horizons)
    lines += [f"| Ordem | Grupo | λ (1/h) | Base | MTBF (h) | MTBF (anos) | {header} |",
              "|---:|---|---:|---|---:|---:|" + "---:|" * (2 * len(horizons))]
    for item in sorted((i for i in items if i["posicoes"]["taxa"]), key=lambda i: i["posicoes"]["taxa"]):
        for reading in item["leitura_pelas_taxas"]:
            values = " | ".join(f"{_percent(reading['horizontes'][t]['chance_de_falhar'])} | "
                                f"{reading['horizontes'][t]['falhas_esperadas']:.2f}" for t in horizons)
            lines.append(f"| {item['posicoes']['taxa']} | {item['nome']} | {reading['taxa_por_hora']:.3g} | "
                         f"{BASIS_NAMES[reading['base']]} ({reading['horas_por_ano']:g} h/ano) | "
                         f"{reading['mtbf_horas']:.0f} | {reading['mtbf_anos']:.1f} | {values} |")
    lines += ["", "## 3. As duas leituras lado a lado", "",
              "| Grupo | Posição pelo NPR | Posição pela ocorrência O | Posição pela taxa λ |", "|---|---:|---:|---:|",
              *[f"| {item['nome']} | {item['posicoes']['npr']} | {item['posicoes']['ocorrencia']} | "
                f"{item['posicoes']['taxa'] or '—'} |" for item in items], ""]
    if result["pares_discordantes_O_taxa"]:
        lines.append("Pares em que a ocorrência e a taxa apontam em sentidos opostos:")
        lines += [f"- {_name(items, pair['maior_O'])} tem O maior que {_name(items, pair['menor_O'])} "
                  f"({pair['O'][0]} > {pair['O'][1]}), mas taxa menor ({pair['taxas'][0]:.3g} < {pair['taxas'][1]:.3g} por hora)."
                  for pair in result["pares_discordantes_O_taxa"]]
        lines.append("")
    lines += ["As notas vêm de um levantamento de campo e as taxas, de outras fontes e populações. As duas "
              "leituras não são fundidas numa nota única.", "", "## 4. Ressalvas e limites", "",
              *[f"- {text}" for text in result["ressalvas"]],
              *[f"- {item['nome']}: {text}" for item in items for text in item["ressalvas"]],
              *[f"- {text}" for text in result["limites"]], "", "## Fontes das taxas", ""]
    for item in items:
        sources = {source for reading in item["leitura_pelas_taxas"] for source in reading["fontes"]}
        lines += [f"- {item['nome']}: " + " ".join(sorted(sources))]
    return "\n".join(lines) + "\n"


def _csv(result: dict) -> str:
    stream = io.StringIO()
    horizons = [str(t) for t in result["horizontes_anos"]]
    fields = ["id", "nome", "item_na_fonte", "S", "O", "D", "npr", "posicao_npr", "posicao_ocorrencia", "posicao_taxa",
              "base", "taxa_por_hora", "mtbf_horas", "mtbf_anos",
              *[f"{key}_{t}_anos" for t in horizons for key in ("chance_de_falhar", "falhas_esperadas")]]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for item in result["itens"]:
        base = {key: item[key] for key in ("id", "nome", "item_na_fonte", "S", "O", "D", "npr")} | {
            "posicao_npr": item["posicoes"]["npr"], "posicao_ocorrencia": item["posicoes"]["ocorrencia"],
            "posicao_taxa": item["posicoes"]["taxa"]}
        for reading in item["leitura_pelas_taxas"] or [{}]:
            row = dict(base)
            if reading:
                row |= {key: reading[key] for key in ("base", "taxa_por_hora", "mtbf_horas", "mtbf_anos")}
                for t in horizons:
                    row[f"chance_de_falhar_{t}_anos"] = reading["horizontes"][t]["chance_de_falhar"]
                    row[f"falhas_esperadas_{t}_anos"] = reading["horizontes"][t]["falhas_esperadas"]
            writer.writerow(row)
    return stream.getvalue()


def export_fmeca(result: dict, output: str | Path) -> dict[str, str]:
    """JSON, CSV e Markdown numa pasta nova; nunca sobrescreve."""
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    paths = {"json": folder / "fmeca.json", "csv": folder / "fmeca.csv", "markdown": folder / "fmeca.md"}
    paths["json"].write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    paths["csv"].write_text(_csv(result), encoding="utf-8")
    paths["markdown"].write_text(_markdown(result), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
