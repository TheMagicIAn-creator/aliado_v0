"""As métricas por janela da avaliação M13 (lote 15): saudáveis contra pós-falha, sem regra de alarme.

Só depende do numpy. As métricas por janela da origem (scikit-learn em `src/ml/estatistica_comparacao.py`, commit
21f6ddf) foram reescritas e conferidas contra os resultados dela.
"""

from __future__ import annotations

import math

import numpy as np


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


def from_counts(vp: int, fn: int, fp: int, vn: int) -> dict:
    """Sensibilidade, especificidade, precisão, F1, acurácia balanceada e MCC a partir das contagens de janelas
    (lote 56: era repetida no painel por tipo de falha, que soma as contagens dos dois modos)."""
    sensitivity, specificity = vp / (vp + fn), vn / (vn + fp)
    denominator = math.sqrt((vp + fp) * (vp + fn) * (vn + fp) * (vn + fn))
    return {"sensibilidade": sensitivity, "especificidade": specificity,
            "precisao": vp / (vp + fp) if vp + fp else None,
            "f1": 2 * vp / (2 * vp + fp + fn) if 2 * vp + fp + fn else 0.0,
            "acuracia_balanceada": (sensitivity + specificity) / 2,
            "mcc": (vp * vn - fp * fn) / denominator if denominator else 0.0,
            "vp": vp, "fn": fn, "fp": fp, "vn": vn}


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
    fp = int((negatives > threshold).sum())
    metrics = from_counts(tp, len(positives) - tp, fp, len(negatives) - fp)
    counts = {key: metrics.pop(key) for key in ("vp", "fn", "fp", "vn")}  # depois das AUCs, como sempre foram gravadas
    labels = np.r_[np.zeros(len(negatives), dtype=bool), np.ones(len(positives), dtype=bool)]
    scores = np.r_[negatives, positives]
    return {**metrics, "auc_roc": auc_roc(labels, scores), "auc_pr": auc_pr(labels, scores), **counts}
