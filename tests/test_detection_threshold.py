"""Lote 14: limiar empírico e informação efetiva da calibração (só numpy)."""

from __future__ import annotations

import numpy as np
import pytest

from aliado.science.detection.threshold import (
    DegenerateThresholdError,
    calibrate_threshold,
    effective_sample_size,
    false_alarm_interval,
    minimum_n_for_percentile,
)


def test_threshold_takes_the_higher_order_statistic_and_expected_false_alarm():
    scores = np.arange(1.0, 211.0)[::-1]  # 210 escores distintos, fora de ordem
    calibration = calibrate_threshold(scores, 99.0)
    assert (calibration.rank, calibration.n, calibration.value) == (208, 210, 208.0)  # o 3º maior
    assert calibration.effective_percentile == pytest.approx(100 * 208 / 210)
    assert calibration.expected_false_alarm == pytest.approx(3 / 211)
    assert not calibration.is_sample_maximum
    canonical = calibrate_threshold(np.arange(192.0), 99.0)
    assert (canonical.rank, canonical.expected_false_alarm) == (191, pytest.approx(2 / 193))  # o 2º maior
    assert calibration.as_dict()["n_minimo_para_o_percentil"] == 101


def test_threshold_refuses_percentiles_that_fall_on_the_maximum():
    assert (minimum_n_for_percentile(99.0), minimum_n_for_percentile(99.9)) == (101, 1001)
    assert minimum_n_for_percentile(100.0) is None
    with pytest.raises(DegenerateThresholdError, match="1001"):
        calibrate_threshold(np.arange(210.0), 99.9)
    assert calibrate_threshold(np.arange(210.0), 99.9, strict=False).is_sample_maximum
    for scores, percentile in (([1.0, np.nan], 50.0), ([1.0], 50.0), ([1.0, 2.0], 0.0)):
        with pytest.raises(ValueError):
            calibrate_threshold(scores, percentile)


def test_effective_sample_size_shrinks_with_autocorrelation():
    rng = np.random.default_rng(0)
    noise = rng.normal(size=2000)
    persistent = np.zeros(2000)
    for t in range(1, 2000):
        persistent[t] = 0.9 * persistent[t - 1] + rng.normal()
    assert effective_sample_size([noise])["n_efetivo"] > 1800
    report = effective_sample_size([persistent[:1000], persistent[1000:]])
    # AR(1) com ρ = 0,9: 2000 × 0,1/1,9 ≈ 105 observações independentes.
    assert report["n"] == 2000 and 70 < report["n_efetivo"] < 160
    assert [block["n"] for block in report["blocos"]] == [1000, 1000]


def test_false_alarm_interval_of_an_order_statistic():
    # No máximo de n escores, a chance é Beta(1, n): quantil q = 1 − (1 − q)^(1/n).
    top = false_alarm_interval(50, 50)
    assert top["ic95"][0] == pytest.approx(1 - 0.975 ** (1 / 50), rel=1e-6)
    assert top["ic95"][1] == pytest.approx(1 - 0.025 ** (1 / 50), rel=1e-6)
    gpvs = false_alarm_interval(191, 192)
    calibration = calibrate_threshold(np.arange(192.0), 99.0)
    assert gpvs["media"] == pytest.approx(calibration.expected_false_alarm)
    draws = np.random.default_rng(3).beta(2, 191, 400_000)
    assert gpvs["ic95"] == pytest.approx(np.percentile(draws, [2.5, 97.5]).tolist(), rel=0.03)
    with pytest.raises(ValueError):
        false_alarm_interval(0, 10)
