"""A leitura da base: exatamente os 16 arquivos, a proveniência pelos hashes, os CSVs e a conferência da amostragem."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aliado.science.identidade.hashes import sha256_file
from aliado.specializations.mestrado.base.ensaios import (
    EXPERIMENTS,
    GRID_HZ,
    SOURCE_COLUMNS,
    WINDOW,
)


def dataset_files(directory: str | Path) -> dict[str, Path]:
    """Exatamente F0L–F7M; recusa conjunto incompleto ou CSV fora do contrato."""
    base = Path(directory)
    files = {name: base / f"{name}.csv" for name in EXPERIMENTS}
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        raise ValueError("GPVS incompleto; faltam: " + ", ".join(missing))
    extra = sorted(p.name for p in base.glob("*.csv") if p.stem.upper() not in EXPERIMENTS)
    if extra:
        raise ValueError("CSVs fora do contrato GPVS: " + ", ".join(extra))
    return files


def verify_provenance(directory: str | Path) -> dict[str, str]:
    """Hashes atuais; se houver `proveniencia.json`, cada arquivo precisa coincidir com ele."""
    files = dataset_files(directory)
    hashes = {name: sha256_file(path) for name, path in files.items()}
    record = Path(directory) / "proveniencia.json"
    if record.is_file():
        expected = json.loads(record.read_text(encoding="utf-8"))["files"]
        wrong = [name for name, digest in hashes.items() if expected.get(name, {}).get("sha256") != digest]
        if wrong:
            raise ValueError("Arquivos GPVS divergem da proveniência registrada: " + ", ".join(wrong))
    return hashes


def load_csv(path: Path) -> np.ndarray:
    with Path(path).open(encoding="utf-8") as handle:
        header = tuple(handle.readline().strip().split(","))
    if header[:len(SOURCE_COLUMNS)] != SOURCE_COLUMNS:
        raise ValueError(f"{Path(path).name}: colunas fora do contrato GPVS.")
    data = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.float64, ndmin=2)
    if not np.isfinite(data).all():
        raise ValueError(f"{Path(path).name}: há valores NaN ou infinitos.")
    return data


def sampling(time: np.ndarray) -> dict:
    delta = np.diff(np.asarray(time, dtype=np.float64))
    if len(time) < 1000 or np.any(delta <= 0):
        raise ValueError("Time deve ser estritamente crescente e ter ao menos 1000 pontos.")
    median = float(np.median(delta))
    rate = 1.0 / median
    if not 9_000.0 <= rate <= 11_000.0:
        raise ValueError(f"Taxa de amostragem fora do contrato GPVS: {rate:.1f} Hz.")
    if int(round(rate / GRID_HZ)) != WINDOW:
        raise ValueError("A amostragem não permite janelas de um ciclo de 200 amostras.")
    return {"fs_hz": rate, "dt_mediano_s": median, "dt_min_s": float(delta.min()), "dt_max_s": float(delta.max())}
