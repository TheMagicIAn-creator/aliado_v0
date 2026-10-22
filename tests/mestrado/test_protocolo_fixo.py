"""O protocolo fixo do experimento (regra 1 do relatório em LaTeX de 21/10/2026): mudar um destes valores é mudar o
método, e pede uma spec própria."""

from __future__ import annotations

import pytest

pytest.importorskip("torch")

from aliado.science.deteccao.particao.blocos import DEFAULT_FRACTIONS  # noqa: E402
from aliado.specializations.mestrado.atributos import variaveis  # noqa: E402
from aliado.specializations.mestrado.avaliacao.configuracao import EvaluationConfig  # noqa: E402
from aliado.specializations.mestrado.base import ensaios  # noqa: E402
from aliado.specializations.mestrado.preparo import preparacao  # noqa: E402
from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig  # noqa: E402

FEATURES = (
    "Ipv_median", "Ipv_iqr", "Vpv_median", "Vpv_iqr", "Vdc_median", "Vdc_iqr",
    "ia_rms", "ib_rms", "ic_rms", "va_rms", "vb_rms", "vc_rms",
    "ia_thd", "ib_thd", "ic_thd", "va_thd", "vb_thd", "vc_thd",
    "i_rms_unbalance", "v_rms_unbalance", "p_ac_mean", "p_ac_std", "p_dc_median", "p_dc_iqr",
)


def test_the_protocol_values_are_the_ones_decided():
    """EXP-12: os 24 atributos na ordem, a janela de um ciclo, a divisão, o escore, o limiar, o alarme e a sequência."""
    assert variaveis.FEATURES == FEATURES
    assert (ensaios.WINDOW, ensaios.SAMPLING_HZ, ensaios.GRID_HZ) == (200, 10_000.0, 50.0)
    assert preparacao.PURGE == 11 and tuple(DEFAULT_FRACTIONS) == (0.50, 0.15, 0.15, 0.20)
    config = ExperimentConfig()
    assert (config.top_k, config.percentile, config.purge, tuple(config.fractions)) == (5, 99.0, 11, (0.50, 0.15, 0.15, 0.20))
    assert config.hyperparameters.sequence == 8
    assert EvaluationConfig().confirmations == 3


def test_normalization_is_the_robust_one_of_the_training_baseline():
    """EXP-12: a escala é a mediana e o IQR da linha de base do treino, com piso de 10% do IQR."""
    from aliado.science.deteccao.normalizacao.escala_robusta import robust_center_scale

    np = pytest.importorskip("numpy")
    center, scale = robust_center_scale(np.array([[1.0], [2.0], [3.0], [4.0], [100.0]]))
    assert (center.tolist(), scale.tolist()) == ([3.0], [2.0])
    assert preparacao.IQR_FLOOR_FRACTION == 0.10
