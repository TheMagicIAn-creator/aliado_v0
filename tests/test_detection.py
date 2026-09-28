"""Lote 13: protocolo M14 e contrato GPVS, com dados sintéticos; reprodução com os dados reais se presentes."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from aliado.science.detection import gpvs
from aliado.science.detection.protocol import (
    RobustScaler,
    autocorrelation,
    decorrelation_report,
    robust_center_scale,
    sequences_for_blocks,
    sequences_from_flow,
    temporal_split,
)

ROOT = Path(__file__).resolve().parents[1]
REAL_DATA = ROOT / "data" / "gpvs"


@pytest.mark.parametrize("n,expected", [(718, (359, 105, 106, 142)), (705, (352, 104, 104, 139))])
def test_temporal_split_reproduces_reference_blocks_with_purge(n, expected):
    split = temporal_split(n)
    assert tuple(len(split[r]) for r in ("train", "validation", "calibration", "test")) == expected
    assert split["validation"][0] - split["train"][-1] == 3  # 2 janelas descartadas entre blocos
    assert split["test"][-1] == n - 1
    combined = np.concatenate(list(split.values()))
    assert len(np.unique(combined)) == len(combined)


@pytest.mark.parametrize("kwargs", [{"fractions": (0.5, 0.5, 0.1, 0.1)}, {"fractions": (1, 0, 0, 0)},
                                    {"purge": -1}])
def test_temporal_split_rejects_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        temporal_split(718, **kwargs)
    with pytest.raises(ValueError):
        temporal_split(40)  # blocos com menos de 10 janelas


def test_robust_scaling_matches_median_iqr_and_handles_zero_spread():
    block = np.array([[1.0, 5.0], [2.0, 5.0], [3.0, 5.0], [4.0, 5.0], [100.0, 5.0]])
    center, scale = robust_center_scale(block)
    assert center.tolist() == [3.0, 5.0] and scale.tolist() == [2.0, 1.0]  # IQR nulo vira 1
    _, floored = robust_center_scale(block, floor=[3.0, 0.5])
    assert floored.tolist() == [3.0, 0.5]
    scaler = RobustScaler.fit(block)
    assert scaler.transform([[5.0, 6.0]]).tolist() == [[1.0, 1.0]]


def test_sequences_pad_only_at_block_start_and_never_cross_blocks():
    values = np.arange(10, dtype=float).reshape(10, 1)
    sequences = sequences_from_flow(values[:4], length=3)
    assert sequences[:, :, 0].tolist() == [[0, 0, 0], [0, 0, 1], [0, 1, 2], [1, 2, 3]]
    stacked, targets = sequences_for_blocks(values, [np.arange(0, 3), np.arange(5, 8)], length=3)
    assert stacked[3, :, 0].tolist() == [5, 5, 5] and targets.tolist() == [0, 1, 2, 5, 6, 7]
    with pytest.raises(ValueError):
        sequences_for_blocks(values, [np.array([1, 3])])


def test_autocorrelation_distinguishes_noise_from_persistent_series():
    rng = np.random.default_rng(7)
    noise = rng.normal(size=(4000, 2))
    ar = np.zeros((4000, 2))
    for i in range(1, 4000):
        ar[i] = 0.9 * ar[i - 1] + rng.normal(size=2)
    assert np.all(np.abs(autocorrelation(noise, 3)) < 0.06)
    assert autocorrelation(ar, 1)[0] == pytest.approx([0.9, 0.9], abs=0.03)
    persistent = decorrelation_report({"A": ar}, names=["x", "y"], purge=2)
    assert persistent["lag_necessario"] > 3 and not persistent["suficiente"]
    assert decorrelation_report({"A": noise}, names=["x", "y"], purge=2)["suficiente"]


def test_feature_vector_on_known_signals():
    t = np.arange(gpvs.WINDOW) / gpvs.SAMPLING_HZ
    window = np.zeros((gpvs.WINDOW, len(gpvs.PRIMARY_COLUMNS)))
    window[:, 0], window[:, 1], window[:, 2] = 2.0, 100.0, 150.0
    for k, shift in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
        window[:, 3 + k] = 10 * np.sin(2 * np.pi * 50 * t + shift)
        window[:, 6 + k] = 200 * np.sin(2 * np.pi * 50 * t + shift)
    features = dict(zip(gpvs.FEATURES, gpvs.feature_vector(window)))
    assert features["Ipv_median"] == pytest.approx(2.0) and features["Ipv_iqr"] == 0
    assert features["ia_rms"] == pytest.approx(10 / np.sqrt(2), rel=1e-5)
    assert features["ia_thd"] < 1e-5 and features["i_rms_unbalance"] < 1e-5
    assert features["p_ac_mean"] == pytest.approx(3 * 10 * 200 / 2, rel=1e-5)
    assert features["p_dc_median"] == pytest.approx(200.0)
    with pytest.raises(ValueError):
        gpvs.feature_vector(window[:100])


def write_synthetic(folder: Path, rows: int = 16_000, seed: int = 3) -> None:
    """16 ensaios pequenos: senoides trifásicas a 10 kHz; a falha muda a amplitude no meio do registro."""
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


# Os ensaios sintéticos são curtos (80 janelas saudáveis): os testes usam a separação da origem.
SHORT_PURGE = 2


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory):
    folder = tmp_path_factory.mktemp("gpvs")
    write_synthetic(folder)
    return folder


def test_prepare_on_synthetic_dataset_follows_the_contract(synthetic, tmp_path):
    prepared = gpvs.prepare(synthetic, cache=tmp_path / "cache.npz", purge=SHORT_PURGE)
    assert len(prepared.healthy_values) == 160  # 80 janelas por ensaio saudável
    assert [len(prepared.split[r]) for r in ("train", "validation", "calibration", "test")] == [80, 20, 20, 28]
    fault = prepared.faults["F1L"]
    assert len(fault["comissionamento"]) == 30 and len(fault["pre_teste"]) == 10
    assert len(fault["pos_falha"]) == 40 and len(fault["transicao"]) == 0  # fronteira coincide com uma janela
    summary = gpvs.report(prepared)
    assert summary["total_janelas"] == {"saudaveis": 160, "com_falha": 1120}
    json.dumps(summary)  # relatório serializável


def test_normalizer_and_scaler_see_only_training_windows(synthetic, tmp_path):
    prepared = gpvs.prepare(synthetic, purge=SHORT_PURGE)
    before = prepared.scaler
    changed = tmp_path / "alterado"
    changed.mkdir()
    for path in synthetic.glob("*.csv"):
        (changed / path.name).write_bytes(path.read_bytes())
    data = np.loadtxt(changed / "F0L.csv", delimiter=",", skiprows=1)
    data[12_000:, 1:10] *= 50  # só o bloco de teste de F0L muda
    np.savetxt(changed / "F0L.csv", data, delimiter=",", header=",".join(gpvs.SOURCE_COLUMNS), comments="")
    after = gpvs.prepare(changed, purge=SHORT_PURGE)
    assert np.allclose(before.center, after.scaler.center) and np.allclose(before.scale, after.scaler.scale)
    assert not np.allclose(prepared.scaled[prepared.split["test"]], after.scaled[after.split["test"]])


def test_commissioning_uses_only_first_half_of_pre_fault(synthetic):
    prepared = gpvs.prepare(synthetic, purge=SHORT_PURGE)
    fault = prepared.faults["F7M"]
    pre_test = fault["scaled"][fault["pre_teste"]]
    post = fault["scaled"][fault["pos_falha"]]
    rms = [gpvs.FEATURES.index(n) for n in ("ia_rms", "ib_rms", "ic_rms")]
    # A corrente cresce 70% depois da falha: o pós-falha se afasta da linha de base do pré-falha.
    assert np.abs(post[:, rms]).mean() > 10 * np.abs(pre_test[:, rms]).mean()


def test_provenance_cache_and_dataset_errors(synthetic, tmp_path):
    folder = tmp_path / "gpvs"
    folder.mkdir()
    for path in synthetic.glob("*.csv"):
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


def test_cli_prepares_report_without_overwriting(synthetic, tmp_path, capsys):
    from aliado.cli import main

    output = tmp_path / "preparo"
    args = ["ciencia", "preparar-gpvs", "--dados", str(synthetic), "--saida", str(output),
            "--cache", str(tmp_path / "cache.npz"), "--separacao", str(SHORT_PURGE)]
    assert main(args) == 0
    report = json.loads((output / "relatorio.json").read_text(encoding="utf-8"))
    assert report["saudavel"]["papeis"]["train"] == 80
    assert "Verificação do M14" in (output / "relatorio.md").read_text(encoding="utf-8")
    with np.load(output / "normalizacao.npz") as stored:
        assert stored["papel_train"].shape == (80,) and stored["piso_iqr"].shape == (24,)
    assert main(args) == 2 and "já existe" in capsys.readouterr().err


@pytest.mark.skipif(not (REAL_DATA / "F0L.csv").is_file(), reason="GPVS real ausente nesta máquina")
def test_real_gpvs_reproduces_reference_counts_and_statistics(tmp_path):
    prepared = gpvs.prepare(REAL_DATA, cache=tmp_path / "cache.npz", purge=2)  # separação da origem
    assert len(prepared.healthy_values) == 1423
    assert [len(prepared.split[r]) for r in ("train", "validation", "calibration", "test")] == [711, 209, 210, 281]
    assert gpvs.report(prepared)["total_janelas"]["com_falha"] == 9391
    reference = {row[""]: row for row in csv.DictReader(
        (ROOT / "tests" / "data" / "gpvs_estatisticas_referencia.csv").open(encoding="utf-8"))}
    values = prepared.healthy_values.astype(np.float64)
    for j, name in enumerate(gpvs.FEATURES):
        column = values[:, j]
        ours = [column.mean(), column.std(ddof=1), column.min(), *np.percentile(column, (25, 50, 75)), column.max()]
        expected = [float(reference[name][k]) for k in ("mean", "std", "min", "25%", "50%", "75%", "max")]
        assert np.allclose(ours, expected, rtol=1e-5, atol=1e-9), name
    canonical = gpvs.prepare(REAL_DATA, cache=tmp_path / "cache.npz")
    assert canonical.purge == gpvs.PURGE == 11
    assert [len(canonical.split[r]) for r in ("train", "validation", "calibration", "test")] == [711, 191, 192, 263]
    assert gpvs.report(canonical)["verificacao_m14_autocorrelacao"]["suficiente"]
