"""Lote 34: experimentos do zero, rodada atual, resultados em JSON e Markdown, PDF por pedido e comparação."""

from __future__ import annotations

import io
import json
import threading
import time
from pathlib import Path

import pytest

from aliado import experiments
from aliado.science.detection import registry
from aliado.specializations.mestrado import autoencoders

np = pytest.importorskip("numpy")
ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"x-aliado": "1"}
SHA = "a" * 64


def legacy_results(root: Path) -> Path:
    """A avaliação de 27/09 em miniatura: avaliação sintética, treino e os hashes que o resultado cita."""
    from test_science_views import synthetic

    results = synthetic(root / "resultados")
    evaluation = results / autoencoders.LEGACY_EVALUATION / "configuracao.json"
    evaluation.write_text(json.dumps({"executado_em": "2026-09-27", "sha256": "c" * 64,
                                      "treino": {"pasta": "data/resultados/gpvs-modelos-002", "configuracao_sha256": SHA},
                                      "dados": {"hashes": {"F0L": "d" * 64}}}), encoding="utf-8")
    training = results / "gpvs-modelos-002"
    training.mkdir()
    (training / "configuracao.json").write_text(json.dumps({"sha256": SHA, "ambiente": {"python": "3.12"}, "configuracao": {
        "purge": 11, "seeds": [2, 1], "reference_seed": 2, "fractions": [0.5, 0.15, 0.15, 0.2], "top_k": 5,
        "percentile": 99.0, "hyperparameters": {"max_epochs": 2000, "sequence": 8, "patience": 20}}}), encoding="utf-8")
    return results


def test_core_finds_the_experiment_and_checks_parameters():
    """EXP-01 e EXP-05: o núcleo acha o experimento sem o nome dele e confere os parâmetros pela declaração."""
    experiment = experiments.find("ae-denso-lstm")
    assert experiment is autoencoders and experiment in experiments.available()
    assert experiments.normalize(experiment, {}) == {"separacao": 11, "sementes": [13, 29, 42, 71, 101], "teto_epocas": 2000}
    assert experiments.normalize(experiment, {"sementes": "101, 42,13", "separacao": "2"})["sementes"] == [13, 42, 101]
    for bad in ({"sementes": "1,1"}, {"separacao": "2.5"}, {"teto_epocas": 0}, {"nada": 1}, {"separacao": True}):
        with pytest.raises(ValueError):
            experiments.normalize(experiment, bad)
    current = {"parametros": {"separacao": 11, "sementes": [13, 29, 42, 71, 101], "teto_epocas": 2000}}
    assert experiments.same_parameters(experiment, {"sementes": "101,71,42,29,13"}, current)
    assert not experiments.same_parameters(experiment, {"separacao": 2}, current)
    assert not experiments.same_parameters(experiment, {}, None)
    with pytest.raises(ValueError):
        experiments.find("nada")


def test_runs_are_numbered_and_only_complete_ones_count(tmp_path):
    """EXP-02, EXP-03 e EXP-08: pasta nova a cada rodada; sem resultado.json legível, a rodada não conta."""
    results = tmp_path / "resultados"
    assert experiments.next_folder(results, "x").name == "rodada-001"
    first = results / "x" / "rodada-001"
    first.mkdir(parents=True)
    assert experiments.latest(results, "x") is None and experiments.next_folder(results, "x").name == "rodada-002"
    result = {"experimento": "x", "titulo": "X", "base": "B", "rodada": "rodada-001", "rotulo": "Rodada de hoje",
              "parametros_texto": [{"rotulo": "P", "texto": "1"}], "numeros": {"a": {"rotulo": "A", "texto": "1", "valor": 1}}}
    experiments.write_result(first, result)
    assert experiments.latest(results, "x") == (first, result)
    assert "| P | 1 |" in (first / experiments.REPORT).read_text(encoding="utf-8")
    assert not list(first.glob(".*"))  # o arquivo parcial virou o resultado
    broken = results / "x" / "rodada-002"
    broken.mkdir()
    (broken / experiments.RESULT).write_text("{quebrado", encoding="utf-8")
    other = results / "x" / "rodada-003"
    other.mkdir()
    (other / experiments.RESULT).write_text(json.dumps({"experimento": "outro"}), encoding="utf-8")
    assert experiments.latest(results, "x")[0] == first
    assert experiments.next_folder(results, "x").name == "rodada-004"


def test_without_new_runs_the_current_run_is_the_official_one(tmp_path):
    """EXP-04 e EXP-11: sem rodada nova vale a avaliação de 27/09, chamada de oficial só ela."""
    results = legacy_results(tmp_path)
    result = experiments.current(results, autoencoders)
    assert result["oficial"] and result["rodada"] == "avaliacao-oficial" and result["consulta"] == 1
    assert result["rotulo"] == "Avaliação oficial de 27/09/2026"
    assert result["parametros"] == {"separacao": 11, "sementes": [1, 2], "teto_epocas": 2000}
    assert result["numeros"]["denso.detectados"]["texto"] == "10 de 14" and result["detalhe"]["inicio"] is None
    assert experiments.current(tmp_path / "vazio", autoencoders) is None


def test_registry_seeds_the_official_consultation_and_closes_open_ones(tmp_path):
    """EXP-06: a frase é exigida, a consulta oficial abre o registro, e uma consulta aberta é fechada."""
    results = legacy_results(tmp_path)
    canonical = autoencoders.LEGACY_EVALUATION
    assert [(c["numero"], c["canonica"]) for c in registry.consultations(results, canonical)] == [(1, True)]
    assert not (results / registry.REGISTRY).exists()  # ler não grava
    with pytest.raises(ValueError, match="consultar o teste"):
        registry.start(results, training="t", training_sha=SHA, output="x", phrase="sim", canonical=canonical)
    number = registry.start(results, training="t", training_sha=SHA, output="ae-denso-lstm/rodada-001",
                            phrase=" Consultar o teste ", canonical=canonical)
    assert number == 2 and autoencoders.consultations(results) == 2
    assert registry.close_open(results, "ae-denso-lstm/rodada-001", "cancelada") == [2]
    assert registry.close_open(results, "ae-denso-lstm/rodada-001", "cancelada") == []
    assert [(c["numero"], c["estado"]) for c in registry.consultations(results)] == [(1, "concluida"), (2, "cancelada")]
    with pytest.raises(ValueError):
        registry.finish(results, number, "apagada")


def _fake_result(params: dict) -> dict:
    return {"experimento": "x", "titulo": "Experimento × Teste", "base": "Base", "rodada": "rodada-001", "oficial": False,
            "rotulo": "Rodada de 18/10/2026 · 6ª vez que os dados de teste foram usados", "executado_em": "2026-10-18T10:00:00",
            "versao": "0.7.0", "parametros": params, "parametros_texto": [{"rotulo": "Separação", "texto": "2 janelas"}],
            "numeros": {"m.a": {"rotulo": "Modelo · A", "valor": 0.5, "texto": "0,5", "nota": "nota"}}}


def test_pdf_is_formal_has_contents_pages_and_carries_the_json():
    """EXP-09: capa, sumário com as páginas certas, tabelas numeradas e o resultado.json anexo."""
    pytest.importorskip("matplotlib")
    pypdf = pytest.importorskip("pypdf")
    from aliado.experiments import pdf

    result = _fake_result({"separacao": 2})
    rows = [[f"Linha {i} com um texto comprido o bastante para precisar de espaço", f"{i},5"] for i in range(70)]
    blocks = [{"tipo": "secao", "titulo": "Objetivo"}, {"tipo": "paragrafo", "texto": "Texto. " * 120},
              {"tipo": "secao", "titulo": "Resultados"},
              {"tipo": "tabela", "legenda": "Muitas linhas", "colunas": ["Indicador", "Valor"], "linhas": rows,
               "numericas": [False, True], "notas": ["Uma nota."]},
              {"tipo": "secao", "titulo": "Reprodução"}, {"tipo": "codigo", "texto": "aliado experimento rodar x " + "b" * 90},
              {"tipo": "lista", "itens": ["um", "dois"]}]
    reader = pypdf.PdfReader(io.BytesIO(pdf.render(result, blocks)))
    assert json.loads(reader.attachments["resultado.json"][0]) == result
    outline = [(item.title, reader.get_destination_page_number(item)) for item in reader.outline]
    assert [title for title, _ in outline] == ["1 Objetivo", "2 Resultados", "3 Reprodução"]
    contents = reader.pages[1].extract_text()
    for title, page in outline:
        number, name = title.split(" ", 1)
        assert name in reader.pages[page].extract_text()
        assert f"{name}" in contents and str(page + 1) in contents
    assert "continuação" in "".join(page.extract_text() for page in reader.pages)
    last = reader.pages[-1].extract_text()
    assert f"página {len(reader.pages)} de {len(reader.pages)}" in last
    for line in pdf.wrap("palavra " * 50 + "x" * 200, "corpo", 100):
        assert pdf.width(line, "corpo") <= 100


def test_saved_results_are_read_from_the_pdf_or_the_json_and_compared():
    """EXP-10: o anexo do PDF ou o JSON, comparados indicador por indicador; lixo vira aviso."""
    pytest.importorskip("matplotlib")
    pytest.importorskip("pypdf")
    from aliado.experiments import pdf

    saved = _fake_result({"separacao": 2})
    data = pdf.render(saved, [{"tipo": "secao", "titulo": "Só"}, {"tipo": "paragrafo", "texto": "x"}])
    assert experiments.saved_result("guardado.pdf", data) == saved
    assert experiments.saved_result("resultado.json", json.dumps(saved).encode()) == saved
    now = _fake_result({"separacao": 11}) | {"numeros": {"m.a": {"rotulo": "Modelo · A", "valor": 0.75, "texto": "0,75"}}}
    comparison = experiments.compare(saved, now)
    assert comparison["linhas"][0] | {} == {"chave": "m.a", "rotulo": "Modelo · A", "nota": "nota", "guardado": "0,5",
                                            "atual": "0,75", "diferenca": 0.25, "igual": False}
    assert comparison["guardado"]["parametros"] == {"separacao": 2} and comparison["iguais"] == 0
    assert experiments.compare(saved, saved)["iguais"] == 1
    for name, raw in (("a.pdf", b"%PDF-nada"), ("a.json", b"{"), ("a.txt", b"{}"), ("a.json", b"[]")):
        with pytest.raises(ValueError):
            experiments.saved_result(name, raw)
    with pytest.raises(ValueError, match="outro experimento"):
        experiments.compare(saved | {"experimento": "y"}, now)


class FakeCommand:
    """Faz o que `aliado experimento rodar` faria: abre a consulta e grava o resultado; `hold` segura a rodada."""

    def __init__(self, results: Path):
        self.results, self.calls, self.hold, self.release = results, [], False, threading.Event()

    def __call__(self, args, on_line, on_process):
        self.calls.append(args)
        folder = Path(args[args.index("--saida") + 1])
        if not folder.is_absolute():
            folder = Path.cwd() / folder
        folder.mkdir(parents=True)
        on_line("Treinando os dois modelos…")
        output = folder.relative_to(self.results).as_posix()
        number = registry.start(self.results, training=f"{output}/modelos", training_sha=SHA, output=output,
                                phrase=args[args.index("--frase") + 1], canonical=autoencoders.LEGACY_EVALUATION)
        if self.hold:
            on_process(type("Process", (), {"terminate": lambda _self: self.release.set()})())
            self.release.wait(5)
            on_process(None)
            return -15, ""
        registry.finish(self.results, number, "concluida")
        params = experiments.normalize(autoencoders, dict(args[i + 1].split("=", 1) for i, item in enumerate(args)
                                                          if item == "--parametro"))
        legacy = autoencoders.legacy(self.results)
        experiments.write_result(folder, legacy | {"rodada": folder.name, "oficial": False, "consulta": number,
                                                   "parametros": params, "rotulo": f"Rodada de hoje · {number}ª vez"})
        return 0, "{}"


@pytest.fixture
def web(tmp_path):
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    from aliado.interfaces.web.app import WebSettings, create_app
    from aliado.llm.contracts import LLMResult

    def stream(question, **kwargs):
        yield "final", LLMResult("ok", "google", "lite", "critical_reasoning")

    results = legacy_results(tmp_path).resolve()
    (tmp_path / "base").mkdir()
    (tmp_path / "base" / "proveniencia.json").write_text("{}", encoding="utf-8")
    command = FakeCommand(results)
    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765, stream=stream,
                           models=[], library_factory=lambda: None, results_dir=results, dataset_dir=tmp_path / "base",
                           experiment_command=command)
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8765") as client:
        yield client, settings, command


def wait(client, job):
    for _ in range(300):
        status = client.get(f"/api/ciencia/tarefas/{job}").json()
        if status["estado"] != "processando":
            return status
        time.sleep(0.02)
    raise AssertionError("A rodada não terminou")


def test_running_again_needs_new_parameters_and_the_phrase(web):
    """EXP-02, EXP-04, EXP-05 e EXP-06 pela interface: recusas, a rodada nova e a aba passando a mostrá-la."""
    client, settings, command = web
    listed = client.get("/api/experimentos").json()["experimentos"][0]
    assert listed["chave"] == "ae-denso-lstm" and listed["base"] == "GPVS" and listed["faltando"] == []
    assert listed["atual"]["oficial"] and listed["atual"]["parametros"]["sementes"] == [1, 2]
    assert listed["consultas"] == 1 and listed["frase"] == "consultar o teste"
    same = {"parametros": {"separacao": 11, "sementes": "2, 1", "teto_epocas": 2000}, "frase": "consultar o teste"}
    url = "/api/experimentos/ae-denso-lstm/rodar"
    assert client.post(url, json=same).status_code == 403
    assert client.post(url, headers=HEADERS, json=same).status_code == 409
    changed = same | {"parametros": same["parametros"] | {"separacao": 2}}
    assert client.post(url, headers=HEADERS, json=changed | {"frase": "sim"}).status_code == 400
    assert client.post(url, headers=HEADERS, json=changed | {"parametros": {"separacao": -1}}).status_code == 400
    assert client.post("/api/experimentos/nada/rodar", headers=HEADERS, json=changed).status_code == 400
    job = client.post(url, headers=HEADERS, json=changed).json()
    assert job["pasta"] == "rodada-001" and wait(client, job["tarefa"])["estado"] == "concluido"
    args = command.calls[-1]
    assert args[:3] == ["experimento", "rodar", "ae-denso-lstm"] and "separacao=2" in args
    folder = settings.results_dir / "ae-denso-lstm" / "rodada-001"
    assert json.loads((folder / "execucao.json").read_text(encoding="utf-8"))["estado"] == "concluido"
    listed = client.get("/api/experimentos").json()["experimentos"][0]
    assert listed["atual"]["rodada"] == "rodada-001" and not listed["atual"]["oficial"] and listed["consultas"] == 2
    assert client.post(url, headers=HEADERS, json=changed).status_code == 409  # agora são os da rodada mostrada
    assert client.post(url, headers=HEADERS, json=same).status_code == 202  # os de 27/09 já não são os mostrados


def test_one_run_at_a_time_and_cancel_closes_the_consultation(web):
    """EXP-06 e EXP-07: uma rodada por vez; cancelar encerra o processo e fecha a consulta aberta."""
    client, settings, command = web
    command.hold = True
    url = "/api/experimentos/ae-denso-lstm/rodar"
    body = {"parametros": {"separacao": 3}, "frase": "consultar o teste"}
    job = client.post(url, headers=HEADERS, json=body).json()
    assert client.post(url, headers=HEADERS, json=body | {"parametros": {"separacao": 4}}).status_code == 409
    for _ in range(200):  # espera o processo falso abrir a consulta
        if any(c["estado"] == "iniciada" for c in registry.consultations(settings.results_dir)):
            break
        time.sleep(0.01)
    assert client.post("/api/experimentos/cancelar", headers=HEADERS).json() == {"cancelando": True}
    status = wait(client, job["tarefa"])
    assert status["estado"] == "cancelado" and status["resultado"] is None
    assert [(c["numero"], c["estado"]) for c in registry.consultations(settings.results_dir)] == [
        (1, "concluida"), (2, "cancelada")]
    assert experiments.latest(settings.results_dir, "ae-denso-lstm") is None  # a rodada parcial não aparece
    assert client.post("/api/experimentos/cancelar", headers=HEADERS).status_code == 409


def test_pdf_is_downloaded_on_request_and_compares_with_itself(web):
    """EXP-09 e EXP-10 pela interface: PDF só no pedido, sem gravar nada; comparação; arquivos ruins viram aviso."""
    pytest.importorskip("matplotlib")
    pypdf = pytest.importorskip("pypdf")
    client, settings, command = web
    before = sorted(path.name for path in settings.results_dir.rglob("*"))
    response = client.get("/api/experimentos/ae-denso-lstm/pdf")
    assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="AL-IAdo_AE-Denso-x-AE-LSTM_avaliacao-oficial.pdf"' == response.headers["content-disposition"]
    assert sorted(path.name for path in settings.results_dir.rglob("*")) == before  # nada gravado
    saved = json.loads(pypdf.PdfReader(io.BytesIO(response.content)).attachments["resultado.json"][0])
    assert saved["rodada"] == "avaliacao-oficial"
    url = "/api/experimentos/ae-denso-lstm/comparar"
    compared = client.post(url, headers=HEADERS, files={"arquivo": ("guardado.pdf", response.content)}).json()
    assert compared["iguais"] == compared["total"] > 0 and compared["guardado"]["parametros"]["sementes"] == [1, 2]
    as_json = client.post(url, headers=HEADERS, files={"arquivo": ("resultado.json", json.dumps(saved).encode())}).json()
    assert as_json["iguais"] == as_json["total"]
    assert client.post(url, headers=HEADERS, files={"arquivo": ("x.pdf", b"lixo")}).status_code == 400
    assert client.post(url, headers=HEADERS, files={"arquivo": ("x.exe", b"MZ")}).status_code == 400
    assert client.post(url, headers=HEADERS, files={"arquivo": ("x.json", b" " * (5 * 1024 * 1024 + 1))}).status_code == 413
    assert client.post(url, headers=HEADERS).status_code == 400


GPVS = ROOT / "data" / "gpvs"


@pytest.mark.skipif(not (GPVS / "proveniencia.json").is_file(), reason="Sem a base GPVS neste computador.")
def test_real_run_goes_from_zero_to_the_current_run(tmp_path, capsys):
    """EXP-02, EXP-03, EXP-06 e EXP-08 com a base real: o experimento inteiro, de ponta a ponta (5 épocas)."""
    pytest.importorskip("torch")
    from aliado.cli import main
    from aliado.science.detection import summary

    results = tmp_path / "resultados"
    args = ["experimento", "rodar", "ae-denso-lstm", "--resultados", str(results), "--base", str(GPVS),
            "--parametro", "teto_epocas=5", "--parametro", "sementes=42,13"]
    assert main(args) == 2 and "consultar o teste" in capsys.readouterr().err  # sem a frase, nada roda
    assert not results.exists()
    assert main([*args, "--frase", "consultar o teste"]) == 0
    folder = results / "ae-denso-lstm" / "rodada-001"
    result = json.loads((folder / experiments.RESULT).read_text(encoding="utf-8"))
    assert result["parametros"] == {"separacao": 11, "sementes": [13, 42], "teto_epocas": 5}
    assert result["consulta"] == 1 and not result["oficial"] and result["detalhe"]["inicio"]
    assert {path.name for path in folder.iterdir()} >= {"preparo", "modelos", "avaliacao", "inicio", "resultado.md"}
    assert summary.current(results).evaluation == folder / "avaliacao"
    assert [(c["numero"], c["estado"]) for c in registry.consultations(results)] == [(1, "concluida")]
    assert result["rotulo"].endswith("1ª vez que os dados de teste foram usados")
