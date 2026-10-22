"""A bateria não usa rede nem credenciais do ambiente do pesquisador.

Lote 49: os dados reais (a base GPVS e os resultados oficiais) entram por fixtures de sessão, numa pasta temporária,
e nada é gravado em `data/`. Os testes que treinam redes ou leem esses dados ficam marcados (`treina` e
`dados_reais`), para a bateria rápida deixá-los de fora."""

import os
import shutil
import socket

import pytest
from apoio.caminhos import BASE_PRESENTE, GPVS, OFFICIAL, RESULTADOS_OFICIAIS, RESULTS

# A marcação vem do uso da fixture: quem pede uma destas treina redes ou lê os dados reais.
TRAINING_FIXTURES = frozenset({"rodada_sintetica", "rodada_sintetica_copia", "origin_gpvs_runs"})
REAL_DATA_FIXTURES = frozenset({"base_real", "official_results", "origin_gpvs_runs"})


def pytest_collection_modifyitems(config, items):
    for item in items:
        used = set(getattr(item, "fixturenames", ()))
        if used & TRAINING_FIXTURES:
            item.add_marker(pytest.mark.treina)
        if used & REAL_DATA_FIXTURES:
            item.add_marker(pytest.mark.dados_reais)


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
    if not RESULTADOS_OFICIAIS:
        pytest.skip("Sem a avaliação oficial, o treino dela e a reanálise neste computador.")
    copy = tmp_path_factory.mktemp("resultados-oficiais")
    for name in OFFICIAL:
        shutil.copytree(RESULTS / name, copy / name)
    return copy


@pytest.fixture(scope="session")
def base_real(tmp_path_factory):
    """A base GPVS real numa pasta temporária, com o cache dos 24 atributos montado uma vez a partir dos CSVs.

    Os CSVs entram por ligação (sem copiar os 460 MB) quando o disco permite; os testes só os leem. O cache é feito
    pelo código de hoje, e nada é gravado em `data/gpvs`."""
    if not BASE_PRESENTE:
        pytest.skip("Sem a base GPVS neste computador.")
    from aliado.specializations.mestrado.atributos import extracao
    from aliado.specializations.mestrado.atributos.cache import features_cache

    folder = tmp_path_factory.mktemp("gpvs-real")
    for path in [*sorted(GPVS.glob("*.csv")), GPVS / "proveniencia.json"]:
        try:
            os.link(path, folder / path.name)
        except OSError:
            shutil.copy2(path, folder / path.name)
    extracao.extract_all(folder, cache=features_cache(folder))
    return folder
