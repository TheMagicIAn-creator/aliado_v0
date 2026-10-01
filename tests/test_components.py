"""Lote 25: confiabilidade por componente e disponibilidade dos 4 grupos da FMECA (sem rede)."""

from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

import pytest

from aliado.science.components import component_view, load_repairs, validate_repairs
from aliado.science.fmeca import evaluate_fmeca, load_table
from aliado.science.ram import evaluate_scenario

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs" / "pesquisa-inversores"
INTERNAL = re.compile(r"semente|canônic|canonic|M1[0-9]", re.IGNORECASE)


@pytest.fixture(scope="module")
def view():
    return component_view(*load_table(REFERENCE / "fmeca.json"), load_repairs(REFERENCE / "reparos.json"))


def _group(view, gid):
    return next(g for g in view["grupos"] if g["id"] == gid)


def test_one_block_per_fmeca_group_with_both_time_bases(view):
    assert [g["id"] for g in view["grupos"]] == ["ccb", "contatores", "igbt", "ventiladores"]
    for group in view["grupos"]:
        assert set(group["bases"]) == {"operation", "calendar"}
        curve = group["bases"]["operation"]["curva"]
        assert curve[0] == {"t": 0.0, "r": 1.0, "f": 0.0} and curve[-1]["t"] == view["horizonte_anos"] == 20
    assert [r["id"] for r in view["reparo"]] == ["ieee493", "baschel"]


def test_igbt_numbers_follow_the_rate_and_the_hours_per_year(view):
    igbt = _group(view, "igbt")["bases"]
    operation, calendar = igbt["operation"], igbt["calendar"]
    assert operation["taxa_por_ano"] == pytest.approx(8.9e-6 * 4015)
    assert operation["f_horizonte"] == pytest.approx(-math.expm1(-8.9e-6 * 4015 * 20))
    assert operation["f_horizonte"] == pytest.approx(0.511, abs=1e-3)
    assert calendar["f_horizonte"] == pytest.approx(0.790, abs=1e-3)
    assert operation["mtbf_anos"] == pytest.approx(1 / (8.9e-6 * 4015))
    assert operation["falhas_no_horizonte"] == pytest.approx(8.9e-6 * 4015 * 20)
    ieee, baschel = operation["disponibilidade"]["ieee493"], operation["disponibilidade"]["baschel"]
    assert (ieee["parada_horas"], baschel["parada_horas"]) == (26, 144)
    assert ieee["horas_paradas_por_ano"] == pytest.approx(8.9e-6 * 4015 * 26)  # cerca de 0,93 h
    assert ieee["mtbf_calendario_horas"] == pytest.approx(8760 / (8.9e-6 * 4015))


def test_availability_is_the_one_of_the_ram_service(view):
    ccb = _group(view, "ccb")["bases"]["operation"]
    for scenario, downtime in (("ieee493", 26), ("baschel", 144)):
        item = ccb["disponibilidade"][scenario]
        expected = evaluate_scenario({"name": "x", "kind": "availability_inherent", "time_unit": "h",
                                      "parameters": {"mtbf": 8760 / (6.37e-5 * 4015), "mttr": downtime},
                                      "sources": ["x"], "assumptions": ["x"]})["summary"]["availability_inherent"]
        assert item["disponibilidade"] == pytest.approx(expected)
        assert 1 - item["disponibilidade"] == pytest.approx(item["horas_paradas_por_ano"] / (8760 + item["horas_paradas_por_ano"]))
    assert ccb["disponibilidade"]["ieee493"]["horas_paradas_por_ano"] == pytest.approx(6.65, abs=0.01)
    assert ccb["disponibilidade"]["baschel"]["horas_paradas_por_ano"] == pytest.approx(36.8, abs=0.1)


def test_invalid_repair_tables_are_refused():
    repairs = load_repairs(REFERENCE / "reparos.json")
    groups = ["ccb", "contatores", "igbt", "ventiladores"]
    assert validate_repairs(copy.deepcopy(repairs), groups)
    broken = []
    missing = copy.deepcopy(repairs)
    del missing["cenarios"][0]["reparo_horas"]["igbt"]
    broken.append(missing)
    negative = copy.deepcopy(repairs)
    negative["cenarios"][1]["reparo_horas"]["ccb"] = -5
    broken.append(negative)
    no_source = copy.deepcopy(repairs)
    no_source["cenarios"][0]["fontes"] = []
    broken.append(no_source)
    other_groups = copy.deepcopy(repairs)
    other_groups["grupos"] = groups[:3]
    broken.append(other_groups)
    twice = copy.deepcopy(repairs)
    twice["cenarios"][1]["id"] = "ieee493"
    broken.append(twice)
    for item in broken:
        with pytest.raises(ValueError):
            validate_repairs(item, groups)


def test_sources_are_cited_with_table_and_page():
    repairs = load_repairs(REFERENCE / "reparos.json")
    ieee, baschel = repairs["cenarios"]
    assert "Tabela 10-4" in ieee["fontes"][0] and "p. 290" in ieee["fontes"][0] and set(ieee["reparo_horas"].values()) == {26}
    assert "Figura 7" in baschel["fontes"][0] and baschel["deteccao_horas"] == 24 and set(baschel["reparo_horas"].values()) == {120}


def test_fmeca_points_to_the_availability_and_the_skill_says_so():
    limits = " ".join(evaluate_fmeca(*load_table(REFERENCE / "fmeca.json"))["limites"])
    assert "Disponibilidade não calculada" not in limits and "IEEE 493" in limits and "reparos.json" not in limits
    skill = (ROOT / "src" / "aliado" / "skills" / "builtin" / "pesquisa-inversores" / "SKILL.md").read_text(encoding="utf-8")
    assert 'version: "0.2.1"' in skill and "26 h" in skill and "Não há disponibilidade calculada" not in skill


@pytest.fixture
def client(tmp_path):
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    from aliado.interfaces.web.app import WebSettings, create_app

    def make(reference):
        settings = WebSettings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765,
                               stream=lambda *a, **k: iter(()), models=[{"alias": "flash", "model_id": "x"}],
                               library_factory=lambda: None, results_dir=tmp_path / "resultados",
                               gpvs_dir=tmp_path / "gpvs", reference_dir=reference)
        return TestClient(create_app(settings), base_url="http://127.0.0.1:8765")
    return make


def test_route_serves_the_view_and_explains_what_is_missing(client, tmp_path):
    data = client(REFERENCE).get("/api/ciencia/componentes")
    assert data.status_code == 200 and len(data.json()["grupos"]) == 4
    assert not INTERNAL.search(json.dumps(data.json(), ensure_ascii=False))
    partial = tmp_path / "referencia"
    partial.mkdir()
    (partial / "fmeca.json").write_text((REFERENCE / "fmeca.json").read_text(encoding="utf-8"), encoding="utf-8")
    missing = client(partial).get("/api/ciencia/componentes")
    assert missing.status_code == 404 and "reparos.json" in missing.json()["erro"]
