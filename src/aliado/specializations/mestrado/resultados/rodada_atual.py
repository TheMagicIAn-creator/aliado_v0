"""A rodada atual: a completa mais nova do experimento; sem nenhuma, a avaliação oficial de 27/09/2026 e a reanálise
dela. Só lê, e só a biblioteca padrão."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from aliado import experiments
from aliado.specializations.mestrado.avaliacao.oficial import EVALUATION
from aliado.specializations.mestrado.rodada.declaracao import KEY, LEGACY_ID, STAGES

REANALYSIS_PREFIX = "gpvs-reanalise-"


@dataclass(frozen=True)
class Run:
    """Uma rodada: a pasta da avaliação, a do início observado das falhas e como ela é chamada."""

    evaluation: Path
    reanalysis: Path | None
    official: bool
    id: str
    consultation: int | None = None


def _legacy_reanalysis(results_dir: Path) -> Path | None:
    """A reanálise mais recente dos escores da avaliação de 27/09, com o início observado (lote 24)."""
    for folder in sorted(results_dir.glob(f"{REANALYSIS_PREFIX}*"), reverse=True):
        try:
            if _json(folder / "relatorio.json").get("origem", {}).get("avaliacao") == EVALUATION:
                return folder
        except (OSError, ValueError, AttributeError):
            continue  # reanálise ilegível: é secundária e não pode derrubar as visões da avaliação oficial
    return None


def current(results_dir: str | Path) -> Run:
    """A rodada que a aba mostra: a completa mais nova; sem nenhuma, a avaliação oficial de 27/09."""
    results_dir = Path(results_dir)
    found = experiments.latest(results_dir, KEY)
    if found:
        folder, result = found
        return Run(folder / STAGES["avaliacao"], folder / STAGES["inicio"], False,
                   folder.name, result.get("consulta"))
    return Run(results_dir / EVALUATION, _legacy_reanalysis(results_dir), True, LEGACY_ID, 1)


def _run(source) -> Run:
    return source if isinstance(source, Run) else current(source)


def _evaluation(source) -> Path:
    run = _run(source)
    folder = run.evaluation
    for name in ("configuracao.json", "relatorio.json", "metricas_por_ensaio.csv"):
        if not (folder / name).is_file():
            missing = "a avaliação oficial de 27/09" if run.official else f"a avaliação da {run.id}"
            raise FileNotFoundError(f"Falta {missing} ({name}) na pasta de resultados.")
    return folder


def label(run: Run, day: str | None) -> dict:
    """Como a rodada aparece nas telas, no chat e no PDF: "oficial" só para a avaliação de 27/09."""
    when = "/".join(reversed(str(day)[:10].split("-"))) if day else ""
    text = (f"Avaliação oficial de {when}" if run.official else
            f"Rodada de {when}" + (f" · {run.consultation}ª vez que os dados de teste foram usados"
                                   if run.consultation else ""))
    return {"id": run.id, "oficial": run.official, "data": day, "consulta": run.consultation, "rotulo": text}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
