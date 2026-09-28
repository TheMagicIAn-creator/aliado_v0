"""Limiar empírico sobre escores saudáveis de calibração (lote 14). Só depende do numpy.

Reescrita do contrato da origem (`calibrate_threshold` em `src/ml/treino_comparacao.py`,
commit 21f6ddf): o limiar é o escore de índice ceil((n − 1)·p/100) na fila crescente,
a regra "higher" dos percentis empíricos (Hyndman e Fan, 1996).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from aliado.science.detection.protocol import autocorrelation

PERCENTILE = 99.0


class DegenerateThresholdError(ValueError):
    """O percentil pedido cai no maior escore da calibração e não pode ser declarado."""


def minimum_n_for_percentile(percentile: float) -> int | None:
    """Menor calibração em que o percentil não cai no máximo: n ≥ (q − 2)/(q − 1), q = p/100.

    p99 exige 101 escores; p99,9 exige 1001. p100 é o máximo por definição (None).
    """
    q = float(percentile) / 100.0
    if q >= 1.0:
        return None
    return int(math.ceil(round((q - 2.0) / (q - 1.0), 9)))


@dataclass(frozen=True)
class ThresholdCalibration:
    value: float
    percentile: float
    rank: int  # posição do limiar na fila crescente, de 1 a n
    n: int

    @property
    def effective_percentile(self) -> float:
        return 100.0 * self.rank / self.n

    @property
    def is_sample_maximum(self) -> bool:
        return self.rank >= self.n

    @property
    def expected_false_alarm(self) -> float:
        """Chance de uma janela saudável nova passar do limiar: (n + 1 − posição)/(n + 1).

        Vale se a janela nova for permutável com as da calibração (o argumento da
        predição conformal; Vovk, Gammerman e Shafer, 2005). Janelas autocorrelacionadas
        mantêm essa média, mas a taxa observada num trecho curto varia muito mais.
        """
        return (self.n + 1 - self.rank) / (self.n + 1)

    def as_dict(self) -> dict:
        return {
            "limiar": self.value,
            "percentil_pedido": self.percentile,
            "percentil_efetivo": self.effective_percentile,
            "posicao": self.rank,
            "n_calibracao": self.n,
            "resolucao_pp": 100.0 / self.n,
            "maximo_amostral": self.is_sample_maximum,
            "n_minimo_para_o_percentil": minimum_n_for_percentile(self.percentile),
            "falso_alarme_esperado_por_janela": self.expected_false_alarm,
        }


def calibrate_threshold(scores, percentile: float = PERCENTILE, *, strict: bool = True) -> ThresholdCalibration:
    """Limiar na posição ceil((n − 1)·p/100) + 1; com `strict`, recusa cair no máximo da calibração."""
    values = np.asarray(scores, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("A calibração exige ao menos dois escores finitos.")
    if not 0.0 < percentile <= 100.0:
        raise ValueError("O percentil do limiar deve estar em (0, 100].")
    index = int(np.ceil((len(values) - 1) * percentile / 100.0))
    calibration = ThresholdCalibration(float(np.sort(values)[index]), float(percentile), index + 1, len(values))
    if strict and calibration.is_sample_maximum:
        minimum = minimum_n_for_percentile(percentile)
        fix = f"use ao menos {minimum} escores" if minimum else "peça um percentil menor que 100"
        raise DegenerateThresholdError(
            f"p{percentile:g} com n={len(values)} cai no maior escore da calibração; {fix} ou baixe o percentil.")
    return calibration


def effective_sample_size(blocks) -> dict:
    """Informação independente em escores autocorrelacionados: Σ n·(1 − ρ)/(1 + ρ) por bloco.

    ρ é a autocorrelação de lag 1 de cada bloco contíguo. É a aproximação de um processo
    AR(1) (Bayley e Hammersley, 1946), feita para médias: aqui dá só a ordem de grandeza.
    ρ negativo conta como zero.
    """
    per_block = []
    for block in blocks:
        series = np.asarray(block, dtype=float)
        rho = float(autocorrelation(series, 1)[0, 0])
        kept = max(rho, 0.0)
        per_block.append({"n": int(len(series)), "acf_lag1": rho,
                          "n_efetivo": float(len(series) * (1 - kept) / (1 + kept))})
    return {"blocos": per_block, "n": sum(item["n"] for item in per_block),
            "n_efetivo": float(sum(item["n_efetivo"] for item in per_block))}
