"""Lote 24: reanálise dos escores gravados com o início observado; repete a oficial com o início nominal."""

from __future__ import annotations

import json
import re

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from aliado.science.deteccao.registro import consultas as registry  # noqa: E402
from aliado.specializations.mestrado import reanalysis, summary  # noqa: E402
from aliado.specializations.mestrado.atributos.cache import features_cache  # noqa: E402
from aliado.specializations.mestrado.base import ensaios  # noqa: E402
from aliado.specializations.mestrado.evaluation import (  # noqa: E402
    load_thresholds,
    load_training,
    run_metrics,
    score_all,
    summarize,
)
from aliado.specializations.mestrado.preparo import preparacao  # noqa: E402


def test_thresholds_load_without_the_weights(rodada_sintetica):
    results = rodada_sintetica.resultados
    light, summary = load_thresholds(results / "gpvs-modelos-002")
    full = load_training(results / "gpvs-modelos-002")
    assert light.thresholds == full.thresholds and light.models == {} and set(full.models) == {
        ("denso", 3), ("denso", 4), ("lstm", 3), ("lstm", 4)}
    assert summary["configuracao_sha256"] == full.frozen["sha256"]


def test_stored_scores_are_the_ones_of_the_evaluation(rodada_sintetica):
    data, results = rodada_sintetica.preparado, rodada_sintetica.resultados
    trained, _ = load_thresholds(results / "gpvs-modelos-002")
    stored = reanalysis.load_scores(results / reanalysis.EVALUATION / "escores.npz", trained)
    fresh = score_all(load_training(results / "gpvs-modelos-002"), data)
    for key, values in fresh.items():
        assert all(np.array_equal(a, b) for a, b in zip(values["saudavel"], stored[key]["saudavel"]))
        assert all(np.array_equal(values["ensaios"][name], stored[key]["ensaios"][name]) for name in ensaios.FAULTY)


def test_relabel_moves_the_positives_and_leaves_the_gap_out(rodada_sintetica):
    data = rodada_sintetica.preparado
    item = data.faults["F1L"]
    nominal = int(item["pos_falha"][0])
    trials = {"F1L": {"classe": "clara", "observado_janela": nominal + 5},
              "F2L": {"classe": "clara", "observado_janela": nominal - 3},
              "F3L": {"classe": "fraca", "observado_janela": nominal + 9}}
    relabeled = reanalysis.relabel(data, trials)
    later = relabeled.faults["F1L"]
    assert np.array_equal(later["pre_teste"], item["pre_teste"])
    assert later["transicao"].tolist() == list(range(nominal, nominal + 5))
    assert later["pos_falha"][0] == nominal + 5 and later["pos_falha"][-1] == len(item["scaled"]) - 1
    assert relabeled.extraction["F1L"]["fronteira_falha_amostra"] == (nominal + 5) * ensaios.WINDOW
    earlier = relabeled.faults["F2L"]
    assert earlier["pre_teste"].max() < nominal - 3 and len(earlier["transicao"]) == 0
    assert earlier["pos_falha"][0] == nominal - 3
    assert relabeled.faults["F3L"] is data.faults["F3L"]
    assert data.extraction["F1L"]["fronteira_falha_amostra"] == nominal * ensaios.WINDOW  # o original não muda

    # Alarme que vem antes da mudança: detectado, com atraso negativo; as positivas começam na mudança.
    run = {"saudavel": [np.zeros(len(block)) for block in (data.split["test"],)],
           "ensaios": {name: np.zeros(len(data.faults[name]["scaled"])) for name in ensaios.FAULTY}}
    run["ensaios"]["F1L"][nominal:] = 1.0
    result = run_metrics(run, 0.5, relabeled, 3)["ensaios"]["F1L"]
    assert result["detectado"] and result["atraso_ms"] == pytest.approx(-2 * 20.0, abs=0.01)
    assert result["vp"] + result["fn"] == len(later["pos_falha"]) and result["sensibilidade"] == 1.0


def test_reanalysis_exports_registers_and_never_overwrites(rodada_sintetica_copia, capsys):
    from aliado.cli import main

    data_dir, results = rodada_sintetica_copia.dados, rodada_sintetica_copia.resultados
    output = results / "gpvs-reanalise-001"
    args = ["ciencia", "reanalisar-gpvs", "--avaliacao", str(results / reanalysis.EVALUATION),
            "--modelos", str(results / "gpvs-modelos-002"), "--saida", str(output), "--dados", str(data_dir),
            "--cache", str(results / "cache.npz")]
    assert main(args) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["consulta"] == 2
    report = json.loads((output / "relatorio.json").read_text(encoding="utf-8"))
    official = json.loads((results / reanalysis.EVALUATION / "relatorio.json").read_text(encoding="utf-8"))
    # No sintético a mudança é no meio: a reanálise dá os números da avaliação.
    for kind in ("denso", "lstm"):
        assert report["modelos"][kind]["referencia"]["resumo"] == official["modelos"][kind]["referencia"]["resumo"]
    assert report["so_mudanca_clara"]["ensaios"] == list(ensaios.FAULTY)
    assert set(report["sensibilidade"]["percentil"]) == {"95", "97.5", "99"}
    assert set(report["alarmes_estimados"]) == {"denso", "lstm"} and "limiar_incerteza" in report
    frozen = json.loads((output / "configuracao.json").read_text(encoding="utf-8"))
    assert frozen["sha256"] == report["inicio"]["configuracao_sha256"]
    assert frozen["origem"]["avaliacao"] == reanalysis.EVALUATION
    markdown = (output / "relatorio.md").read_text(encoding="utf-8")
    assert "Quando cada falha aparece nos sinais" in markdown and "continua sendo a oficial" in markdown
    assert (output / "metricas_por_ensaio.csv").read_text(encoding="utf-8").count("\n") == 1 + 2 * 2 * 14
    consultations = registry.consultations(results)
    assert [(c["numero"], c.get("tipo"), c["estado"], c["canonica"]) for c in consultations] == [
        (1, None, "concluida", True), (2, "reanalise", "concluida", False)]
    assert consultations[1]["reusa"] == reanalysis.EVALUATION and consultations[1]["saida"] == output.name
    assert main(args) == 2 and "já existe" in capsys.readouterr().err
    assert len(registry.events(results)) == 2

    # As visões da aba leem a reanálise: início por ensaio, indicadores e a estimativa no Resumo.
    view = summary.onsets(results)
    assert [item["id"] for item in view["ensaios"]] == list(ensaios.FAULTY) and view["clara"] == list(ensaios.FAULTY)
    assert view["controle_saudavel"] == {"F0L": 0, "F0M": 0}
    assert view["modelos"]["denso"]["meio"]["sensibilidade"] == view["modelos"]["denso"]["mudanca"]["sensibilidade"]
    assert not re.search(r"semente|canônic|canonic|M1[0-9]", json.dumps(view, ensure_ascii=False), re.IGNORECASE)
    denso = summary.overview(results)["modelos"]["denso"]
    assert denso["alarmes_estimados"]["alarmes_por_hora"] == report["alarmes_estimados"]["denso"]["alarmes_por_hora"]
    assert denso["limiar_faixa"]["ic95"] == report["limiar_incerteza"]["denso"]["ic95"]
    assert summary.current(results).reanalysis == output and view["rodada"]["oficial"]


def test_real_nominal_onsets_repeat_the_official_report(official_results, base_real):
    trained, _ = load_thresholds(official_results / "gpvs-modelos-002")
    config, _ = reanalysis.evaluation_config(official_results / reanalysis.EVALUATION)
    data = preparacao.prepare(base_real, cache=features_cache(base_real), purge=trained.config.purge,
                        fractions=trained.config.fractions)
    scores = reanalysis.load_scores(official_results / reanalysis.EVALUATION / "escores.npz", trained)
    official = json.loads((official_results / reanalysis.EVALUATION / "relatorio.json").read_text(encoding="utf-8"))
    same = summarize(scores, trained, reanalysis.relabel(data, {}), config)
    assert json.loads(json.dumps(same, allow_nan=False)) == official


def test_real_reanalysis_keeps_detection_and_moves_delay_and_sensitivity(official_results, base_real):
    report = reanalysis.reanalyze(official_results / reanalysis.EVALUATION, official_results / "gpvs-modelos-002",
                                  base_real, cache=features_cache(base_real))
    official = json.loads((official_results / reanalysis.EVALUATION / "relatorio.json").read_text(encoding="utf-8"))
    clear = report["so_mudanca_clara"]["ensaios"]
    assert len(clear) == 8
    for kind in ("denso", "lstm"):
        for name, result in report["modelos"][kind]["referencia"]["ensaios"].items():
            before = official["modelos"][kind]["referencia"]["ensaios"][name]
            assert result["detectado"] == before["detectado"]
            if result["detectado"]:
                assert result["atraso_desde_o_meio_ms"] == pytest.approx(before["atraso_ms"])
            if name not in clear:
                assert result["sensibilidade"] == before["sensibilidade"]
        assert report["so_mudanca_clara"]["modelos"][kind]["resumo"]["sensibilidade_media"] == pytest.approx(1.0)
        assert report["modelos"][kind]["referencia"]["resumo"]["atraso_mediano_ms"] <= 60.0 + 1e-9
    estimate = report["alarmes_estimados"]["denso"]
    assert estimate["observado"] == {"sequencias_de_2": 4, "alarmes": 0}
    assert estimate["alarmes_por_hora"] == pytest.approx(19.4, abs=0.1)
    assert report["limiar_incerteza"]["denso"]["ic95"] == pytest.approx([0.00126, 0.02868], abs=2e-5)
