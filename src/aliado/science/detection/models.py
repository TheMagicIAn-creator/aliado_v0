"""Autoencoders Denso e AE-LSTM do experimento de detecção (lote 14). Exige o extra `ml`.

Reescrita do contrato da origem (`src/ml/modelos_autoencoder.py`, commit 21f6ddf): mesmas
arquiteturas, hiperparâmetros, ordem de criação das camadas e sequência de sementes, para
que a mesma semente gere os mesmos pesos. O erro de reconstrução como sinal de anomalia
segue Sakurada e Yairi (2014) e, no caso recorrente, Malhotra et al. (2016).
"""

from __future__ import annotations

import copy
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

MODELS = ("denso", "lstm")
MODEL_NAMES = {"denso": "Autoencoder Denso", "lstm": "AE-LSTM"}


@dataclass(frozen=True)
class Hyperparameters:
    dense_hidden: int = 16
    latent: int = 8
    lstm_hidden: int = 32
    sequence: int = 8
    learning_rate: float = 1e-3
    # Teto só de segurança: quem para o treino é a paciência na validação (decisão de
    # 27/09/2026). A origem usava 150, que encerrava a maioria dos treinos ainda melhorando.
    max_epochs: int = 2000
    patience: int = 20
    batch_size: int = 32
    dropout: float = 0.2


class DenseAutoencoder(nn.Module):
    """24-16-8-16-24 com saída linear; dropout antes do gargalo e antes da saída."""

    def __init__(self, n_features: int, hidden: int, latent: int, dropout: float):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(n_features, hidden), nn.ReLU(), nn.Dropout(dropout),
                                     nn.Linear(hidden, latent))
        self.decoder = nn.Sequential(nn.Linear(latent, hidden), nn.ReLU(), nn.Dropout(dropout),
                                     nn.Linear(hidden, n_features))

    def forward(self, x):
        return self.decoder(self.encoder(x))


class LSTMAutoencoder(nn.Module):
    """Resume a sequência num vetor latente e a reconstrói repetindo-o em cada passo.

    O dropout fica nas duas travessias do gargalo, como no denso: `nn.LSTM` de uma
    camada ignora o próprio argumento `dropout`.
    """

    def __init__(self, n_features: int, hidden: int, latent: int, dropout: float):
        super().__init__()
        self.encoder = nn.LSTM(n_features, hidden, batch_first=True)
        self.encoder_dropout = nn.Dropout(dropout)
        self.to_latent = nn.Linear(hidden, latent)
        self.from_latent = nn.Linear(latent, hidden)
        self.decoder = nn.LSTM(hidden, hidden, batch_first=True)
        self.decoder_dropout = nn.Dropout(dropout)
        self.output = nn.Linear(hidden, n_features)

    def forward(self, x):
        _, (hidden, _) = self.encoder(x)
        latent = self.to_latent(self.encoder_dropout(hidden[-1]))
        repeated = self.from_latent(latent).unsqueeze(1).repeat(1, x.size(1), 1)
        decoded, _ = self.decoder(repeated)
        return self.output(self.decoder_dropout(decoded))


def build(kind: str, n_features: int, hp: Hyperparameters) -> nn.Module:
    if kind == "denso":
        return DenseAutoencoder(n_features, hp.dense_hidden, hp.latent, hp.dropout)
    if kind == "lstm":
        return LSTMAutoencoder(n_features, hp.lstm_hidden, hp.latent, hp.dropout)
    raise ValueError(f"Modelo desconhecido: {kind}.")


def parameter_count(model: nn.Module) -> int:
    return int(sum(parameter.numel() for parameter in model.parameters()))


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


def feature_errors(model: nn.Module, inputs) -> np.ndarray:
    """Erro quadrático por variável; no AE-LSTM, só o do último passo de cada sequência."""
    tensor = torch.as_tensor(inputs, dtype=torch.float32)
    model.eval()
    with torch.no_grad():
        reconstructed = model(tensor)
    if tensor.ndim == 3:
        reconstructed, tensor = reconstructed[:, -1, :], tensor[:, -1, :]
    return ((reconstructed - tensor) ** 2).numpy()


def top_k_scores(errors, k: int) -> np.ndarray:
    """Escore da janela: média dos k maiores erros por variável (mesma conta da origem)."""
    tensor = torch.as_tensor(np.asarray(errors, dtype=np.float32))
    if tensor.ndim != 2 or isinstance(k, bool) or not 1 <= int(k) <= tensor.shape[1]:
        raise ValueError("k deve estar entre 1 e o número de variáveis, com erros (janelas, variáveis).")
    return torch.topk(tensor, k=int(k), dim=-1, largest=True, sorted=False).values.mean(dim=-1).numpy()


def save_model(model: nn.Module, path: str | Path, *, kind: str, seed: int, n_features: int,
               hp: Hyperparameters) -> None:
    """Só tensores e tipos simples: o arquivo abre com `weights_only=True`, sem pickle arbitrário."""
    torch.save({"state_dict": model.state_dict(), "modelo": kind, "semente": int(seed),
                "n_variaveis": int(n_features), "hiperparametros": asdict(hp)}, path)


def load_model(path: str | Path) -> tuple[nn.Module, dict]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model = build(checkpoint["modelo"], checkpoint["n_variaveis"], Hyperparameters(**checkpoint["hiperparametros"]))
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return model, checkpoint
