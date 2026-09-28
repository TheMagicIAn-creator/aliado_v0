"""Modelos analíticos RAM; contratos e referências em docs/ciencia/confiabilidade.md."""

from __future__ import annotations

import copy
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

NIST = "https://www.itl.nist.gov/div898/handbook/apr/section1/"
NASA = "https://extapps.ksc.nasa.gov/Reliability/Documents/Availability_What_is_it.pdf"
METHOD_SOURCES = {
    "exponential": [NIST + "apr161.htm"],
    "weibull": [NIST + "apr162.htm"],
    "series": [NIST + "apr182.htm"],
    "parallel": [NIST + "apr183.htm"],
    "maintainability_exponential": [NIST + "apr161.htm", NASA],
    "availability_inherent": [NASA],
}
TIME_UNITS = {"s", "min", "h", "day", "year"}
TIME_BASES = {"operation": "horas de operação", "calendar": "horas de calendário"}
_LOG_MAX = math.log(sys.float_info.max)


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: forneça um número finito.")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label}: fora do intervalo numérico suportado.") from exc
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        bound = "maior que zero" if positive else "não negativo"
        raise ValueError(f"{label}: deve ser finito e {bound}.")
    return result


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: informe texto não vazio.")
    return value


def _texts(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label}: informe uma lista não vazia de textos.")
    return [_text(item, label) for item in value]


def _fields(value: Any, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label}: campos esperados: {', '.join(sorted(expected))}.")
    return value


def _finite(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{label}: resultado fora do intervalo numérico suportado.")
    return value


def _exp(log_value: float, label: str) -> float:
    if log_value > _LOG_MAX:
        raise ValueError(f"{label}: resultado fora do intervalo numérico suportado.")
    return _finite(math.exp(log_value), label)


def _complement_product(complements: list[float]) -> float:
    """Return 1-prod(1-x), retaining small probabilities near the endpoints."""
    if any(value == 1 for value in complements):
        return 1.0
    return -math.expm1(math.fsum(math.log1p(-value) for value in complements))


def _lifetime(model: str, params: dict, times: list[float]) -> tuple[list[dict], float]:
    if model == "exponential":
        _fields(params, {"rate"}, "parameters/exponential")
        rate = _number(params["rate"], "rate", positive=True)
        mttf = _finite(1 / rate, "MTTF")
        rows = [
            {
                "time": t,
                "reliability": math.exp(-rate * t),
                "failure_probability": -math.expm1(-rate * t),
                "hazard": rate,
                "hazard_status": "finite",
            }
            for t in times
        ]
        return rows, mttf
    if model != "weibull":
        raise ValueError("Modelo de vida deve ser exponential ou weibull.")
    _fields(params, {"shape", "scale"}, "parameters/weibull")
    shape = _number(params["shape"], "shape", positive=True)
    scale = _number(params["scale"], "scale", positive=True)
    try:
        mttf = _exp(math.log(scale) + math.lgamma(1 + 1 / shape), "MTTF")
    except (OverflowError, ValueError) as exc:
        raise ValueError("MTTF: resultado fora do intervalo numérico suportado.") from exc
    rows = []
    for t in times:
        if t == 0:
            hazard = None if shape < 1 else (1 / scale if shape == 1 else 0.0)
            cumulative = 0.0
        else:
            log_ratio = math.log(t) - math.log(scale)
            log_cumulative = shape * log_ratio
            cumulative = math.inf if log_cumulative > _LOG_MAX else math.exp(log_cumulative)
            hazard = _exp(math.log(shape) - math.log(scale) + (shape - 1) * log_ratio, "h(t)")
        if hazard is not None:
            _finite(hazard, "h(t)")
        rows.append({
            "time": t,
            "reliability": math.exp(-cumulative),
            "failure_probability": -math.expm1(-cumulative),
            "hazard": hazard,
            "hazard_status": "positive_infinity" if hazard is None else "finite",
        })
    return rows, mttf


def _hourly_rate_in_years(kind: str, unit: str, params: dict, time_base: Any) -> tuple[dict, str]:
    """Convert a constant hourly rate to 1/year; the only unit conversion offered."""
    if kind != "exponential" or unit != "year":
        raise ValueError("time_base: disponível apenas para exponential com time_unit year.")
    _fields(time_base, {"rate_unit", "hours_per_year", "basis"}, "time_base")
    if time_base["rate_unit"] != "h":
        raise ValueError("time_base.rate_unit: informe h.")
    basis = time_base["basis"]
    if not isinstance(basis, str) or basis not in TIME_BASES:
        raise ValueError(f"time_base.basis: escolha entre {', '.join(TIME_BASES)}.")
    hours = _number(time_base["hours_per_year"], "time_base.hours_per_year", positive=True)
    if hours > 8784:
        raise ValueError("time_base.hours_per_year: no máximo 8784 h por ano.")
    _fields(params, {"rate"}, "parameters/exponential")
    rate = _number(params["rate"], "rate", positive=True) * hours
    note = (f"Taxa informada em 1/h convertida para 1/ano com {hours:g} h/ano ({TIME_BASES[basis]}); "
            "tempos e MTTF em anos dessa base; h(t) em 1/ano; R(t) e F(t) adimensionais.")
    return {"rate": rate}, note


def evaluate_scenario(scenario: dict) -> dict:
    """Evaluate an explicit scenario without fitting data, I/O, network, or defaults.

    Required common fields: name, kind, time_unit, parameters, sources, assumptions.
    Curves also require sorted, distinct nonnegative times. Optional time_base converts
    an hourly exponential rate to years. See the documented schemas.
    """
    if not isinstance(scenario, dict):
        raise ValueError("O cenário deve ser um objeto JSON.")
    kind = scenario.get("kind")
    if not isinstance(kind, str) or kind not in METHOD_SOURCES:
        raise ValueError(f"kind: escolha entre {', '.join(METHOD_SOURCES)}.")
    fields = {"name", "kind", "time_unit", "parameters", "sources", "assumptions"}
    if kind != "availability_inherent":
        fields.add("times")
    if "time_base" in scenario:
        fields.add("time_base")
    _fields(scenario, fields, "scenario")
    _text(scenario["name"], "name")
    unit = scenario["time_unit"]
    if not isinstance(unit, str) or unit not in TIME_UNITS:
        raise ValueError(f"time_unit: escolha entre {', '.join(sorted(TIME_UNITS))}.")
    _texts(scenario["sources"], "sources")
    _texts(scenario["assumptions"], "assumptions")
    params = scenario["parameters"]
    if not isinstance(params, dict):
        raise ValueError("parameters: deve ser um objeto JSON.")
    conversion = None
    if "time_base" in scenario:
        params, conversion = _hourly_rate_in_years(kind, unit, params, scenario["time_base"])
    times = []
    if kind != "availability_inherent":
        raw_times = scenario["times"]
        if not isinstance(raw_times, list) or not raw_times:
            raise ValueError("times: informe uma lista não vazia.")
        times = [_number(t, "times") for t in raw_times]
        if any(a >= b for a, b in zip(times, times[1:])):
            raise ValueError("times: devem estar em ordem crescente, sem repetições.")
    result = {
        "schema_version": 1,
        **copy.deepcopy(scenario),
        "method_sources": list(METHOD_SOURCES[kind]),
        "units": {"time": unit, "probability": "1"},
        "summary": {},
        "rows": [],
        "limitations": [
            "Projeção condicionada aos parâmetros e hipóteses informados; sem ajuste empírico.",
            conversion or "Nenhuma conversão entre tempo de calendário e tempo de operação foi realizada.",
            "Referências fornecidas não foram verificadas automaticamente.",
        ],
    }
    if kind in {"exponential", "weibull"}:
        rows, mttf = _lifetime(kind, params, times)
        result["rows"] = rows
        result["summary"] = {"mttf": mttf}
        result["units"].update({"mttf": unit, "hazard": f"1/{unit}"})
        if conversion:
            result["summary"]["rate"] = params["rate"]
            result["units"].update({"rate": f"1/{unit}", "parameters.rate": "1/h"})
        result["limitations"].append("MTTF é tempo médio até falha, não MTBF de sistema reparável.")
        if kind == "weibull" and params["shape"] < 1 and times[0] == 0:
            result["limitations"].append(
                "Weibull com shape < 1: h(0) tem limite +infinito; representado por null e hazard_status."
            )
    elif kind in {"series", "parallel"}:
        _fields(params, {"independent", "components"}, "parameters/system")
        if params["independent"] is not True:
            raise ValueError("Série/paralelo exigem independent: true, como hipótese explícita.")
        components = params["components"]
        if not isinstance(components, list) or not components:
            raise ValueError("components: informe ao menos um componente.")
        curves = []
        names = set()
        for component in components:
            _fields(component, {"name", "model", "parameters"}, "component")
            name = _text(component["name"], "component.name")
            if name in names:
                raise ValueError("Os nomes dos componentes devem ser distintos.")
            names.add(name)
            curve, _ = _lifetime(component["model"], component["parameters"], times)
            curves.append(curve)
            source = METHOD_SOURCES[component["model"]][0]
            if source not in result["method_sources"]:
                result["method_sources"].append(source)
        for index, t in enumerate(times):
            if kind == "series":
                r = math.prod(curve[index]["reliability"] for curve in curves)
                f = _complement_product([curve[index]["failure_probability"] for curve in curves])
            else:
                f = math.prod(curve[index]["failure_probability"] for curve in curves)
                r = _complement_product([curve[index]["reliability"] for curve in curves])
            result["rows"].append({"time": t, "reliability": r, "failure_probability": f})
        result["limitations"].append(
            "Componentes independentes: não representa causas comuns, reparos, standby ou partilha de carga."
        )
        result["limitations"].append(
            "Série: a primeira falha derruba o sistema."
            if kind == "series" else "Paralelo ativo: basta um componente em operação."
        )
    elif kind == "maintainability_exponential":
        _fields(params, {"mttr"}, "parameters/maintainability")
        mttr = _number(params["mttr"], "mttr", positive=True)
        result["rows"] = [{"time": t, "maintainability": -math.expm1(-t / mttr)} for t in times]
        result["summary"] = {"mttr": mttr}
        result["units"]["mttr"] = unit
        result["limitations"].append("Tempo de reparo exponencial; taxa de reparo constante.")
    else:
        _fields(params, {"mtbf", "mttr"}, "parameters/availability")
        mtbf = _number(params["mtbf"], "mtbf", positive=True)
        mttr = _number(params["mttr"], "mttr")
        scale = max(mtbf, mttr)
        availability = (mtbf / scale) / (mtbf / scale + mttr / scale)
        result["summary"] = {"mtbf": mtbf, "mttr": mttr, "availability_inherent": availability}
        result["units"].update({"mtbf": unit, "mttr": unit})
        result["rows"] = [{"availability_inherent": availability}]
        result["limitations"].extend([
            "Disponibilidade inerente estacionária: inclui somente manutenção corretiva ativa.",
            "Exclui preventiva e atrasos logísticos/administrativos; não é disponibilidade operacional.",
            "MTBF é tempo médio de operação entre falhas; não foi inferido de MTTF.",
            "Médias constantes e ciclo reparável estacionário; MTTR zero representa limite ideal.",
        ])
    # Reject accidental NaN/Infinity in the public, portable JSON contract.
    json.dumps(result, allow_nan=False)
    return result


def export_result(result: dict, output_dir: str | Path, *, plot: bool = False) -> dict[str, str]:
    """Export into a new explicit directory; never overwrite an existing directory.

    Optional plotting imports matplotlib lazily. Export does not evaluate a scenario.
    """
    payload = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
    rows = result["rows"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("Resultado deve conter linhas para exportação.")
    figure = None
    if plot:
        try:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure
        except ImportError as exc:
            raise RuntimeError("Para curvas PNG, instale o extra aliado[science].") from exc
        figure = Figure(figsize=(8, 4.8), layout="constrained")
        FigureCanvasAgg(figure)
        axes = figure.subplots()
        if "time" in rows[0]:
            for metric in ("reliability", "failure_probability", "maintainability"):
                if metric in rows[0]:
                    axes.plot([row["time"] for row in rows], [row[metric] for row in rows], label=metric)
            axes.set_xlabel(f"Tempo ({result['time_unit']})")
            axes.legend()
        else:
            axes.bar(["Disponibilidade inerente"], [rows[0]["availability_inherent"]])
        axes.set_ylim(0, 1.02)
        axes.set_ylabel("Probabilidade")
        axes.set_title(result["name"])
        axes.grid(alpha=0.25)
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    paths = {extension: output / filename for extension, filename in {
        "json": "resultado.json", "csv": "curvas.csv", "markdown": "relatorio.md",
    }.items()}
    paths["json"].write_text(payload + "\n", encoding="utf-8")
    with paths["csv"].open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        f"# {result['name']}", "", f"Modelo: `{result['kind']}`. Unidade de tempo: `{result['time_unit']}`.",
        "", "## Parâmetros", "", "```json",
        json.dumps(result["parameters"], indent=2, ensure_ascii=False), "```",
        "", "## Resultados resumidos", "", "```json",
        json.dumps(result["summary"], indent=2, ensure_ascii=False), "```",
        "", "Curvas completas: [CSV](curvas.csv). Registro completo: [JSON](resultado.json).",
    ]
    for title, key in (("Unidades", "units"),):
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {name}: {unit}" for name, unit in result[key].items())
    for title, key in (("Hipóteses fornecidas", "assumptions"), ("Fontes dos parâmetros", "sources"),
                       ("Referências dos métodos", "method_sources"), ("Limitações", "limitations")):
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {entry}" for entry in result[key])
    if figure is not None:
        paths["png"] = output / "curvas.png"
        figure.savefig(paths["png"], dpi=150)
        lines.extend(["", "![Curvas](curvas.png)"])
    paths["markdown"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {kind: str(path) for kind, path in paths.items()}
