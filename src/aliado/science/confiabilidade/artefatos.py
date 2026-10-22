"""Os arquivos de um cenário de confiabilidade: JSON, CSV e Markdown e, se pedida, a curva em PNG, numa pasta nova."""

from __future__ import annotations

import csv
import json
from pathlib import Path


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
