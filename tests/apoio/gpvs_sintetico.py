"""O GPVS sintético: 16 ensaios pequenos com o contrato da base real."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aliado.specializations.mestrado import gpvs

# Os ensaios sintéticos são curtos (80 janelas saudáveis): os testes usam a separação da origem.
SHORT_PURGE = 2


def write_synthetic(folder: Path, rows: int = 16_000, seed: int = 3, *, provenance: bool = False) -> None:
    """16 ensaios pequenos: senoides trifásicas a 10 kHz; a falha muda a amplitude no meio do registro.

    Com `provenance`, grava também o `proveniencia.json` com os hashes, como a base real tem."""
    rng = np.random.default_rng(seed)
    folder.mkdir(parents=True, exist_ok=True)
    t = np.arange(rows) / gpvs.SAMPLING_HZ
    for name in gpvs.EXPERIMENTS:
        amplitude = np.full(rows, 10.0)
        if name not in gpvs.HEALTHY:
            amplitude[rows // 2:] *= 1.0 + 0.1 * int(name[1])
        data = np.zeros((rows, len(gpvs.SOURCE_COLUMNS)))
        data[:, 0] = t + 1e-5
        data[:, 1] = 2 + 0.05 * rng.normal(size=rows)
        data[:, 2] = 100 + 0.2 * rng.normal(size=rows)
        data[:, 3] = 150 + 0.2 * rng.normal(size=rows)
        for k, shift in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
            data[:, 4 + k] = amplitude * np.sin(2 * np.pi * 50 * t + shift) + 0.1 * rng.normal(size=rows)
            data[:, 7 + k] = 200 * np.sin(2 * np.pi * 50 * t + shift) + rng.normal(size=rows)
        data[:, 10:] = (1, 50, 1, 50)
        np.savetxt(folder / f"{name}.csv", data, delimiter=",", header=",".join(gpvs.SOURCE_COLUMNS),
                   comments="")
    if provenance:
        hashes = gpvs.verify_provenance(folder)
        (folder / "proveniencia.json").write_text(
            json.dumps({"files": {name: {"sha256": digest} for name, digest in hashes.items()}}), encoding="utf-8")
