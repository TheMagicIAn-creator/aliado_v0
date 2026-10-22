"""Os arquivos da reanálise: a configuração, os inícios, o relatório e as métricas por ensaio, numa pasta nova; nunca
sobrescreve."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from aliado.specializations.mestrado.avaliacao.artefatos import _csv
from aliado.specializations.mestrado.reanalise.relatorio import _markdown
from aliado.specializations.mestrado.treino.artefatos import environment


def export_reanalysis(report: dict, evaluation_dir: str | Path, output: str | Path,
                      runs: dict | None = None) -> dict[str, str]:
    """Configuração, inícios, relatório e métricas por ensaio numa pasta nova; nunca sobrescreve."""
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    paths = {"configuracao": folder / "configuracao.json", "inicio": folder / "inicio.json",
             "relatorio_json": folder / "relatorio.json", "relatorio_md": folder / "relatorio.md"}
    frozen = {"inicio": report["inicio"]["configuracao"], "sha256": report["inicio"]["configuracao_sha256"],
              "executado_em": date.today().isoformat(), "origem": report["origem"], "regras": report["regras"],
              "ambiente": environment()}
    paths["configuracao"].write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["inicio"].write_text(json.dumps(report["inicio"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["relatorio_json"].write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                       encoding="utf-8")
    official = json.loads((Path(evaluation_dir) / "relatorio.json").read_text(encoding="utf-8"))
    paths["relatorio_md"].write_text(_markdown(report, official), encoding="utf-8")
    if runs is not None:
        paths["metricas"] = folder / "metricas_por_ensaio.csv"
        paths["metricas"].write_text(_csv(runs), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
