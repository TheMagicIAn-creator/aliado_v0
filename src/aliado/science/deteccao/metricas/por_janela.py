"""Métricas da avaliação M13 (lote 15): alarme, detecção, métricas por janela e incerteza.

Só depende do numpy. As métricas por janela da origem (scikit-learn em
`src/ml/estatistica_comparacao.py`, commit 21f6ddf) foram reescritas e conferidas contra os
resultados dela.
"""

from __future__ import annotations

import math

import numpy as np

CONFIRMATIONS = 3
BLOCK = 12
RESAMPLES = 20_000


def alarm_starts(above, confirmations: int = CONFIRMATIONS) -> np.ndarray:
    """Janelas em que um alarme dispara: a m-ésima de uma sequência seguida acima do limiar.

    Enquanto as janelas seguem acima, é o mesmo alarme; um novo exige voltar abaixo antes.
    """
    if isinstance(confirmations, bool) or int(confirmations) < 1:
        raise ValueError("A confirmação exige ao menos uma janela.")
    alarms, run = [], 0
    for index, flag in enumerate(np.asarray(above, dtype=bool)):
        run = run + 1 if flag else 0
        if run == confirmations:
            alarms.append(index)
    return np.asarray(alarms, dtype=int)


def first_alarm(above, confirmations: int = CONFIRMATIONS) -> int | None:
    starts = alarm_starts(above, confirmations)
    return int(starts[0]) if len(starts) else None


def _average_ranks(values: np.ndarray) -> np.ndarray:
    _, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    ends = np.cumsum(counts)
    return ((ends - counts + 1 + ends) / 2.0)[inverse]


def auc_roc(positive: np.ndarray, scores: np.ndarray) -> float:
    """Área sob a curva ROC pela estatística de Mann-Whitney, com empates pela média."""
    n_positive = int(positive.sum())
    n_negative = len(positive) - n_positive
    ranks = _average_ranks(scores)
    return float((ranks[positive].sum() - n_positive * (n_positive + 1) / 2) / (n_positive * n_negative))


def auc_pr(positive: np.ndarray, scores: np.ndarray) -> float:
    """Área trapezoidal da curva precisão-revocação, com os mesmos pontos da origem."""
    order = np.argsort(-scores, kind="mergesort")
    ordered, labels = scores[order], positive[order]
    last = np.r_[np.flatnonzero(np.diff(ordered)), len(ordered) - 1]
    true_positives = np.cumsum(labels)[last]
    false_positives = 1 + last - true_positives
    precision = np.r_[(true_positives / (true_positives + false_positives))[::-1], 1.0]
    recall = np.r_[(true_positives / true_positives[-1])[::-1], 0.0]
    return float(-np.trapezoid(precision, recall))


def window_metrics(negative_scores, positive_scores, threshold: float) -> dict:
    """Métricas por janela: saudáveis (negativas) contra pós-falha (positivas), sem regra de alarme.

    Sensibilidade e especificidade são as principais; as demais são descritivas. Precisão,
    F1 e MCC dependem da proporção entre as classes, que é fixada pelo registro.
    """
    negatives = np.asarray(negative_scores, dtype=float)
    positives = np.asarray(positive_scores, dtype=float)
    if not len(negatives) or not len(positives):
        raise ValueError("As métricas por janela exigem janelas saudáveis e pós-falha.")
    if not (np.isfinite(negatives).all() and np.isfinite(positives).all() and math.isfinite(threshold)):
        raise ValueError("Escores e limiar devem ser finitos.")
    tp = int((positives > threshold).sum())
    fn = len(positives) - tp
    fp = int((negatives > threshold).sum())
    tn = len(negatives) - fp
    sensitivity, specificity = tp / (tp + fn), tn / (tn + fp)
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    labels = np.r_[np.zeros(len(negatives), dtype=bool), np.ones(len(positives), dtype=bool)]
    scores = np.r_[negatives, positives]
    return {
        "sensibilidade": sensitivity,
        "especificidade": specificity,
        "precisao": tp / (tp + fp) if tp + fp else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        "acuracia_balanceada": (sensitivity + specificity) / 2,
        "mcc": (tp * tn - fp * fn) / denominator if denominator else 0.0,
        "auc_roc": auc_roc(labels, scores),
        "auc_pr": auc_pr(labels, scores),
        "vp": tp, "fn": fn, "fp": fp, "vn": tn,
    }


def block_bootstrap_indices(n: int, *, block: int, resamples: int, rng: np.random.Generator) -> np.ndarray:
    """Reamostragem em blocos móveis (Künsch, 1989): blocos de janelas seguidas, com reposição."""
    size = min(int(block), int(n))
    count = math.ceil(n / size)
    starts = rng.integers(0, n - size + 1, size=(resamples, count))
    return (starts[:, :, None] + np.arange(size)).reshape(resamples, count * size)[:, :n]


def proportion_interval(segments, *, block: int = BLOCK, resamples: int = RESAMPLES, seed: int) -> list[float]:
    """IC de 95% de uma proporção sobre trechos contíguos, cada um reamostrado em blocos.

    Blocos preservam a semelhança entre janelas vizinhas, que um intervalo binomial ignora.
    """
    rng = np.random.default_rng(seed)
    totals, n = np.zeros(resamples), 0
    for segment in segments:
        flags = np.asarray(segment, dtype=float)
        if len(flags):
            totals += flags[block_bootstrap_indices(len(flags), block=block, resamples=resamples, rng=rng)].sum(axis=1)
            n += len(flags)
    if not n:
        raise ValueError("Nenhuma janela para o intervalo.")
    means = totals / n
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def poisson_upper(count: int, confidence: float = 0.95) -> float:
    """Maior média de Poisson compatível com `count` eventos: P(X ≤ count; λ) = 1 − confiança.

    Limite exato unilateral (Garwood, 1936). Com zero eventos, λ = −ln(0,05) ≈ 3,0: a regra do três.
    """
    alpha = 1.0 - confidence

    def cdf(mean: float) -> float:
        term = total = math.exp(-mean)
        for i in range(1, int(count) + 1):
            term *= mean / i
            total += term
        return total

    low, high = 0.0, 10.0 * (int(count) + 1)
    while cdf(high) > alpha:
        high *= 2
    for _ in range(200):
        middle = (low + high) / 2
        low, high = (middle, high) if cdf(middle) > alpha else (low, middle)
    return (low + high) / 2


WINDOWS_PER_HOUR = 3600 * 50  # janelas de um ciclo de 50 Hz


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
                      seed: int) -> dict:
    """Alarmes falsos por hora estimados por uma cadeia de Markov de dois estados (abaixo e acima do limiar).

    A cadeia é ajustada às transições entre janelas vizinhas de cada trecho saudável; um alarme é
    a m-ésima janela seguida acima do limiar, com chance π0 · p01 · p11^(m−1) por janela. É a
    abordagem de cadeia de Markov para o tempo até o alarme (Brook e Evans, 1972). O intervalo de
    95% sorteia os trechos com reposição. O previsto e o observado nas sequências de 2 janelas e nos
    alarmes ficam lado a lado para conferir a cadeia.
    """
    flags = [np.asarray(segment, dtype=bool) for segment in segments if len(segment)]
    if not flags:
        raise ValueError("Nenhuma janela saudável para a estimativa.")
    counts = np.array([_transitions(segment) for segment in flags])
    p01, p11, per_window = (float(value[0]) for value in _chain_rate(counts.sum(axis=0), confirmations))
    rng = np.random.default_rng(seed)
    drawn = counts[rng.integers(0, len(counts), size=(resamples, len(counts)))].sum(axis=1)
    rates = _chain_rate(drawn, confirmations)[2] * WINDOWS_PER_HOUR
    windows = sum(len(segment) for segment in flags)
    pairs = float(_chain_rate(counts.sum(axis=0), 2)[2][0])
    return {
        "janelas": windows, "janelas_acima": int(sum(segment.sum() for segment in flags)),
        "p01": p01, "p11": p11, "prob_alarme_por_janela": per_window,
        "alarmes_por_hora": per_window * WINDOWS_PER_HOUR,
        "ic95": [float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5))],
        "previsto": {"sequencias_de_2": windows * pairs, "alarmes": windows * per_window},
        "observado": {"sequencias_de_2": int(sum(len(alarm_starts(segment, 2)) for segment in flags)),
                      "alarmes": int(sum(len(alarm_starts(segment, confirmations)) for segment in flags))},
    }


def paired_interval(differences, *, resamples: int = RESAMPLES, seed: int) -> dict:
    """Média das diferenças pareadas e IC de 95% sorteando os ensaios com reposição."""
    values = np.asarray([d for d in differences if d is not None and math.isfinite(d)], dtype=float)
    if not len(values):
        return {"media": None, "ic95": None, "n": 0}
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, len(values), size=(resamples, len(values)))].mean(axis=1)
    return {"media": float(values.mean()),
            "ic95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))], "n": int(len(values))}


def verdict(interval: list[float] | None, *, higher_is_better: bool) -> str:
    """Leitura de uma diferença Denso − AE-LSTM: quem é melhor, ou sem diferença clara."""
    if interval is None:
        return "sem dados"
    low, high = interval
    if low > 0:
        return "Denso" if higher_is_better else "AE-LSTM"
    if high < 0:
        return "AE-LSTM" if higher_is_better else "Denso"
    return "sem diferença clara"
