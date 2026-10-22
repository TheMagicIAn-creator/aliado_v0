"""Specs vivas (lote 34): cada requisito numerado é citado por pelo menos um teste, e só os que existem."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVING = ROOT / "docs" / "specs" / "capacidades"
REQUIREMENT = re.compile(r"^\*\*([A-Z]{3}-\d{2})\.", re.MULTILINE)


def requirements() -> dict[str, str]:
    found = {}
    for path in sorted(LIVING.glob("*.md")):
        for requirement in REQUIREMENT.findall(path.read_text(encoding="utf-8")):
            assert requirement not in found, f"{requirement} aparece em {found.get(requirement)} e em {path.name}"
            found[requirement] = path.name
    return found


def _tests() -> str:
    # Lote 49: os testes da ciência e do mestrado ficam em subpastas; todas contam.
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "tests").rglob("test_*.py"))
                     if path != Path(__file__).resolve())


def test_every_living_requirement_is_cited_by_a_test():
    known = requirements()
    assert known, "Nenhuma spec viva em docs/specs/capacidades."
    text = _tests()
    assert not sorted(item for item in known if item not in text), "Requisitos sem teste."


def test_tests_cite_only_requirements_that_exist():
    known = requirements()
    prefixes = {item[:3] for item in known}
    cited = {item for item in re.findall(r"\b([A-Z]{3}-\d{2})\b", _tests()) if item[:3] in prefixes}
    assert cited <= set(known), f"Testes citam requisitos que não existem: {sorted(cited - set(known))}"
