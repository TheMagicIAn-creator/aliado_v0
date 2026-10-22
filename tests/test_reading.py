"""Lote 30: leitura integral — a busca escolhe os documentos, e o modelo recebe páginas inteiras."""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from test_figures import Sentences

from aliado.agent import LIBRARY_RULES, PASSAGES_NOTE, READING_RULES, Agent, prepare_request
from aliado.knowledge import reading
from aliado.knowledge.library import DocumentLibrary
from aliado.llm.contracts import LLMResult

pytest.importorskip("pypdf")
pytest.importorskip("pypdfium2")

# Nomes sem números: linhas que só mudam nos dígitos seriam tiradas como cabeçalho repetido.
NAMES = ["abacate", "banana", "caju", "damasco", "figo", "goiaba", "jaca", "kiwi", "laranja", "manga", "nectarina",
         "pitanga", "romã", "tamarindo", "uva"]


def make_pdf(path, pages: list[str]) -> None:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica"),
                             NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 9 Tf 40 770 Td ({text}) Tj ET".encode("cp1252"))
        page[NameObject("/Contents")] = writer._add_object(stream)  # o pdfium só lê o conteúdo por referência
    writer.write(path)


def texts(count: int, special: dict[int, str]) -> list[str]:
    return [f"Capitulo {NAMES[index]} sobre manutencao.{' ' + special[index + 1] if index + 1 in special else ''}"
            for index in range(count)]


@pytest.fixture
def shelf(tmp_path):
    """Um livro de 12 páginas, com o alfa na página 7, e um artigo de 3 páginas, sem ele."""
    make_pdf(tmp_path / "livro.pdf", texts(12, {7: "O alfa aparece aqui."}))
    make_pdf(tmp_path / "artigo.pdf", texts(3, {2: "O beta aparece aqui."}))
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences())
    book, article = library.add(tmp_path / "livro.pdf"), library.add(tmp_path / "artigo.pdf")
    return SimpleNamespace(library=library, book=book, article=article, root=tmp_path)


def options(**changes) -> dict:
    return {"budget": 400_000, "fixed": [], "whole": True, "search": True} | changes


def sent(request) -> list[list[dict]]:
    """As mensagens de documento do pedido: as que seguem em partes."""
    return [message["content"] for message in request.messages if isinstance(message["content"], list)]


def test_share_gives_fixed_documents_what_they_need_and_caps_the_others():
    assert reading.share([100, 100], 1000) == [100, 100]
    # O primeiro da busca leva um quarto do teto, os seguintes entram, e a sobra volta para ele.
    assert reading.share([900, 100, 100], 1000) == [800, 100, 100]
    assert reading.share([900, 300, 300, 300, 300], 1000) == [250, 250, 250, 250, 0]
    # O fixado na conversa não tem limite por documento.
    assert reading.share([900, 300], 1000, fixed=1) == [900, 100]
    assert reading.share([2000, 300], 1000, fixed=1) == [1000, 0]
    # Todo documento da busca recebe o seu mínimo antes de os primeiros crescerem.
    assert reading.share([900] * 6, 1000, floors=[60] * 6) == [250, 250, 250, 130, 60, 60]
    assert reading.share([900] * 6, 1000) == [250, 250, 250, 250, 0, 0]
    assert reading.share([500] * 5, 1000, floors=[300] * 5) == [300, 300, 300, 100, 0]
    assert reading.share([900, 300, 300], 1000, fixed=1, floors=[0, 50, 80]) == [900, 50, 50]
    for costs, fixed in (([5000, 10, 4000, 3], 0), ([700, 700, 700], 2), ([0, 0], 1), ([], 0)):
        for floors in (None, [40] * len(costs), [9000] * len(costs)):
            allowances = reading.share(costs, 1000, fixed, floors)
            assert sum(allowances) <= 1000 and all(0 <= a <= c for a, c in zip(allowances, costs, strict=True))


def test_ranges_and_spans_describe_the_blocks():
    assert reading.ranges([5, 3, 4, 9, 9]) == [(3, 5), (9, 9)]
    assert reading.spans([(3, 5)]) == "3–5" and reading.spans([(3, 5), (9, 9)]) == "3–5 e 9"
    assert reading.spans([(3, 5), (9, 9), (12, 14)]) == "3–5, 9 e 12–14" and reading.spans([]) == ""


def test_small_documents_are_one_block_and_large_ones_have_fixed_blocks():
    assert reading.blocks_of(list(range(1, 41))) == [list(range(1, 41))]
    assert [(block[0], block[-1]) for block in reading.blocks_of(list(range(1, 46)))] == [(1, 10), (11, 20), (21, 30), (31, 40), (41, 45)]
    assert reading.blocks_of(list(range(1, 90)), pdf=False) == [list(range(1, 90))]  # texto: sempre inteiro


def test_fit_starts_at_the_found_pages_and_grows_to_the_neighbours():
    costs = {page: 10 for page in range(1, 21)}
    assert reading.fit(costs, [10], 30) == [9, 10, 11]
    assert reading.fit(costs, [10, 3], 50) == [2, 3, 4, 9, 10]
    assert reading.ranges(reading.fit(costs, [10, 12], 50)) == [(9, 13)]  # blocos encostados viram um só
    assert reading.fit(costs, [], 30) == [1, 2, 3]  # sem página achada, começa pela primeira
    assert reading.fit(costs, [10], 9) == [] and reading.fit(costs, [99], 30) == []


def test_select_sends_whole_what_fits_and_blocks_of_what_does_not():
    big = {"costs": {page: 10 for page in range(1, 101)}, "found": [50, 80]}
    small = {"costs": {page: 10 for page in range(1, 6)}, "found": [2]}
    first, second = reading.select([big, small], 400)
    assert second == [1, 2, 3, 4, 5]
    blocks = reading.ranges(first)
    assert len(first) == 35 and len(blocks) == 2 and blocks[0][0] <= 50 <= blocks[0][1] and blocks[1][0] <= 80 <= blocks[1][1]
    for budget in (0, 5, 55, 400, 1050, 5000):
        chosen = reading.select([big, small], budget)
        assert 10 * sum(len(pages) for pages in chosen) <= budget
    assert reading.select([big, small], 5000) == [list(range(1, 101)), [1, 2, 3, 4, 5]]
    # Fixado na conversa: entra antes e sem o limite por documento.
    assert reading.select([big, small], 1000, fixed=1) == [list(range(1, 101)), []]


def test_a_rule_that_passes_the_budget_is_refused(monkeypatch):
    monkeypatch.setattr(reading, "share", lambda costs, budget, fixed=0, floors=None: list(costs))
    with pytest.raises(ValueError):
        reading.select([{"costs": {1: 10, 2: 10}, "found": []}], 15)


def test_library_gives_the_stored_text_of_every_page(shelf):
    record = shelf.library.pages(shelf.book["id"])
    assert record["pdf"] and record["title"] == "livro.pdf" and len(record["units"]) == 12
    seventh = record["units"][6]
    assert seventh["number"] == seventh["page"] == 7 and seventh["locator"] == "página PDF 7"
    assert seventh["method"] == "native" and "alfa" in seventh["text"]
    with pytest.raises(ValueError):
        shelf.library.pages("0" * 32)


def test_a_page_without_text_and_a_text_document_still_enter(tmp_path):
    from test_figures import build_pdf

    class Blind:
        def extract(self, path, page):
            return "", None

        def extract_region(self, path, page, box, size):
            return []

    build_pdf(tmp_path / "figuras.pdf")
    (tmp_path / "nota.md").write_text("# Primeira\nO alfa da nota.\n\n# Segunda\nO beta da nota.\n", encoding="utf-8")
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences(), ocr=Blind())
    scanned, note = library.add(tmp_path / "figuras.pdf"), library.add(tmp_path / "nota.md")
    last = library.pages(scanned["id"])["units"][4]
    assert (last["page"], last["method"], last["text"]) == (5, "imagem", "")  # a página digitalizada, sem texto lido
    units = library.pages(note["id"])["units"]
    assert [unit["page"] for unit in units] == [None, None] and "alfa" in units[0]["text"]
    request = prepare_request("alfa", library=library, reading=options(fixed=[scanned["id"], note["id"]], search=False))
    pdf, text = sent(request)
    assert pdf[-1]["text"].splitlines()[-1].endswith("p5] página PDF 5 — sem texto extraído")
    # O documento de texto segue sem PDF, com um identificador por seção.
    assert [part["type"] for part in text] == ["text", "text"] and "Enviado inteiro: 2 seções." in text[0]["text"]
    marks = [hit["citation_id"] for hit in request.metadata["citations"] if hit["document_id"] == note["id"]]
    assert [mark[-2:] for mark in marks] == ["s1", "s2"] and f"[{marks[0]}] linhas" in text[1]["text"]


def test_search_tells_the_best_pages_of_each_document(shelf):
    ranked = {"sobra": [1]}
    hits = shelf.library.search("alfa", limit=20, ranked=ranked)
    assert hits[0]["page"] == 7 and "sobra" not in ranked
    assert ranked[shelf.book["id"]][0] == 7 and len(ranked[shelf.book["id"]]) == 12
    assert sorted(ranked[shelf.article["id"]]) == [1, 2, 3]


def test_the_model_gets_whole_documents_with_one_mark_per_page(shelf):
    history = [{"role": "user", "content": "Oi."}, {"role": "assistant", "content": "Olá."}]
    request = prepare_request("Onde aparece o alfa?", library=shelf.library, history=history, reading=options())
    book, article = sent(request)
    assert request.multimodal is True
    head, pdf, pages = book
    assert head["type"] == "text" and "arquivo \"livro.pdf\", versão 1." in head["text"]
    assert "Enviado inteiro: 12 páginas." in head["text"] and "O PDF a seguir traz essas páginas, na ordem." in head["text"]
    assert pdf["type"] == "document" and pdf["mime_type"] == "application/pdf"
    # O conteúdo só é lido se for preciso; inteiro e pequeno, é o próprio original.
    assert callable(pdf["data"]) and pdf["data"]() == (shelf.root / "livro.pdf").read_bytes()
    assert pdf["key"] == f"{shelf.book['sha256']}:1-12" and set(pdf) == {"type", "mime_type", "key", "data", "text"}
    assert "Depois vem a lista das páginas, na mesma ordem do PDF" in head["text"]
    mark = f"K{shelf.book['sha256'][:8]}p7"
    # PRV-06: o PDF leva o texto guardado das suas páginas, que o modelo local lê no lugar da imagem.
    assert f"=== [{mark}] página PDF 7 ===\nCapitulo jaca sobre manutencao. O alfa aparece aqui." in pdf["text"]
    assert pdf["text"].count("=== [K") == 12
    lines = pages["text"].splitlines()
    # A lista segue a ordem do PDF: o identificador de cada página e as primeiras palavras dela.
    assert lines[6] == f"[{mark}] página PDF 7 — começa com: Capitulo jaca sobre manutencao. O alfa aparece aqui."
    assert len(lines) == 12 and all(line.startswith("[K") for line in lines)
    assert "Enviado inteiro: 3 páginas." in article[0]["text"]
    cited = {hit["citation_id"]: hit for hit in request.metadata["citations"]}
    assert len(cited) == 15 and cited[mark]["page"] == 7 and cited[mark]["leitura"] == "pagina"
    assert cited[mark]["document_id"] == shelf.book["id"] and cited[mark]["locator"] == "página PDF 7"
    summary = request.metadata["reading"]
    assert summary["teto"] == 400_000 and summary["fora"] == [] and summary["tokens_estimados"] <= 400_000
    assert [(d["titulo"], d["paginas"], d["total"], d["inteiro"], d["fixado"]) for d in summary["documentos"]] == [
        ("livro.pdf", 12, 12, True, False), ("artigo.pdf", 3, 3, True, False)]
    assert "text" not in str(summary)  # o resumo não leva o texto das páginas
    # As regras são as da leitura integral, e os documentos vêm antes da conversa.
    rules = [m["content"] for m in request.messages if m["role"] == "developer"]
    assert READING_RULES in rules and LIBRARY_RULES not in rules
    order = [index for index, message in enumerate(request.messages) if isinstance(message["content"], list)]
    assert max(order) < request.messages.index(history[0]) < len(request.messages) - 1
    assert request.messages[min(order) - 1]["content"].startswith("Catálogo da biblioteca selecionada")
    assert request.messages[-1] == {"role": "user", "content": "Onde aparece o alfa?"}
    # Com `full_text`, o texto guardado de cada página segue junto com o PDF.
    full = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=options(full_text=True))
    head, _pdf, pages = sent(full)[0]
    assert "Depois vem o texto guardado de cada página" in head["text"] and pages["text"].count("=== [K") == 12
    assert f"=== [{mark}] página PDF 7 ===\nCapitulo jaca sobre manutencao. O alfa aparece aqui." in pages["text"]
    assert full.metadata["reading"]["tokens_estimados"] > summary["tokens_estimados"] - 200


def test_the_opening_of_a_page_fits_in_one_line():
    assert reading._opening("Linha um\n  linha dois") == "Linha um linha dois"
    long = reading._opening("palavra " * 60)
    assert len(long) <= reading.OPENING_CHARS and long.endswith("palavra…") and "\n" not in long
    assert reading.page_cost("x" * 9000) == reading.page_cost("x" * 120) < reading.page_cost("x" * 9000, full_text=True)
    assert reading.page_cost("x" * 300, pdf=False) == 115  # sem PDF, só o texto e a linha do identificador


def large(monkeypatch) -> None:
    """O livro de 12 páginas passa a ser um documento grande, com blocos fixos de 3 páginas."""
    monkeypatch.setattr(reading, "WHOLE_PAGES", 5)
    monkeypatch.setattr(reading, "BLOCK_PAGES", 3)
    monkeypatch.setattr(reading, "FOUND_PAGES", 1)  # só a melhor página: as outras empatam na busca de teste


def test_a_large_document_goes_in_fixed_blocks_around_what_the_search_found(shelf, monkeypatch):
    large(monkeypatch)
    request = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=options(budget=6000))
    book, article = request.metadata["reading"]["documentos"]
    # O bloco da página achada (7–9) e o vizinho que coube; o artigo, pequeno, vai inteiro.
    assert (book["paginas"], book["total"], book["inteiro"], book["blocos"]) == (6, 12, False, "4–9")
    assert article["inteiro"] and request.metadata["reading"]["tokens_estimados"] <= 6000
    head, first, second, pages = sent(request)[0]
    assert "Enviado em parte: páginas 4–9, de 12; as outras páginas não foram enviadas e não foram lidas." in head["text"]
    assert "Os 2 PDFs a seguir trazem essas páginas, na ordem: páginas 4–6; páginas 7–9." in head["text"]
    # Um PDF por bloco, com a chave das páginas dele: o mesmo bloco serve a outra pergunta.
    assert [part["key"] for part in (first, second)] == [f"{shelf.book['sha256']}:4-6", f"{shelf.book['sha256']}:7-9"]
    assert len(pages["text"].splitlines()) == 6

    from pypdf import PdfReader

    cut = PdfReader(io.BytesIO(first["data"]()))
    assert len(cut.pages) == 3 and "damasco" in cut.pages[0].extract_text() and "goiaba" in cut.pages[-1].extract_text()
    # Com o teto ainda menor, o que não coube é dito à tela.
    tight = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=options(budget=2000))
    assert [(d["paginas"], d["blocos"]) for d in tight.metadata["reading"]["documentos"]] == [(3, "7–9")]
    assert tight.metadata["reading"]["fora"] == ["artigo.pdf"]
    nothing = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=options(budget=10))
    assert sent(nothing) == [] and nothing.messages[-2]["content"] == "Nenhum documento da biblioteca foi recuperado para esta pergunta."


def test_a_large_pdf_goes_in_several_parts(shelf, monkeypatch):
    monkeypatch.setattr(reading, "PDF_BYTES", 1)
    request = prepare_request("beta", library=shelf.library, reading=options(fixed=[shelf.article["id"]], search=False))
    head, *files, pages = sent(request)[0]
    assert "Os 3 PDFs a seguir trazem essas páginas, na ordem: páginas 1; páginas 2; páginas 3." in head["text"]
    assert [part["key"].split(":")[1] for part in files] == ["1-1", "2-2", "3-3"] and pages["type"] == "text"


def answer(content: str, shelf, **reading_options) -> LLMResult:
    def execute(request, **_):
        return LLMResult(content, "fake", "test", request.task_type)

    return Agent(SimpleNamespace(execute=execute)).answer(
        "Onde aparece o alfa?", provider="fake", model_alias="test", library=shelf.library, append_sources=False,
        reading=options(**reading_options))


def test_a_page_mark_is_accepted_and_an_invented_one_blocks_the_answer(shelf):
    mark = f"K{shelf.book['sha256'][:8]}p7"
    cited = answer(f"O alfa aparece no capítulo jaca [{mark}].", shelf)
    assert cited.validation_status == "citation_ids_verified"
    source, = cited.sources
    assert (source["citation_id"], source["page"], source["title"], source["leitura"]) == (mark, 7, "livro.pdf", "pagina")
    assert "alfa" in source["text"]
    # "A busca também trouxe": os trechos que a busca achou, menos o da página citada; não as 15 páginas lidas.
    assert cited.retrieved and all(not hit.get("leitura") for hit in cited.retrieved)
    assert (shelf.book["id"], 7) not in {(hit["document_id"], hit["page"]) for hit in cited.retrieved}
    assert cited.reading["documentos"][0]["titulo"] == "livro.pdf"
    invented = answer(f"O alfa aparece na página 13 [K{shelf.book['sha256'][:8]}p13].", shelf)
    assert invented.validation_status == "invalid_citations" and invented.sources == () and invented.reading
    uncited = answer("Não encontrei.", shelf)
    # Sem citação, ficam os 15 trechos que a busca achou (um por página destes documentos de teste).
    assert uncited.validation_status == "uncited" and len(uncited.retrieved) == 15
    assert all(not hit.get("leitura") for hit in uncited.retrieved)


def test_stream_answers_carry_what_was_read(shelf):
    from aliado.llm.contracts import LLMStreamChunk

    mark = f"K{shelf.article['sha256'][:8]}p2"

    def stream(request, **_):
        yield LLMStreamChunk(f"O beta está no artigo [{mark}].", "fake", "test", request.task_type)

    events = list(Agent(SimpleNamespace(stream=stream)).stream_answer(
        "beta", provider="fake", model_alias="test", library=shelf.library, append_sources=False, reading=options()))
    final = events[-1][1]
    assert final.validation_status == "citation_ids_verified" and final.sources[0]["page"] == 2
    assert {d["titulo"] for d in final.reading["documentos"]} == {"livro.pdf", "artigo.pdf"}


def test_a_fixed_document_goes_whole_without_the_search(shelf, monkeypatch):
    calls = []
    search = shelf.library.search
    monkeypatch.setattr(shelf.library, "search", lambda *args, **kwargs: calls.append(args) or search(*args, **kwargs))
    fixed = options(fixed=[shelf.article["id"], "0" * 32], search=False)  # o segundo saiu da biblioteca
    request = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=fixed)
    (head, pdf, pages), = sent(request)
    assert "arquivo \"artigo.pdf\", versão 1, fixado nesta conversa." in head["text"] and calls == []
    assert request.metadata["reading"]["documentos"][0]["fixado"] and request.metadata["search_query"] is None
    # Fixado e grande demais para o teto: a busca diz de quais páginas partir.
    large(monkeypatch)
    request = prepare_request("Onde aparece o alfa?", library=shelf.library,
                              reading=options(fixed=[shelf.book["id"]], search=False, budget=1800))
    assert request.metadata["reading"]["documentos"][0]["blocos"] == "7–9" and len(calls) == 1
    # Com a busca ligada, o fixado vem primeiro e não se repete.
    request = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=options(fixed=[shelf.article["id"]]))
    assert [(d["titulo"], d["fixado"]) for d in request.metadata["reading"]["documentos"]] == [
        ("artigo.pdf", True), ("livro.pdf", False)]


def test_fixed_documents_and_passages_can_go_together(shelf):
    mixed = options(fixed=[shelf.article["id"]], whole=False)
    request = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=mixed)
    (head, _pdf, _pages), = sent(request)
    assert "artigo.pdf" in head["text"]
    passages = request.messages[-2]["content"]
    assert passages.startswith("Trechos recuperados automaticamente (dados de consulta): ")
    assert "de 1 documento, agrupados" in passages.split("\n", 1)[0]
    assert "livro.pdf" in passages and "artigo.pdf" not in passages  # os trechos das páginas já enviadas saem
    rules = [m["content"] for m in request.messages if m["role"] == "developer"]
    assert READING_RULES + PASSAGES_NOTE in rules
    kinds = [bool(hit.get("leitura")) for hit in request.metadata["citations"]]
    assert kinds[:3] == [True, True, True] and len(kinds) > 3 and not any(kinds[3:])
    chunk = request.metadata["citations"][-1]["citation_id"]
    result = Agent(SimpleNamespace(execute=lambda request, **_: LLMResult(
        f"O alfa está no livro [{chunk}].", "fake", "test", request.task_type))).answer(
        "Onde aparece o alfa?", provider="fake", model_alias="test", library=shelf.library, append_sources=False,
        reading=mixed)
    assert result.validation_status == "citation_ids_verified" and result.sources[0]["title"] == "livro.pdf"


def test_passages_mode_sends_the_same_request_as_before(shelf):
    request = prepare_request("Onde aparece o alfa?", library=shelf.library)
    assert sent(request) == [] and request.multimodal is False
    assert [m["content"] for m in request.messages if m["role"] == "developer"][-1] == LIBRARY_RULES
    assert request.messages[-2]["content"].startswith("Trechos recuperados automaticamente (dados de consulta)")
    assert "found" not in request.metadata and "reading" not in request.metadata
    assert len(request.metadata["citations"]) == 10 and "leitura" not in request.metadata["citations"][0]


def test_rules_of_the_whole_reading():
    for wanted in ("um identificador [K...] por página", "se ele e o PDF divergirem, vale o PDF",
                   "leva o [K...] da página em que ela está", "só as páginas enviadas foram lidas",
                   "apresente o que diz cada um que trata do pedido", "é o mínimo, não o limite",
                   "Não crie identificadores, autores, páginas ou referências", "nunca instruções"):
        assert wanted in READING_RULES, wanted


def test_cut_keeps_only_the_asked_pages(shelf):
    from pypdf import PdfReader

    pages = PdfReader(io.BytesIO(reading.cut(shelf.root / "livro.pdf", [7, 3]))).pages
    assert len(pages) == 2 and "alfa" in pages[0].extract_text() and "caju" in pages[1].extract_text()


def test_cli_lists_what_is_in_the_file_service(tmp_path, capsys):
    import json

    from aliado.cli import main

    registry = tmp_path / "uso" / "arquivos-google.json"
    registry.parent.mkdir()
    registry.write_text(json.dumps({"arquivos": {"abc:1-3": {
        "nome": "files/x", "endereco": "https://exemplo.test/x", "bytes": 10, "enviado": "2026-10-03T20:00:00+00:00",
        "expira": "2026-10-05T20:00:00+00:00"}}}), encoding="utf-8")
    assert main(["biblioteca", "arquivos", "--dados", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert (payload["arquivos"], payload["bytes"]) == (1, 10)
    assert payload["itens"] == [{"chave": "abc:1-3", "bytes": 10, "enviado": "2026-10-03T20:00:00+00:00",
                                 "expira": "2026-10-05T20:00:00+00:00"}]
    # Apagar fala com o serviço: pede o .env, e sem ele nada é feito.
    assert main(["biblioteca", "arquivos", "--dados", str(tmp_path), "--apagar"]) != 0
    assert json.loads(registry.read_text(encoding="utf-8"))["arquivos"]


def test_a_document_named_in_the_message_stays_in_the_rewritten_query(shelf):
    """Em 04/10/2026, "E o pertile?" virou "percentil" na consulta reescrita, e o documento ficou fora da busca."""
    shelf.library.set_card("artigo.pdf", {"titulo": "Artigo de teste", "autores": ["Ana Pertile"], "ano": 2023}, edited=False)
    request = prepare_request("E o pertile?", library=shelf.library, search_query="alfa e percentil percentile",
                              reading=options())
    assert request.metadata["search_query"] == "alfa e percentil percentile Pertile, 2023"
    # O documento citado vem primeiro, à frente do que combina com o resto da consulta.
    assert [d["titulo"] for d in request.metadata["reading"]["documentos"]] == ["Pertile, 2023", "livro.pdf"]
    # Vale também no modo de trechos, e a consulta que já cita o documento não muda.
    request = prepare_request("E o pertile?", library=shelf.library, search_query="alfa e percentil percentile")
    assert request.metadata["search_query"].endswith("Pertile, 2023")
    assert request.metadata["citations"][0]["title"] == "artigo.pdf"
    kept = prepare_request("E o pertile?", library=shelf.library, search_query="beta em Pertile (2023)")
    assert kept.metadata["search_query"] == "beta em Pertile (2023)"
    plain = prepare_request("Onde aparece o alfa?", library=shelf.library, search_query="alfa")
    assert plain.metadata["search_query"] == "alfa"

