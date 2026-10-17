"""NUC-01 (lotes 34 a 36): nenhum arquivo do núcleo menciona o domínio de uma especialização."""

from __future__ import annotations

import re
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "src" / "aliado"
DOMAIN = re.compile(r"gpvs|inversor|mestrado|fotovolt", re.IGNORECASE)
SUFFIXES = {".py", ".js", ".html", ".css", ".md", ".json"}
# O que o lote 34 deixou no núcleo, por arquivo: cada lote só pode diminuir, e o lote 36 zera a lista.
PENDING = {
    "agent.py": 1,
    "cli.py": 34,
    "interfaces/web/app.py": 4,
    "interfaces/web/static/app.js": 5,
    "interfaces/web/static/graficos.js": 6,
    "interfaces/web/static/index.html": 1,
    "knowledge/rewrite.py": 1,
    "routing.py": 2,
    "routing_examples.py": 9,
    "science/components.py": 1,
    "science/detection/__init__.py": 3,
    "science/detection/evaluation.py": 13,
    "science/detection/gpvs.py": 17,
    "science/detection/onset.py": 9,
    "science/detection/reanalysis.py": 23,
    "science/detection/summary.py": 22,
    "science/detection/training.py": 14,
    "science/digest.py": 14,
    "science/explorer.py": 22,
    "skills/builtin/pesquisa-inversores/references/decisoes-2026-09-13.md": 12,
    "skills/builtin/pesquisa-inversores/references/diretrizes-aprovadas-2026-09-22.md": 6,
    "skills/builtin/pesquisa-inversores/SKILL.md": 8,
}


def mentions() -> dict[str, int]:
    """Linhas com menção ao domínio em cada arquivo do núcleo: tudo fora das pastas de especialização."""
    found = {}
    for path in sorted(CORE.rglob("*")):
        relative = path.relative_to(CORE).as_posix()
        parts = relative.split("/")
        if (path.suffix not in SUFFIXES or "__pycache__" in parts or relative.startswith("interfaces/web/static/vendor/")
                or (parts[0] == "specializations" and len(parts) > 2)):
            continue
        count = sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if DOMAIN.search(line))
        if count:
            found[relative] = count
    return found


def test_nuc_01_core_has_no_new_domain_mentions():
    """NUC-01: só os arquivos da lista têm menções, nunca mais que nela; uma redução atualiza a lista."""
    assert mentions() == PENDING, "Atualize PENDING: uma menção nova entrou no núcleo, ou uma saiu e a lista ficou para trás."


def test_nuc_01_specialization_discovery_has_no_names():
    """NUC-01: o núcleo acha as especializações percorrendo a pasta, sem citar nenhuma pelo nome."""
    assert "specializations/__init__.py" not in mentions()
    assert "experiments/__init__.py" not in mentions() and "experiments/pdf.py" not in mentions()
    assert "interfaces/web/experiments.py" not in mentions()
