"""Treino dos autoencoders e limiar na calibração saudável do GPVS (lote 14, protocolo M14).

Os modelos veem só o treino (pesos) e a validação (parada). A calibração serve só para o
limiar. O teste saudável e os ensaios com falha não são pontuados aqui: ficam fechados até
a avaliação do lote 15, com a configuração já congelada. Exige o extra `ml`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from aliado.science.deteccao.escore.top_k import top_k_scores
from aliado.science.deteccao.inferencia.erros import feature_errors
from aliado.science.deteccao.limiar.calibracao import (
    DegenerateThresholdError,
    ThresholdCalibration,
    calibrate_threshold,
    minimum_n_for_percentile,
)
from aliado.science.deteccao.particao.sequencias import sequences_for_blocks
from aliado.science.deteccao.redes.autoencoders import (
    MODEL_NAMES,
    MODELS,
)
from aliado.science.deteccao.treino.laco import TrainingHistory, fit
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.preparo import preparacao
from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig

TRAINING_ROLES = ("train", "validation", "calibration")


@dataclass
class Run:
    kind: str
    seed: int
    model: torch.nn.Module
    history: TrainingHistory
    scores: dict[int, np.ndarray]  # k -> escores da calibração
    thresholds: dict[int, ThresholdCalibration]
    block_sizes: tuple[int, ...]  # calibração de cada ensaio saudável, na ordem de ensaios.HEALTHY


def training_blocks(prepared: preparacao.PreparedGPVS) -> dict[str, list[np.ndarray]]:
    """Blocos contíguos por papel e ensaio saudável; o teste não é entregue ao treino."""
    return {role: [prepared.split["por_ensaio"][name][role] for name in ensaios.HEALTHY] for role in TRAINING_ROLES}


def model_inputs(kind: str, scaled: np.ndarray, blocks, sequence: int) -> np.ndarray:
    if kind == "denso":
        return np.asarray(scaled, dtype=np.float32)[np.concatenate(blocks)]
    return sequences_for_blocks(scaled, blocks, sequence)[0]


def train_detectors(scaled: np.ndarray, blocks: dict, config: ExperimentConfig, *, progress=None) -> list[Run]:
    """Cada modelo em cada semente: treino, parada pela validação e limiar na calibração."""
    hp = config.hyperparameters
    inputs = {kind: {role: model_inputs(kind, scaled, blocks[role], hp.sequence) for role in TRAINING_ROLES}
              for kind in MODELS}
    sizes = tuple(len(block) for block in blocks["calibration"])
    minimum = minimum_n_for_percentile(config.percentile)
    if minimum is None or sum(sizes) < minimum:
        # Recusa antes de treinar: o limiar cairia no maior escore da calibração.
        raise DegenerateThresholdError(
            f"p{config.percentile:g} exige ao menos {minimum} janelas de calibração; há {sum(sizes)}.")
    runs = []
    for seed in config.seeds:
        for kind in MODELS:
            model, history = fit(kind, inputs[kind]["train"], inputs[kind]["validation"], seed=seed, hp=hp)
            errors = feature_errors(model, inputs[kind]["calibration"])
            scores = {k: top_k_scores(errors, k) for k in config.sensitivity_k}
            thresholds = {k: calibrate_threshold(scores[k], config.percentile) for k in config.sensitivity_k}
            runs.append(Run(kind, seed, model, history, scores, thresholds, sizes))
            if progress:
                progress(f"{MODEL_NAMES[kind]}, semente {seed}: melhor época {history.best_epoch} de "
                         f"{history.epochs}; limiar {thresholds[config.top_k].value:.4g}")
    return runs
