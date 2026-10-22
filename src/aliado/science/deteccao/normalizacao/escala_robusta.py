"""A escala robusta (mediana e amplitude interquartil), ajustada só no bloco de treino e aplicada a qualquer bloco."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def robust_center_scale(block: np.ndarray, *, floor=None) -> tuple[np.ndarray, np.ndarray]:
    """Mediana e amplitude interquartil por coluna; `floor` impõe escala mínima.

    Sem `floor`, escalas nulas viram 1, como no RobustScaler do scikit-learn.
    """
    data = np.asarray(block, dtype=np.float64)
    if data.ndim != 2 or not len(data):
        raise ValueError("O bloco deve ter formato (janelas, variáveis) e não ser vazio.")
    center = np.median(data, axis=0)
    q25, q75 = np.percentile(data, (25, 75), axis=0)
    scale = q75 - q25
    if floor is None:
        scale = np.where(scale == 0, 1.0, scale)
    else:
        scale = np.maximum(scale, np.asarray(floor, dtype=np.float64))
    return center, scale


@dataclass(frozen=True)
class RobustScaler:
    """Escala robusta (mediana e IQR) ajustada no treino e aplicada a qualquer bloco."""

    center: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, block: np.ndarray) -> RobustScaler:
        return cls(*robust_center_scale(block))

    def transform(self, values: np.ndarray) -> np.ndarray:
        return ((np.asarray(values, dtype=np.float64) - self.center) / self.scale).astype(np.float32)
