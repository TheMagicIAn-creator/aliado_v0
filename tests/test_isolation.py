"""NUC-01 (lotes 34 a 36): nenhum arquivo do núcleo menciona o domínio de uma especialização."""

from __future__ import annotations

import re
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "src" / "aliado"
DOMAIN = re.compile(r"gpvs|inversor|mestrado|fotovolt", re.IGNORECASE)
SUFFIXES = {".py", ".js", ".html", ".css", ".md", ".json"}


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


def test_nuc_01_core_has_no_domain_mentions():
    """NUC-01: nenhum arquivo do núcleo menciona o domínio (o lote 36 zerou a lista de transição do lote 34)."""
    assert mentions() == {}, "Uma menção ao domínio entrou no núcleo: o lugar dela é a pasta da especialização."


def test_nuc_02_the_core_reads_the_specialization_only_through_its_attributes(capsys):
    """NUC-02: a skill padrão, os comandos do terminal, as frases do roteador e os resultados vêm dos atributos da
    especialização, lidos quando o núcleo precisa deles, nunca ao importá-lo."""
    import subprocess
    import sys

    from aliado import routing, specializations
    from aliado.cli import main

    code = ("import sys, aliado.cli, aliado.routing, aliado.agent, aliado.interfaces.web.science\n"
            "print(sorted(name for name in sys.modules if name.startswith('aliado.specializations.')))")
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "[]"
    assert specializations.first("DEFAULT_SKILL") == "pesquisa-inversores" and specializations.first("ausente", 7) == 7
    assert callable(specializations.first("results_digest")) and specializations.first("REWRITE_SUBJECT")
    assert routing._about_results("quais falhas do gpvs nao foram detectadas", None)
    assert "pesquisa-inversores" in routing._specialized()["skills"]
    try:
        main(["ciencia", "treinar-gpvs", "--help"])
    except SystemExit as exit_:
        assert exit_.code == 0
    assert "--teto-epocas" in capsys.readouterr().out


def test_nuc_01_specialization_discovery_has_no_names():
    """NUC-01: o núcleo acha as especializações percorrendo a pasta, sem citar nenhuma pelo nome."""
    assert "specializations/__init__.py" not in mentions()
    assert "experiments/__init__.py" not in mentions() and "experiments/pdf.py" not in mentions()
    assert "interfaces/web/experiments.py" not in mentions()
