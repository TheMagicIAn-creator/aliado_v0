"""O escore da janela: a média dos k maiores erros por variável."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("torch")

from aliado.science.deteccao.redes.autoencoders import top_k_scores  # noqa: E402


def test_top_k_score_is_the_mean_of_the_largest_errors():
    errors = np.array([[1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1]], dtype=np.float32)
    assert np.allclose(top_k_scores(errors, 2), [5.5, 5.5])
    assert np.allclose(top_k_scores(errors, 6), [3.5, 3.5])
    for k in (0, 7, True):
        with pytest.raises(ValueError):
            top_k_scores(errors, k)
