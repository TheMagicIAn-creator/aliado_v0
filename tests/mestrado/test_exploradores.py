"""Os exploradores do limiar e dos alarmes: o que falta, o cache dos erros e a reprodução da avaliação de 27/09."""

from __future__ import annotations

import csv
import json

import pytest

from aliado.specializations.mestrado.exploradores.explorador import Explorer, plain


def test_plain_converts_numpy_for_json():
    np = pytest.importorskip("numpy")
    data = plain({"a": np.int64(3), "b": np.float32(0.5), "c": np.array([1, 2]), "d": (np.bool_(True),)})
    assert data == {"a": 3, "b": 0.5, "c": [1, 2], "d": [True]}
    assert json.dumps(data)


def test_explorer_reports_what_is_missing_without_loading_models(tmp_path):
    explorer = Explorer(tmp_path / "resultados", tmp_path / "gpvs", tmp_path / "cache")
    status = explorer.status()
    assert not status["disponivel"] and not status["pronto"] and len(status["faltando"]) == 2
    with pytest.raises(ValueError, match="Prepare"):
        explorer.threshold("denso", 42, 5, 99)
    with pytest.raises(ValueError, match="indisponíveis"):
        explorer.prepare()


def test_the_error_cache_is_tied_to_the_weights_and_the_variable_order(tmp_path, monkeypatch):
    """Lote 46: o cache dos erros por variável guarda o hash dos pesos e a ordem das 24 variáveis. Um treino com a
    mesma configuração e outros pesos recalcula em outro arquivo, sem reaproveitar os erros do anterior."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("torch")
    from types import SimpleNamespace

    from aliado.science.deteccao.inferencia import erros
    from aliado.specializations.mestrado.atributos import variaveis
    from aliado.specializations.mestrado.avaliacao import pontuacao
    from aliado.specializations.mestrado.base import ensaios
    from aliado.specializations.mestrado.treino import detectores as training

    computed = []
    monkeypatch.setattr(erros, "feature_errors",
                        lambda model, inputs: computed.append(model) or np.zeros((2, 24), np.float32))
    monkeypatch.setattr(pontuacao, "segment_errors", lambda kind, model, scaled, sequence: np.ones((3, 24), np.float32))
    monkeypatch.setattr(training, "training_blocks", lambda prepared: {"calibration": None})
    monkeypatch.setattr(training, "model_inputs", lambda kind, scaled, blocks, sequence: scaled)
    trained = SimpleNamespace(frozen={"sha256": "c" * 64}, models={("denso", 42): "rede"},
                              config=SimpleNamespace(hyperparameters=SimpleNamespace(sequence=8)))
    prepared = SimpleNamespace(hashes={"F0L.csv": "d" * 64}, scaled=np.zeros((4, 24), np.float32), faults={},
                               split={"por_ensaio": {name: {"test": slice(2, 4)} for name in ensaios.HEALTHY}})
    explorer = Explorer(tmp_path / "resultados", tmp_path / "gpvs", tmp_path / "cache")
    first = explorer._errors(trained, prepared, {"denso_s42": "a" * 64})
    again = explorer._errors(trained, prepared, {"denso_s42": "a" * 64})
    assert len(computed) == 1 and again[("denso", 42)].keys() == first[("denso", 42)].keys()
    explorer._errors(trained, prepared, {"denso_s42": "b" * 64})
    files = sorted((tmp_path / "cache").glob("erros-*.npz"))
    assert len(computed) == 2 and len(files) == 2
    metas = []
    for path in files:
        with np.load(path) as cached:
            metas.append(json.loads(str(cached["meta"])))
    assert {meta["pesos"]["denso_s42"] for meta in metas} == {"a" * 64, "b" * 64}
    assert all(meta["variaveis"] == list(variaveis.FEATURES) and meta["treino"] == "c" * 64 for meta in metas)


def test_explorers_reproduce_the_canonical_evaluation_exactly(tmp_path, official_results, base_real):
    explorer = Explorer(official_results, base_real, tmp_path / "cache")
    explorer.prepare()
    report = json.loads((official_results / "gpvs-avaliacao-001" / "relatorio.json").read_text(encoding="utf-8"))
    with (official_results / "gpvs-avaliacao-001" / "metricas_por_ensaio.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for kind in ("denso", "lstm"):
        for seed in (13, 29, 42, 71, 101):
            threshold = explorer.threshold(kind, seed, 5, 99.0)
            alarms = explorer.alarms(kind, seed, 5, 99.0, 3, trial="F1L")
            run = report["modelos"][kind]["sementes"][str(seed)]
            assert threshold["limiar"]["limiar"] == threshold["canonico"]["limiar"]
            assert alarms["parametros_canonicos"]
            shared = set(alarms["resumo"]) & set(run["resumo"])
            assert {"detectados", "atraso_mediano_ms", "sensibilidade_media"} <= shared
            assert all(alarms["resumo"][key] == run["resumo"][key] for key in shared)
            assert alarms["falsos_alarmes"]["teste_saudavel"]["alarmes"] == run["alarmes_teste_saudavel"]
            assert alarms["falsos_alarmes"]["pre_falha"]["alarmes"] == run["alarmes_pre_falha"]
            canonical = {row["ensaio"]: row for row in rows if row["modelo"] == kind and int(row["semente"]) == seed}
            for trial in alarms["ensaios"]:
                row = canonical[trial["ensaio"]]
                assert str(trial["detectado"]) == row["detectado"]
                assert trial["atraso_ms"] == (float(row["atraso_ms"]) if row["atraso_ms"] else None)
    # As grades de sensibilidade relatadas (m e k, semente de referência) também se repetem.
    seed = report["semente_referencia"]
    for grid, values in report["sensibilidade"].items():
        for value, by_model in values.items():
            for kind, expected in by_model.items():
                k, m = (int(value), 3) if grid == "k" else (5, int(value))
                got = explorer.alarms(kind, seed, k, 99.0, m)
                assert got["resumo"]["detectados"] == expected["detectados"]
                assert got["resumo"]["atraso_mediano_ms"] == expected["atraso_mediano_ms"]
                assert got["falsos_alarmes"]["teste_saudavel"]["alarmes"] == expected["alarmes_teste_saudavel"]
                assert got["falsos_alarmes"]["pre_falha"]["alarmes"] == expected["alarmes_pre_falha"]
    # O cache é reaproveitado e outro k muda o limiar sem tocar nos resultados congelados.
    again = Explorer(official_results, base_real, tmp_path / "cache")
    again.prepare()
    other = again.threshold("denso", 42, 10, 99.0)
    assert other["limiar"]["limiar"] != other["canonico"]["limiar"]
    assert not again.alarms("denso", 42, 10, 99.0, 3)["parametros_canonicos"]
    assert len(list((tmp_path / "cache").glob("erros-*.npz"))) == 1
    with pytest.raises(ValueError):
        again.threshold("denso", 42, 25, 99.0)
    with pytest.raises(ValueError):
        again.alarms("denso", 42, 5, 99.0, 11)
