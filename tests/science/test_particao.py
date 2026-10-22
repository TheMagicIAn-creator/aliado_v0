"""Partição do tempo em blocos de treino, validação, calibração e teste; sequências do AE-LSTM; autocorrelação."""

from __future__ import annotations

import numpy as np
import pytest

from aliado.science.deteccao.particao.blocos import (
    autocorrelation,
    decorrelation_report,
    sequences_for_blocks,
    sequences_from_flow,
    temporal_split,
)


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
