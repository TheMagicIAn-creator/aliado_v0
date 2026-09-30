"""Lote 22: skill do mestrado atualizada e fontes da FMECA conferidas nos PDFs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aliado.agent import prepare_request
from aliado.skills.library import load_skill

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs" / "pesquisa-inversores"
# Bloco de M09 a M14 aprovado em 22/09/2026, com finais de linha LF, igual ao do commit 50c4a63.
RULES_SHA256 = "754ba9ad1153ff5fcf2109e9e3edbc04bf5443f99fdf3d76a6b528cc08f7de4f"
STALE = ("nenhuma memória persistente foi ativada", "O acervo está vazio", "nenhum executor científico",
         "a reconferir", "não reconferidas")


def test_approved_rules_are_unchanged_and_the_status_is_current():
    skill = load_skill("pesquisa-inversores")
    text = skill.references[0][1].replace("\r\n", "\n")
    rules = text[text.index("## M09"):text.index("## Aplicação e limites atuais")]
    assert hashlib.sha256(rules.encode("utf-8")).hexdigest() == RULES_SHA256
    context = "\n".join(m["content"] for m in prepare_request("O que falta?", skill_name="pesquisa-inversores").messages)
    assert not any(stale in context for stale in STALE)
    assert "aba Ciência" in context and "27/09/2026" in context and "30/09/2026" in context


def test_skill_asks_for_plain_words_and_records_where_each_rate_is():
    instructions = load_skill("pesquisa-inversores").instructions
    assert "não cite esses códigos" in instructions and "memória do AL-IAdo existe" in instructions
    for where in ("Tab. III, p. 3", "Tab. 1, p. 5", "Tab. 1, p. 6", "Tab. 6, p. 6", "11,4e-6/h"):
        assert where in instructions


def test_fmeca_and_scenarios_cite_the_checked_table_and_page():
    fmeca = json.loads((REFERENCE / "fmeca.json").read_text(encoding="utf-8"))
    assert "Tabela 6, p. 6" in fmeca["fonte_notas"]
    assert "conferid" in fmeca["ressalvas"][0] and "conferido em 30/09/2026" in fmeca["itens"][0]["ressalvas"][0]
    for path in sorted((REFERENCE / "cenarios").glob("*.json")):
        sources = json.loads(path.read_text(encoding="utf-8"))["sources"]
        assert any("Conferido" in source and "30/09/2026" in source for source in sources), path.name
        assert not any("não reconferidas" in source for source in sources), path.name
        assert any("p. 3" in source or "p. 5" in source or "p. 6" in source for source in sources), path.name
