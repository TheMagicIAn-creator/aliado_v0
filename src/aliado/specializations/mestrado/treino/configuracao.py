"""A configuração congelada do treino, gravada com hash em cada saída (M14): separação, frações, sementes, k,
percentil e hiperparâmetros."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from aliado.science.deteccao.particao.blocos import DEFAULT_FRACTIONS
from aliado.science.deteccao.redes.autoencoders import Hyperparameters
from aliado.science.identidade.hashes import config_digest
from aliado.specializations.mestrado.preparo import preparacao


@dataclass(frozen=True)
class ExperimentConfig:
    """Escolhas congeladas antes de qualquer avaliação (M14), gravadas com hash em cada saída."""

    purge: int = preparacao.PURGE
    fractions: tuple[float, ...] = DEFAULT_FRACTIONS
    seeds: tuple[int, ...] = (13, 29, 42, 71, 101)
    reference_seed: int = 42
    top_k: int = 5
    sensitivity_k: tuple[int, ...] = (5, 10, 20)  # só relatada; nunca escolhe o k principal
    percentile: float = 99.0
    hyperparameters: Hyperparameters = field(default_factory=Hyperparameters)

    def __post_init__(self):
        if not self.seeds or len(set(self.seeds)) != len(self.seeds) or self.reference_seed not in self.seeds:
            raise ValueError("As sementes devem ser distintas e incluir a de referência.")
        if self.top_k not in self.sensitivity_k:
            raise ValueError("A grade de sensibilidade deve incluir o k principal.")

    def as_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self)))

    def digest(self) -> str:
        return config_digest(self.as_dict())
