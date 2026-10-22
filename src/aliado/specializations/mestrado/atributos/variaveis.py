"""As 24 variáveis de cada janela de um ciclo de 50 Hz (200 amostras × 9 colunas primárias): mediana e IQR das
grandezas de corrente contínua, RMS e THD de cada fase, desequilíbrios e potências."""

from __future__ import annotations

import numpy as np

from aliado.science.espectro.decomposicao import thd
from aliado.specializations.mestrado.base.ensaios import WINDOW

PRIMARY_COLUMNS = ("Ipv", "Vpv", "Vdc", "ia", "ib", "ic", "va", "vb", "vc")
FEATURES = (
    "Ipv_median", "Ipv_iqr", "Vpv_median", "Vpv_iqr", "Vdc_median", "Vdc_iqr",
    "ia_rms", "ib_rms", "ic_rms", "va_rms", "vb_rms", "vc_rms",
    "ia_thd", "ib_thd", "ic_thd", "va_thd", "vb_thd", "vc_thd",
    "i_rms_unbalance", "v_rms_unbalance", "p_ac_mean", "p_ac_std", "p_dc_median", "p_dc_iqr",
)


def _iqr(values: np.ndarray) -> float:
    q25, q75 = np.percentile(values, (25, 75))
    return float(q75 - q25)


def feature_vector(window: np.ndarray) -> np.ndarray:
    """24 variáveis de uma janela (200 × 9 colunas primárias, na ordem de PRIMARY_COLUMNS)."""
    matrix = np.asarray(window, dtype=np.float64)
    if matrix.shape != (WINDOW, len(PRIMARY_COLUMNS)):
        raise ValueError(f"A janela deve ter formato ({WINDOW}, {len(PRIMARY_COLUMNS)}).")
    values: list[float] = []
    for column in range(3):  # Ipv, Vpv, Vdc
        values += [float(np.median(matrix[:, column])), _iqr(matrix[:, column])]
    current_rms = np.sqrt(np.mean(matrix[:, 3:6] ** 2, axis=0))
    voltage_rms = np.sqrt(np.mean(matrix[:, 6:9] ** 2, axis=0))
    values += current_rms.tolist() + voltage_rms.tolist()
    values += [thd(matrix[:, column]) for column in range(3, 9)]  # a mesma conta da evidência espectral (lote 55)
    eps = np.finfo(float).eps
    values += [float(np.std(current_rms) / max(float(np.mean(current_rms)), eps)),
               float(np.std(voltage_rms) / max(float(np.mean(voltage_rms)), eps))]
    ac_power = np.sum(matrix[:, 3:6] * matrix[:, 6:9], axis=1)
    dc_power = matrix[:, 0] * matrix[:, 1]
    values += [float(np.mean(ac_power)), float(np.std(ac_power)), float(np.median(dc_power)), _iqr(dc_power)]
    return np.asarray(values, dtype=np.float32)
