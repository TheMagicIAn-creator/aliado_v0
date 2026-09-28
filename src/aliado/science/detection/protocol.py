"""Protocolo temporal de detecção (M14), independente do conjunto de dados.

Divisão em blocos contíguos com janelas de separação, normalização robusta ajustada
só no treino, sequências que não atravessam blocos e verificação de autocorrelação.
Só depende do numpy; nada aqui treina modelos nem escolhe limiares.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ROLES = ("train", "validation", "calibration", "test")
DEFAULT_FRACTIONS = (0.50, 0.15, 0.15, 0.20)
DEFAULT_PURGE = 2
DEFAULT_SEQUENCE = 8


def temporal_split(n: int, *, fractions=DEFAULT_FRACTIONS, purge: int = DEFAULT_PURGE,
                   min_block: int = 10) -> dict[str, np.ndarray]:
    """Blocos contíguos treino/validação/calibração/teste; `purge` janelas descartadas entre eles.

    As fronteiras são int(n × fração acumulada), como no protocolo de referência.
    """
    if len(fractions) != len(ROLES) or any(f <= 0 for f in fractions) or abs(sum(fractions) - 1) > 1e-9:
        raise ValueError("As quatro frações devem ser positivas e somar 1.")
    if purge < 0:
        raise ValueError("A separação não pode ser negativa.")
    cumulative = np.round(np.cumsum(fractions)[:-1], 10)
    bounds = [int(n * c) for c in cumulative]
    starts = [0] + [b + purge for b in bounds]
    ends = bounds + [n]
    split = {role: np.arange(start, end) for role, start, end in zip(ROLES, starts, ends)}
    if any(len(block) < min_block for block in split.values()):
        raise ValueError(f"A divisão produziu um papel com menos de {min_block} janelas.")
    return split


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


def sequences_from_flow(values: np.ndarray, length: int = DEFAULT_SEQUENCE) -> np.ndarray:
    """Uma sequência por janela; a primeira janela se repete só no início do bloco."""
    matrix = np.asarray(values, dtype=np.float32)
    if matrix.ndim != 2 or not len(matrix):
        raise ValueError("O fluxo deve ter formato (janelas, variáveis) e não ser vazio.")
    if length < 2:
        raise ValueError("A sequência precisa de ao menos dois passos.")
    padded = np.vstack([np.repeat(matrix[:1], length - 1, axis=0), matrix])
    return np.stack([padded[i:i + length] for i in range(len(matrix))])


def sequences_for_blocks(values: np.ndarray, blocks, length: int = DEFAULT_SEQUENCE):
    """Sequências de cada bloco contíguo, sem atravessar ensaios nem papéis."""
    matrix = np.asarray(values, dtype=np.float32)
    sequences, targets = [], []
    for block in blocks:
        indices = np.asarray(block, dtype=int)
        if not len(indices):
            continue
        if np.any(np.diff(indices) != 1):
            raise ValueError("Cada bloco temporal deve ter índices contíguos.")
        sequences.append(sequences_from_flow(matrix[indices], length))
        targets.append(indices)
    if not sequences:
        raise ValueError("Nenhum bloco temporal válido foi fornecido.")
    return np.concatenate(sequences), np.concatenate(targets)


def autocorrelation(series: np.ndarray, max_lag: int) -> np.ndarray:
    """Autocorrelação amostral (estimador enviesado) por coluna, lags 1..max_lag."""
    data = np.asarray(series, dtype=np.float64)
    if data.ndim == 1:
        data = data[:, None]
    if len(data) <= max_lag:
        raise ValueError("O bloco é curto demais para o lag pedido.")
    centered = data - data.mean(axis=0)
    variance = np.sum(centered ** 2, axis=0)
    result = np.zeros((max_lag, data.shape[1]))
    valid = variance > 0
    for lag in range(1, max_lag + 1):
        product = np.sum(centered[lag:] * centered[:-lag], axis=0)
        result[lag - 1, valid] = product[valid] / variance[valid]
    return result


def decorrelation_report(blocks, *, names, purge: int = DEFAULT_PURGE, max_lag: int = 20,
                         threshold: float = 0.2, share: float = 0.9) -> dict:
    """Verificação do M14: a separação cobre a dependência temporal?

    Para cada bloco (ex.: treino de cada ensaio saudável), mede em que lag |ACF| fica
    abaixo de `threshold` em ao menos `share` das variáveis. Só relata; não muda o protocolo.
    """
    per_block = {}
    for label, block in blocks.items():
        acf = np.abs(autocorrelation(block, max_lag))
        below = (acf < threshold).mean(axis=1)
        lag = next((i + 1 for i, fraction in enumerate(below) if fraction >= share), None)
        per_variable = {name: next((i + 1 for i in range(max_lag) if acf[i, j] < threshold), None)
                        for j, name in enumerate(names)}
        per_block[label] = {
            "lag_descorrelacao": lag,
            "acf_mediana_por_lag": [round(float(v), 4) for v in np.median(acf, axis=1)],
            "lag_por_variavel": per_variable,
        }
    lags = [item["lag_descorrelacao"] for item in per_block.values()]
    needed = None if any(lag is None for lag in lags) else max(lags)
    # A separação de `purge` janelas afasta as fronteiras em purge + 1 passos.
    return {
        "criterio": {"limite_abs_acf": threshold, "fracao_variaveis": share, "lag_maximo": max_lag},
        "separacao_atual": purge,
        "distancia_entre_blocos": purge + 1,
        "lag_necessario": needed,
        "suficiente": needed is not None and needed <= purge + 1,
        "blocos": per_block,
    }
