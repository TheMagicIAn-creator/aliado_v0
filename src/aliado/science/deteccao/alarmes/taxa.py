"""A taxa de alarmes falsos estimada por uma cadeia de Markov de dois estados (Brook e Evans, 1972)."""

from __future__ import annotations

import numpy as np

from aliado.science.deteccao.alarmes.confirmacao import CONFIRMATIONS, alarm_starts
from aliado.science.deteccao.metricas.incerteza import RESAMPLES


def _transitions(flags: np.ndarray) -> np.ndarray:
    """Contagens 0→0, 0→1, 1→0 e 1→1 dentro de um trecho."""
    a, b = flags[:-1], flags[1:]
    return np.array([np.sum(~a & ~b), np.sum(~a & b), np.sum(a & ~b), np.sum(a & b)], dtype=float)


def _chain_rate(counts: np.ndarray, confirmations: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """p01, p11 e a chance de um alarme por janela, π0 · p01 · p11^(m−1), para cada linha de contagens."""
    n00, n01, n10, n11 = np.moveaxis(np.atleast_2d(counts), -1, 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        p01 = np.where(n00 + n01 > 0, n01 / (n00 + n01), 0.0)
        p11 = np.where(n10 + n11 > 0, n11 / (n10 + n11), 0.0)
        p10 = 1.0 - p11
        pi0 = np.where(p01 + p10 > 0, p10 / (p01 + p10), 1.0)
    return p01, p11, pi0 * p01 * p11 ** (confirmations - 1)


def markov_alarm_rate(segments, confirmations: int = CONFIRMATIONS, *, resamples: int = RESAMPLES,
                      seed: int, windows_per_hour: float) -> dict:
    """Alarmes falsos por hora estimados por uma cadeia de Markov de dois estados (abaixo e acima do limiar).

    A cadeia é ajustada às transições entre janelas vizinhas de cada trecho saudável; um alarme é
    a m-ésima janela seguida acima do limiar, com chance π0 · p01 · p11^(m−1) por janela. É a
    abordagem de cadeia de Markov para o tempo até o alarme (Brook e Evans, 1972). O intervalo de
    95% sorteia os trechos com reposição. O previsto e o observado nas sequências de 2 janelas e nos
    alarmes ficam lado a lado para conferir a cadeia.

    `windows_per_hour` converte a chance por janela em alarmes por hora. Vem de quem conhece a janela e a
    amostragem, sem valor padrão (lote 56: era fixo aqui, com a rede de 50 Hz).
    """
    flags = [np.asarray(segment, dtype=bool) for segment in segments if len(segment)]
    if not flags:
        raise ValueError("Nenhuma janela saudável para a estimativa.")
    counts = np.array([_transitions(segment) for segment in flags])
    p01, p11, per_window = (float(value[0]) for value in _chain_rate(counts.sum(axis=0), confirmations))
    rng = np.random.default_rng(seed)
    drawn = counts[rng.integers(0, len(counts), size=(resamples, len(counts)))].sum(axis=1)
    rates = _chain_rate(drawn, confirmations)[2] * windows_per_hour
    windows = sum(len(segment) for segment in flags)
    pairs = float(_chain_rate(counts.sum(axis=0), 2)[2][0])
    return {
        "janelas": windows, "janelas_acima": int(sum(segment.sum() for segment in flags)),
        "p01": p01, "p11": p11, "prob_alarme_por_janela": per_window,
        "alarmes_por_hora": per_window * windows_per_hour,
        "ic95": [float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5))],
        "previsto": {"sequencias_de_2": windows * pairs, "alarmes": windows * per_window},
        "observado": {"sequencias_de_2": int(sum(len(alarm_starts(segment, 2)) for segment in flags)),
                      "alarmes": int(sum(len(alarm_starts(segment, confirmations)) for segment in flags))},
    }
