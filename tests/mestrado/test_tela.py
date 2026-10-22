"""As rotas da aba Ciência do mestrado: as visões e o que falta, sem rede."""

from __future__ import annotations

import pytest
from apoio.avaliacao_sintetica import synthetic


@pytest.fixture
def client(tmp_path):
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    from aliado.interfaces.web.app import WebSettings, create_app

    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765,
                           stream=lambda *a, **k: iter(()), models=[{"alias": "flash", "model_id": "x"}],
                           library_factory=lambda: None, results_dir=synthetic(tmp_path / "resultados"),
                           dataset_dir=tmp_path / "gpvs")
    return TestClient(create_app(settings), base_url="http://127.0.0.1:8765")


def test_routes_serve_the_views_and_explain_what_is_missing(client):
    overview = client.get("/api/ciencia/resumo")
    assert overview.status_code == 200 and overview.json()["modelos"]["lstm"]["nome"] == "AE-LSTM"
    assert client.get("/api/ciencia/metricas").json()["falhas"][0]["nome"] == "Falha em IGBT"
    missing = client.get("/api/ciencia/escores")
    assert missing.status_code == 404 and "dados do GPVS" in missing.json()["erro"]
    # Lote 24: sem a reanálise, a seção do início das falhas diz o que falta, e o Resumo segue sem a estimativa.
    onsets = client.get("/api/ciencia/inicio")
    assert onsets.status_code == 404 and "reanálise" in onsets.json()["erro"]
    denso = overview.json()["modelos"]["denso"]
    assert denso["alarmes_estimados"] is None and denso["limiar_faixa"] is None
    assert denso["saudavel"]["janelas"] == 263 + 2348 and denso["saudavel"]["alarmes"] == 7
    assert denso["saudavel"]["alarmes_por_hora"] == pytest.approx(7 / 52.22 * 3600)
