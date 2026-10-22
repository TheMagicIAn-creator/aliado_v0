"""O erro de reconstrução por variável, que é o sinal de anomalia (Sakurada e Yairi, 2014; no caso recorrente,
Malhotra et al., 2016)."""

from __future__ import annotations

import numpy as np
import torch
from torch import nn


def feature_errors(model: nn.Module, inputs) -> np.ndarray:
    """Erro quadrático por variável; no AE-LSTM, só o do último passo de cada sequência."""
    tensor = torch.as_tensor(inputs, dtype=torch.float32)
    model.eval()
    with torch.no_grad():
        reconstructed = model(tensor)
    if tensor.ndim == 3:
        reconstructed, tensor = reconstructed[:, -1, :], tensor[:, -1, :]
    return ((reconstructed - tensor) ** 2).numpy()
