"""Lote 15: avaliação M13 com dados sintéticos; conferência com a origem se os dados reais existirem."""

from __future__ import annotations

import csv
import dataclasses
import json
import shutil
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from test_detection import ROOT, SHORT_PURGE, write_synthetic  # noqa: E402

from aliado.science.detection import gpvs  # noqa: E402
from aliado.science.detection.evaluation import (  # noqa: E402
    EvaluationConfig,
    TrainedDetectors,
    export_evaluation,
    load_training,
    run_metrics,
    score_all,
)
from aliado.science.detection.models import Hyperparameters  # noqa: E402
from aliado.science.detection.training import (  # noqa: E402
    ExperimentConfig,
    export_training,
    train_detectors,
    training_blocks,
)

QUICK = EvaluationConfig(resamples=200)


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    folder = tmp_path_factory.mktemp("gpvs")
    write_synthetic(folder)
    data = gpvs.prepare(folder, purge=SHORT_PURGE)
    config = ExperimentConfig(purge=SHORT_PURGE, seeds=(3, 4), reference_seed=3, percentile=90.0,
                              hyperparameters=Hyperparameters(max_epochs=3))
    output = tmp_path_factory.mktemp("treino") / "rodada"
    export_training(train_detectors(data.scaled, training_blocks(data), config), data, config, output)
    return folder, data, output


def test_loading_checks_configuration_and_weight_hashes(trained, tmp_path):
    _, _, output = trained
    detectors = load_training(output)
    report = json.loads((output / "relatorio.json").read_text(encoding="utf-8"))
    assert detectors.thresholds[("lstm", 3, 5)] == report["modelos"]["lstm"]["sementes"]["3"]["limiar"]["limiar"]
    assert set(detectors.models) == {("denso", 3), ("denso", 4), ("lstm", 3), ("lstm", 4)}
    tampered = tmp_path / "pesos"
    shutil.copytree(output, tampered)
    weights = tampered / "modelos" / "denso-s4.pt"
    weights.write_bytes(weights.read_bytes() + b"x")
    with pytest.raises(ValueError, match="não conferem"):
        load_training(tampered)
    changed = tmp_path / "configuracao"
    shutil.copytree(output, changed)
    frozen = json.loads((changed / "configuracao.json").read_text(encoding="utf-8"))
    frozen["configuracao"]["top_k"] = 10
    (changed / "configuracao.json").write_text(json.dumps(frozen), encoding="utf-8")
    with pytest.raises(ValueError, match="configuração"):
        load_training(changed)


def test_scoring_refuses_data_that_differ_from_the_training(trained):
    _, data, output = trained
    detectors = load_training(output)
    with pytest.raises(ValueError, match="não são os do treino"):
        score_all(detectors, dataclasses.replace(data, hashes={}))
    with pytest.raises(ValueError, match="divisão"):
        score_all(detectors, dataclasses.replace(data, purge=5))


def test_evaluation_exports_alarms_detection_comparison_and_grids(trained, tmp_path):
    _, data, output = trained
    detectors = load_training(output)
    paths = export_evaluation(score_all(detectors, data), detectors, data, QUICK, tmp_path / "avaliacao")
    report = json.loads(Path(paths["relatorio_json"]).read_text(encoding="utf-8"))
    reference = report["modelos"]["denso"]["referencia"]
    alarms = reference["falsos_alarmes"]
    assert alarms["teste_saudavel"]["janelas"] == len(data.split["test"])
    assert alarms["pre_falha"]["janelas"] == sum(len(item["pre_teste"]) for item in data.faults.values())
    assert alarms["combinado"]["duracao_s"] == pytest.approx(
        (alarms["teste_saudavel"]["janelas"] + alarms["pre_falha"]["janelas"]) / gpvs.GRID_HZ)
    assert len(reference["ensaios"]) == 14 and "sensibilidade_ic95" in reference["ensaios"]["F1L"]
    for result in reference["ensaios"].values():
        if result["detectado"]:
            # Fronteira sintética na borda de uma janela: o atraso é um número inteiro de ciclos.
            assert result["atraso_janelas"] >= QUICK.confirmations
            assert result["atraso_ms"] == pytest.approx(20.0 * result["atraso_janelas"])
    assert [row["metrica"] for row in report["comparacao"]] == [
        "alarmes_pre_falha", "especificidade", "detectado", "sensibilidade", "atraso_ms"]
    assert all(row["leitura"] in {"Denso", "AE-LSTM", "sem diferença clara", "sem dados"} for row in report["comparacao"])
    assert set(report["sensibilidade"]["confirmacao"]) == {"1", "2", "3", "5"}
    assert set(report["sensibilidade"]["k"]) == {"5", "10", "20"}
    frozen = json.loads(Path(paths["configuracao"]).read_text(encoding="utf-8"))
    assert frozen["sha256"] == QUICK.digest() and frozen["treino"]["configuracao_sha256"] == detectors.frozen["sha256"]
    rows = list(csv.DictReader(Path(paths["metricas"]).open(encoding="utf-8")))
    assert len(rows) == 2 * 2 * 14
    markdown = Path(paths["relatorio_md"]).read_text(encoding="utf-8")
    assert "foram consultados em" in markdown and "Não há vencedor geral" in markdown
    with pytest.raises(FileExistsError):
        export_evaluation(score_all(detectors, data), detectors, data, QUICK, tmp_path / "avaliacao")


def test_cli_evaluates_and_refuses_existing_folder(trained, tmp_path, capsys):
    from aliado.cli import main

    folder, _, output = trained
    args = ["ciencia", "avaliar-gpvs", "--modelos", str(output), "--saida", str(tmp_path / "avaliacao"),
            "--dados", str(folder), "--cache", str(tmp_path / "cache.npz")]
    assert main(args) == 0 and (tmp_path / "avaliacao" / "relatorio.md").is_file()
    capsys.readouterr()
    assert main(args) == 2 and "já existe" in capsys.readouterr().err


def test_evaluation_config_is_validated():
    assert EvaluationConfig().confirmations == 3 and EvaluationConfig().block == 12
    for bad in ({"confirmations": 4}, {"confirmation_grid": (0, 3)}, {"block": 0}):
        with pytest.raises(ValueError):
            EvaluationConfig(**bad)


def test_real_gpvs_reproduces_the_origin_window_metrics(origin_gpvs_runs):
    reference = json.loads((ROOT / "tests" / "data" / "gpvs_avaliacao_referencia.json").read_text(encoding="utf-8"))
    config, data, runs = origin_gpvs_runs
    detectors = TrainedDetectors(Path("."), config, {"dados": {"hashes": data.hashes}},
                                 {(run.kind, run.seed): run.model for run in runs},
                                 {(run.kind, run.seed, k): t.value for run in runs for k, t in run.thresholds.items()})
    scores = score_all(detectors, data)
    for kind, experiments in reference["ensaios"].items():
        metrics = run_metrics(scores[(kind, 42, 5)], detectors.thresholds[(kind, 42, 5)], data, 3)
        for name, expected in experiments.items():
            result = metrics["ensaios"][name]
            assert result["janelas_pre_falha"] == expected["janelas_pre_falha"]
            assert result["vp"] + result["fn"] == expected["janelas_pos_falha"]
            for key in ("sensibilidade", "especificidade", "precisao", "f1", "acuracia_balanceada", "mcc",
                        "auc_roc", "auc_pr"):
                if expected[key] is None:
                    assert result[key] is None, (kind, name, key)
                else:
                    assert result[key] == pytest.approx(expected[key], abs=1e-12), (kind, name, key)
