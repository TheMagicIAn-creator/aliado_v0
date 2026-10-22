"""A inferência: o erro quadrático por variável; no AE-LSTM, só o do último passo de cada sequência."""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from aliado.science.detection.models import feature_errors  # noqa: E402


class Zero(torch.nn.Module):
    def forward(self, x):
        return torch.zeros_like(x)


def test_feature_errors_use_only_the_last_step_of_each_sequence():
    sequences = np.arange(2 * 4 * 3, dtype=np.float32).reshape(2, 4, 3)
    assert np.array_equal(feature_errors(Zero(), sequences), sequences[:, -1, :] ** 2)
    windows = sequences[:, 0, :]
    assert np.array_equal(feature_errors(Zero(), windows), windows ** 2)
