"""Lote 26: os resultados da pesquisa no pedido e a conferência das marcas [R] e dos números."""

from __future__ import annotations

from types import SimpleNamespace

from aliado.agent import RESULT_REFS_WARNING, RESULTS_RULES, Agent, prepare_request
from aliado.interfaces.web.rendering import render_markdown
from aliado.llm.contracts import LLMResult, LLMStreamChunk


def block(mark: str, text: str, status: str = "oficial") -> dict:
    return {"citation_id": mark, "titulo": f"Bloco {mark}", "fonte": "Avaliação oficial de 27/09/2026", "data": "2026-09-27",
            "estatuto": status, "secao": "resumo", "texto": text,
            "notas": [{"nome": "MCC", "texto": "Resume a matriz de confusão num número de −1 a 1; 0,5 equivale a sortear."}]}


DIGEST = {"cabecalho": "A avaliação oficial é a de 27/09/2026.", "faltando": [],
          "blocos": [block("R1", "| Denso | 10 de 14 | 2,04 s | 0,402 |"),
                     block("R4", "| Falha em IGBT (F1) | 2 de 2 | 0,728 |")]}
HIT = {"citation_id": "Kabc", "title": "Baschel", "version": 1, "sha256": "x", "locator": "p. 5", "page": 5,
       "method": "text", "status": "ready", "text": "IGBT", "original": "o.pdf"}


class Library:
    def search(self, query, limit=10):
        return [dict(HIT)]

    def documents(self):
        return []


def agent(content: str) -> Agent:
    def execute(request, provider, model_alias):
        return LLMResult(content, provider, "modelo", request.task_type)

    def stream(request, provider, model_alias):
        yield LLMStreamChunk(content, provider, "modelo", request.task_type)

    return Agent(SimpleNamespace(execute=execute, stream=stream))


def ask(content: str, **kwargs) -> LLMResult:
    return agent(content).answer("Quantos ensaios?", provider="fake", model_alias="x", results=DIGEST, **kwargs)


def test_results_enter_after_the_skill_and_before_memory_and_history():
    memories = [{"id": "m1", "kind": "preferencia", "origin": "feedback", "text": "Respostas curtas."}]
    request = prepare_request("Quantos ensaios?", skill_name="pesquisa-inversores", memories=memories, results=DIGEST,
                              history=[{"role": "user", "content": "antes"}])
    roles = [(m["role"], m["content"][:40]) for m in request.messages]
    rules = next(i for i, m in enumerate(request.messages) if m["content"] == RESULTS_RULES)
    data = request.messages[rules + 1]
    assert data["role"] == "user" and data["content"].startswith("Resultados da pesquisa (dados de consulta):")
    assert '"citation_id": "R1"' in data["content"] and '"secao"' not in data["content"]
    reference = next(i for i, m in enumerate(request.messages) if m["content"].startswith("Material de referência"))
    memory = next(i for i, m in enumerate(request.messages) if m["content"].startswith("Anotações da memória"))
    assert reference < rules < memory, roles
    assert request.metadata["results"] == ["R1", "R4"] and request.tools is None
    assert "result_blocks" not in request.metadata and '"onde_ver": "aba Ciência, seção Resumo"' in data["content"]
    assert data["content"].count("equivale a sortear") == 1  # as notas vão uma vez só


def test_request_is_the_same_without_results():
    plain = prepare_request("Quantos ensaios?", skill_name="pesquisa-inversores")
    for empty in (None, {"cabecalho": "x", "blocos": [], "faltando": ["tudo"]}):
        other = prepare_request("Quantos ensaios?", skill_name="pesquisa-inversores", results=empty)
        assert other.messages == plain.messages and other.metadata == plain.metadata


def test_cited_numbers_are_checked_against_the_cited_block():
    ok = ask("O Denso detectou 10 de 14 ensaios, com atraso de 2,04 s [R1].", append_sources=False)
    assert ok.results_status == "conferido" and [b["citation_id"] for b in ok.result_sources] == ["R1"]
    assert ok.unverified_numbers == () and ok.validation_status is None
    grouped = ask("São 10 de 14 e 2 de 2 [R1, R4].", append_sources=False)
    assert "[R1][R4]" in grouped.content and [b["citation_id"] for b in grouped.result_sources] == ["R1", "R4"]
    assert grouped.results_status == "conferido"
    silent = ask("Não há números para citar.")
    assert silent.results_status == "sem_citacao" and silent.result_sources == () and silent.unmarked_numbers == 0
    unmarked = ask("O Denso detectou 12 de 14 ensaios e teve sensibilidade de 0,45.")
    assert unmarked.results_status == "sem_citacao" and unmarked.unmarked_numbers == 2  # 12 e 0,45; o 14 está no bloco
    mixed = ask("O Denso detectou 10 de 14 [R1].\nA sensibilidade foi de 0,95.", append_sources=False)
    assert mixed.results_status == "conferido" and mixed.unmarked_numbers == 1
    note = ask("O MCC vai de −1 a 1; 0,5 equivale a sortear [R4].", append_sources=False)
    assert note.results_status == "conferido"  # os números das notas enviadas valem
    table = ask("Na avaliação oficial [R1]:\n\n| Modelo | Detectou |\n|---|---|\n| Denso | 13 de 14 |", append_sources=False)
    assert table.results_status == "numeros_nao_conferidos" and table.unverified_numbers == ("13",)


def test_numbers_that_are_not_in_the_block_are_listed_and_shown():
    rounded = ask("A sensibilidade é de 0,40 [R1] e o atraso, de 2040 ms [R1].", append_sources=False)
    assert rounded.results_status == "numeros_nao_conferidos" and rounded.unverified_numbers == ("0,40", "2040")
    assert rounded.content.startswith("A sensibilidade") and "Aviso" not in rounded.content
    printed = ask("A sensibilidade é de 0,45 [R1].")
    assert printed.content.endswith("Aviso: estes números não vieram dos resultados citados: 0,45. Confira na aba Ciência.")


def test_invented_marks_block_the_answer():
    invented = ask("O valor é 5 [R9].")
    assert invented.content == RESULT_REFS_WARNING and invented.results_status == "invalid_result_refs"
    assert invented.validation_status == "invalid_result_refs" and invented.result_sources == ()


def test_document_citations_are_checked_first():
    both = ask("O artigo diz isso [Kabc] e o Denso detectou 10 de 14 [R1].", library=Library(), append_sources=False)
    assert both.validation_status == "citation_ids_verified" and both.results_status == "conferido"
    assert [s["citation_id"] for s in both.sources] == ["Kabc"]
    forged = ask("O artigo diz isso [Kzzz] e o Denso detectou 10 de 14 [R1].", library=Library())
    assert forged.validation_status == "invalid_citations" and forged.results_status is None and forged.result_sources == ()
    only_results = ask("O Denso detectou 10 de 14 [R1].", library=Library(), append_sources=False)
    assert only_results.validation_status == "uncited" and only_results.results_status == "conferido"
    # Número do documento e número do resultado na mesma linha: cada um com a sua marca.
    side = ask("Baschel et al. (2018) relatam 0,95% [Kabc]. Na sua avaliação, o Denso detectou 10 de 14 [R1].",
               library=Library(), append_sources=False)
    assert side.validation_status == "citation_ids_verified" and side.results_status == "conferido"
    # Grupos mistos são separados antes das duas conferências.
    grouped = ask("A sensibilidade foi 0,402 [Kabc,R1].", library=Library(), append_sources=False)
    assert grouped.validation_status == "citation_ids_verified" and grouped.results_status == "conferido"
    assert "[Kabc][R1]" in grouped.content
    wrong = ask("A sensibilidade foi 0,999 [R1, Kabc].", library=Library(), append_sources=False)
    assert wrong.results_status == "numeros_nao_conferidos" and wrong.unverified_numbers == ("0,999",)


def test_stream_ends_with_the_checked_result():
    events = list(agent("O Denso detectou 11 de 14 [R1].").stream_answer(
        "Quantos?", provider="fake", model_alias="x", results=DIGEST, append_sources=False))
    assert events[0] == ("texto", "O Denso detectou 11 de 14 [R1].")
    final = events[-1][1]
    assert events[-1][0] == "final" and final.results_status == "numeros_nao_conferidos" and final.unverified_numbers == ("11",)
    without = list(agent("O Denso detectou 11 de 14 [R1].").stream_answer("Quantos?", provider="fake", model_alias="x"))
    assert without[-1][1].results_status is None  # com os resultados desligados, [R] é só texto


def test_result_marks_render_only_when_the_block_was_cited():
    html = render_markdown("Detectou 10 [R1], não [R2]; fórmula $x_{[R1]}$.", result_sources=[{"citation_id": "R1"}])
    assert html.count('class="cite cite-result" data-result="R1"') == 1
    assert "[R2]" in html and "$x_{[R1]}$" in html
    assert "cite-result" not in render_markdown("Detectou 10 [R1].")


def test_cli_shows_the_request_with_the_results_without_calling_a_model(tmp_path, capsys):
    import json
    from pathlib import Path

    from aliado.cli import main

    reference = Path(__file__).resolve().parents[1] / "docs" / "pesquisa-inversores"
    assert main(["preparar", "Qual o NPR da CCB?", "--resultados", "--resultados-dir", str(tmp_path),
                 "--referencias", str(reference)]) == 0
    request = json.loads(capsys.readouterr().out)
    assert request["metadata"]["results"] == ["R7", "R8"]
    data = next(m["content"] for m in request["messages"] if m["content"].startswith("Resultados da pesquisa (dados"))
    assert "168" in data and "Não entraram neste pedido" in data  # o cabeçalho diz o que faltou
    assert "result_blocks" not in request["metadata"]
    assert main(["preparar", "Qual o NPR da CCB?"]) == 0
    assert "results" not in json.loads(capsys.readouterr().out)["metadata"]
