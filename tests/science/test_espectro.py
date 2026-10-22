"""O espectro de uma janela de um período (lote 55, EXP-14): amplitudes exatas, Nyquist sem dobrar, Parseval e a THD."""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from aliado.science.espectro.decomposicao import harmonics, thd  # noqa: E402


def _signal(size: int, terms: dict, level: float = 0.0):
    n = np.arange(size)
    return level + sum(amplitude * np.cos(2 * np.pi * k * n / size + phase) for k, (amplitude, phase) in terms.items())


def test_amplitudes_are_exact_and_the_nyquist_bin_is_not_doubled():
    """EXP-14: com um período inteiro na janela, cada harmônica sai com a sua amplitude, sem vazamento."""
    size = 200
    x = _signal(size, {1: (10.0, 0.3), 2: (0.5, -1.1), 3: (0.8, 2.0), 5: (0.2, 0.7)}, level=0.4) \
        + 0.05 * np.cos(np.pi * np.arange(size))  # o bin de Nyquist (k = W/2)
    a0, amplitudes = harmonics(x)
    assert len(amplitudes) == size // 2 and a0 == pytest.approx(0.4, abs=1e-12)
    expected = np.zeros(size // 2)
    expected[[0, 1, 2, 4]] = (10.0, 0.5, 0.8, 0.2)
    expected[-1] = 0.05
    assert np.allclose(amplitudes, expected, atol=1e-12)
    # W ímpar: não há bin de Nyquist, e todas as amplitudes são dobradas.
    a0, odd = harmonics(_signal(201, {3: (2.0, 0.0)}, level=1.0))
    assert len(odd) == 100 and a0 == pytest.approx(1.0, abs=1e-12) and odd[2] == pytest.approx(2.0, abs=1e-12)
    assert np.allclose(np.delete(odd, 2), 0.0, atol=1e-12)


@pytest.mark.parametrize("size", [200, 201])
def test_parseval_holds_to_the_last_digits(size):
    """EXP-14: média(x²) = a0² + Σ C_k²/2, com o termo de Nyquist inteiro quando W é par."""
    x = np.random.default_rng(size).normal(1.5, 3.0, size)
    a0, amplitudes = harmonics(x)
    halves = amplitudes ** 2 / 2
    if size % 2 == 0:
        halves[-1] = amplitudes[-1] ** 2
    assert np.mean(x ** 2) == pytest.approx(a0 ** 2 + halves.sum(), rel=1e-12)


def test_thd_is_the_ratio_of_the_harmonics_to_the_fundamental():
    """EXP-14: a THD é a raiz da soma dos quadrados da 2ª à 40ª harmônica sobre a fundamental, sem o nível médio."""
    x = _signal(200, {1: (10.0, 0.1), 2: (0.3, 0.0), 7: (0.4, 1.0), 41: (5.0, 0.0)}, level=3.0)
    _, amplitudes = harmonics(x)
    assert thd(x) == pytest.approx(np.sqrt(0.3 ** 2 + 0.4 ** 2) / 10.0, rel=1e-12)
    assert thd(x) == pytest.approx(np.sqrt(np.sum(amplitudes[1:40] ** 2)) / amplitudes[0], rel=1e-12)


def test_the_rectangular_window_keeps_a_pure_sine_clean_and_hann_would_not():
    """EXP-14: o porquê da janela retangular. Num seno puro, ela dá nível médio e 2ª harmônica nulos; uma janela de Hann
    daria os dois com metade da fundamental, a mesma assinatura de uma falha, em toda janela sadia."""
    x = _signal(200, {1: (1.0, 0.0)})
    a0, amplitudes = harmonics(x)
    assert abs(a0) < 1e-12 and amplitudes[1] < 1e-12 and amplitudes[0] == pytest.approx(1.0)
    hann = np.hanning(201)[:-1]  # a de Hann periódica, de um período
    a0, amplitudes = harmonics(x * hann)
    assert abs(a0) / amplitudes[0] == pytest.approx(0.5) and amplitudes[1] / amplitudes[0] == pytest.approx(0.5)
