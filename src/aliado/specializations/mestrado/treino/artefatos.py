"""Os arquivos do treino: os pesos, os históricos, os escores da calibração, a configuração congelada e o relatório,
numa pasta nova; nunca sobrescreve."""

from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import torch

from aliado.science.deteccao.pesos.arquivos import save_model
from aliado.science.identidade.hashes import sha256_file
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.preparo import artefatos as artefatos_do_preparo
from aliado.specializations.mestrado.preparo import preparacao
from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig
from aliado.specializations.mestrado.treino.detectores import Run
from aliado.specializations.mestrado.treino.relatorio import _markdown
from aliado.specializations.mestrado.treino.resumo import summarize


def environment() -> dict:
    return {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
            "threads": torch.get_num_threads(), "sistema": platform.platform()}


def export_training(runs: list[Run], prepared: preparacao.PreparedGPVS, config: ExperimentConfig,
                    output: str | Path) -> dict[str, str]:
    """Modelos, históricos, escores de calibração, configuração e relatório numa pasta nova."""
    if prepared.purge != config.purge or tuple(prepared.fractions) != tuple(config.fractions):
        raise ValueError("Os dados preparados não seguem a divisão da configuração congelada.")
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "modelos").mkdir()
    (folder / "historicos").mkdir()
    files = {}
    for run in runs:
        name = f"{run.kind}-s{run.seed}"
        model_path = folder / "modelos" / f"{name}.pt"
        save_model(run.model, model_path, kind=run.kind, seed=run.seed, n_features=prepared.scaled.shape[1],
                   hp=config.hyperparameters)
        history_path = folder / "historicos" / f"{name}.csv"
        rows = zip(run.history.train_loss, run.history.validation_loss)
        history_path.write_text("epoca,perda_treino,perda_validacao\n" + "".join(
            f"{epoch},{train!r},{validation!r}\n" for epoch, (train, validation) in enumerate(rows, start=1)),
            encoding="utf-8")
        files[name] = {"modelo": {"caminho": f"modelos/{name}.pt", "sha256": sha256_file(model_path)},
                       "historico": {"caminho": f"historicos/{name}.csv", "sha256": sha256_file(history_path)}}
    paths = {"configuracao": folder / "configuracao.json", "relatorio_json": folder / "relatorio.json",
             "relatorio_md": folder / "relatorio.md", "escores": folder / "escores_calibracao.npz",
             "normalizacao": folder / "normalizacao.npz"}
    np.savez_compressed(paths["escores"], **{f"{run.kind}_s{run.seed}_k{k}": scores
                                             for run in runs for k, scores in run.scores.items()})
    artefatos_do_preparo.save_normalization(prepared, paths["normalizacao"])
    frozen = {"configuracao": config.as_dict(), "sha256": config.digest(), "ambiente": environment(),
              "dados": {"conjunto": ensaios.DATASET_NAME, "doi": ensaios.DATASET_DOI, "hashes": prepared.hashes}}
    paths["configuracao"].write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = summarize(runs, prepared, config, files)
    paths["relatorio_json"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                       encoding="utf-8")
    paths["relatorio_md"].write_text(_markdown(summary, config), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
