"""Os arquivos da avaliação: a configuração congelada, os escores, as métricas por ensaio e o relatório, numa pasta
nova; nunca sobrescreve."""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from pathlib import Path

import numpy as np

from aliado.science.deteccao.redes.autoencoders import MODELS
from aliado.specializations.mestrado.avaliacao.configuracao import EvaluationConfig
from aliado.specializations.mestrado.avaliacao.decisao import SECONDARY, run_metrics
from aliado.specializations.mestrado.avaliacao.relatorio import _markdown
from aliado.specializations.mestrado.avaliacao.resumo import summarize
from aliado.specializations.mestrado.avaliacao.treino_congelado import TrainedDetectors
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.preparo import preparacao
from aliado.specializations.mestrado.treino.artefatos import environment


def _csv(runs_by_seed: dict) -> str:
    stream = io.StringIO()
    fields = ["modelo", "semente", "ensaio", "detectado", "atraso_ms", "atraso_janelas", "alarmes_pre_falha",
              "janelas_pre_falha", "sensibilidade", "especificidade", *SECONDARY, "vp", "fn", "fp", "vn"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for (kind, seed), metrics in runs_by_seed.items():
        for name, result in metrics["ensaios"].items():
            writer.writerow({"modelo": kind, "semente": seed, "ensaio": name, **result})
    return stream.getvalue()


def export_evaluation(scores: dict, trained: TrainedDetectors, prepared: preparacao.PreparedGPVS,
                      config: EvaluationConfig, output: str | Path) -> dict[str, str]:
    """Configuração congelada, escores, métricas por ensaio e relatório numa pasta nova."""
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    run_date = date.today().isoformat()
    summary = summarize(scores, trained, prepared, config)
    paths = {"configuracao": folder / "configuracao.json", "relatorio_json": folder / "relatorio.json",
             "relatorio_md": folder / "relatorio.md", "metricas": folder / "metricas_por_ensaio.csv",
             "escores": folder / "escores.npz"}
    frozen = {"avaliacao": config.as_dict(), "sha256": config.digest(), "executado_em": run_date,
              "treino": {"pasta": trained.folder.as_posix(), "configuracao_sha256": trained.frozen["sha256"]},
              "dados": {"conjunto": ensaios.DATASET_NAME, "doi": ensaios.DATASET_DOI, "hashes": prepared.hashes},
              "ambiente": environment()}
    paths["configuracao"].write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    arrays = {}
    for (kind, seed, k), values in scores.items():
        arrays |= {f"{kind}_s{seed}_k{k}_saudavel_{name}": block for name, block in zip(ensaios.HEALTHY, values["saudavel"])}
        arrays |= {f"{kind}_s{seed}_k{k}_{name}": array for name, array in values["ensaios"].items()}
    np.savez_compressed(paths["escores"], **arrays)
    k = trained.config.top_k
    runs = {(kind, seed): run_metrics(scores[(kind, seed, k)], trained.thresholds[(kind, seed, k)], prepared,
                                      config.confirmations)
            for kind in MODELS for seed in trained.config.seeds}
    paths["metricas"].write_text(_csv(runs), encoding="utf-8")
    paths["relatorio_json"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                       encoding="utf-8")
    paths["relatorio_md"].write_text(_markdown(summary, trained, config, run_date), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
