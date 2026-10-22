"""O treino dos detectores do mestrado: configuração congelada, calibração sem o teste e exportação (lote 14); com
os dados reais, a reprodução exata da origem."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from apoio.caminhos import ROOT  # noqa: E402
from apoio.gpvs_sintetico import SHORT_PURGE  # noqa: E402

from aliado.science.deteccao.redes.autoencoders import (  # noqa: E402
    Hyperparameters,
    feature_errors,
    load_model,
    parameter_count,
    top_k_scores,
)
from aliado.specializations.mestrado import gpvs  # noqa: E402
from aliado.specializations.mestrado import training as training_module  # noqa: E402
from aliado.specializations.mestrado.training import (  # noqa: E402
    ExperimentConfig,
    export_training,
    model_inputs,
    train_detectors,
    training_blocks,
)

FAST = Hyperparameters(max_epochs=3)


def small_config(**changes) -> ExperimentConfig:
    # 20 janelas de calibração sintéticas não sustentam p99; p90 exige só 11.
    options = {"purge": SHORT_PURGE, "seeds": (3,), "reference_seed": 3, "percentile": 90.0,
               "hyperparameters": FAST} | changes
    return ExperimentConfig(**options)


def test_config_is_validated_and_hashed():
    config = ExperimentConfig()
    assert config.purge == gpvs.PURGE == 11 and config.seeds == (13, 29, 42, 71, 101)
    assert (config.reference_seed, config.top_k, config.sensitivity_k, config.percentile) == (42, 5, (5, 10, 20), 99.0)
    assert (config.hyperparameters.max_epochs, config.hyperparameters.patience) == (2000, 20)
    assert config.digest() == ExperimentConfig().digest() != ExperimentConfig(top_k=10).digest()
    for bad in ({"seeds": (1, 2)}, {"seeds": (42, 42)}, {"top_k": 7}):
        with pytest.raises(ValueError):
            ExperimentConfig(**bad)


@pytest.mark.treina
def test_training_scores_only_calibration_and_never_the_test_block(preparado_sintetico, monkeypatch):
    data = preparado_sintetico
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


def test_export_writes_frozen_configuration_models_and_report(rodada_sintetica, tmp_path):
    data, config, runs = rodada_sintetica.preparado, rodada_sintetica.config, rodada_sintetica.runs
    assert config == small_config(seeds=(3, 4))  # o treino da sessão é o deste teste
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
