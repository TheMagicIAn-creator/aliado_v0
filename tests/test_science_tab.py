"""Lote 20: aba Ciência — exploradores, confiabilidade, FMECA e resultados, sem rede."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from aliado.science import evaluate_scenario, export_result
from aliado.science.explorer import EXPLORATION_SOURCE, Explorer, plain, reliability
from aliado.science.fmeca import evaluate_fmeca, export_fmeca, load_table

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs" / "pesquisa-inversores"
RESULTS = ROOT / "data" / "resultados"
GPVS = ROOT / "data" / "gpvs"
REAL = (RESULTS / "gpvs-avaliacao-001" / "relatorio.json").is_file() and (GPVS / "proveniencia.json").is_file()


def test_plain_converts_numpy_for_json():
    np = pytest.importorskip("numpy")
    data = plain({"a": np.int64(3), "b": np.float32(0.5), "c": np.array([1, 2]), "d": (np.bool_(True),)})
    assert data == {"a": 3, "b": 0.5, "c": [1, 2], "d": [True]}
    assert json.dumps(data)


def test_explorer_reports_what_is_missing_without_loading_models(tmp_path):
    explorer = Explorer(tmp_path / "resultados", tmp_path / "gpvs", tmp_path / "cache")
    status = explorer.status()
    assert not status["disponivel"] and not status["pronto"] and len(status["faltando"]) == 2
    with pytest.raises(ValueError, match="Prepare"):
        explorer.threshold("denso", 42, 5, 99)
    with pytest.raises(ValueError, match="indisponíveis"):
        explorer.prepare()


def test_reliability_explorer_matches_the_saved_igbt_scenario():
    scenario = json.loads((REFERENCE / "cenarios" / "igbt-operacao.json").read_text(encoding="utf-8"))
    expected = {row["time"]: row for row in evaluate_scenario(scenario)["rows"]}
    rows = {row["time"]: row for row in reliability(8.9e-6, 4015, "operation", 20)["rows"]}
    for year in (1.0, 5.0, 10.0, 20.0):
        assert rows[year]["failure_probability"] == expected[year]["failure_probability"]
    assert reliability(8.9e-6, 8760, "calendar", 0.5)["rows"][-1]["time"] == 0.5
    with pytest.raises(ValueError):
        reliability(8.9e-6, 4015, "operation", 0)
    with pytest.raises(ValueError):
        reliability(8.9e-6, 9000, "operation", 20)


@pytest.mark.skipif(not REAL, reason="Sem os resultados canônicos e os dados do GPVS neste computador.")
def test_explorers_reproduce_the_canonical_evaluation_exactly(tmp_path):
    explorer = Explorer(RESULTS, GPVS, tmp_path / "cache")
    explorer.prepare()
    report = json.loads((RESULTS / "gpvs-avaliacao-001" / "relatorio.json").read_text(encoding="utf-8"))
    with (RESULTS / "gpvs-avaliacao-001" / "metricas_por_ensaio.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for kind in ("denso", "lstm"):
        for seed in (13, 29, 42, 71, 101):
            threshold = explorer.threshold(kind, seed, 5, 99.0)
            alarms = explorer.alarms(kind, seed, 5, 99.0, 3, trial="F1L")
            run = report["modelos"][kind]["sementes"][str(seed)]
            assert threshold["limiar"]["limiar"] == threshold["canonico"]["limiar"]
            assert alarms["parametros_canonicos"]
            shared = set(alarms["resumo"]) & set(run["resumo"])
            assert {"detectados", "atraso_mediano_ms", "sensibilidade_media"} <= shared
            assert all(alarms["resumo"][key] == run["resumo"][key] for key in shared)
            assert alarms["falsos_alarmes"]["teste_saudavel"]["alarmes"] == run["alarmes_teste_saudavel"]
            assert alarms["falsos_alarmes"]["pre_falha"]["alarmes"] == run["alarmes_pre_falha"]
            canonical = {row["ensaio"]: row for row in rows if row["modelo"] == kind and int(row["semente"]) == seed}
            for trial in alarms["ensaios"]:
                row = canonical[trial["ensaio"]]
                assert str(trial["detectado"]) == row["detectado"]
                assert trial["atraso_ms"] == (float(row["atraso_ms"]) if row["atraso_ms"] else None)
    # As grades de sensibilidade relatadas (m e k, semente de referência) também se repetem.
    seed = report["semente_referencia"]
    for grid, values in report["sensibilidade"].items():
        for value, by_model in values.items():
            for kind, expected in by_model.items():
                k, m = (int(value), 3) if grid == "k" else (5, int(value))
                got = explorer.alarms(kind, seed, k, 99.0, m)
                assert got["resumo"]["detectados"] == expected["detectados"]
                assert got["resumo"]["atraso_mediano_ms"] == expected["atraso_mediano_ms"]
                assert got["falsos_alarmes"]["teste_saudavel"]["alarmes"] == expected["alarmes_teste_saudavel"]
                assert got["falsos_alarmes"]["pre_falha"]["alarmes"] == expected["alarmes_pre_falha"]
    # O cache é reaproveitado e outro k muda o limiar sem tocar nos resultados congelados.
    again = Explorer(RESULTS, GPVS, tmp_path / "cache")
    again.prepare()
    other = again.threshold("denso", 42, 10, 99.0)
    assert other["limiar"]["limiar"] != other["canonico"]["limiar"]
    assert not again.alarms("denso", 42, 10, 99.0, 3)["parametros_canonicos"]
    assert len(list((tmp_path / "cache").glob("erros-*.npz"))) == 1
    with pytest.raises(ValueError):
        again.threshold("denso", 42, 25, 99.0)
    with pytest.raises(ValueError):
        again.alarms("denso", 42, 5, 99.0, 11)


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
                           gpvs_dir=tmp_path / "gpvs", reference_dir=REFERENCE)
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8765") as test_client:
        yield test_client, settings


HEADERS = {"x-aliado": "1"}


def test_science_state_and_results(client):
    client, settings = client
    state = client.get("/api/ciencia").json()
    assert state["fmeca"] and state["cenarios"] and not state["gpvs"]["disponivel"]
    items = {item["id"]: item for item in client.get("/api/ciencia/resultados").json()}
    assert set(items) == {"fmeca-001", "lote-07/igbt-operacao"}
    detail = client.get("/api/ciencia/resultados/lote-07/igbt-operacao").json()
    assert detail["tipo"] == "cenario" and detail["curvas"]["linhas"][0]["reliability"] == 1.0 and "<" in detail["html"]
    assert client.get("/api/ciencia/resultados/fmeca-001").json()["fmeca"]["itens"]
    assert client.get("/api/ciencia/resultados/../dados").status_code == 404
    assert client.get("/api/ciencia/resultados/nada").status_code == 404
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
