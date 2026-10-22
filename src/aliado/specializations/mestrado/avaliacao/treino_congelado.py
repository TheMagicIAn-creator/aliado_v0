"""O treino congelado: a configuração e os pesos de uma rodada de treino, conferidos pelos hashes gravados antes de
qualquer pontuação."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from aliado.science.deteccao.pesos.arquivos import load_model
from aliado.science.deteccao.redes.autoencoders import MODELS, Hyperparameters
from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig


@dataclass
class TrainedDetectors:
    folder: Path
    config: ExperimentConfig
    frozen: dict
    models: dict  # (modelo, semente) -> rede
    thresholds: dict  # (modelo, semente, k) -> limiar


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_thresholds(folder: str | Path) -> tuple[TrainedDetectors, dict]:
    """Configuração e limiares de uma rodada congelada, conferidos pelo hash, sem carregar os pesos.

    Devolve também o relatório do treino, que guarda o caminho e o hash de cada modelo.
    """
    folder = Path(folder)
    frozen = json.loads((folder / "configuracao.json").read_text(encoding="utf-8"))
    summary = json.loads((folder / "relatorio.json").read_text(encoding="utf-8"))
    raw = frozen["configuracao"]
    config = ExperimentConfig(**(raw | {
        "fractions": tuple(raw["fractions"]), "seeds": tuple(raw["seeds"]),
        "sensitivity_k": tuple(raw["sensitivity_k"]), "hyperparameters": Hyperparameters(**raw["hyperparameters"])}))
    if config.digest() != frozen["sha256"] or summary["configuracao_sha256"] != frozen["sha256"]:
        raise ValueError("A configuração do treino não confere com o hash gravado.")
    thresholds = {(kind, seed, int(k)): float(value)
                  for kind in MODELS for seed in config.seeds
                  for k, value in summary["modelos"][kind]["sementes"][str(seed)]["sensibilidade_k"].items()}
    return TrainedDetectors(folder, config, frozen, {}, thresholds), summary


def load_training(folder: str | Path) -> TrainedDetectors:
    """Rodada de treino congelada, com configuração e pesos conferidos pelos hashes gravados."""
    trained, summary = load_thresholds(folder)
    for kind in MODELS:
        for seed in trained.config.seeds:
            run = summary["modelos"][kind]["sementes"][str(seed)]
            path = trained.folder / run["arquivos"]["modelo"]["caminho"]
            if _sha256(path) != run["arquivos"]["modelo"]["sha256"]:
                raise ValueError(f"Os pesos de {path.name} não conferem com o hash gravado.")
            model, checkpoint = load_model(path)
            if (checkpoint["modelo"], checkpoint["semente"]) != (kind, seed):
                raise ValueError(f"{path.name} não é o modelo {kind} da semente {seed}.")
            trained.models[(kind, seed)] = model
    return trained
