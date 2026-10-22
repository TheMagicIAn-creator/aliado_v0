"""Os arquivos da FMECA: JSON, CSV e Markdown numa pasta nova; nunca sobrescreve."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from aliado.science.fmeca.relatorio import _markdown


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
