"""O laço de treino dos autoencoders (lote 14): sementes, épocas, paciência na validação e a melhor época guardada.

Mesma sequência de sementes da origem (`src/ml/modelos_autoencoder.py`, commit 21f6ddf): a mesma semente gera os
mesmos pesos. Exige o extra `ml`.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from aliado.science.deteccao.redes.autoencoders import Hyperparameters, build


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)


@dataclass(frozen=True)
class TrainingHistory:
    train_loss: tuple[float, ...]
    validation_loss: tuple[float, ...]
    best_epoch: int

    @property
    def epochs(self) -> int:
        return len(self.train_loss)

    @property
    def best_validation_loss(self) -> float:
        return float(min(self.validation_loss))

    def stop_reason(self, patience: int) -> str:
        """"paciencia" se a validação parou o treino; "teto" se o limite de épocas o cortou."""
        return "paciencia" if self.epochs - self.best_epoch >= patience else "teto"


def fit(kind: str, train, validation, *, seed: int, hp: Hyperparameters) -> tuple[nn.Module, TrainingHistory]:
    """Pesos só pelo treino; a validação decide a parada e qual época fica guardada."""
    train_tensor = torch.as_tensor(train, dtype=torch.float32)
    validation_tensor = torch.as_tensor(validation, dtype=torch.float32)
    set_seed(seed)
    model = build(kind, int(train_tensor.shape[-1]), hp)
    # A origem semeia de novo depois de criar o modelo; repetir a sequência reproduz
    # os mesmos sorteios de dropout e de ordem dos lotes.
    set_seed(seed)
    loader = DataLoader(TensorDataset(train_tensor), batch_size=min(hp.batch_size, len(train_tensor)),
                        shuffle=True, generator=torch.Generator().manual_seed(seed))
    optimizer = torch.optim.Adam(model.parameters(), lr=hp.learning_rate)
    loss_function = nn.MSELoss()
    train_losses, validation_losses = [], []
    best_state, best_loss, best_epoch, stale = copy.deepcopy(model.state_dict()), float("inf"), 0, 0
    for epoch in range(1, hp.max_epochs + 1):
        model.train()
        batch_losses = []
        for (batch,) in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(batch), batch)
            loss.backward()
            optimizer.step()
            batch_losses.append(float(loss.detach()))
        model.eval()
        with torch.no_grad():
            validation_loss = float(loss_function(model(validation_tensor), validation_tensor))
        train_losses.append(float(np.mean(batch_losses)))
        validation_losses.append(validation_loss)
        if validation_loss < best_loss - 1e-8:
            best_loss, best_epoch, stale = validation_loss, epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            stale += 1
            if stale >= hp.patience:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model, TrainingHistory(tuple(train_losses), tuple(validation_losses), best_epoch)
