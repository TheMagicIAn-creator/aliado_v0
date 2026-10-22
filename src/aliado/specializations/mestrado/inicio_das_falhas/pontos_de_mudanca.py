"""Os pontos de mudança: o PELT (Killick, Fearnhead e Eckley, 2012) com custo quadrático e penalidade c · d · ln n,
sobre as variáveis normalizadas por um trecho de referência. Só depende do numpy."""

from __future__ import annotations

import math

import numpy as np

from aliado.science.deteccao.normalizacao.escala_robusta import robust_center_scale


def robust_z(values: np.ndarray, reference: np.ndarray, *, floor: float, clip: float) -> np.ndarray:
    """Mediana e IQR do trecho de referência; valores fora de ±clip ficam no limite."""
    center, scale = robust_center_scale(reference, floor=floor)
    return np.clip((np.asarray(values, dtype=np.float64) - center) / scale, -clip, clip)


def penalty(multiplier: float, n: int, d: int) -> float:
    return float(multiplier) * int(d) * math.log(int(n))


def pelt(matrix: np.ndarray, penalty: float, min_segment: int = 5) -> list[int]:
    """Mudanças na média pelo PELT com custo quadrático: o índice em que cada segmento novo começa.

    O custo de um trecho é a soma dos quadrados em torno da própria média; a poda descarta um
    início s quando F(s) + custo(s, t) já passa de F(t), o que vale para este custo.
    """
    data = np.asarray(matrix, dtype=np.float64)
    if data.ndim == 1:
        data = data[:, None]
    n = len(data)
    if n < 2 * min_segment:
        return []
    sums = np.vstack([np.zeros(data.shape[1]), np.cumsum(data, axis=0)])
    squares = np.r_[0.0, np.cumsum((data ** 2).sum(axis=1))]
    best = np.full(n + 1, np.inf)
    best[0] = -penalty
    previous = np.zeros(n + 1, dtype=int)
    candidates = np.array([0])
    for t in range(min_segment, n + 1):
        ready = candidates[t - candidates >= min_segment]
        waiting = candidates[t - candidates < min_segment]
        if len(ready):
            delta = sums[t] - sums[ready]
            cost = squares[t] - squares[ready] - (delta ** 2).sum(axis=1) / (t - ready)
            total = best[ready] + cost + penalty
            choice = int(np.argmin(total))
            best[t], previous[t] = total[choice], ready[choice]
            ready = ready[total - penalty <= best[t]]
        candidates = np.r_[ready, waiting, t]
    changes, t = [], n
    while t > 0:
        t = int(previous[t])
        if t > 0:
            changes.append(t)
    return sorted(changes)
