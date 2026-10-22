"""Caminhos do repositório e as duas condições dos dados reais, as mesmas para todos os testes."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "data" / "resultados"
GPVS = ROOT / "data" / "gpvs"
REFERENCE = ROOT / "docs" / "pesquisa-inversores"
STATIC = ROOT / "src" / "aliado" / "interfaces" / "web" / "static"

# Base presente: os 16 CSVs do GPVS e o registro de proveniência deles.
BASE_PRESENTE = (GPVS / "proveniencia.json").is_file() and (GPVS / "F0L.csv").is_file()
# Resultados oficiais presentes: a avaliação de 27/09/2026, o treino dela e a reanálise de 30/09/2026.
OFFICIAL = ("gpvs-avaliacao-001", "gpvs-modelos-002", "gpvs-reanalise-001")
RESULTADOS_OFICIAIS = ((RESULTS / "gpvs-avaliacao-001" / "escores.npz").is_file()
                       and (RESULTS / "gpvs-modelos-002" / "configuracao.json").is_file()
                       and (RESULTS / "gpvs-reanalise-001" / "relatorio.json").is_file())
