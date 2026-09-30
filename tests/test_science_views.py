"""Lote 23: visões dos resultados oficiais do GPVS na aba Ciência (resumo, métricas e escores)."""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

from aliado.science.detection import gpvs, summary  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS, GPVS = ROOT / "data" / "resultados", ROOT / "data" / "gpvs"
REAL = (RESULTS / summary.EVALUATION / "escores.npz").is_file() and (GPVS / "proveniencia.json").is_file()
INTERNAL = re.compile(r"semente|canônic|canonic|M1[0-9]", re.IGNORECASE)
FIELDS = ["modelo", "semente", "ensaio", "detectado", "atraso_ms", "atraso_janelas", "alarmes_pre_falha",
          "janelas_pre_falha", "sensibilidade", "especificidade", "precisao", "f1", "acuracia_balanceada", "mcc",
          "auc_roc", "auc_pr", "vp", "fn", "fp", "vn"]


def synthetic(root: Path) -> Path:
    """Uma avaliação sintética com 2 modelos, 2 treinamentos (sementes 1 e 2) e os 14 ensaios."""
    folder = root / summary.EVALUATION
    folder.mkdir(parents=True)
    rows = []
    for kind in ("denso", "lstm"):
        for seed in (1, 2):
            for index, name in enumerate(gpvs.FAULTY):
                vp, fn, fp, vn = 100 + index + seed, 50 - index, index % 3 + seed, 150 + seed
                metrics = summary.from_counts(vp, fn, fp, vn)
                detected = index % 4 != 0
                rows.append({"modelo": kind, "semente": seed, "ensaio": name, "detectado": str(detected),
                             "atraso_ms": 1000.0 + 10 * index + seed if detected else "", "atraso_janelas": 50,
                             "alarmes_pre_falha": index % 2, "janelas_pre_falha": 160,
                             **{k: metrics[k] for k in summary.COUNT_METRICS},
                             "auc_roc": 0.8 + index / 100, "auc_pr": 0.9 - index / 100, "vp": vp, "fn": fn, "fp": fp, "vn": vn})
    with (folder / "metricas_por_ensaio.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    spread = {f"{k}_media": [0.1, 0.9] for k in summary.METRICS} | {"detectados": [9, 10], "atraso_mediano_ms": [900.0, 1100.0],
                                                                     "alarmes_teste_saudavel": [0, 1], "alarmes_pre_falha": [3, 7]}
    model = lambda name: {  # noqa: E731
        "nome": name, "limiar": 2.0, "faixa_sementes": spread, "sementes": {},
        "referencia": {"resumo": {"detectados": 10, "atraso_mediano_ms": 1000.0, **{f"{k}_media": 0.5 for k in summary.METRICS}},
                       "falsos_alarmes": {"teste_saudavel": {"janelas": 263, "janelas_acima": 2, "alarmes": 0, "duracao_s": 5.26,
                                                             "alarmes_por_hora": 0.0, "limite_superior_por_hora": 2050.3,
                                                             "fracao_janelas_acima": 2 / 263,
                                                             "fracao_janelas_acima_ic95": [0.0, 0.019]},
                                          "pre_falha": {"janelas": 2348, "janelas_acima": 55, "alarmes": 7, "duracao_s": 46.96,
                                                        "fracao_janelas_acima": 55 / 2348,
                                                        "fracao_janelas_acima_ic95": [0.018, 0.027]},
                                          "combinado": {"alarmes": 7, "duracao_s": 52.22,
                                                        "limite_superior_por_hora": 950.0}}}}
    report = {"semente_referencia": 2, "top_k": 5, "confirmacao": 3,
              "modelos": {"denso": model("Autoencoder Denso"), "lstm": model("AE-LSTM")},
              "comparacao": [{"objetivo": "Detecta mais falhas", "metrica": "sensibilidade", "maior_e_melhor": True, "media": 0.02,
                              "ic95": [-0.01, 0.04], "n": 14, "mesmo_sinal_sementes": 5, "sementes": 5,
                              "leitura": "sem diferença clara"}]}
    (folder / "relatorio.json").write_text(json.dumps(report), encoding="utf-8")
    (folder / "configuracao.json").write_text(json.dumps({"executado_em": "2026-09-27", "treino": {"pasta": "gpvs-modelos-002"}}),
                                              encoding="utf-8")
    return root


def test_counts_give_the_same_metrics_as_the_window_formulas():
    from aliado.science.detection.metrics import window_metrics

    negatives, positives = np.array([0.1, 0.2, 0.9, 0.3]), np.array([0.8, 0.95, 0.4, 1.2, 2.0])
    reference = window_metrics(negatives, positives, 0.5)
    counts = summary.from_counts(reference["vp"], reference["fn"], reference["fp"], reference["vn"])
    for key in summary.COUNT_METRICS:
        assert counts[key] == pytest.approx(reference[key])


def test_overview_sums_the_reference_training_and_hides_internal_words(tmp_path):
    result = summary.overview(synthetic(tmp_path))
    denso = result["modelos"]["denso"]
    assert denso["detectados"] == 10 and denso["ensaios"] == 14
    expected = {"vp": sum(100 + i + 2 for i in range(14)), "fn": sum(50 - i for i in range(14)),
                "fp": sum(i % 3 + 2 for i in range(14)), "vn": 14 * 152}
    assert denso["matrizes"]["total"] == expected  # só o treino de referência (semente 2)
    assert denso["matrizes"]["por_falha"]["F1"] == {"vp": 102 + 103, "fn": 50 + 49, "fp": 2 + 3, "vn": 304}
    assert denso["matrizes"]["por_ensaio"]["F7M"]["vp"] == 100 + 13 + 2
    assert denso["faixa"]["sensibilidade"] == [0.1, 0.9] and denso["teste_saudavel"]["limite_superior_por_hora"] == 2050.3
    assert result["comparacao"][0]["metrica"] == "Sensibilidade" and "sementes" not in result["comparacao"][0]
    assert not INTERNAL.search(json.dumps(result, ensure_ascii=False).replace("gpvs-modelos-002", ""))


def test_per_fault_recomputes_from_summed_counts_and_keeps_the_spread(tmp_path):
    result = summary.per_fault(synthetic(tmp_path))["modelos"]["lstm"]
    f1 = result["por_falha"]["F1"]
    assert f1 == pytest.approx({**summary.from_counts(205, 99, 5, 304), "auc_roc": (0.80 + 0.81) / 2,
                                "auc_pr": (0.90 + 0.89) / 2, "atraso_ms": 1010.0 + 2, "detectados": 1, "ensaios": 2})
    trial = result["por_ensaio"]["F1M"]
    assert trial["vp"] == 103 and trial["faixa"]["sensibilidade"][0] <= trial["sensibilidade"] <= trial["faixa"]["sensibilidade"][1]
    assert trial["detectado_em"] == 2 and trial["treinamentos"] == 2
    assert result["gerais"]["f1"] == {"valor": 0.5, "faixa": [0.1, 0.9]}


def test_missing_evaluation_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="avaliação oficial"):
        summary.overview(tmp_path)
    synthetic(tmp_path)
    with pytest.raises(FileNotFoundError, match="dados do GPVS"):
        summary.score_panels(tmp_path, tmp_path / "gpvs")


@pytest.fixture
def client(tmp_path):
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    from aliado.interfaces.web.app import WebSettings, create_app

    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765,
                           stream=lambda *a, **k: iter(()), models=[{"alias": "flash", "model_id": "x"}],
                           library_factory=lambda: None, results_dir=synthetic(tmp_path / "resultados"),
                           gpvs_dir=tmp_path / "gpvs")
    return TestClient(create_app(settings), base_url="http://127.0.0.1:8765")


def test_routes_serve_the_views_and_explain_what_is_missing(client):
    overview = client.get("/api/ciencia/resumo")
    assert overview.status_code == 200 and overview.json()["modelos"]["lstm"]["nome"] == "AE-LSTM"
    assert client.get("/api/ciencia/metricas").json()["falhas"][0]["nome"] == "Falha em IGBT"
    missing = client.get("/api/ciencia/escores")
    assert missing.status_code == 404 and "dados do GPVS" in missing.json()["erro"]
    # Lote 24: sem a reanálise, a seção do início das falhas diz o que falta, e o Resumo segue sem a estimativa.
    onsets = client.get("/api/ciencia/inicio")
    assert onsets.status_code == 404 and "reanálise" in onsets.json()["erro"]
    denso = overview.json()["modelos"]["denso"]
    assert denso["alarmes_estimados"] is None and denso["limiar_faixa"] is None
    assert denso["saudavel"]["janelas"] == 263 + 2348 and denso["saudavel"]["alarmes"] == 7
    assert denso["saudavel"]["alarmes_por_hora"] == pytest.approx(7 / 52.22 * 3600)


def test_score_panels_gain_only_the_clear_change():
    panels = {"ensaios": [{"id": name, "modelos": {"denso": {"atraso_ms": 1.0}}} for name in ("F1L", "F4L")]}
    report = {"inicio": {"ensaios": {"F1L": {"classe": "clara", "observado_janela": 433},
                                     "F4L": {"classe": "nenhuma", "observado_janela": None}}},
              "modelos": {"denso": {"referencia": {"ensaios": {"F1L": {"atraso_ms": 40.0}, "F4L": {"atraso_ms": None}}}}}}
    merged = summary._with_onsets(panels, report)
    first, second = merged["ensaios"]
    assert (first["inicio_observado"], first["modelos"]["denso"]["atraso_mudanca_ms"]) == (433, 40.0)
    assert (second["inicio_observado"], second["modelos"]["denso"]["atraso_mudanca_ms"]) == (None, None)
    assert "inicio_observado" not in panels["ensaios"][0] and summary._with_onsets(panels, None) is panels


def test_page_loads_d3_and_the_charts_before_the_science_tab():
    page = (ROOT / "src" / "aliado" / "interfaces" / "web" / "static" / "index.html").read_text(encoding="utf-8")
    order = [page.index(name) for name in ("vendor/d3/d3.min.js", "graficos.js", "ciencia.js")]
    assert order == sorted(order)
    d3 = ROOT / "src" / "aliado" / "interfaces" / "web" / "static" / "vendor" / "d3"
    assert (d3 / "d3.min.js").read_text(encoding="utf-8").startswith("// https://d3js.org v7.9.0")
    assert "Mike Bostock" in (d3 / "LICENSE").read_text(encoding="utf-8")


@pytest.mark.skipif(not REAL, reason="Sem a avaliação oficial e os dados do GPVS neste computador.")
def test_real_views_repeat_the_official_evaluation():
    report = json.loads((RESULTS / summary.EVALUATION / "relatorio.json").read_text(encoding="utf-8"))
    overview = summary.overview(RESULTS)
    for kind in summary.MODELS:
        reference = report["modelos"][kind]["referencia"]
        assert overview["modelos"][kind]["detectados"] == reference["resumo"]["detectados"]
        assert overview["modelos"][kind]["teste_saudavel"]["alarmes_por_hora"] == reference["falsos_alarmes"]["teste_saudavel"]["alarmes_por_hora"]
        total = overview["modelos"][kind]["matrizes"]["total"]
        assert total["fp"] + total["vn"] == reference["falsos_alarmes"]["pre_falha"]["janelas"]
        for name, trial in reference["ensaios"].items():
            assert overview["modelos"][kind]["matrizes"]["por_ensaio"][name] == {k: trial[k] for k in ("vp", "fn", "fp", "vn")}
            again = summary.from_counts(trial["vp"], trial["fn"], trial["fp"], trial["vn"])
            assert all(math.isclose(again[k], trial[k]) for k in summary.COUNT_METRICS if trial[k] is not None)


@pytest.mark.skipif(not REAL, reason="Sem a avaliação oficial e os dados do GPVS neste computador.")
def test_real_panels_match_the_scores_and_the_official_alarms():
    from aliado.science.detection.evaluation import _onset

    panels = summary.score_panels(RESULTS, GPVS)
    report = json.loads((RESULTS / summary.EVALUATION / "relatorio.json").read_text(encoding="utf-8"))
    seed, k = report["semente_referencia"], report["top_k"]
    config = json.loads((RESULTS / "gpvs-modelos-002" / "configuracao.json").read_text(encoding="utf-8"))["configuracao"]
    prepared = gpvs.prepare(GPVS, cache=GPVS / "processado" / "variaveis.npz", purge=config["purge"],
                            fractions=tuple(config["fractions"]))
    with np.load(RESULTS / summary.EVALUATION / "escores.npz") as scores:
        for panel in panels["ensaios"]:
            assert panel["inicio"] == _onset(prepared.faults[panel["id"]])
            for kind, model in panel["modelos"].items():
                values = scores[f"{kind}_s{seed}_k{k}_{panel['id']}"]
                assert len(model["razao"]) == len(values) == panel["janelas"]
                limiar = report["modelos"][kind]["limiar"]
                assert model["razao"][10] == pytest.approx(values[10] / limiar, rel=1e-4)
                official = report["modelos"][kind]["referencia"]["ensaios"][panel["id"]]
                assert len(model["alarmes_antes"]) == official["alarmes_pre_falha"]
                assert (model["alarme_deteccao"] is not None) == official["detectado"]
                if official["detectado"]:
                    assert model["alarme_deteccao"] - panel["inicio"] + 1 == official["atraso_janelas"]
