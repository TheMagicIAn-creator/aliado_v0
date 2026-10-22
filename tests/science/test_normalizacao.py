"""Normalização robusta: mediana e IQR do bloco de treino, com piso para o IQR nulo."""

from __future__ import annotations

import numpy as np

from aliado.science.deteccao.particao.blocos import RobustScaler, robust_center_scale


def test_robust_scaling_matches_median_iqr_and_handles_zero_spread():
    block = np.array([[1.0, 5.0], [2.0, 5.0], [3.0, 5.0], [4.0, 5.0], [100.0, 5.0]])
    center, scale = robust_center_scale(block)
    assert center.tolist() == [3.0, 5.0] and scale.tolist() == [2.0, 1.0]  # IQR nulo vira 1
    _, floored = robust_center_scale(block, floor=[3.0, 0.5])
    assert floored.tolist() == [3.0, 0.5]
    scaler = RobustScaler.fit(block)
    assert scaler.transform([[5.0, 6.0]]).tolist() == [[1.0, 1.0]]
