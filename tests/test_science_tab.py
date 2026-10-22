"""Lote 20: a aba Ciência do núcleo — estado, confiabilidade, cenários, FMECA e a página, sem rede. Os exploradores
do GPVS ficam em `tests/mestrado/test_exploradores.py`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aliado.science.confiabilidade.artefatos import export_result
from aliado.science.confiabilidade.cenarios import EXPLORATION_SOURCE, evaluate_scenario
from aliado.science.fmeca.artefatos import export_fmeca
from aliado.science.fmeca.calculo import evaluate_fmeca
from aliado.science.fmeca.tabela import load_table

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs" / "pesquisa-inversores"


def _results(tmp_path) -> Path:
    results = tmp_path / "resultados"
    scenario = json.loads((REFERENCE / "cenarios" / "igbt-operacao.json").read_text(encoding="utf-8"))
    export_result(evaluate_scenario(scenario), results / "lote-07" / "igbt-operacao")
    export_fmeca(evaluate_fmeca(*load_table(REFERENCE / "fmeca.json")), results / "fmeca-001")
    return results


@pytest.fixture
def client(tmp_path):
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    from aliado.interfaces.web.app import WebSettings, create_app
    from aliado.llm.contracts import LLMResult

    def stream(question, **kwargs):
        yield "final", LLMResult("ok", "google", "lite", "critical_reasoning")

    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765, stream=stream,
                           models=[], library_factory=lambda: None, results_dir=_results(tmp_path),
                           dataset_dir=tmp_path / "gpvs", reference_dir=REFERENCE)
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8765") as test_client:
        yield test_client, settings


HEADERS = {"x-aliado": "1"}


def test_science_state_and_no_results_listing(client):
    """EXP-04: a aba mostra só a rodada atual; as pastas de resultados não são listadas."""
    client, settings = client
    state = client.get("/api/ciencia").json()
    assert state["fmeca"] and state["cenarios"] and not state["exploradores"]["disponivel"]
    assert state["rodada"] == "avaliacao-oficial"
    from aliado.specializations.mestrado.notes import NOTES

    assert state["notas"] == NOTES  # NUC-02: o glossário da aba vem da especialização
    assert client.get("/api/ciencia/resultados").status_code == 404
    assert client.get("/api/ciencia/resultados/fmeca-001").status_code == 404
    assert (settings.results_dir / "fmeca-001" / "fmeca.json").is_file()  # as pastas continuam no disco
    assert client.post("/api/ciencia/limiar", headers=HEADERS,
                       json={"modelo": "denso", "semente": 42, "k": 5, "percentil": 99}).status_code == 400


def test_reliability_and_scenarios_are_saved_only_with_sources(client):
    client, settings = client
    curve = client.post("/api/ciencia/confiabilidade", headers=HEADERS,
                        json={"taxa": 8.9e-6, "horas_por_ano": 4015, "base": "operation", "horizonte": 20}).json()
    assert curve["sources"] == [EXPLORATION_SOURCE] and curve["rows"][-1]["time"] == 20
    assert client.post("/api/ciencia/confiabilidade", json={"taxa": 1}).status_code == 403
    assert client.post("/api/ciencia/confiabilidade", headers=HEADERS, json={"taxa": 1}).status_code == 400
    presets = client.get("/api/ciencia/cenarios").json()
    assert len(presets) == 8
    scenario = presets[0]["cenario"]
    ran = client.post("/api/ciencia/cenarios/rodar", headers=HEADERS, json={"cenario": scenario}).json()
    assert ran["name"] == scenario["name"]
    for bad in ({**scenario, "sources": []}, {**scenario, "sources": [EXPLORATION_SOURCE]}, {**scenario, "assumptions": []}):
        response = client.post("/api/ciencia/cenarios/salvar", headers=HEADERS, json={"cenario": bad})
        assert response.status_code == 400 and "fonte" in response.json()["erro"]
    first = client.post("/api/ciencia/cenarios/salvar", headers=HEADERS, json={"cenario": scenario}).json()["pasta"]
    second = client.post("/api/ciencia/cenarios/salvar", headers=HEADERS, json={"cenario": scenario}).json()["pasta"]
    assert first != second and first.startswith("cenario-")
    assert (settings.results_dir / first / "resultado.json").is_file()
    invalid = client.post("/api/ciencia/cenarios/rodar", headers=HEADERS, json={"cenario": {"kind": "nada"}})
    assert invalid.status_code == 400


def test_fmeca_is_shown_and_saved_in_a_new_folder(client):
    client, settings = client
    data = client.get("/api/ciencia/fmeca").json()
    assert [item["posicoes"]["npr"] for item in data["itens"]] == [1, 2, 3, 4]
    saved = client.post("/api/ciencia/fmeca", headers=HEADERS).json()["pasta"]
    assert saved.startswith("fmeca-") and (settings.results_dir / saved / "fmeca.md").is_file()
    assert (settings.results_dir / "fmeca-001" / "fmeca.json").is_file()


def test_page_has_the_science_tab():
    html = (ROOT / "src" / "aliado" / "interfaces" / "web" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="nav-science"' in html and 'id="science-view"' in html and "/static/ciencia.js" in html
    assert "is-soon" not in html


def test_page_loads_d3_and_the_charts_before_the_science_tab():
    page = (ROOT / "src" / "aliado" / "interfaces" / "web" / "static" / "index.html").read_text(encoding="utf-8")
    order = [page.index(name) for name in ("vendor/d3/d3.min.js", "graficos.js", "ciencia.js")]
    assert order == sorted(order)
    d3 = ROOT / "src" / "aliado" / "interfaces" / "web" / "static" / "vendor" / "d3"
    assert (d3 / "d3.min.js").read_text(encoding="utf-8").startswith("// https://d3js.org v7.9.0")
    assert "Mike Bostock" in (d3 / "LICENSE").read_text(encoding="utf-8")
