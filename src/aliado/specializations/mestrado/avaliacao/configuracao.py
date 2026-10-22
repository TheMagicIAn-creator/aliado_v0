"""A configuração da avaliação, congelada antes de pontuar o teste (M14): confirmação, bloco do bootstrap,
reamostragens e semente."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from aliado.science.deteccao.alarmes.confirmacao import CONFIRMATIONS
from aliado.science.deteccao.metricas.incerteza import BLOCK, RESAMPLES


@dataclass(frozen=True)
class EvaluationConfig:
    """Escolhas da avaliação, congeladas antes de pontuar o teste (M14)."""

    confirmations: int = CONFIRMATIONS
    confirmation_grid: tuple[int, ...] = (1, 2, 3, 5)  # só relatada
    block: int = BLOCK  # lag de descorrelação medido no lote 13
    resamples: int = RESAMPLES
    seed: int = 20260927

    def __post_init__(self):
        if self.confirmations not in self.confirmation_grid or min(self.confirmation_grid) < 1:
            raise ValueError("A grade de confirmação deve incluir a principal e só valores positivos.")
        if self.block < 1 or self.resamples < 100:
            raise ValueError("Bloco e reamostragens inválidos.")

    def as_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self)))

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True).encode("utf-8")).hexdigest()
