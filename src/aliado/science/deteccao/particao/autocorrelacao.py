"""A autocorrelação que justifica a separação entre os blocos (verificação do M14). Só relata; não muda o
protocolo."""

from __future__ import annotations

import numpy as np

from aliado.science.deteccao.particao.blocos import DEFAULT_PURGE


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
