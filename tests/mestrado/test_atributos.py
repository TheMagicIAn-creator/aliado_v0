"""Os 24 atributos por janela de um ciclo de 50 Hz; com os dados reais, as estatísticas da origem."""

from __future__ import annotations

import csv

import numpy as np
import pytest
from apoio.caminhos import ROOT

from aliado.specializations.mestrado.atributos import variaveis
from aliado.specializations.mestrado.atributos.cache import features_cache
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.preparo import preparacao
from aliado.specializations.mestrado.preparo import resumo as resumo_do_preparo


def test_feature_vector_on_known_signals():
    t = np.arange(ensaios.WINDOW) / ensaios.SAMPLING_HZ
    window = np.zeros((ensaios.WINDOW, len(variaveis.PRIMARY_COLUMNS)))
    window[:, 0], window[:, 1], window[:, 2] = 2.0, 100.0, 150.0
    for k, shift in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
        window[:, 3 + k] = 10 * np.sin(2 * np.pi * 50 * t + shift)
        window[:, 6 + k] = 200 * np.sin(2 * np.pi * 50 * t + shift)
    features = dict(zip(variaveis.FEATURES, variaveis.feature_vector(window)))
    assert features["Ipv_median"] == pytest.approx(2.0) and features["Ipv_iqr"] == 0
    assert features["ia_rms"] == pytest.approx(10 / np.sqrt(2), rel=1e-5)
    assert features["ia_thd"] < 1e-5 and features["i_rms_unbalance"] < 1e-5
    assert features["p_ac_mean"] == pytest.approx(3 * 10 * 200 / 2, rel=1e-5)
    assert features["p_dc_median"] == pytest.approx(200.0)
    with pytest.raises(ValueError):
        variaveis.feature_vector(window[:100])


def test_real_gpvs_reproduces_reference_counts_and_statistics(base_real):
    cache = features_cache(base_real)
    prepared = preparacao.prepare(base_real, cache=cache, purge=2)  # separação da origem
    assert len(prepared.healthy_values) == 1423
    assert [len(prepared.split[r]) for r in ("train", "validation", "calibration", "test")] == [711, 209, 210, 281]
    assert resumo_do_preparo.report(prepared)["total_janelas"]["com_falha"] == 9391
    reference = {row[""]: row for row in csv.DictReader(
        (ROOT / "tests" / "data" / "gpvs_estatisticas_referencia.csv").open(encoding="utf-8"))}
    values = prepared.healthy_values.astype(np.float64)
    for j, name in enumerate(variaveis.FEATURES):
        column = values[:, j]
        ours = [column.mean(), column.std(ddof=1), column.min(), *np.percentile(column, (25, 50, 75)), column.max()]
        expected = [float(reference[name][k]) for k in ("mean", "std", "min", "25%", "50%", "75%", "max")]
        assert np.allclose(ours, expected, rtol=1e-5, atol=1e-9), name
    canonical = preparacao.prepare(base_real, cache=cache)
    assert canonical.purge == preparacao.PURGE == 11
    assert [len(canonical.split[r]) for r in ("train", "validation", "calibration", "test")] == [711, 191, 192, 263]
    assert resumo_do_preparo.report(canonical)["verificacao_m14_autocorrelacao"]["suficiente"]
