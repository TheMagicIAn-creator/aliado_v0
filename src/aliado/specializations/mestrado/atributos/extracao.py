"""A extração dos 24 atributos de cada ensaio e o cache deles, que só vale com os mesmos arquivos (pelos hashes)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from aliado.specializations.mestrado.atributos.variaveis import PRIMARY_COLUMNS, feature_vector
from aliado.specializations.mestrado.base.ensaios import EXPERIMENTS, SOURCE_COLUMNS, WINDOW
from aliado.specializations.mestrado.base.leitura import (
    dataset_files,
    load_csv,
    sampling,
    verify_provenance,
)

CACHE_VERSION = 1


@dataclass
class ExperimentFeatures:
    name: str
    values: np.ndarray        # (janelas, 24), float32
    sample_start: np.ndarray  # início de cada janela em amostras
    phase: np.ndarray         # healthy | pre_fault | transition | post_fault
    metadata: dict = field(default_factory=dict)


def extract_experiment(name: str, data: np.ndarray) -> ExperimentFeatures:
    fault = int(name[1])
    info = sampling(data[:, 0])
    primary = data[:, [SOURCE_COLUMNS.index(c) for c in PRIMARY_COLUMNS]]
    windows = len(data) // WINDOW
    # Fronteira nominal no meio do registro: os CSVs não trazem canal de disparo.
    boundary = len(data) // 2 if fault else None
    starts = np.arange(windows) * WINDOW
    values = np.stack([feature_vector(primary[s:s + WINDOW]) for s in starts])
    if boundary is None:
        phase = np.full(windows, "healthy")
    else:
        phase = np.where(starts + WINDOW <= boundary, "pre_fault",
                         np.where(starts >= boundary, "post_fault", "transition"))
    if not np.isfinite(values).all():
        raise ValueError(f"{name}: variáveis não finitas.")
    return ExperimentFeatures(name, values, starts, phase.astype("U10"), {
        **info, "linhas": int(len(data)), "janelas": int(windows),
        "amostras_descartadas_no_fim": int(len(data) - windows * WINDOW),
        "fronteira_falha_amostra": boundary, "fronteira_metodo": "meio_nominal" if fault else None,
    })


def extract_all(directory: str | Path, *, cache: str | Path | None = None) -> tuple[dict, dict]:
    """Extrai os 16 ensaios, reaproveitando o cache só se os hashes dos CSVs forem os mesmos."""
    hashes = verify_provenance(directory)
    files = dataset_files(directory)
    cache_path = Path(cache) if cache else None
    if cache_path and cache_path.is_file():
        with np.load(cache_path, allow_pickle=False) as stored:
            meta = json.loads(str(stored["meta"]))
            if meta.get("hashes") == hashes and meta.get("versao") == CACHE_VERSION:
                return {name: ExperimentFeatures(name, stored[f"{name}_values"], stored[f"{name}_start"],
                                                 stored[f"{name}_phase"], meta["experimentos"][name])
                        for name in EXPERIMENTS}, hashes
    experiments = {name: extract_experiment(name, load_csv(path)) for name, path in files.items()}
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        arrays = {}
        for name, item in experiments.items():
            arrays |= {f"{name}_values": item.values, f"{name}_start": item.sample_start, f"{name}_phase": item.phase}
        meta = {"versao": CACHE_VERSION, "hashes": hashes,
                "experimentos": {name: item.metadata for name, item in experiments.items()}}
        temporary = cache_path.with_suffix(".tmp.npz")
        np.savez_compressed(temporary, meta=json.dumps(meta), **arrays)
        temporary.replace(cache_path)
    return experiments, hashes
