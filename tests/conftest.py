"""A bateria não usa rede nem credenciais do ambiente do pesquisador."""

import os
import shutil
import socket
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("AL_IADO_") or name in {"OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"}:
            monkeypatch.delenv(name, raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("Acesso à rede proibido nesta bateria offline.")

    original_connect = socket.socket.connect

    def loopback_only(sock, address):
        # O laço assíncrono do Windows usa um par de sockets em 127.0.0.1; a rede externa segue bloqueada.
        host = address[0] if isinstance(address, tuple) else None
        if host in {"127.0.0.1", "::1"}:
            return original_connect(sock, address)
        return blocked()

    monkeypatch.setattr(socket.socket, "connect", loopback_only)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture(scope="session")
def official_results(tmp_path_factory):
    """A avaliação oficial de 27/09 numa cópia, com o treino e a reanálise dela (lote 36).

    Uma rodada feita depois pela aba Ciência vira a rodada atual em `data/resultados`; os testes com os dados
    reais conferem os números de 27/09, que não mudam."""
    source = Path(__file__).resolve().parents[1] / "data" / "resultados"
    copy = tmp_path_factory.mktemp("resultados-oficiais")
    for name in ("gpvs-avaliacao-001", "gpvs-modelos-002", "gpvs-reanalise-001"):
        if (source / name).is_dir():
            shutil.copytree(source / name, copy / name)
    return copy


@pytest.fixture(scope="session")
def origin_gpvs_runs(tmp_path_factory):
    """Semente 42 com a separação e o teto de épocas da origem, treinada uma vez para as conferências reais."""
    data_dir = Path(__file__).resolve().parents[1] / "data" / "gpvs"
    if not (data_dir / "F0L.csv").is_file():
        pytest.skip("GPVS real ausente nesta máquina")
    pytest.importorskip("torch")
    from aliado.science.detection.models import Hyperparameters
    from aliado.specializations.mestrado import gpvs
    from aliado.specializations.mestrado.training import (
        ExperimentConfig,
        train_detectors,
        training_blocks,
    )

    config = ExperimentConfig(purge=2, seeds=(42,), hyperparameters=Hyperparameters(max_epochs=150))
    data = gpvs.prepare(data_dir, cache=tmp_path_factory.mktemp("gpvs") / "cache.npz", purge=config.purge)
    return config, data, train_detectors(data.scaled, training_blocks(data), config)
