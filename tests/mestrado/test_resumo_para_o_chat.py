"""Lote 26: resumo dos resultados da pesquisa para o chat (blocos [R1]…[R8])."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from apoio.caminhos import REFERENCE, RESULTS, ROOT

from aliado.science.resumo_citavel import formato as core
from aliado.specializations.mestrado.resumo_para_o_chat import blocos

INTERNAL = re.compile(r"semente|canônic|canonic|\bM\d{2}\b|gpvs-|sha256|commit|\.json|lote \d", re.IGNORECASE)
SUMMARY = {"detectados": 10, "atraso_mediano_ms": 1000.0, "sensibilidade_media": 0.5, "especificidade_media": 0.5,
           "precisao_media": 0.5, "f1_media": 0.5, "acuracia_balanceada_media": 0.5, "mcc_media": 0.5,
           "auc_roc_media": 0.5, "auc_pr_media": 0.5}
COMPARISON = [{"objetivo": "Detecta mais falhas", "metrica": "sensibilidade", "maior_e_melhor": True, "media": 0.02,
               "ic95": [-0.01, 0.04], "n": 14, "leitura": "sem diferença clara"}]


def synthetic_results(root: Path, *, reanalysis: bool = True, training: bool = True) -> Path:
    """Avaliação sintética (a de test_science_views), o treino com a posição do limiar e, se pedida, a reanálise."""
    pytest.importorskip("numpy")
    from apoio.avaliacao_sintetica import synthetic

    from aliado.specializations.mestrado.base import ensaios
    from aliado.specializations.mestrado.resultados import rodada_atual

    synthetic(root)
    official = root / rodada_atual.EVALUATION / "relatorio.json"
    report = json.loads(official.read_text(encoding="utf-8"))
    trials = {name: {"detectado": True, "atraso_ms": 1000.0, "sensibilidade": 0.5, "especificidade": 0.9}
              for name in ensaios.FAULTY}
    for model in report["modelos"].values():
        model["referencia"]["ensaios"] = trials
    official.write_text(json.dumps(report), encoding="utf-8")
    if training:
        folder = root / "gpvs-modelos-002"
        folder.mkdir()
        limit = {"sementes": {"2": {"limiar": {"posicao": 191, "n_calibracao": 192}}}}
        (folder / "relatorio.json").write_text(json.dumps({"modelos": {"denso": limit, "lstm": limit}}), encoding="utf-8")
    if reanalysis:
        folder = root / "gpvs-reanalise-001"
        folder.mkdir()
        after = {name: item | {"atraso_ms": 60.0, "atraso_desde_o_meio_ms": 1000.0} for name, item in trials.items()}
        model = {"referencia": {"resumo": SUMMARY, "ensaios": after}}
        brief = {"comparacao": COMPARISON, "modelos": {kind: {"resumo": SUMMARY} for kind in ("denso", "lstm")}}
        estimate = {"alarmes_por_hora": 19.4, "ic95": [0.0, 53.4], "p01": 0.02, "p11": 0.07,
                    "previsto": {"sequencias_de_2": 3.88, "alarmes": 0.28}, "observado": {"sequencias_de_2": 4, "alarmes": 0}}
        data = {
            "origem": {"avaliacao": rodada_atual.EVALUATION}, "comparacao": COMPARISON,
            "modelos": {"denso": model, "lstm": model},
            "inicio": {"penalidade_c": 4.0, "controle_saudavel": {"F0L": {"4.0": 0}, "F0M": {"4.0": 0}},
                       "ensaios": {name: {"classe": "clara" if name < "F4" else "nenhuma", "nominal_s": 7.2,
                                          "observado_s": 8.66 if name < "F4" else None, "janelas": 720}
                                   for name in ensaios.FAULTY}},
            "so_mudanca_clara": {"ensaios": [n for n in ensaios.FAULTY if n < "F4"], **brief, "meio": brief},
            "alarmes_estimados": {"denso": estimate, "lstm": estimate},
        }
        (folder / "relatorio.json").write_text(json.dumps(data), encoding="utf-8")
        (folder / "configuracao.json").write_text(json.dumps({"executado_em": "2026-09-30"}), encoding="utf-8")
    return root


def ids(result):
    return [block["citation_id"] for block in result["blocos"]]


def test_notes_are_the_ones_of_the_science_tab():
    """Lote 36: o glossário da aba e as notas do resumo são um só, o da especialização; a aba o lê de /api/ciencia."""
    static = ROOT / "src" / "aliado" / "interfaces" / "web" / "static"
    assert "const GLOSSARIO = {};" in (static / "graficos.js").read_text(encoding="utf-8")
    assert "Object.assign(GLOSSARIO, science.status.notas || {});" in (static / "ciencia.js").read_text(encoding="utf-8")
    assert blocos.NOTES and set(blocos.NOTE_NAMES) <= set(blocos.NOTES)


def test_eight_blocks_with_source_date_and_status(tmp_path):
    result = blocos.build_digest(synthetic_results(tmp_path / "resultados"), REFERENCE)
    assert ids(result) == [f"R{n}" for n in range(1, 9)] and result["faltando"] == []
    status = {block["citation_id"]: block["estatuto"] for block in result["blocos"]}
    assert {mark for mark, value in status.items() if value == "secundaria"} == {"R5", "R6"}
    assert all(block["fonte"] and block["titulo"] and block["texto"] for block in result["blocos"])
    assert {block["secao"] for block in result["blocos"]} <= {"resumo", "metricas", "inicio", "fmeca", "confiabilidade"}
    by_id = {block["citation_id"]: block for block in result["blocos"]}
    assert by_id["R1"]["data"] == "2026-09-27" and by_id["R5"]["data"] == "2026-09-30"
    assert "| Ensaios detectados, de 14 | 10 (faixa: 9 a 10) |" in by_id["R1"]["texto"] and "1 s" in by_id["R1"]["texto"]
    assert "Secundária" in by_id["R5"]["fonte"] and "8,66 s" in by_id["R5"]["texto"]
    assert "168" in by_id["R7"]["texto"] and "63,7e-6/h" in by_id["R7"]["texto"]
    assert "99,091%" in by_id["R8"]["texto"] and "80,4 h" in by_id["R8"]["texto"]
    text = core.prompt_text(result)
    assert len(text) <= blocos.MAX_CHARS and not INTERNAL.search(text)
    assert "secao" not in json.loads(text)["blocos"][0] and result["cabecalho"].startswith("A avaliação oficial é a de 27/09/2026")


def test_every_indicator_has_its_note_and_notes_go_once_to_the_model(tmp_path):
    result = blocos.build_digest(synthetic_results(tmp_path / "resultados"), REFERENCE)
    by_id = {block["citation_id"]: block for block in result["blocos"]}
    names = {mark: [note["nome"] for note in block["notas"]] for mark, block in by_id.items()}
    assert {"Sensibilidade", "Especificidade", "Precisão", "F1", "Acurácia balanceada", "MCC", "AUC-ROC", "AUC-PR"} <= set(names["R1"])
    assert {"Sensibilidade", "Especificidade", "MCC", "Atraso"} <= set(names["R4"])  # o R4 traz as próprias notas
    assert {"Sensibilidade", "F1", "AUC-ROC", "Mudança observada"} <= set(names["R5"])
    assert all("Notas:" not in block["texto"] and "bloco R1" not in block["texto"] for block in result["blocos"])
    sent = json.loads(core.prompt_text(result))
    assert sent["notas"]["Sensibilidade"] == blocos.NOTES["sensibilidade"] and "notas" not in sent["blocos"][0]
    assert core.prompt_text(result).count(blocos.NOTES["sensibilidade"]) == 1
    assert "0,5" in core.notes_text(result["blocos"])


def test_each_block_says_where_to_see_it_with_the_names_of_the_science_tab(tmp_path):
    page = (ROOT / "src" / "aliado" / "interfaces" / "web" / "static" / "ciencia.js").read_text(encoding="utf-8")
    tabs = dict(re.findall(r'\["(\w+)", "([^"]+)"\]', page.split("const SCIENCE_TABS")[1].split("];")[0]))
    assert all(tabs[key] == name for key, name in core.SECTIONS.items())
    from aliado.agent import RESULTS_RULES

    assert all(name in RESULTS_RULES for name in core.SECTIONS.values())
    sent = json.loads(core.prompt_text(blocos.build_digest(synthetic_results(tmp_path / "resultados"), REFERENCE)))
    assert {block["citation_id"]: block["onde_ver"] for block in sent["blocos"]}["R4"] == "aba Ciência, seção Métricas por falha"


def test_missing_pieces_leave_the_other_blocks_and_say_what_is_missing(tmp_path, monkeypatch):
    no_reanalysis = blocos.build_digest(synthetic_results(tmp_path / "a", reanalysis=False), REFERENCE)
    assert ids(no_reanalysis) == ["R1", "R2", "R3", "R4", "R7", "R8"]
    assert "reanálise" in no_reanalysis["faltando"][0] and "Não entraram neste pedido" in no_reanalysis["cabecalho"]
    # Sem a pasta do treino, o R6 fica só com a estimativa.
    no_training = blocos.build_digest(synthetic_results(tmp_path / "b", training=False), REFERENCE)
    r6 = next(block for block in no_training["blocos"] if block["citation_id"] == "R6")
    assert "19,4" in r6["texto"] and "| — | — |" in r6["texto"] and no_training["faltando"] == []
    assert [note["nome"] for note in r6["notas"]] == ["Alarmes falsos estimados"]
    # Reanálise quebrada (é secundária): os blocos oficiais ficam.
    for name, content in (("c", '{"origem": {'), ("d", json.dumps({"origem": {"avaliacao": "gpvs-avaliacao-001"}}))):
        broken = synthetic_results(tmp_path / name)
        (broken / "gpvs-reanalise-001" / "relatorio.json").write_text(content, encoding="utf-8")
        result = blocos.build_digest(broken, REFERENCE)
        assert ids(result) == ["R1", "R2", "R3", "R4", "R7", "R8"] and "reanálise" in result["faltando"][0], name
    # Arquivo da avaliação truncado: o GPVS sai, e a FMECA e a confiabilidade continuam.
    truncated = synthetic_results(tmp_path / "e")
    table = truncated / "gpvs-avaliacao-001" / "metricas_por_ensaio.csv"
    table.write_text(table.read_text(encoding="utf-8") + "denso,2,F1L,True,1.0,5\n", encoding="utf-8")
    result = blocos.build_digest(truncated, REFERENCE)
    assert ids(result) == ["R7", "R8"] and "incompletos" in result["faltando"][0]
    no_evaluation = blocos.build_digest(tmp_path / "vazio", REFERENCE)
    assert ids(no_evaluation) == ["R7", "R8"] and "avaliação oficial" in no_evaluation["faltando"][0]

    def without_numpy(results_dir, explorer_dir=None):
        raise ImportError("numpy")

    monkeypatch.setattr(blocos, "_gpvs_blocks", without_numpy)
    no_numpy = blocos.build_digest(tmp_path / "a", REFERENCE)
    assert ids(no_numpy) == ["R7", "R8"] and "numpy" in no_numpy["faltando"][0]
    nothing = blocos.build_digest(tmp_path / "a", tmp_path / "sem-referencias")
    assert nothing["blocos"] == [] and len(nothing["faltando"]) == 3


def test_cache_is_rebuilt_only_when_a_source_file_changes(tmp_path):
    reference = tmp_path / "referencias"
    shutil.copytree(REFERENCE, reference)
    first = blocos.cached(tmp_path / "vazio", reference)
    assert blocos.cached(tmp_path / "vazio", reference) is first
    table = reference / "fmeca.json"
    stamp = table.stat().st_mtime_ns + 5_000_000_000
    os.utime(table, ns=(stamp, stamp))
    assert blocos.cached(tmp_path / "vazio", reference) is not first


def test_digest_and_interface_open_without_numpy_or_torch():
    code = ("import sys; sys.modules['numpy'] = None; sys.modules['torch'] = None\n"
            "import aliado.interfaces.web.app\n"
            "from aliado.specializations.mestrado.resumo_para_o_chat import blocos\n"
            f"d = blocos.build_digest(r'{RESULTS}', r'{REFERENCE}')\n"
            "print([b['citation_id'] for b in d['blocos']], len(d['faltando']))")
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "['R7', 'R8'] 1"


def test_real_digest_has_the_numbers_of_the_science_tab(official_results):
    pytest.importorskip("numpy")
    result = blocos.build_digest(official_results, REFERENCE)
    assert ids(result) == [f"R{n}" for n in range(1, 9)] and result["faltando"] == []
    by_id = {block["citation_id"]: block["texto"] for block in result["blocos"]}
    assert "| Ensaios detectados, de 14 | 10 (faixa: 9 a 10) | 8 (faixa: 8 a 9) |" in by_id["R1"]
    assert "2,04 s" in by_id["R1"] and "0,402" in by_id["R1"] and "| Denso | 0 | 52,2 s | 0 | 207 |" in by_id["R2"]
    assert "0,06 s" in by_id["R5"] and "1,000" in by_id["R5"] and "| Denso | 19,4 | 0 a 53,4 |" in by_id["R6"]
    assert "168" in by_id["R7"] and "99,091%" in by_id["R8"]
    text = core.prompt_text(result)
    assert len(text) <= blocos.MAX_CHARS and not INTERNAL.search(text)
