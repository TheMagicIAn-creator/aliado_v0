"""Os pesos: gravados e relidos sem pickle, com o mesmo erro por variável."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("torch")

from aliado.science.detection.models import (  # noqa: E402
    Hyperparameters,
    feature_errors,
    fit,
    load_model,
    save_model,
)


@pytest.mark.treina
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
