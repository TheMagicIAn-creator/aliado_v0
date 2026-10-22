"""As redes: o autoencoder denso e o AE-LSTM, com as contagens de parâmetros da origem."""

from __future__ import annotations

import pytest

pytest.importorskip("torch")

from aliado.science.deteccao.redes.autoencoders import (  # noqa: E402
    Hyperparameters,
    build,
    parameter_count,
)


def test_architectures_match_the_reference_parameter_counts():
    hp = Hyperparameters()
    assert parameter_count(build("denso", 24, hp)) == 1088
    assert parameter_count(build("lstm", 24, hp)) == 17216
    with pytest.raises(ValueError):
        build("atencao", 24, hp)
