"""A partição temporal da detecção (M14), independente do conjunto de dados: blocos contíguos de treino, validação,
calibração e teste, com janelas de separação entre eles. Só depende do numpy; nada aqui treina modelos nem escolhe
limiares.
"""

from __future__ import annotations

import numpy as np

ROLES = ("train", "validation", "calibration", "test")
DEFAULT_FRACTIONS = (0.50, 0.15, 0.15, 0.20)
DEFAULT_PURGE = 2


def temporal_split(n: int, *, fractions=DEFAULT_FRACTIONS, purge: int = DEFAULT_PURGE,
                   min_block: int = 10) -> dict[str, np.ndarray]:
    """Blocos contíguos treino/validação/calibração/teste; `purge` janelas descartadas entre eles.

    As fronteiras são int(n × fração acumulada), como no protocolo de referência.
    """
    if len(fractions) != len(ROLES) or any(f <= 0 for f in fractions) or abs(sum(fractions) - 1) > 1e-9:
        raise ValueError("As quatro frações devem ser positivas e somar 1.")
    if purge < 0:
        raise ValueError("A separação não pode ser negativa.")
    cumulative = np.round(np.cumsum(fractions)[:-1], 10)
    bounds = [int(n * c) for c in cumulative]
    starts = [0] + [b + purge for b in bounds]
    ends = bounds + [n]
    split = {role: np.arange(start, end) for role, start, end in zip(ROLES, starts, ends)}
    if any(len(block) < min_block for block in split.values()):
        raise ValueError(f"A divisão produziu um papel com menos de {min_block} janelas.")
    return split
