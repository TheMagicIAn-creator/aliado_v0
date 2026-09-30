"""Lote 24: início observado das falhas pelo PELT, sem os detectores (só numpy)."""

from __future__ import annotations

import numpy as np
import pytest
from test_detection import ROOT, write_synthetic

from aliado.science.detection import gpvs, onset

GPVS = ROOT / "data" / "gpvs"
REAL = (GPVS / "proveniencia.json").is_file() and (GPVS / "F0L.csv").is_file()


def test_pelt_finds_a_mean_shift_and_nothing_in_noise():
    rng = np.random.default_rng(7)
    noise = rng.normal(size=(300, 4))
    assert onset.pelt(noise, onset.penalty(4, 300, 4)) == []
    shifted = noise.copy()
    shifted[180:] += 2.0
    assert onset.pelt(shifted, onset.penalty(4, 300, 4)) == [180]
    two = shifted.copy()
    two[240:] -= 4.0
    assert onset.pelt(two, onset.penalty(4, 300, 4)) == [180, 240]


def test_pelt_respects_the_minimum_segment():
    rng = np.random.default_rng(8)
    values = rng.normal(scale=0.1, size=(100, 2))
    values[50:53] += 30.0  # um pulso de 3 janelas
    for min_segment in (2, 5, 10):
        changes = onset.pelt(values, 1.0, min_segment)
        bounds = [0, *changes, len(values)]
        assert changes and all(b - a >= min_segment for a, b in zip(bounds, bounds[1:]))


def test_classes_follow_the_grid_from_the_chosen_penalty():
    assert onset.classify({1.0: 12, 2.0: 10, 4.0: 10, 8.0: 10}, 2.0) == "clara"
    assert onset.classify({1.0: 10, 2.0: 10, 4.0: None}, 2.0) == "fraca"
    assert onset.classify({1.0: 10, 2.0: 10, 4.0: 14}, 2.0) == "fraca"
    assert onset.classify({1.0: 10, 2.0: None, 4.0: None}, 2.0) == "nenhuma"


def test_penalty_is_the_smallest_without_changes_in_the_healthy_records():
    rng = np.random.default_rng(9)
    config = onset.OnsetConfig()
    healthy = {"F0L": rng.normal(size=(400, 3)), "F0M": rng.normal(size=(400, 3))}
    chosen, control = onset.choose_penalty(healthy, config)
    assert all(counts[str(chosen)] == 0 for counts in control.values())
    assert all(any(counts[str(c)] for counts in control.values()) for c in config.grid if c < chosen)
    shifted = {name: values.copy() for name, values in healthy.items()}
    shifted["F0L"][200:] += 50.0
    with pytest.raises(ValueError, match="Nenhuma penalidade"):
        onset.choose_penalty(shifted, onset.OnsetConfig(grid=(1.0, 2.0)))


def test_config_is_validated_and_hashed():
    assert onset.OnsetConfig().digest() == onset.OnsetConfig().digest()
    assert onset.OnsetConfig(min_segment=6).digest() != onset.OnsetConfig().digest()
    for bad in ({"grid": ()}, {"grid": (2.0, 1.0)}, {"grid": (0.0, 1.0)}, {"min_segment": 1}, {"clip": 0},
                {"healthy_reference": 1.0}):
        with pytest.raises(ValueError):
            onset.OnsetConfig(**bad)


def test_synthetic_faults_change_at_the_middle(tmp_path):
    write_synthetic(tmp_path / "gpvs")
    experiments, _ = gpvs.extract_all(tmp_path / "gpvs")
    result = onset.estimate(experiments)
    assert result["controle_saudavel"]["F0L"][str(result["penalidade_c"])] == 0
    for name, trial in result["ensaios"].items():
        # A amplitude muda exatamente no meio: o início observado é o nominal.
        assert trial["classe"] == "clara", name
        assert trial["observado_janela"] == trial["nominal_janela"] == 40
        assert trial["comissionamento_janelas"] == 30
        assert trial["observado_s"] == pytest.approx(trial["nominal_s"], abs=1e-3)


@pytest.mark.skipif(not REAL, reason="Sem os dados do GPVS neste computador.")
def test_real_onsets_are_the_ones_reported_on_30_09():
    experiments, _ = gpvs.extract_all(GPVS, cache=GPVS / "processado" / "variaveis.npz")
    result = onset.estimate(experiments)
    assert result["penalidade_c"] == 4.0
    control = result["controle_saudavel"]
    assert all(counts["4.0"] == 0 for counts in control.values()) and control["F0M"]["3.0"] == 1
    trials = result["ensaios"]
    clear = {"F1L": 433, "F1M": 423, "F2L": 444, "F2M": 435, "F3L": 446, "F3M": 337, "F5L": 357, "F5M": 369}
    assert {name: trial["observado_janela"] for name, trial in trials.items() if trial["classe"] == "clara"} == clear
    assert {name for name, trial in trials.items() if trial["classe"] == "fraca"} == {"F6L", "F6M", "F7L", "F7M"}
    assert {name for name, trial in trials.items() if trial["classe"] == "nenhuma"} == {"F4L", "F4M"}
    assert trials["F1L"]["observado_s"] == pytest.approx(8.66, abs=0.01)
