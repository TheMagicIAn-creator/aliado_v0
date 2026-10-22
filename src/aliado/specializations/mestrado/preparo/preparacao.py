"""O preparo dos dados do GPVS-Faults para o protocolo M14, sem pandas nem scikit-learn, como no repositório de
origem: divisão 50/15/15/20 por ensaio saudável, normalização pela linha de base do treino e comissionamento dos
ensaios com falha pela primeira metade do próprio trecho pré-falha.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aliado.science.deteccao.normalizacao.escala_robusta import RobustScaler, robust_center_scale
from aliado.science.deteccao.particao.blocos import DEFAULT_FRACTIONS, ROLES, temporal_split
from aliado.specializations.mestrado.atributos.extracao import extract_all
from aliado.specializations.mestrado.base.ensaios import FAULTY, HEALTHY

BASELINE_FRACTION = 0.50
BASELINE_MIN_WINDOWS = 30
IQR_FLOOR_FRACTION = 0.10
# Separação canônica entre blocos, decidida pelo pesquisador em 27/09/2026: a verificação do
# lote 13 mostrou |ACF| < 0,2 em 90% das variáveis só no lag 12. A origem usava 2 janelas,
# que continuam servindo para conferir a reprodução.
PURGE = 11


@dataclass
class PreparedGPVS:
    healthy_values: np.ndarray       # (N, 24) variáveis brutas de F0L seguido de F0M
    healthy_experiment: np.ndarray   # ensaio de cada janela saudável
    split: dict                      # papel -> índices globais; "por_ensaio" -> ensaio -> papel -> índices
    normalized: np.ndarray           # normalização pela linha de base do treino de cada ensaio
    scaler: RobustScaler             # ajustado só no treino normalizado
    scaled: np.ndarray               # entrada dos modelos
    iqr_floor: np.ndarray
    baselines: dict
    faults: dict                     # ensaio -> escalado, índices de avaliação e metadados
    hashes: dict
    extraction: dict
    fractions: tuple
    purge: int


def prepare(directory: str | Path, *, cache: str | Path | None = None,
            fractions=DEFAULT_FRACTIONS, purge: int = PURGE) -> PreparedGPVS:
    experiments, hashes = extract_all(directory, cache=cache)
    values = np.concatenate([experiments[name].values for name in HEALTHY])
    labels = np.concatenate([np.full(len(experiments[name].values), name) for name in HEALTHY])
    split = {role: [] for role in ROLES}
    per_experiment = {}
    offset = 0
    for name in HEALTHY:
        local = temporal_split(len(experiments[name].values), fractions=fractions, purge=purge)
        per_experiment[name] = {role: local[role] + offset for role in ROLES}
        for role in ROLES:
            split[role].append(per_experiment[name][role])
        offset += len(experiments[name].values)
    split = {role: np.concatenate(parts) for role, parts in split.items()}
    split["por_ensaio"] = per_experiment

    # Piso da escala: 10% do IQR de todo o treino, nunca abaixo de 1e-6.
    train = values[split["train"]].astype(np.float64)
    q25, q75 = np.percentile(train, (25, 75), axis=0)
    iqr_floor = np.maximum((q75 - q25) * IQR_FLOOR_FRACTION, 1e-6)
    normalized = np.empty_like(values, dtype=np.float32)
    baselines = {}
    for name in HEALTHY:
        center, scale = robust_center_scale(values[per_experiment[name]["train"]], floor=iqr_floor)
        mask = labels == name
        normalized[mask] = ((values[mask] - center) / scale).astype(np.float32)
        baselines[name] = {"mediana": center, "escala": scale}
    scaler = RobustScaler.fit(normalized[split["train"]])
    scaled = scaler.transform(normalized)

    faults = {}
    for name in FAULTY:
        item = experiments[name]
        pre = np.flatnonzero(item.phase == "pre_fault")
        n_baseline = max(BASELINE_MIN_WINDOWS, int(np.floor(len(pre) * BASELINE_FRACTION)))
        if n_baseline >= len(pre):
            raise ValueError(f"{name}: pré-falha insuficiente para comissionamento e teste.")
        # Comissionamento: cada ensaio com falha usa a primeira metade do próprio pré-falha.
        center, scale = robust_center_scale(item.values[pre[:n_baseline]], floor=iqr_floor)
        commissioned = ((item.values - center) / scale).astype(np.float32)
        faults[name] = {
            "scaled": scaler.transform(commissioned),
            "comissionamento": pre[:n_baseline],
            "pre_teste": pre[n_baseline:],
            "transicao": np.flatnonzero(item.phase == "transition"),
            "pos_falha": np.flatnonzero(item.phase == "post_fault"),
        }
    return PreparedGPVS(values, labels, split, normalized, scaler, scaled, iqr_floor, baselines, faults,
                        hashes, {name: item.metadata for name, item in experiments.items()},
                       tuple(fractions), int(purge))
