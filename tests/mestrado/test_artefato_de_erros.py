"""A identidade da rodada e a matriz de erros por variável (lote 54, EXP-13): o que a avaliação grava, o que o
explorador lê e como as rodadas anteriores ao contrato continuam abrindo."""

from __future__ import annotations

import json
import shutil

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("torch")

from apoio.caminhos import RESULTS  # noqa: E402

from aliado import experiments  # noqa: E402
from aliado.science.deteccao.escore.top_k import top_k_scores  # noqa: E402
from aliado.science.identidade.contrato import PRIOR, ContractViolationError  # noqa: E402
from aliado.specializations.mestrado.atributos import variaveis  # noqa: E402
from aliado.specializations.mestrado.avaliacao.artefatos import (  # noqa: E402
    ERRORS,
    export_evaluation,
    load_errors,
)
from aliado.specializations.mestrado.avaliacao.configuracao import EvaluationConfig  # noqa: E402
from aliado.specializations.mestrado.avaliacao.pontuacao import score_all  # noqa: E402
from aliado.specializations.mestrado.avaliacao.treino_congelado import load_training  # noqa: E402
from aliado.specializations.mestrado.base import ensaios  # noqa: E402
from aliado.specializations.mestrado.inicio_das_falhas.estimativa import OnsetConfig  # noqa: E402
from aliado.specializations.mestrado.rodada import experimento  # noqa: E402
from aliado.specializations.mestrado.rodada.apresentacao import (  # noqa: E402
    IDENTITY_LABELS,
    identity_rows,
)
from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig  # noqa: E402

PRIOR_TEXT = "não gravado (anterior ao contrato)"


def _bits(array) -> tuple:
    return array.dtype.str, array.shape, array.tobytes()


def test_the_three_configuration_hashes_did_not_change_when_merged():
    """EXP-13: as três cópias do hash da configuração viraram uma só, com os mesmos valores de antes."""
    assert ExperimentConfig().digest() == "be9e54fa5d2100814908d3178a6f2aa9073cd494a12de23d1552a702f36a73d8"
    assert EvaluationConfig().digest() == "ce8b06e483a0270dc2002714c7c3afa79406976255b8bd9b8a429b3a5bbdc2fc"
    assert OnsetConfig().digest() == "1510880c26336589a95afb6a5f4df09ddeb8f73f32f1f0f0ebe4ee7cfb677bdf"


def test_the_evaluation_saves_the_error_matrix_that_gives_the_scores(rodada_sintetica):
    """EXP-13: `erros.npz` traz a matriz de cada modelo e repetição, e os k maiores dela dão, bit a bit, os escores da
    avaliação e os da calibração, em todo k da grade."""
    data = rodada_sintetica.preparado
    meta, arrays = load_errors(rodada_sintetica.avaliacao / ERRORS)
    summary = json.loads((rodada_sintetica.treino / "relatorio.json").read_text(encoding="utf-8"))
    frozen = json.loads((rodada_sintetica.treino / "configuracao.json").read_text(encoding="utf-8"))
    assert meta["contrato"] == 1 and meta["variaveis"] == list(variaveis.FEATURES)
    assert meta["treino"] == frozen["sha256"] and meta["avaliacao"] == EvaluationConfig(resamples=200).digest()
    assert meta["dados"] == data.hashes and meta["janela"]["amostras"] == ensaios.WINDOW == 200
    assert meta["pesos"] == {f"{kind}_s{seed}": summary["modelos"][kind]["sementes"][str(seed)]["arquivos"]["modelo"]["sha256"]
                             for kind in ("denso", "lstm") for seed in (3, 4)}
    # Os trechos contam as janelas de cada ensaio a partir de 0: o teste saudável é o fim do ensaio saudável.
    for name in ensaios.HEALTHY:
        (test,) = meta["trechos"][f"saudavel_{name}"]
        assert test["ensaio"] == name and test["fim"] == int((data.healthy_experiment == name).sum())
        assert test["fim"] - test["inicio"] == len(data.split["por_ensaio"][name]["test"])
    assert meta["trechos"]["F1L"] == [{"ensaio": "F1L", "inicio": 0, "fim": len(data.faults["F1L"]["scaled"])}]
    with np.load(rodada_sintetica.avaliacao / "escores.npz") as scores, \
            np.load(rodada_sintetica.treino / "escores_calibracao.npz") as calibration:
        for kind in ("denso", "lstm"):
            for seed in (3, 4):
                key = f"{kind}_s{seed}"
                for k in (5, 10, 20):
                    assert _bits(top_k_scores(arrays[f"{key}_calibracao"], k)) == _bits(calibration[f"{key}_k{k}"])
                    for name in ensaios.HEALTHY:
                        assert _bits(top_k_scores(arrays[f"{key}_saudavel_{name}"], k)) == \
                            _bits(scores[f"{key}_k{k}_saudavel_{name}"])
                    for name in ensaios.FAULTY:
                        assert _bits(top_k_scores(arrays[f"{key}_{name}"], k)) == _bits(scores[f"{key}_k{k}_{name}"])


def test_a_changed_error_matrix_breaks_the_contract(rodada_sintetica, tmp_path):
    """EXP-13: sem um campo, com as variáveis em outra ordem, com versão desconhecida ou com matrizes que não são as dos
    metadados, a leitura recusa o arquivo com o motivo; nada é suposto."""
    meta, arrays = load_errors(rodada_sintetica.avaliacao / ERRORS)
    first = sorted(arrays)[0]
    cases = [({key: value for key, value in meta.items() if key != "pesos"}, arrays, "faltam os campos do contrato pesos"),
             (meta | {"variaveis": meta["variaveis"][::-1]}, arrays, "variáveis"),
             (meta | {"contrato": 2}, arrays, "versão 2"),
             ({key: value for key, value in meta.items() if key != "contrato"}, arrays, "versão do contrato"),
             (meta | {"trechos": {"F1L": [{"ensaio": "F1L"}]}}, arrays, "fora do formato"),
             (meta, arrays | {"extra": arrays[first]}, "não são as dos metadados"),
             (meta, arrays | {first: arrays[first].astype(np.float64)}, "formato inesperado"),
             (meta, arrays | {first: arrays[first][1:]}, "formato inesperado")]
    for number, (changed, matrices, message) in enumerate(cases):
        path = tmp_path / f"{number}.npz"
        np.savez_compressed(path, meta=np.array(json.dumps(changed)), **matrices)
        with pytest.raises(ContractViolationError, match=message):
            load_errors(path)
    np.savez_compressed(tmp_path / "sem-meta.npz", **arrays)
    with pytest.raises(ContractViolationError, match="faltam os metadados"):
        load_errors(tmp_path / "sem-meta.npz")


def test_scores_that_the_matrix_does_not_give_are_refused_before_saving(rodada_sintetica, tmp_path):
    """EXP-13: a avaliação recalcula a matriz à parte e confere os escores bit a bit; um só valor diferente impede a
    gravação da matriz."""
    detectors = load_training(rodada_sintetica.treino)
    scores = score_all(detectors, rodada_sintetica.preparado)
    changed = scores[("denso", 3, 5)]["ensaios"]["F1L"].copy()
    changed[0] = np.nextafter(changed[0], np.inf)
    scores[("denso", 3, 5)]["ensaios"]["F1L"] = changed
    with pytest.raises(ContractViolationError, match="os 5 maiores erros de denso_s3_F1L não dão os escores"):
        export_evaluation(scores, detectors, rodada_sintetica.preparado, EvaluationConfig(resamples=200),
                          tmp_path / "avaliacao")
    assert not (tmp_path / "avaliacao" / ERRORS).exists()


def test_the_explorer_reads_the_saved_matrix_without_recomputing(rodada_sintetica_copia, tmp_path, monkeypatch):
    """EXP-13: com um `erros.npz` válido, o explorador usa a matriz gravada, sem recalcular nem gravar cache; com um
    de outra rodada, recusa com o erro de contrato e não recalcula por conta própria."""
    from aliado.specializations.mestrado.avaliacao import pontuacao
    from aliado.specializations.mestrado.exploradores.explorador import Explorer

    run = rodada_sintetica_copia
    gpvs = tmp_path / "gpvs"
    shutil.copytree(run.dados, gpvs)
    (gpvs / "proveniencia.json").write_text(json.dumps({"files": {name: {"sha256": digest} for name, digest in
                                                                  run.preparado.hashes.items()}}), encoding="utf-8")
    monkeypatch.setattr(pontuacao, "errors_all", lambda *args: pytest.fail("A matriz gravada foi recalculada."))
    explorer = Explorer(run.resultados, gpvs, tmp_path / "cache")
    assert explorer.evaluation_dir.resolve() == run.avaliacao.resolve()
    explorer.prepare()
    threshold = explorer.threshold("lstm", 4, 5, 90.0)
    assert threshold["limiar"]["limiar"] == threshold["canonico"]["limiar"]
    assert not (tmp_path / "cache").exists()

    meta, arrays = load_errors(run.avaliacao / ERRORS)
    other = meta | {"pesos": meta["pesos"] | {"denso_s3": "0" * 64}}
    np.savez_compressed(run.avaliacao / ERRORS, meta=np.array(json.dumps(other)), **arrays)
    with pytest.raises(ContractViolationError, match="não é desta rodada"):
        Explorer(run.resultados, gpvs, tmp_path / "cache").prepare()


def test_runs_before_the_contract_say_so_and_new_ones_need_every_field():
    """EXP-13: sem a identidade, ou com a marca de anterior ao contrato, o PDF diz "não gravado"; uma rodada que declara
    o contrato precisa de todos os campos."""
    prior = [[label, PRIOR_TEXT] for label in IDENTITY_LABELS]
    assert identity_rows({}) == identity_rows({"identidade": {"contrato": None, "estado": PRIOR}}) == prior
    full = {"contrato": 1, "codigo": {"estado": "registrado", "commit": "a" * 40, "alteracoes_locais": True},
            "pesos": {"denso_s42": "b" * 64, "lstm_s42": "d" * 64}, "variaveis": list(variaveis.FEATURES), "janela": {},
            "erros_sha256": "c" * 64}
    assert identity_rows({"identidade": full}) == [
        [IDENTITY_LABELS[0], "a" * 16 + ", com alterações locais"],
        [IDENTITY_LABELS[1], "2 arquivos conferidos; os códigos completos estão no JSON anexo"],
        [IDENTITY_LABELS[2], "c" * 16]]
    absent = {"estado": "git ausente", "commit": None, "alteracoes_locais": None}
    assert identity_rows({"identidade": full | {"codigo": absent}})[0] == [IDENTITY_LABELS[0], "git ausente"]
    with pytest.raises(ContractViolationError, match="faltam os campos do contrato codigo, pesos"):
        identity_rows({"identidade": {key: value for key, value in full.items() if key not in {"codigo", "pesos"}}})
    with pytest.raises(ContractViolationError, match="commit"):
        identity_rows({"identidade": full | {"codigo": {"estado": "registrado", "alteracoes_locais": False}}})
    with pytest.raises(ContractViolationError, match="versão 2"):
        identity_rows({"identidade": {"contrato": 2}})


@pytest.mark.dados_reais
def test_the_official_run_and_an_old_result_still_compare_and_become_a_pdf(official_results):
    """EXP-13: a avaliação de 27/09 e a rodada-002 são anteriores ao contrato; continuam comparando e virando PDF."""
    pytest.importorskip("matplotlib")
    pytest.importorskip("pypdf")
    from aliado.experiments import pdf

    official = experiments.current(official_results, experimento)
    assert official["oficial"] and official["identidade"] == {"contrato": None, "estado": PRIOR}
    saved = RESULTS / experimento.KEY / "rodada-002" / experiments.RESULT
    old = json.loads(saved.read_text(encoding="utf-8")) if saved.is_file() else None
    for result in (official, old) if old else (official,):
        assert identity_rows(result) == [[label, PRIOR_TEXT] for label in IDENTITY_LABELS]
        assert pdf.render(result, experimento.report(result))[:5] == b"%PDF-"
    if old is None:
        pytest.skip("Sem a rodada-002 neste computador.")
    assert "identidade" not in old
    compared = experiments.compare(old, official)
    assert compared["total"] > 0 and compared["iguais"] == compared["total"]
