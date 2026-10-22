"""A pontuação: o erro por variável e os escores do teste saudável e dos ensaios com falha, para cada modelo, semente
e k."""

from __future__ import annotations

import numpy as np

from aliado.science.deteccao.escore.top_k import top_k_scores
from aliado.science.deteccao.inferencia.erros import feature_errors
from aliado.science.deteccao.particao.sequencias import sequences_from_flow
from aliado.specializations.mestrado.avaliacao.treino_congelado import TrainedDetectors
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.preparo import preparacao
from aliado.specializations.mestrado.treino.detectores import model_inputs, training_blocks


def segment_errors(kind: str, model, scaled: np.ndarray, sequence: int) -> np.ndarray:
    """Erro por variável de um trecho contínuo; no AE-LSTM, a 1ª janela só se repete no início do trecho."""
    inputs = np.asarray(scaled, dtype=np.float32) if kind == "denso" else sequences_from_flow(scaled, sequence)
    return feature_errors(model, inputs)


def errors_all(trained: TrainedDetectors, prepared: preparacao.PreparedGPVS) -> dict[str, np.ndarray]:
    """A matriz de erros por variável de cada modelo e semente: na calibração, no teste saudável de cada ensaio e em
    cada ensaio com falha (`denso_s42_calibracao`, `denso_s42_saudavel_F0L`, `denso_s42_F1L`…)."""
    sequence = trained.config.hyperparameters.sequence
    calibration = training_blocks(prepared)["calibration"]
    arrays = {}
    for (kind, seed), model in trained.models.items():
        key = f"{kind}_s{seed}"
        arrays[f"{key}_calibracao"] = feature_errors(model, model_inputs(kind, prepared.scaled, calibration, sequence))
        for name in ensaios.HEALTHY:
            block = prepared.split["por_ensaio"][name]["test"]
            arrays[f"{key}_saudavel_{name}"] = segment_errors(kind, model, prepared.scaled[block], sequence)
        for name, item in prepared.faults.items():
            arrays[f"{key}_{name}"] = segment_errors(kind, model, item["scaled"], sequence)
    return arrays


def score_segment(kind: str, model, scaled: np.ndarray, sequence: int, ks) -> dict[int, np.ndarray]:
    errors = segment_errors(kind, model, scaled, sequence)
    return {int(k): top_k_scores(errors, k) for k in ks}


def score_all(trained: TrainedDetectors, prepared: preparacao.PreparedGPVS) -> dict:
    """Escores do teste saudável (por ensaio) e dos 14 ensaios com falha, para cada modelo, semente e k."""
    config = trained.config
    if prepared.hashes != trained.frozen["dados"]["hashes"]:
        raise ValueError("Os dados preparados não são os do treino.")
    if prepared.purge != config.purge or tuple(prepared.fractions) != tuple(config.fractions):
        raise ValueError("Os dados preparados não seguem a divisão do treino.")
    tests = [prepared.split["por_ensaio"][name]["test"] for name in ensaios.HEALTHY]
    scores = {}
    for (kind, seed), model in trained.models.items():
        sequence = config.hyperparameters.sequence
        healthy = [score_segment(kind, model, prepared.scaled[block], sequence, config.sensitivity_k) for block in tests]
        faults = {name: score_segment(kind, model, item["scaled"], sequence, config.sensitivity_k)
                  for name, item in prepared.faults.items()}
        for k in config.sensitivity_k:
            scores[(kind, seed, int(k))] = {"saudavel": [block[k] for block in healthy],
                                            "ensaios": {name: values[k] for name, values in faults.items()}}
    return scores
