"""Lote 14: autoencoders, treino congelado e exportação; reprodução exata da origem com os dados reais."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from test_detection import ROOT, SHORT_PURGE, write_synthetic  # noqa: E402

from aliado.science.detection import gpvs  # noqa: E402
from aliado.science.detection import training as training_module  # noqa: E402
from aliado.science.detection.models import (  # noqa: E402
    Hyperparameters,
    build,
    feature_errors,
    fit,
    load_model,
    parameter_count,
    save_model,
    top_k_scores,
)
from aliado.science.detection.training import (  # noqa: E402
    ExperimentConfig,
    export_training,
    model_inputs,
    train_detectors,
    training_blocks,
)

FAST = Hyperparameters(max_epochs=3)


class Zero(torch.nn.Module):
    def forward(self, x):
        return torch.zeros_like(x)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    folder = tmp_path_factory.mktemp("gpvs")
    write_synthetic(folder)
    return folder, gpvs.prepare(folder, purge=SHORT_PURGE)


def small_config(**changes) -> ExperimentConfig:
    # 20 janelas de calibração sintéticas não sustentam p99; p90 exige só 11.
    options = {"purge": SHORT_PURGE, "seeds": (3,), "reference_seed": 3, "percentile": 90.0,
               "hyperparameters": FAST} | changes
    return ExperimentConfig(**options)


def test_top_k_score_is_the_mean_of_the_largest_errors():
    errors = np.array([[1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1]], dtype=np.float32)
    assert np.allclose(top_k_scores(errors, 2), [5.5, 5.5])
    assert np.allclose(top_k_scores(errors, 6), [3.5, 3.5])
    for k in (0, 7, True):
        with pytest.raises(ValueError):
            top_k_scores(errors, k)


def test_feature_errors_use_only_the_last_step_of_each_sequence():
    sequences = np.arange(2 * 4 * 3, dtype=np.float32).reshape(2, 4, 3)
    assert np.array_equal(feature_errors(Zero(), sequences), sequences[:, -1, :] ** 2)
    windows = sequences[:, 0, :]
    assert np.array_equal(feature_errors(Zero(), windows), windows ** 2)


def test_architectures_match_the_reference_parameter_counts():
    hp = Hyperparameters()
    assert parameter_count(build("denso", 24, hp)) == 1088
    assert parameter_count(build("lstm", 24, hp)) == 17216
    with pytest.raises(ValueError):
        build("atencao", 24, hp)


def test_training_is_deterministic_and_keeps_the_best_validation_epoch():
    rng = np.random.default_rng(0)
    train, validation = rng.normal(size=(64, 24)), rng.normal(size=(20, 24))
    hp = Hyperparameters(max_epochs=6)
    model, history = fit("denso", train, validation, seed=5, hp=hp)
    again, _ = fit("denso", train, validation, seed=5, hp=hp)
    other, _ = fit("denso", train, validation, seed=6, hp=hp)
    state = model.state_dict()
    assert all(torch.equal(state[key], again.state_dict()[key]) for key in state)
    assert not all(torch.equal(state[key], other.state_dict()[key]) for key in state)
    assert history.epochs == 6 and 1 <= history.best_epoch <= 6
    target = torch.as_tensor(validation, dtype=torch.float32)
    with torch.no_grad():
        restored = float(torch.nn.functional.mse_loss(model(target), target))
    assert restored == pytest.approx(history.best_validation_loss, rel=1e-6)


def test_training_stops_after_patience_without_improvement():
    rng = np.random.default_rng(1)
    train, validation = rng.normal(size=(64, 24)), rng.normal(size=(20, 24))
    # Sem aprendizado, a validação não melhora depois da 1ª época: para após 3 épocas paradas.
    _, history = fit("denso", train, validation, seed=1,
                     hp=Hyperparameters(max_epochs=50, patience=3, learning_rate=0.0))
    assert (history.best_epoch, history.epochs) == (1, 4) and history.stop_reason(3) == "paciencia"
    _, capped = fit("denso", train, validation, seed=1, hp=Hyperparameters(max_epochs=2, learning_rate=0.0))
    assert capped.epochs == 2 and capped.stop_reason(20) == "teto"


def test_lstm_trains_on_sequences_and_models_reload_without_pickle(tmp_path):
    sequences = np.random.default_rng(2).normal(size=(40, 8, 24)).astype(np.float32)
    hp = Hyperparameters(max_epochs=2)
    model, _ = fit("lstm", sequences[:30], sequences[30:], seed=3, hp=hp)
    path = tmp_path / "lstm.pt"
    save_model(model, path, kind="lstm", seed=3, n_features=24, hp=hp)
    loaded, checkpoint = load_model(path)
    assert checkpoint["semente"] == 3 and checkpoint["hiperparametros"]["max_epochs"] == 2
    assert feature_errors(model, sequences).shape == (40, 24)
    assert np.array_equal(feature_errors(model, sequences), feature_errors(loaded, sequences))


def test_config_is_validated_and_hashed():
    config = ExperimentConfig()
    assert config.purge == gpvs.PURGE == 11 and config.seeds == (13, 29, 42, 71, 101)
    assert (config.reference_seed, config.top_k, config.sensitivity_k, config.percentile) == (42, 5, (5, 10, 20), 99.0)
    assert (config.hyperparameters.max_epochs, config.hyperparameters.patience) == (2000, 20)
    assert config.digest() == ExperimentConfig().digest() != ExperimentConfig(top_k=10).digest()
    for bad in ({"seeds": (1, 2)}, {"seeds": (42, 42)}, {"top_k": 7}):
        with pytest.raises(ValueError):
            ExperimentConfig(**bad)


def test_training_scores_only_calibration_and_never_the_test_block(prepared, monkeypatch):
    _, data = prepared
    sealed = data.scaled.copy()
    sealed[data.split["test"]] = np.nan  # se o teste entrasse, o limiar não seria finito
    scored = []
    original = training_module.feature_errors

    def spy(model, inputs):
        scored.append(len(inputs))
        return original(model, inputs)

    monkeypatch.setattr(training_module, "feature_errors", spy)
    blocks = training_blocks(data)
    assert set(blocks) == {"train", "validation", "calibration"}
    runs = train_detectors(sealed, blocks, small_config())
    assert [(run.kind, run.seed) for run in runs] == [("denso", 3), ("lstm", 3)]
    assert scored == [20, 20] and runs[0].block_sizes == (10, 10)
    assert all(np.isfinite(run.thresholds[k].value) for run in runs for k in (5, 10, 20))


def test_export_writes_frozen_configuration_models_and_report(prepared, tmp_path):
    _, data = prepared
    config = small_config(seeds=(3, 4))
    runs = train_detectors(data.scaled, training_blocks(data), config)
    output = tmp_path / "treino"
    paths = export_training(runs, data, config, output)
    frozen = json.loads(Path(paths["configuracao"]).read_text(encoding="utf-8"))
    assert frozen["sha256"] == config.digest() and frozen["configuracao"]["seeds"] == [3, 4]
    assert frozen["dados"]["hashes"] == data.hashes and frozen["ambiente"]["torch"] == torch.__version__
    report = json.loads(Path(paths["relatorio_json"]).read_text(encoding="utf-8"))
    run = report["modelos"]["lstm"]["sementes"]["3"]
    assert (run["limiar"]["posicao"], run["limiar"]["n_calibracao"]) == (19, 20)  # índice ceil(19 × 0,9) = 18
    assert run["limiar"]["falso_alarme_esperado_por_hora"] == pytest.approx(2 / 21 * 50 * 3600)
    assert set(run["sensibilidade_k"]) == {"5", "10", "20"} and run["parada"] == "teto"  # 3 épocas
    model_file = output / run["arquivos"]["modelo"]["caminho"]
    assert hashlib.sha256(model_file.read_bytes()).hexdigest() == run["arquivos"]["modelo"]["sha256"]
    loaded, _ = load_model(model_file)
    sequences = model_inputs("lstm", data.scaled, training_blocks(data)["calibration"], FAST.sequence)
    with np.load(paths["escores"]) as stored:
        assert np.array_equal(top_k_scores(feature_errors(loaded, sequences), 5), stored["lstm_s3_k5"])
    history = (output / run["arquivos"]["historico"]["caminho"]).read_text(encoding="utf-8").splitlines()
    assert len(history) == 1 + run["epocas_executadas"]
    assert "fechados até o lote 15" in Path(paths["relatorio_md"]).read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        export_training(runs, data, config, output)
    with pytest.raises(ValueError, match="divisão"):
        export_training(runs, data, small_config(purge=11, seeds=(3, 4)), tmp_path / "outra")


def test_cli_refuses_degenerate_threshold_before_training_and_existing_folder(prepared, tmp_path, capsys):
    from aliado.cli import main

    folder, _ = prepared
    output = tmp_path / "treino"
    args = ["ciencia", "treinar-gpvs", "--dados", str(folder), "--saida", str(output),
            "--cache", str(tmp_path / "cache.npz"), "--separacao", str(SHORT_PURGE), "--sementes", "7"]
    assert main(args) == 2
    assert "exige ao menos 101 janelas" in capsys.readouterr().err and not output.exists()
    output.mkdir()
    assert main(args) == 2 and "já existe" in capsys.readouterr().err


def _weights_digest(model) -> str:
    digest = hashlib.sha256()
    for key, tensor in model.state_dict().items():
        digest.update(key.encode())
        digest.update(tensor.contiguous().numpy().tobytes())
    return digest.hexdigest()


def test_real_gpvs_reproduces_the_origin_models_bit_for_bit(origin_gpvs_runs):
    reference = json.loads((ROOT / "tests" / "data" / "gpvs_modelos_referencia.json").read_text(encoding="utf-8"))
    config, _, runs = origin_gpvs_runs
    for run in runs:
        expected = reference["modelos"][run.kind]
        threshold = run.thresholds[config.top_k]
        assert (threshold.value, threshold.rank, threshold.n) == (
            expected["limiar"], expected["posicao"], expected["n_calibracao"])
        assert (run.history.best_epoch, run.history.epochs) == (expected["melhor_epoca"], expected["epocas"])
        assert run.history.best_validation_loss == expected["perda_validacao_minima"]
        assert parameter_count(run.model) == expected["parametros"]
        assert _weights_digest(run.model) == expected["pesos_sha256"]
