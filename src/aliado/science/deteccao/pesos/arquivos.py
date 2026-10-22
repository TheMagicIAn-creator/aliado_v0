"""Os pesos dos autoencoders em `.pt`: só tensores e tipos simples, para abrir com `weights_only=True`, sem pickle."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import torch
from torch import nn

from aliado.science.deteccao.redes.autoencoders import Hyperparameters, build


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
