"""A decomposição harmônica de uma janela de W amostras que cobre exatamente um período da fundamental.

A janela é retangular: com um período inteiro, o bin k da FFT é a k-ésima harmônica, sem vazamento entre elas. Uma
janela de Hann misturaria a fundamental com o nível médio e com a 2ª harmônica: num seno puro, daria nível médio e
2ª harmônica de metade da fundamental, a mesma assinatura de uma falha. Uma janela por vez: a FFT em lote não garante
os mesmos bits.
"""

from __future__ import annotations

import numpy as np


def thd(values: np.ndarray, max_harmonic: int = 40) -> float:
    """Distorção harmônica total: a raiz da soma dos quadrados da 2ª à `max_harmonic`-ésima harmônica, dividida pela
    fundamental (a conta dos atributos desde a origem)."""
    spectrum = np.abs(np.fft.rfft(values - np.mean(values)))
    fundamental = max(float(spectrum[1]), np.finfo(float).eps)
    limit = min(max_harmonic + 1, len(spectrum))
    return float(np.sqrt(np.sum(spectrum[2:limit] ** 2)) / fundamental)


def harmonics(values) -> tuple[float, np.ndarray]:
    """O nível médio a0 e a amplitude C_k de cada harmônica k = 1…W//2.

    C_k = 2|X_k|/W, com X = rfft(x − a0); no bin de Nyquist (W par), |X|/W, sem dobrar. Assim vale a igualdade de
    Parseval: média(x²) = a0² + Σ C_k²/2, com o termo de Nyquist inteiro, sem a metade."""
    x = np.asarray(values, dtype=np.float64)
    a0 = float(np.mean(x))
    spectrum = np.abs(np.fft.rfft(x - a0)) / len(x)
    amplitudes = 2 * spectrum[1:]
    if len(x) % 2 == 0:
        amplitudes[-1] = spectrum[-1]
    return a0, amplitudes
