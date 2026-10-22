"""As redes do experimento de detecção (lote 14): o autoencoder denso e o AE-LSTM. Exige o extra `ml`.

Reescrita do contrato da origem (`src/ml/modelos_autoencoder.py`, commit 21f6ddf): mesmas arquiteturas,
hiperparâmetros e ordem de criação das camadas, para que a mesma semente gere os mesmos pesos. O laço de treino fica em
`treino/laco.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from torch import nn

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
