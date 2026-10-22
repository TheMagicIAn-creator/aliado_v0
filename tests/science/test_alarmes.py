"""Os alarmes: a confirmação por janelas seguidas e a taxa de alarmes falsos estimada (só numpy)."""

from __future__ import annotations

import numpy as np
import pytest

from aliado.science.detection.metrics import (
    WINDOWS_PER_HOUR,
    alarm_starts,
    first_alarm,
    markov_alarm_rate,
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
