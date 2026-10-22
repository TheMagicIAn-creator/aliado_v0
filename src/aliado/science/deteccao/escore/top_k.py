"""O escore de cada janela: a média dos k maiores erros por variável, a mesma conta da origem."""

from __future__ import annotations

import numpy as np
import torch


def top_k_scores(errors, k: int) -> np.ndarray:
    """Escore da janela: média dos k maiores erros por variável (mesma conta da origem)."""
    tensor = torch.as_tensor(np.asarray(errors, dtype=np.float32))
    if tensor.ndim != 2 or isinstance(k, bool) or not 1 <= int(k) <= tensor.shape[1]:
        raise ValueError("k deve estar entre 1 e o número de variáveis, com erros (janelas, variáveis).")
    return torch.topk(tensor, k=int(k), dim=-1, largest=True, sorted=False).values.mean(dim=-1).numpy()
