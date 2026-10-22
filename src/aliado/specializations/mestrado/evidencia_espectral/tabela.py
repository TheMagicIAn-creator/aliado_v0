"""O que muda em cada ensaio: por fase e indicador, a mediana nas janelas de comissionamento e depois do início
nominal da falha, e a mudança entre as duas medida em amplitudes interquartis (IQR) do comissionamento. O início é o
da avaliação (o meio do registro), e não o observado: a tabela não usa o que ela mesma mostraria."""

from __future__ import annotations

import numpy as np

from aliado.science.deteccao.normalizacao.escala_robusta import robust_center_scale
from aliado.specializations.mestrado.base.ensaios import FAULTY
from aliado.specializations.mestrado.evidencia_espectral.espectros import PHASES
from aliado.specializations.mestrado.preparo.inicio_nominal import nominal_onset

INDICATORS = ("dc", "fundamental", "thd", "h2", "h3", "h5")
FLOOR = 1e-9  # o IQR mínimo de um indicador quase constante no comissionamento


def indicators(rows: np.ndarray, reference: float) -> np.ndarray:
    """v = [a0/C1, C1/referência, THD, C2/C1, C3/C1, C5/C1] de cada janela, das colunas a0, C1…C5 e THD."""
    c1 = np.maximum(rows[:, 1], np.finfo(float).eps)
    return np.column_stack([rows[:, 0] / c1, rows[:, 1] / reference, rows[:, 6], rows[:, 2] / c1, rows[:, 3] / c1,
                            rows[:, 5] / c1])


def phase_indicators(spectra: dict, prepared, name: str, phase: str) -> np.ndarray:
    """Os indicadores de cada janela de uma fase, com a referência da fundamental no comissionamento do ensaio."""
    rows = spectra[name]["fases"][phase]
    return indicators(rows, float(np.median(rows[prepared.faults[name]["comissionamento"], 1])))


def changes(spectra: dict, prepared) -> dict:
    """{ensaio: {fase: {indicador: {"comissionamento", "depois", "mudanca"}}}}."""
    table = {}
    for name in FAULTY:
        item = prepared.faults[name]
        after = np.arange(nominal_onset(item), len(item["scaled"]))
        table[name] = {}
        for phase in PHASES:
            values = phase_indicators(spectra, prepared, name, phase)
            center, scale = robust_center_scale(values[item["comissionamento"]], floor=FLOOR)
            later = np.median(values[after], axis=0)
            table[name][phase] = {key: {"comissionamento": float(center[i]), "depois": float(later[i]),
                                        "mudanca": float((later[i] - center[i]) / scale[i])}
                                  for i, key in enumerate(INDICATORS)}
    return table


def strongest(table: dict, count: int = 2) -> dict[str, list[dict]]:
    """Em cada ensaio, os `count` pares de fase e indicador que mais mudam, pelo valor absoluto da mudança."""
    return {name: sorted(({"fase": phase, "indicador": key, **values} for phase, row in phases.items()
                          for key, values in row.items()), key=lambda entry: -abs(entry["mudanca"]))[:count]
            for name, phases in table.items()}
