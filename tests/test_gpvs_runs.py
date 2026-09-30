"""Lote 21: GPVS pela interface e registro das consultas ao teste (M14), sem rede."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from aliado.science.detection import registry

pytest.importorskip("starlette")
np = pytest.importorskip("numpy")
from starlette.testclient import TestClient  # noqa: E402

from aliado.interfaces.web.app import WebSettings, create_app  # noqa: E402
from aliado.interfaces.web.gpvs_runs import next_folder  # noqa: E402
from aliado.llm.contracts import LLMResult  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"x-aliado": "1"}
CANONICAL_SHA = "a" * 64
CANONICAL_CONFIG = {"purge": 11, "seeds": [13, 29, 42, 71, 101], "hyperparameters": {"max_epochs": 2000}}


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _results(tmp_path) -> Path:
    results = tmp_path / "resultados"
    _write(results / "gpvs-avaliacao-001" / "configuracao.json", {
        "executado_em": "2026-09-27", "treino": {"pasta": "data/resultados/gpvs-modelos-002",
                                                 "configuracao_sha256": CANONICAL_SHA}})
    _write(results / "gpvs-modelos-002" / "configuracao.json", {"sha256": CANONICAL_SHA, "configuracao": CANONICAL_CONFIG})
    np.savez(results / "gpvs-modelos-002" / "escores_calibracao.npz", x=np.zeros(2))
    return results


class FakeCommand:
    """Cria a pasta que o comando criaria; `hold` segura a etapa até ser liberada ou cancelada."""

    def __init__(self):
        self.calls, self.hold, self.release = [], False, threading.Event()

    def __call__(self, args, on_line, on_process):
        self.calls.append(args)
        step, output = args[1], Path(args[args.index("--saida") + 1])
        on_line(f"começando {step}")
        if self.hold:
            fake = type("Process", (), {"terminate": lambda _self: self.release.set()})()
            on_process(fake)
            self.release.wait(5)
            on_process(None)
            return -15, ""
        output.mkdir(parents=True)
        if step == "preparar-gpvs":
            _write(output / "relatorio.json", {"ok": True})
            np.savez(output / "normalizacao.npz", x=np.zeros(1))
        elif step == "treinar-gpvs":
            seeds = [int(s) for s in args[args.index("--sementes") + 1].split(",")]
            sha = CANONICAL_SHA if seeds == CANONICAL_CONFIG["seeds"] else "b" * 64
            _write(output / "configuracao.json", {"sha256": sha, "configuracao": CANONICAL_CONFIG})
            np.savez(output / "escores_calibracao.npz", x=np.zeros(1))
            on_line("Autoencoder Denso, semente 13: melhor época 150 de 170; limiar 3.5")
        else:
            _write(output / "configuracao.json", {"executado_em": "2026-09-28"})
            _write(output / "relatorio.json", {"semente_referencia": 42})
            (output / "metricas_por_ensaio.csv").write_text(
                "modelo,semente,ensaio,detectado,atraso_ms,alarmes_pre_falha\n", encoding="utf-8")
            np.savez(output / "escores.npz", x=np.zeros(1))
        return 0, "{}"


@pytest.fixture
def env(tmp_path):
    def stream(question, **kwargs):
        yield "final", LLMResult("ok", "google", "lite", "critical_reasoning")

    (tmp_path / "gpvs").mkdir()
    (tmp_path / "gpvs" / "proveniencia.json").write_text("{}", encoding="utf-8")
    command = FakeCommand()
    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765, stream=stream,
                           models=[], library_factory=lambda: None, results_dir=_results(tmp_path),
                           gpvs_dir=tmp_path / "gpvs", gpvs_command=command)
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8765") as client:
        yield client, settings, command


def wait(client, job):
    for _ in range(200):
        status = client.get(f"/api/ciencia/tarefas/{job}").json()
        if status["estado"] != "processando":
            return status
        time.sleep(0.02)
    raise AssertionError("Etapa não terminou")


def test_registry_is_seeded_with_the_canonical_consultation_and_only_appended(tmp_path):
    results = _results(tmp_path)
    view = registry.consultations(results)
    assert [(c["numero"], c["canonica"], c["data"]) for c in view] == [(1, True, "2026-09-27")]
    assert not (results / registry.REGISTRY).exists()  # ler não grava
    with pytest.raises(ValueError, match="consultar o teste"):
        registry.start(results, training="gpvs-modelos-002", training_sha=CANONICAL_SHA, output="x", phrase="sim")
    number = registry.start(results, training="gpvs-modelos-002", training_sha=CANONICAL_SHA, output="gpvs-avaliacao-002",
                            phrase=" Consultar o teste ")
    registry.finish(results, number, "concluida")
    assert number == 2
    assert [(c["numero"], c["estado"], c["canonica"]) for c in registry.consultations(results)] == [
        (1, "concluida", True), (2, "concluida", False)]
    assert len(registry.events(results)) == 3
    with pytest.raises(ValueError):
        registry.finish(results, number, "apagada")


def test_new_folders_are_numbered_and_never_reused(tmp_path):
    results = _results(tmp_path)
    assert next_folder(results, "gpvs-modelos").name == "gpvs-modelos-003"
    assert next_folder(results, "gpvs-preparo").name == "gpvs-preparo-001"


def test_prepare_and_train_through_the_interface(env):
    client, settings, command = env
    state = client.get("/api/ciencia/gpvs").json()
    assert state["disponivel"] and state["canonica"]["treino"] == "gpvs-modelos-002"
    assert state["canonica"]["sementes"] == [13, 29, 42, 71, 101] and state["frase"] == "consultar o teste"
    assert client.post("/api/ciencia/gpvs/preparar", json={"separacao": 11}).status_code == 403
    job = client.post("/api/ciencia/gpvs/preparar", headers=HEADERS, json={"separacao": 11}).json()
    assert job["pasta"] == "gpvs-preparo-001" and wait(client, job["tarefa"])["estado"] == "concluido"
    assert command.calls[-1][:2] == ["ciencia", "preparar-gpvs"] and "--separacao" in command.calls[-1]
    execution = json.loads((settings.results_dir / "gpvs-preparo-001" / "execucao.json").read_text(encoding="utf-8"))
    assert execution["origem"] == "interface" and execution["estado"] == "concluido"
    items = {item["id"]: item["tipo"] for item in client.get("/api/ciencia/resultados").json()}
    assert items["gpvs-preparo-001"] == "gpvs-preparo"

    canonical = {"separacao": 11, "sementes": "13, 29, 42, 71, 101", "teto_epocas": 2000}
    job = client.post("/api/ciencia/gpvs/treinar", headers=HEADERS, json=canonical).json()
    status = wait(client, job["tarefa"])
    assert status["estado"] == "concluido" and status["resultado"]["pasta"] == "gpvs-modelos-003"
    assert any("melhor época" in line for line in status["linhas"])
    args = command.calls[-1]
    assert args[args.index("--sementes") + 1] == "13,29,42,71,101" and args[args.index("--teto-epocas") + 1] == "2000"
    execution = json.loads((settings.results_dir / "gpvs-modelos-003" / "execucao.json").read_text(encoding="utf-8"))
    assert execution["configuracao_canonica"] is True
    job = client.post("/api/ciencia/gpvs/treinar", headers=HEADERS, json=canonical | {"sementes": "7"}).json()
    wait(client, job["tarefa"])
    treinos = {item["pasta"]: item["canonica"] for item in client.get("/api/ciencia/gpvs").json()["treinos"]}
    assert treinos == {"gpvs-modelos-002": True, "gpvs-modelos-003": True, "gpvs-modelos-004": False}
    for bad in (canonical | {"sementes": "1,1"}, canonical | {"separacao": "2.5"}, canonical | {"teto_epocas": 0}):
        assert client.post("/api/ciencia/gpvs/treinar", headers=HEADERS, json=bad).status_code == 400


def test_evaluation_needs_the_phrase_and_is_registered_as_non_canonical(env):
    client, settings, command = env
    for body in ({"treino": "gpvs-modelos-002"}, {"treino": "gpvs-modelos-002", "frase": "sim"},
                 {"treino": "nada", "frase": "consultar o teste"}):
        assert client.post("/api/ciencia/gpvs/avaliar", headers=HEADERS, json=body).status_code == 400
    assert not (settings.results_dir / registry.REGISTRY).exists()
    job = client.post("/api/ciencia/gpvs/avaliar", headers=HEADERS,
                      json={"treino": "gpvs-modelos-002", "frase": "consultar o teste"}).json()
    assert job["consulta"] == 2 and job["pasta"] == "gpvs-avaliacao-002"
    assert wait(client, job["tarefa"])["estado"] == "concluido"
    args = command.calls[-1]
    assert Path(args[args.index("--modelos") + 1]).name == "gpvs-modelos-002"
    consultations = client.get("/api/ciencia/gpvs").json()["consultas"]
    assert [(c["numero"], c["estado"], c["canonica"]) for c in consultations] == [
        (1, "concluida", True), (2, "concluida", False)]
    detail = client.get("/api/ciencia/resultados/gpvs-avaliacao-002").json()
    assert detail["consulta"]["numero"] == 2 and detail["consulta"]["canonica"] is False
    assert detail["execucao"]["consulta"] == 2


def test_one_step_at_a_time_and_cancel(env):
    client, settings, command = env
    command.hold = True
    job = client.post("/api/ciencia/gpvs/avaliar", headers=HEADERS,
                      json={"treino": "gpvs-modelos-002", "frase": "consultar o teste"}).json()
    busy = client.post("/api/ciencia/gpvs/preparar", headers=HEADERS, json={"separacao": 11})
    assert busy.status_code == 409
    again = client.post("/api/ciencia/gpvs/avaliar", headers=HEADERS,
                        json={"treino": "gpvs-modelos-002", "frase": "consultar o teste"})
    assert again.status_code == 409
    for _ in range(100):  # espera o processo falso existir
        if command.calls:
            break
        time.sleep(0.01)
    assert client.post("/api/ciencia/gpvs/cancelar", headers=HEADERS).json() == {"cancelando": True}
    status = wait(client, job["tarefa"])
    assert status["estado"] == "cancelado" and status["resultado"] is None
    assert [(c["numero"], c["estado"]) for c in registry.consultations(settings.results_dir)] == [
        (1, "concluida"), (2, "cancelada")]
    assert client.post("/api/ciencia/gpvs/cancelar", headers=HEADERS).status_code == 409


def test_canonical_evaluation_is_labelled_in_results(env):
    client, settings, command = env
    (settings.results_dir / "gpvs-avaliacao-001" / "relatorio.json").write_text(
        json.dumps({"semente_referencia": 42}), encoding="utf-8")
    (settings.results_dir / "gpvs-avaliacao-001" / "metricas_por_ensaio.csv").write_text(
        "modelo,semente,ensaio,detectado,atraso_ms,alarmes_pre_falha\n", encoding="utf-8")
    np.savez(settings.results_dir / "gpvs-avaliacao-001" / "escores.npz", x=np.zeros(1))
    detail = client.get("/api/ciencia/resultados/gpvs-avaliacao-001").json()
    assert detail["consulta"] == {"numero": 1, "canonica": True}


GPVS = ROOT / "data" / "gpvs"


@pytest.mark.skipif(not (GPVS / "proveniencia.json").is_file(), reason="Sem os dados do GPVS neste computador.")
def test_real_prepare_through_the_interface_matches_the_command(tmp_path):
    from aliado.cli import main

    def stream(question, **kwargs):
        yield "final", LLMResult("ok", "google", "lite", "critical_reasoning")

    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765, stream=stream,
                           models=[], library_factory=lambda: None, results_dir=tmp_path / "resultados", gpvs_dir=GPVS)
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8765") as client:
        job = client.post("/api/ciencia/gpvs/preparar", headers=HEADERS, json={"separacao": 11}).json()
        for _ in range(600):
            status = client.get(f"/api/ciencia/tarefas/{job['tarefa']}").json()
            if status["estado"] != "processando":
                break
            time.sleep(0.1)
    assert status["estado"] == "concluido", status
    assert main(["ciencia", "preparar-gpvs", "--dados", str(GPVS), "--cache", str(GPVS / "processado" / "variaveis.npz"),
                 "--saida", str(tmp_path / "comando")]) == 0
    via_interface = json.loads((tmp_path / "resultados" / "gpvs-preparo-001" / "relatorio.json").read_text(encoding="utf-8"))
    via_command = json.loads((tmp_path / "comando" / "relatorio.json").read_text(encoding="utf-8"))
    assert via_interface == via_command
