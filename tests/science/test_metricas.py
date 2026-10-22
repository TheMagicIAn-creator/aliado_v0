"""Lote 15: regra de alarme, métricas por janela e intervalos (só numpy)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from aliado.science.detection.metrics import (
    WINDOWS_PER_HOUR,
    alarm_starts,
    auc_pr,
    auc_roc,
    block_bootstrap_indices,
    first_alarm,
    markov_alarm_rate,
    paired_interval,
    poisson_upper,
    proportion_interval,
    verdict,
    window_metrics,
)


def test_alarm_rule_on_the_eight_cycle_example():
    above = [0, 1, 0, 1, 1, 1, 1, 0]  # ciclos 1 a 8
    assert alarm_starts(above, 1).tolist() == [1, 3]  # ciclos 2 e 4
    assert alarm_starts(above, 3).tolist() == [5]  # ciclo 6, quando 4, 5 e 6 se completam
    assert alarm_starts(above, 5).tolist() == [] and first_alarm(above, 5) is None
    assert first_alarm(above, 3) == 5
    # Uma sequência longa é um só alarme; um novo exige voltar abaixo do limiar.
    assert alarm_starts([1, 1, 1, 1, 1, 0, 1, 1, 1], 3).tolist() == [2, 8]
    for bad in (0, True):
        with pytest.raises(ValueError):
            alarm_starts(above, bad)


def test_window_metrics_match_hand_calculation():
    result = window_metrics([0.1, 0.4], [0.35, 0.8], 0.3)
    assert (result["vp"], result["fn"], result["fp"], result["vn"]) == (2, 0, 1, 1)
    assert (result["sensibilidade"], result["especificidade"]) == (1.0, 0.5)
    assert result["precisao"] == pytest.approx(2 / 3) and result["f1"] == pytest.approx(0.8)
    assert result["acuracia_balanceada"] == 0.75 and result["mcc"] == pytest.approx(2 / math.sqrt(12))
    assert result["auc_roc"] == pytest.approx(0.75)
    # Curva precisão-revocação: pontos (1; 0,5), (1; 0,667), (0,5; 0,5), (0,5; 1) e (0; 1).
    assert result["auc_pr"] == pytest.approx(0.5 * (2 / 3 + 0.5) / 2 + 0.5)
    none_predicted = window_metrics([0.1, 0.2], [0.3, 0.4], 1.0)
    assert none_predicted["precisao"] is None and none_predicted["f1"] == 0.0 and none_predicted["mcc"] == 0.0
    tied = np.array([True, False, True, False])
    # Com empate total, a curva vai de (1; 0,5) ao ponto acrescentado (0; 1): área 0,75, como na origem.
    assert auc_roc(tied, np.ones(4)) == 0.5 and auc_pr(tied, np.ones(4)) == pytest.approx(0.75)
    with pytest.raises(ValueError):
        window_metrics([], [1.0], 0.5)


def test_poisson_upper_bound_is_the_rule_of_three_for_zero_events():
    assert poisson_upper(0) == pytest.approx(-math.log(0.05), rel=1e-9)  # ≈ 3,0
    assert poisson_upper(1) == pytest.approx(4.7439, abs=1e-4)
    assert poisson_upper(2) == pytest.approx(6.2958, abs=1e-4)


def test_block_bootstrap_is_reproducible_and_wider_on_correlated_series():
    rng = np.random.default_rng(0)
    indices = block_bootstrap_indices(25, block=12, resamples=3, rng=rng)
    assert indices.shape == (3, 25) and indices.max() < 25
    assert np.all(np.diff(indices[:, :12], axis=1) == 1)  # o primeiro bloco é contíguo
    flags = np.repeat(np.tile([1, 0], 10), 30)  # 600 janelas em trechos de 30 iguais
    first = proportion_interval([flags], block=12, resamples=2000, seed=1)
    assert first == proportion_interval([flags], block=12, resamples=2000, seed=1)
    independent = proportion_interval([flags], block=1, resamples=2000, seed=1)
    assert first[1] - first[0] > 1.5 * (independent[1] - independent[0])


def test_paired_interval_and_verdict():
    assert paired_interval([2.0, 2.0, None, 2.0], resamples=500, seed=0) == {"media": 2.0, "ic95": [2.0, 2.0], "n": 3}
    assert paired_interval([None], resamples=500, seed=0) == {"media": None, "ic95": None, "n": 0}
    assert verdict([0.1, 0.5], higher_is_better=True) == "Denso"
    assert verdict([-0.5, -0.1], higher_is_better=True) == "AE-LSTM"
    assert verdict([0.1, 0.5], higher_is_better=False) == "AE-LSTM"
    assert verdict([-1.0, 1.0], higher_is_better=False) == "sem diferença clara"
    assert verdict(None, higher_is_better=True) == "sem dados"


def test_markov_alarm_rate_recovers_a_known_chain():
    rng = np.random.default_rng(11)
    p01, p11 = 0.05, 0.4
    segments = []
    for _ in range(16):
        state, flags = False, []
        for _ in range(5000):
            state = rng.random() < (p11 if state else p01)
            flags.append(state)
        segments.append(np.array(flags))
    result = markov_alarm_rate(segments, 3, resamples=500, seed=1)
    assert result["p01"] == pytest.approx(p01, abs=0.005) and result["p11"] == pytest.approx(p11, abs=0.02)
    pi0 = (1 - p11) / (p01 + 1 - p11)
    assert result["prob_alarme_por_janela"] == pytest.approx(pi0 * p01 * p11 ** 2, rel=0.15)
    assert result["alarmes_por_hora"] == pytest.approx(result["prob_alarme_por_janela"] * WINDOWS_PER_HOUR)
    low, high = result["ic95"]
    assert low <= result["alarmes_por_hora"] <= high
    assert result["previsto"]["alarmes"] == pytest.approx(result["observado"]["alarmes"], rel=0.2)


def test_markov_alarm_rate_counts_and_the_all_healthy_case():
    quiet = markov_alarm_rate([np.zeros(50, dtype=bool)] * 3, 3, resamples=200, seed=1)
    assert quiet["alarmes_por_hora"] == 0 and quiet["ic95"] == [0.0, 0.0] and quiet["observado"]["alarmes"] == 0
    example = markov_alarm_rate([[0, 1, 1, 1, 0, 1, 1, 0]], 3, resamples=200, seed=1)
    assert example["observado"] == {"sequencias_de_2": 2, "alarmes": 1}
    assert (example["janelas"], example["janelas_acima"]) == (8, 5)
    with pytest.raises(ValueError):
        markov_alarm_rate([[]], 3, seed=1)
