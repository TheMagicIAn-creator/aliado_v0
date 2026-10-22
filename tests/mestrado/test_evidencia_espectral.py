"""A evidência espectral descritiva (lote 55, EXP-14): os espectros conferidos contra os atributos, a evidência na
janela do primeiro alarme, o 4º passo do explorador e os blocos R9 e R10, sob pedido, no chat."""

from __future__ import annotations

import json
import re
import shutil

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("torch")

from apoio.caminhos import REFERENCE  # noqa: E402

from aliado import routing  # noqa: E402
from aliado.agent import _check_results, prepare_request  # noqa: E402
from aliado.llm.contracts import LLMResult  # noqa: E402
from aliado.science.espectro.decomposicao import harmonics, thd  # noqa: E402
from aliado.science.identidade.contrato import ContractViolationError  # noqa: E402
from aliado.science.resumo_citavel import formato  # noqa: E402
from aliado.specializations.mestrado.atributos.variaveis import (  # noqa: E402
    FEATURES,
    feature_vector,
)
from aliado.specializations.mestrado.avaliacao.artefatos import ERRORS, load_errors  # noqa: E402
from aliado.specializations.mestrado.base import ensaios  # noqa: E402
from aliado.specializations.mestrado.base.leitura import load_csv  # noqa: E402
from aliado.specializations.mestrado.evidencia_espectral import (  # noqa: E402
    artefatos,
    espectros,
    evidencia,
)
from aliado.specializations.mestrado.resultados import paineis, rodada_atual  # noqa: E402
from aliado.specializations.mestrado.resumo_para_o_chat import blocos  # noqa: E402

INTERNAL = re.compile(r"semente|canônic|canonic|\bM\d{2}\b|gpvs-|sha256|commit|\.json|lote \d", re.IGNORECASE)
QUESTION = "O que os harmônicos mostram no primeiro alarme da falha de IGBT?"


def _gpvs(run, folder):
    """A base sintética numa cópia, com o registro de proveniência, como a base real tem."""
    shutil.copytree(run.dados, folder)
    hashes = run.preparado.hashes
    (folder / "proveniencia.json").write_text(json.dumps({"files": {name: {"sha256": digest} for name, digest in
                                                                       hashes.items()}}), encoding="utf-8")
    return folder


def _evidence(run, gpvs):
    current = rodada_atual.current(run.resultados)
    _, errors = load_errors(current.evaluation / ERRORS)
    return current, errors, evidencia.build(current, gpvs, run.preparado, errors, origin="exploracao")


def test_the_spectra_share_the_thd_of_the_features_and_are_cached(rodada_sintetica, tmp_path, monkeypatch):
    """EXP-14: a THD dos espectros é a dos atributos, bit a bit; o cache só é refeito com outros arquivos."""
    gpvs = _gpvs(rodada_sintetica, tmp_path / "gpvs")
    window = load_csv(gpvs / "F1L.csv")[:200, 1:10]
    features = feature_vector(window)
    assert all(features[12 + i] == np.float32(thd(np.asarray(window, dtype=np.float64)[:, 3 + i])) for i in range(6))
    spectra = espectros.load_spectra(gpvs)
    assert set(spectra) == set(ensaios.FAULTY) and espectros.spectra_cache(gpvs).is_file()
    item = spectra["F1L"]
    assert item["fases"]["ia"].shape == (80, len(espectros.COLUMNS)) and not item["irregular"].any()
    a0, amplitudes = harmonics(np.asarray(window, dtype=np.float64)[:, 3])
    assert np.array_equal(item["fases"]["ia"][0, :6], [a0, *amplitudes[:5]]) and item["inicio"][1] == 200
    monkeypatch.setattr(espectros, "_trial", lambda data: pytest.fail("O cache não foi usado."))
    assert np.array_equal(espectros.load_spectra(gpvs)["F7M"]["fases"]["vc"], spectra["F7M"]["fases"]["vc"])


def test_the_evidence_reads_the_first_alarm_and_says_when_there_is_none(rodada_sintetica_copia, tmp_path):
    """EXP-14: a janela do alarme é a da aba; a fase é a do maior dos 12 erros próprios das fases; os indicadores vêm do
    espectro dela, ao lado do comissionamento; um ensaio sem alarme diz isso, sem números."""
    run = rodada_sintetica_copia
    gpvs = _gpvs(run, tmp_path / "gpvs")
    current, errors, found = _evidence(run, gpvs)
    panels = {panel["id"]: panel["modelos"] for panel in paineis.score_panels(current, gpvs)["ensaios"]}
    seed = found["treino_de_referencia"]
    for kind in evidencia.MODELS:
        for name in ensaios.FAULTY:
            item, window = found["alarmes"][kind][name], panels[name][kind]["alarme_deteccao"]
            assert item["alarme"] == window
            if window is None:
                assert item == {"alarme": None}
                continue
            row = errors[f"{kind}_s{seed}_{name}"][window]
            phase_errors = {f"{p}_{k}": row[FEATURES.index(f"{p}_{k}")] for p in espectros.PHASES for k in ("rms", "thd")}
            assert item["atributo_da_fase"] == max(phase_errors, key=phase_errors.get) and item["posicao_da_fase"] >= 1
    # Uma janela recalculada à parte, do CSV: os indicadores e o comissionamento saem dos mesmos números.
    name, kind = next((n, k) for k in evidencia.MODELS for n in ensaios.FAULTY if found["alarmes"][k][n]["alarme"])
    item = found["alarmes"][kind][name]
    phase = espectros.PRIMARY_COLUMNS.index(item["fase"])
    samples = load_csv(gpvs / f"{name}.csv")[:, 1:10]
    rows = [harmonics(np.asarray(samples[s:s + 200], dtype=np.float64)[:, phase]) for s in range(0, len(samples) // 200 * 200, 200)]
    c1 = np.array([amplitudes[0] for _, amplitudes in rows])
    reference = np.median(c1[run.preparado.faults[name]["comissionamento"]])
    a0, amplitudes = rows[item["alarme"]]
    assert item["indicadores"]["dc"] == pytest.approx(a0 / amplitudes[0], rel=1e-12)
    assert item["indicadores"]["fundamental"] == pytest.approx(amplitudes[0] / reference, rel=1e-12)
    assert item["indicadores"]["h3"] == pytest.approx(amplitudes[2] / amplitudes[0], rel=1e-12)
    assert item["comissionamento"]["fundamental"] == pytest.approx(1.0, abs=0.05)
    # A tabela: os dois que mais mudam em cada ensaio, pelo tamanho da mudança.
    for name, entries in found["mais_mudam"].items():
        table = found["tabela"][name]
        sizes = sorted((abs(values["mudanca"]) for phase in table.values() for values in phase.values()), reverse=True)
        assert [abs(entry["mudanca"]) for entry in entries] == sizes[:2]
    assert json.loads(json.dumps(found, allow_nan=False)) == found
    assert found["janelas_antes_da_mudanca"] == dict.fromkeys(ensaios.FAULTY)  # sem a reanálise, nada a dizer
    changed = dict(errors) | {f"lstm_s{seed}_F3M": errors[f"lstm_s{seed}_F3M"] * np.float32(1.5)}
    with pytest.raises(ContractViolationError, match="não dá os escores salvos"):
        evidencia.build(current, gpvs, run.preparado, changed, origin="exploracao")
    # O PDF de uma rodada com a evidência ganha a seção dela; o de uma rodada sem ela não muda.
    pytest.importorskip("matplotlib")
    pytest.importorskip("pypdf")
    from aliado.experiments import pdf
    from aliado.specializations.mestrado.rodada import experimento

    plain = experimento.legacy(run.resultados)
    with_evidence = plain | {"detalhe": plain["detalhe"] | {
        "evidencia_espectral": {key: found[key] for key in artefatos.SUMMARY_KEYS}}}
    titles = [block.get("titulo") for block in experimento.report(with_evidence) if block["tipo"] == "secao"]
    assert "Evidência espectral no primeiro alarme" in titles
    assert "Evidência espectral no primeiro alarme" not in str(experimento.report(plain))
    assert pdf.render(with_evidence, experimento.report(with_evidence))[:5] == b"%PDF-"


def test_the_explorer_builds_it_outside_the_results_for_a_run_without_it(rodada_sintetica_copia, tmp_path, monkeypatch):
    """EXP-14: numa rodada anterior, o 4º passo do "Preparar" grava a evidência na pasta dos exploradores, como
    exploração pós-teste; nada muda em data/resultados."""
    from aliado.specializations.mestrado.exploradores.explorador import Explorer

    run = rodada_sintetica_copia
    gpvs = _gpvs(run, tmp_path / "gpvs")
    before = sorted(path.relative_to(run.resultados).as_posix() for path in run.resultados.rglob("*"))
    explorer = Explorer(run.resultados, gpvs, tmp_path / "ciencia")
    assert explorer.status()["evidencia_espectral"] == {"pronta": False, "origem": None, "erro": None}
    steps = []
    explorer.prepare(lambda stage, current, total: steps.append((stage, current, total)))
    assert steps[-2:] == [("evidência espectral", 3, 4), ("pronto", 4, 4)]
    assert explorer.status()["evidencia_espectral"] == {"pronta": True, "origem": "exploracao", "erro": None}
    saved = artefatos.read(tmp_path / "ciencia" / "evidencia-espectral-avaliacao-oficial-gpvs-avaliacao-001.json")
    assert saved["origem"] == "exploracao" and saved["rodada"] == "avaliacao-oficial"
    assert sorted(path.relative_to(run.resultados).as_posix() for path in run.resultados.rglob("*")) == before

    def broken(*args, **kwargs):
        raise ContractViolationError("A matriz de erros de lstm em F3M não dá os escores salvos.")

    monkeypatch.setattr(evidencia, "build", broken)
    again = Explorer(run.resultados, gpvs, tmp_path / "ciencia")
    again.prepare()  # a evidência é secundária: a falha fica no estado, com o motivo, e os exploradores seguem
    assert again.status()["evidencia_espectral"]["erro"] == "A matriz de erros de lstm em F3M não dá os escores salvos."
    assert again.threshold("denso", 3, 5, 90.0)["janela"]


def test_r9_and_r10_go_to_the_model_only_when_asked(rodada_sintetica_copia, tmp_path):
    """EXP-14: R9 e R10 só existem com o arquivo da evidência e só vão nas perguntas sobre o assunto; os outros blocos
    não mudam, e quem copia o R9 com a marca dele tem os números conferidos."""
    run = rodada_sintetica_copia
    gpvs = _gpvs(run, tmp_path / "gpvs")
    data_dir = tmp_path / "dados"
    without = blocos.cached(run.resultados, REFERENCE, data_dir)
    assert not {"R9", "R10"} & {block["citation_id"] for block in without["blocos"]}
    current, _, found = _evidence(run, gpvs)
    artefatos.write(found, artefatos.exploration_file(data_dir / "ciencia", current))
    digest = blocos.cached(run.resultados, REFERENCE, data_dir)
    assert digest is not without  # a assinatura muda quando a evidência aparece
    marks = [block["citation_id"] for block in digest["blocos"]]
    assert marks[-4:] == ["R7", "R8", "R9", "R10"]
    by_id = {block["citation_id"]: block for block in digest["blocos"]}
    by_id_before = {block["citation_id"]: block for block in without["blocos"]}
    assert by_id["R7"] == by_id_before["R7"] and by_id["R1"] == by_id_before["R1"]
    spectral = [by_id["R9"], by_id["R10"]]
    assert all(block["sob_pedido"] == blocos.SPECTRAL_TERMS and block["estatuto"] == "exploracao" for block in spectral)
    assert all(block["secao"] == "explorar" and not INTERNAL.search(formato.block_text(block)) for block in spectral)
    assert "sem alarme" in by_id["R9"]["texto"] or all(item["alarme"] is not None for model in found["alarmes"].values()
                                                       for item in model.values())
    assert by_id["R9"]["texto"].startswith("| Ensaio | Modelo |") and by_id["R10"]["texto"].startswith("| Ensaio | Falha |")
    assert routing.results_vocabulary(digest)["modelos"] == {"denso", "ae-lstm"}
    # Os blocos de sempre ficam no limite; R9 e R10 só somam quando pedidos.
    always = digest | {"blocos": [block for block in digest["blocos"] if "sob_pedido" not in block]}
    assert len(formato.prompt_text(always)) <= blocos.MAX_CHARS
    assert sum(len(formato.block_text(block)) for block in spectral) <= 7_500
    assert prepare_request("Qual a sensibilidade do Denso?", results=digest).metadata["results"] == marks[:-2]
    assert prepare_request(QUESTION, results=digest).metadata["results"] == marks
    copied = next(line for line in by_id["R9"]["texto"].splitlines() if "| F" in line and "sem alarme" not in line)
    checked = _check_results(LLMResult(f"{copied} [R9]", "fake", "x", "critical_reasoning"), spectral, False)
    assert checked.results_status == "conferido" and not checked.unverified_numbers
