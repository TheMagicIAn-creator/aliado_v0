"""As sequências do AE-LSTM: uma por janela, sem atravessar blocos; a primeira janela se repete só no início."""

from __future__ import annotations

import numpy as np

DEFAULT_SEQUENCE = 8


def sequences_from_flow(values: np.ndarray, length: int = DEFAULT_SEQUENCE) -> np.ndarray:
    """Uma sequência por janela; a primeira janela se repete só no início do bloco."""
    matrix = np.asarray(values, dtype=np.float32)
    if matrix.ndim != 2 or not len(matrix):
        raise ValueError("O fluxo deve ter formato (janelas, variáveis) e não ser vazio.")
    if length < 2:
        raise ValueError("A sequência precisa de ao menos dois passos.")
    padded = np.vstack([np.repeat(matrix[:1], length - 1, axis=0), matrix])
    return np.stack([padded[i:i + length] for i in range(len(matrix))])


def sequences_for_blocks(values: np.ndarray, blocks, length: int = DEFAULT_SEQUENCE):
    """Sequências de cada bloco contíguo, sem atravessar ensaios nem papéis."""
    matrix = np.asarray(values, dtype=np.float32)
    sequences, targets = [], []
    for block in blocks:
        indices = np.asarray(block, dtype=int)
        if not len(indices):
            continue
        if np.any(np.diff(indices) != 1):
            raise ValueError("Cada bloco temporal deve ter índices contíguos.")
        sequences.append(sequences_from_flow(matrix[indices], length))
        targets.append(indices)
    if not sequences:
        raise ValueError("Nenhum bloco temporal válido foi fornecido.")
    return np.concatenate(sequences), np.concatenate(targets)
