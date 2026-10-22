"""O preparo: divisão por ensaio, normalização pela linha de base do treino e comissionamento dos ensaios com falha
(lote 13), no GPVS sintético."""

from __future__ import annotations

import json

import numpy as np
from apoio.gpvs_sintetico import SHORT_PURGE

from aliado.specializations.mestrado import gpvs


def test_prepare_on_synthetic_dataset_follows_the_contract(gpvs_sintetico, tmp_path):
    prepared = gpvs.prepare(gpvs_sintetico, cache=tmp_path / "cache.npz", purge=SHORT_PURGE)
    assert len(prepared.healthy_values) == 160  # 80 janelas por ensaio saudável
    assert [len(prepared.split[r]) for r in ("train", "validation", "calibration", "test")] == [80, 20, 20, 28]
    fault = prepared.faults["F1L"]
    assert len(fault["comissionamento"]) == 30 and len(fault["pre_teste"]) == 10
    assert len(fault["pos_falha"]) == 40 and len(fault["transicao"]) == 0  # fronteira coincide com uma janela
    summary = gpvs.report(prepared)
    assert summary["total_janelas"] == {"saudaveis": 160, "com_falha": 1120}
    json.dumps(summary)  # relatório serializável


def test_normalizer_and_scaler_see_only_training_windows(gpvs_sintetico, tmp_path):
    prepared = gpvs.prepare(gpvs_sintetico, purge=SHORT_PURGE)
    before = prepared.scaler
    changed = tmp_path / "alterado"
    changed.mkdir()
    for path in gpvs_sintetico.glob("*.csv"):
        (changed / path.name).write_bytes(path.read_bytes())
    data = np.loadtxt(changed / "F0L.csv", delimiter=",", skiprows=1)
    data[12_000:, 1:10] *= 50  # só o bloco de teste de F0L muda
    np.savetxt(changed / "F0L.csv", data, delimiter=",", header=",".join(gpvs.SOURCE_COLUMNS), comments="")
    after = gpvs.prepare(changed, purge=SHORT_PURGE)
    assert np.allclose(before.center, after.scaler.center) and np.allclose(before.scale, after.scaler.scale)
    assert not np.allclose(prepared.scaled[prepared.split["test"]], after.scaled[after.split["test"]])


def test_commissioning_uses_only_first_half_of_pre_fault(gpvs_sintetico):
    prepared = gpvs.prepare(gpvs_sintetico, purge=SHORT_PURGE)
    fault = prepared.faults["F7M"]
    pre_test = fault["scaled"][fault["pre_teste"]]
    post = fault["scaled"][fault["pos_falha"]]
    rms = [gpvs.FEATURES.index(n) for n in ("ia_rms", "ib_rms", "ic_rms")]
    # A corrente cresce 70% depois da falha: o pós-falha se afasta da linha de base do pré-falha.
    assert np.abs(post[:, rms]).mean() > 10 * np.abs(pre_test[:, rms]).mean()
