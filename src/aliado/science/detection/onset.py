"""Início observado das falhas do GPVS (lote 24): a mudança nas variáveis, sem os detectores.

Os CSVs do GPVS não têm canal de disparo, e o conjunto diz só que as falhas foram introduzidas
manualmente, na metade de cada experimento; o início nominal é o meio do registro. O início
observado é a primeira mudança na média das 24 variáveis depois do comissionamento, achada pelo
PELT (Killick, Fearnhead e Eckley, 2012) com custo quadrático e penalidade c · d · ln n. O c é o
menor da grade que não acha mudança nenhuma nos dois ensaios saudáveis. Nenhum escore dos
autoencoders entra. Só depende do numpy.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

import numpy as np

from aliado.science.detection import gpvs
from aliado.science.detection.protocol import robust_center_scale

GRID = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 30.0)
CLASSES = ("clara", "fraca", "nenhuma")


@dataclass(frozen=True)
class OnsetConfig:
    """Escolhas do início observado, congeladas antes de recalcular qualquer métrica."""

    grid: tuple[float, ...] = GRID
    min_segment: int = 5  # 100 ms
    clip: float = 10.0
    scale_floor: float = 1e-6
    healthy_reference: float = 0.25  # nos saudáveis, o trecho inicial que faz as vezes do comissionamento

    def __post_init__(self):
        if not self.grid or any(c <= 0 for c in self.grid) or list(self.grid) != sorted(set(self.grid)):
            raise ValueError("A grade de penalidades deve ser crescente, sem repetição e positiva.")
        if self.min_segment < 2 or self.clip <= 0 or self.scale_floor <= 0 or not 0 < self.healthy_reference < 1:
            raise ValueError("Segmento mínimo, limite, piso e trecho de referência inválidos.")

    def as_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self)))

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True).encode("utf-8")).hexdigest()


def robust_z(values: np.ndarray, reference: np.ndarray, *, floor: float, clip: float) -> np.ndarray:
    """Mediana e IQR do trecho de referência; valores fora de ±clip ficam no limite."""
    center, scale = robust_center_scale(reference, floor=floor)
    return np.clip((np.asarray(values, dtype=np.float64) - center) / scale, -clip, clip)


def penalty(multiplier: float, n: int, d: int) -> float:
    return float(multiplier) * int(d) * math.log(int(n))


def pelt(matrix: np.ndarray, penalty: float, min_segment: int = 5) -> list[int]:
    """Mudanças na média pelo PELT com custo quadrático: o índice em que cada segmento novo começa.

    O custo de um trecho é a soma dos quadrados em torno da própria média; a poda descarta um
    início s quando F(s) + custo(s, t) já passa de F(t), o que vale para este custo.
    """
    data = np.asarray(matrix, dtype=np.float64)
    if data.ndim == 1:
        data = data[:, None]
    n = len(data)
    if n < 2 * min_segment:
        return []
    sums = np.vstack([np.zeros(data.shape[1]), np.cumsum(data, axis=0)])
    squares = np.r_[0.0, np.cumsum((data ** 2).sum(axis=1))]
    best = np.full(n + 1, np.inf)
    best[0] = -penalty
    previous = np.zeros(n + 1, dtype=int)
    candidates = np.array([0])
    for t in range(min_segment, n + 1):
        ready = candidates[t - candidates >= min_segment]
        waiting = candidates[t - candidates < min_segment]
        if len(ready):
            delta = sums[t] - sums[ready]
            cost = squares[t] - squares[ready] - (delta ** 2).sum(axis=1) / (t - ready)
            total = best[ready] + cost + penalty
            choice = int(np.argmin(total))
            best[t], previous[t] = total[choice], ready[choice]
            ready = ready[total - penalty <= best[t]]
        candidates = np.r_[ready, waiting, t]
    changes, t = [], n
    while t > 0:
        t = int(previous[t])
        if t > 0:
            changes.append(t)
    return sorted(changes)


def _changes(values, reference_windows: int, config: OnsetConfig) -> dict[float, list[int]]:
    matrix = robust_z(values, values[:reference_windows], floor=config.scale_floor, clip=config.clip)
    return {c: pelt(matrix, penalty(c, len(matrix), matrix.shape[1]), config.min_segment) for c in config.grid}


def choose_penalty(healthy: dict[str, np.ndarray], config: OnsetConfig) -> tuple[float, dict]:
    """O menor c da grade sem mudança nenhuma nos ensaios saudáveis, e as mudanças de cada c."""
    control = {name: {str(c): len(found) for c, found in
                      _changes(values, int(len(values) * config.healthy_reference), config).items()}
               for name, values in healthy.items()}
    for c in config.grid:
        if all(counts[str(c)] == 0 for counts in control.values()):
            return c, control
    raise ValueError("Nenhuma penalidade da grade deixa os ensaios saudáveis sem mudança.")


def commissioning_windows(phase: np.ndarray) -> int:
    """O comissionamento de `gpvs.prepare`: a primeira metade do pré-falha, com o mínimo de janelas."""
    pre = int(np.sum(phase == "pre_fault"))
    return max(gpvs.BASELINE_MIN_WINDOWS, int(np.floor(pre * gpvs.BASELINE_FRACTION)))


def classify(first: dict[float, int | None], chosen: float) -> str:
    """Clara se a mesma mudança fica de c em diante; fraca se some com um c maior; senão, nenhuma."""
    at = first[chosen]
    if at is None:
        return "nenhuma"
    return "clara" if all(first[c] == at for c in first if c >= chosen) else "fraca"


def estimate(experiments: dict, config: OnsetConfig | None = None) -> dict:
    """Início nominal e observado de cada ensaio com falha, com a classe e o controle nos saudáveis.

    `experiments` são os `gpvs.ExperimentFeatures` (variáveis brutas por janela, fases e metadados).
    """
    config = config or OnsetConfig()
    chosen, control = choose_penalty({name: experiments[name].values for name in gpvs.HEALTHY}, config)
    trials = {}
    for name in gpvs.FAULTY:
        item = experiments[name]
        fs = float(item.metadata["fs_hz"])
        reference = commissioning_windows(item.phase)
        first = {}
        for c, found in _changes(item.values, reference, config).items():
            after = [t for t in found if t > reference]
            first[c] = after[0] if after else None
        nominal = int(np.flatnonzero(item.phase != "pre_fault")[0])
        observed = first[chosen]
        trials[name] = {
            "classe": classify(first, chosen),
            "nominal_janela": nominal,
            "nominal_s": item.metadata["fronteira_falha_amostra"] / fs,
            "observado_janela": observed,
            "observado_s": None if observed is None else observed * gpvs.WINDOW / fs,
            "comissionamento_janelas": reference,
            "janelas": int(len(item.values)),
            "primeira_mudanca_por_c": {str(c): value for c, value in first.items()},
        }
    return {"penalidade_c": chosen, "controle_saudavel": control, "ensaios": trials,
            "configuracao": config.as_dict(), "configuracao_sha256": config.digest()}
