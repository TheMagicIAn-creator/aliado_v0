"""Onde a evidência espectral fica e como é gravada e lida, só com a biblioteca padrão (o chat e o PDF a leem sem o
numpy). Uma rodada nova a grava na própria pasta, dentro da consulta registrada dela. Para uma rodada anterior, o
"Preparar" do explorador a grava na pasta dos exploradores, como exploração pós-teste: nunca em data/resultados."""

from __future__ import annotations

import json
import os
from pathlib import Path

from aliado.specializations.mestrado.rodada.declaracao import STAGES

FILE = "evidencia.json"
# O que vai para o resultado da rodada e para o PDF: tudo, menos a tabela completa, que fica no arquivo.
SUMMARY_KEYS = ("origem", "executado_em", "treino_de_referencia", "k", "confirmacoes", "alarmes", "mais_mudam",
                "janelas_antes_da_mudanca")


def run_file(run) -> Path:
    """A da própria rodada, ao lado da avaliação."""
    return run.evaluation.parent / STAGES["evidencia"] / FILE


def exploration_file(explorer_dir: str | Path, run) -> Path:
    """A de exploração pós-teste de uma rodada anterior, na pasta dos exploradores."""
    return Path(explorer_dir) / f"evidencia-espectral-{run.id}-{run.evaluation.name}.json"


def find(run, explorer_dir: str | Path | None = None) -> Path | None:
    """A evidência da rodada, se houver: a da própria pasta (nunca a da avaliação oficial) ou a do explorador."""
    places = ([] if run.official else [run_file(run)]) + ([exploration_file(explorer_dir, run)] if explorer_dir else [])
    return next((path for path in places if path.is_file()), None)


def write(evidence: dict, path: Path) -> Path:
    """Grava de uma vez: quem lê nunca vê o arquivo pela metade."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.parcial")
    partial.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(partial, path)
    return path


def read(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
