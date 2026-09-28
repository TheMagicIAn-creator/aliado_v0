"""Lote 16: FMECA com NPR calculado e leitura separada pelas taxas."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

from aliado.science import evaluate_scenario
from aliado.science.fmeca import evaluate_fmeca, export_fmeca, load_table

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "docs" / "pesquisa-inversores" / "fmeca.json"


def scenario(rate: float, basis: str = "operation", hours: float = 4000) -> dict:
    return {"name": f"teste {rate} {basis}", "kind": "exponential", "time_unit": "year",
            "time_base": {"rate_unit": "h", "hours_per_year": hours, "basis": basis},
            "parameters": {"rate": rate}, "times": [0, 1], "sources": ["Sintético."], "assumptions": ["Teste."]}


def table(**changes) -> tuple[dict, dict]:
    base = {
        "nome": "FMECA sintética", "decidida_em": "2026-09-27", "criterio": "Teste.", "fonte_notas": "Sintética.",
        "horizontes_anos": [1, 20], "ressalvas": [],
        "itens": [
            {"id": "a", "nome": "Item A", "item_na_fonte": "A", "S": 5, "O": 6, "D": 2, "cenarios": ["a.json"],
             "ressalvas": []},
            {"id": "b", "nome": "Item B", "item_na_fonte": "B", "S": 2, "O": 3, "D": 9, "cenarios": ["b.json"],
             "ressalvas": []},
        ],
    }
    return base | changes, {"a.json": scenario(1e-6), "b.json": scenario(5e-5)}


def test_npr_is_computed_and_ties_share_the_priority():
    result = evaluate_fmeca(*table())
    assert [(item["id"], item["npr"], item["posicoes"]["npr"]) for item in result["itens"]] == [("a", 60, 1), ("b", 54, 2)]
    data, scenarios = table()
    data["itens"][1] |= {"S": 3, "O": 4, "D": 5}  # 60, empate com A
    assert [item["posicoes"]["npr"] for item in evaluate_fmeca(data, scenarios)["itens"]] == [1, 1]


@pytest.mark.parametrize("change", [{"S": 0}, {"O": 11}, {"D": 2.5}, {"S": True}, {"NPR": 60}])
def test_invalid_notes_and_given_npr_are_refused(change):
    data, scenarios = table()
    data["itens"][0] = data["itens"][0] | change
    with pytest.raises(ValueError):
        evaluate_fmeca(data, scenarios)


def test_rate_reading_matches_the_reliability_service():
    result = evaluate_fmeca(*table())
    reading = next(item for item in result["itens"] if item["id"] == "b")["leitura_pelas_taxas"][0]
    assert reading["mtbf_horas"] == pytest.approx(1 / 5e-5)
    assert reading["mtbf_anos"] == pytest.approx(1 / (5e-5 * 4000))
    assert reading["horizontes"]["20"]["falhas_esperadas"] == pytest.approx(5e-5 * 4000 * 20)
    service = evaluate_scenario(scenario(5e-5))["rows"][1]["failure_probability"]
    assert reading["horizontes"]["1"]["chance_de_falhar"] == pytest.approx(service)
    assert reading["horizontes"]["20"]["chance_de_falhar"] == pytest.approx(-math.expm1(-5e-5 * 4000 * 20))


def test_occurrence_and_rate_are_compared_but_never_merged():
    result = evaluate_fmeca(*table())
    a, b = sorted(result["itens"], key=lambda item: item["id"])
    assert (a["posicoes"], b["posicoes"]) == ({"npr": 1, "ocorrencia": 1, "taxa": 2}, {"npr": 2, "ocorrencia": 2, "taxa": 1})
    assert result["pares_discordantes_O_taxa"] == [{"maior_O": "a", "menor_O": "b", "O": [6, 3], "taxas": [1e-6, 5e-5]}]
    assert (a["S"], a["O"], a["D"], a["npr"]) == (5, 6, 2, 60)  # as notas não mudam com as taxas


def test_items_with_inconsistent_scenarios_are_refused():
    data, scenarios = table()
    data["itens"][0]["cenarios"] = ["a.json", "b.json"]
    with pytest.raises(ValueError, match="taxas diferentes"):
        evaluate_fmeca(data, scenarios)
    weibull = copy.deepcopy(scenarios)
    weibull["a.json"] = {"name": "w", "kind": "weibull", "time_unit": "h", "parameters": {"shape": 2, "scale": 10},
                         "times": [0, 1], "sources": ["s"], "assumptions": ["a"]}
    with pytest.raises(ValueError, match="exponencial"):
        evaluate_fmeca(table()[0], weibull)


def test_decided_fmeca_keeps_cristaldi_scores_and_reads_the_rates_apart():
    result = evaluate_fmeca(*load_table(TABLE))
    assert [(item["id"], item["npr"]) for item in result["itens"]] == [
        ("ccb", 168), ("contatores", 150), ("igbt", 63), ("ventiladores", 48)]
    by_id = {item["id"]: item for item in result["itens"]}
    assert [by_id[i]["posicoes"]["taxa"] for i in ("ccb", "ventiladores", "igbt", "contatores")] == [1, 2, 3, 4]
    assert {(pair["maior_O"], pair["menor_O"]) for pair in result["pares_discordantes_O_taxa"]} == {
        ("contatores", "ccb"), ("contatores", "igbt"), ("contatores", "ventiladores")}
    operation = next(r for r in by_id["ccb"]["leitura_pelas_taxas"] if r["base"] == "operation")
    assert operation["horizontes"]["20"]["falhas_esperadas"] == pytest.approx(63.7e-6 * 4015 * 20)
    assert by_id["ccb"]["item_na_fonte"] == "PCB" and "reconferir" in by_id["ccb"]["ressalvas"][0]
    assert any("tempo de reparo" in text for text in result["limites"])


def test_cli_exports_and_never_overwrites(tmp_path, capsys):
    from aliado.cli import main

    output = tmp_path / "fmeca"
    assert main(["ciencia", "fmeca", "--tabela", str(TABLE), "--saida", str(output)]) == 0
    markdown = (output / "fmeca.md").read_text(encoding="utf-8")
    assert "não são fundidas numa nota única" in markdown and "> 99.9%" in markdown
    assert json.loads((output / "fmeca.json").read_text(encoding="utf-8"))["itens"][0]["npr"] == 168
    assert len((output / "fmeca.csv").read_text(encoding="utf-8").splitlines()) == 1 + 8
    capsys.readouterr()
    assert main(["ciencia", "fmeca", "--tabela", str(TABLE), "--saida", str(output)]) == 2
    assert "já existe" in capsys.readouterr().err
    with pytest.raises(FileExistsError):
        export_fmeca(evaluate_fmeca(*load_table(TABLE)), output)
