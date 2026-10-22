"""Os resultados da rodada: as visões da aba Ciência (resumo, métricas por falha e painéis dos escores), do lote 23."""

from __future__ import annotations

import json
import math
import re

import pytest
from apoio.avaliacao_sintetica import synthetic

np = pytest.importorskip("numpy")

from aliado.specializations.mestrado.atributos.cache import features_cache  # noqa: E402
from aliado.specializations.mestrado.preparo import preparacao  # noqa: E402
from aliado.specializations.mestrado.resultados import paineis, rodada_atual  # noqa: E402

INTERNAL = re.compile(r"semente|canônic|canonic|M1[0-9]", re.IGNORECASE)
def test_counts_give_the_same_metrics_as_the_window_formulas():
    from aliado.science.deteccao.metricas.por_janela import window_metrics

    negatives, positives = np.array([0.1, 0.2, 0.9, 0.3]), np.array([0.8, 0.95, 0.4, 1.2, 2.0])
    reference = window_metrics(negatives, positives, 0.5)
    counts = paineis.from_counts(reference["vp"], reference["fn"], reference["fp"], reference["vn"])
    for key in paineis.COUNT_METRICS:
        assert counts[key] == pytest.approx(reference[key])


def test_overview_sums_the_reference_training_and_hides_internal_words(tmp_path):
    result = paineis.overview(synthetic(tmp_path))
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
    result = paineis.per_fault(synthetic(tmp_path))["modelos"]["lstm"]
    f1 = result["por_falha"]["F1"]
    assert f1 == pytest.approx({**paineis.from_counts(205, 99, 5, 304), "auc_roc": (0.80 + 0.81) / 2,
                                "auc_pr": (0.90 + 0.89) / 2, "atraso_ms": 1010.0 + 2, "detectados": 1, "ensaios": 2})
    trial = result["por_ensaio"]["F1M"]
    assert trial["vp"] == 103 and trial["faixa"]["sensibilidade"][0] <= trial["sensibilidade"] <= trial["faixa"]["sensibilidade"][1]
    assert trial["detectado_em"] == 2 and trial["treinamentos"] == 2
    assert result["gerais"]["f1"] == {"valor": 0.5, "faixa": [0.1, 0.9]}


def test_missing_evaluation_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="avaliação oficial"):
        paineis.overview(tmp_path)
    synthetic(tmp_path)
    with pytest.raises(FileNotFoundError, match="dados do GPVS"):
        paineis.score_panels(tmp_path, tmp_path / "gpvs")


def test_score_panels_gain_only_the_clear_change():
    panels = {"ensaios": [{"id": name, "modelos": {"denso": {"atraso_ms": 1.0}}} for name in ("F1L", "F4L")]}
    report = {"inicio": {"ensaios": {"F1L": {"classe": "clara", "observado_janela": 433},
                                     "F4L": {"classe": "nenhuma", "observado_janela": None}}},
              "modelos": {"denso": {"referencia": {"ensaios": {"F1L": {"atraso_ms": 40.0}, "F4L": {"atraso_ms": None}}}}}}
    merged = paineis._with_onsets(panels, report)
    first, second = merged["ensaios"]
    assert (first["inicio_observado"], first["modelos"]["denso"]["atraso_mudanca_ms"]) == (433, 40.0)
    assert (second["inicio_observado"], second["modelos"]["denso"]["atraso_mudanca_ms"]) == (None, None)
    assert "inicio_observado" not in panels["ensaios"][0] and paineis._with_onsets(panels, None) is panels


def test_real_views_repeat_the_official_evaluation(official_results):
    report = json.loads((official_results / rodada_atual.EVALUATION / "relatorio.json").read_text(encoding="utf-8"))
    overview = paineis.overview(official_results)
    for kind in paineis.MODELS:
        reference = report["modelos"][kind]["referencia"]
        assert overview["modelos"][kind]["detectados"] == reference["resumo"]["detectados"]
        assert overview["modelos"][kind]["teste_saudavel"]["alarmes_por_hora"] == reference["falsos_alarmes"]["teste_saudavel"]["alarmes_por_hora"]
        total = overview["modelos"][kind]["matrizes"]["total"]
        assert total["fp"] + total["vn"] == reference["falsos_alarmes"]["pre_falha"]["janelas"]
        for name, trial in reference["ensaios"].items():
            assert overview["modelos"][kind]["matrizes"]["por_ensaio"][name] == {k: trial[k] for k in ("vp", "fn", "fp", "vn")}
            again = paineis.from_counts(trial["vp"], trial["fn"], trial["fp"], trial["vn"])
            assert all(math.isclose(again[k], trial[k]) for k in paineis.COUNT_METRICS if trial[k] is not None)


def test_real_panels_match_the_scores_and_the_official_alarms(official_results, base_real):
    from aliado.specializations.mestrado.preparo.inicio_nominal import nominal_onset

    panels = paineis.score_panels(official_results, base_real)
    report = json.loads((official_results / rodada_atual.EVALUATION / "relatorio.json").read_text(encoding="utf-8"))
    seed, k = report["semente_referencia"], report["top_k"]
    config = json.loads((official_results / "gpvs-modelos-002" / "configuracao.json").read_text(encoding="utf-8"))["configuracao"]
    prepared = preparacao.prepare(base_real, cache=features_cache(base_real), purge=config["purge"],
                            fractions=tuple(config["fractions"]))
    with np.load(official_results / rodada_atual.EVALUATION / "escores.npz") as scores:
        for panel in panels["ensaios"]:
            assert panel["inicio"] == nominal_onset(prepared.faults[panel["id"]])
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
