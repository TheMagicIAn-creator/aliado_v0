"""O laço de treino: determinismo pela semente, melhor época da validação e parada pela paciência."""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from aliado.science.detection.models import Hyperparameters, fit  # noqa: E402


@pytest.mark.treina
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


@pytest.mark.treina
def test_training_stops_after_patience_without_improvement():
    rng = np.random.default_rng(1)
    train, validation = rng.normal(size=(64, 24)), rng.normal(size=(20, 24))
    # Sem aprendizado, a validação não melhora depois da 1ª época: para após 3 épocas paradas.
    _, history = fit("denso", train, validation, seed=1,
                     hp=Hyperparameters(max_epochs=50, patience=3, learning_rate=0.0))
    assert (history.best_epoch, history.epochs) == (1, 4) and history.stop_reason(3) == "paciencia"
    _, capped = fit("denso", train, validation, seed=1, hp=Hyperparameters(max_epochs=2, learning_rate=0.0))
    assert capped.epochs == 2 and capped.stop_reason(20) == "teto"
