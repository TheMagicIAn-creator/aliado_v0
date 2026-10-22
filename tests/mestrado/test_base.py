"""A base GPVS: os 16 arquivos, a proveniência pelos hashes e o cache que só vale com os mesmos arquivos."""

from __future__ import annotations

import json

import numpy as np
import pytest

from aliado.specializations.mestrado.preparo import preparacao as gpvs


def test_provenance_cache_and_dataset_errors(gpvs_sintetico, tmp_path):
    folder = tmp_path / "gpvs"
    folder.mkdir()
    for path in gpvs_sintetico.glob("*.csv"):
        (folder / path.name).write_bytes(path.read_bytes())
    hashes = gpvs.verify_provenance(folder)
    (folder / "proveniencia.json").write_text(json.dumps({"files": {k: {"sha256": v} for k, v in hashes.items()}}))
    cache = tmp_path / "cache.npz"
    first, _ = gpvs.extract_all(folder, cache=cache)
    stamp = cache.stat().st_mtime_ns
    second, _ = gpvs.extract_all(folder, cache=cache)
    assert cache.stat().st_mtime_ns == stamp and np.array_equal(first["F3L"].values, second["F3L"].values)
    (folder / "F3L.csv").write_text((folder / "F3L.csv").read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="proveniência"):
        gpvs.extract_all(folder, cache=cache)
    (folder / "extra.csv").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="fora do contrato"):
        gpvs.dataset_files(folder)
    (folder / "extra.csv").unlink()
    (folder / "F0M.csv").unlink()
    with pytest.raises(ValueError, match="faltam"):
        gpvs.dataset_files(folder)
