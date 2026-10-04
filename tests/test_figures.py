"""Lote 29: figuras e tabelas — sinais da página, texto reconhecido, descrição do modelo e a biblioteca."""

from __future__ import annotations

import io
import json
import re
import sqlite3

import pytest

from aliado.knowledge import figures
from aliado.knowledge.library import DocumentLibrary
from aliado.llm.contracts import LLMResult, LLMUsage
from aliado.llm.providers.base import ProviderError

pytest.importorskip("pypdf")
pytest.importorskip("pypdfium2")
pytest.importorskip("PIL")


class Sentences:
    """Encoder de teste com a posição dos tokens: cada palavra é um token, 12 por trecho."""

    fingerprint = "synthetic-window-encoder-v1"
    chunk_tokens = 12

    def token_spans(self, text):
        return [(match.start(), match.end()) for match in re.finditer(r"\S+", text)]

    def split(self, text):
        return [text] if text.strip() else []

    def encode(self, texts):
        return [[float("alfa" in text.lower()), float("beta" in text.lower()), 1.0] for text in texts]


class Reader:
    """Reconhecimento de texto de teste: a página digitalizada e as linhas de cada recorte de figura."""

    def __init__(self, lines=()):
        self.lines, self.regions, self.pages = list(lines), [], []

    def extract(self, path, page):
        self.pages.append(page)
        return "Figura 3. Curva da banheira digitalizada, com tres regioes.", 91.0

    def extract_region(self, path, page, box, size):
        self.regions.append((page, tuple(box)))
        return list(self.lines)


LABELS = [("Inversor central", 95.0), ("Barramento CC", 92.0), ("Fusivel de string", 88.0)]


FIRST_PAGE = ("O alfa do sistema aparece no diagrama desta pagina.", "Figure 1. Diagrama de blocos do sistema.")


def build_pdf(path, first=FIRST_PAGE) -> None:
    """Cinco páginas: figura embutida com legenda, só texto, tabela com legenda, desenho vetorial e digitalizada."""
    from PIL import Image
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica"),
                             NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})

    def text_page(lines, extra=""):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        body = " T* ".join(f"({line}) Tj" for line in lines)
        stream.set_data(f"BT /F1 9 Tf 11 TL 40 770 Td {body} ET {extra}".encode("cp1252"))
        page[NameObject("/Contents")] = writer._add_object(stream)  # o pdfium só lê o conteúdo por referência
        return page

    def image_page(width, height):
        buffer = io.BytesIO()
        Image.new("RGB", (width, height), "white").save(buffer, "PDF")
        return PdfReader(io.BytesIO(buffer.getvalue())).pages[0]

    first = text_page(list(first))
    first.merge_transformed_page(image_page(400, 300), Transformation().scale(0.75, 0.75).translate(100, 300))
    text_page(["Segunda pagina, so com texto corrido sobre o beta."])
    text_page(["Terceira pagina, com a tabela.", "Table 2. Taxas de falha por componente.", "Inversor 26.7 4015"])
    text_page(["Quarta pagina, com um desenho vetorial."], " ".join(f"{10 + n} 100 m {10 + n} 400 l S" for n in range(200)))
    scan = writer.add_blank_page(width=612, height=792)
    scan.merge_transformed_page(image_page(612, 792), Transformation())
    writer.write(path)


def library_with(tmp_path, reader=None) -> tuple[DocumentLibrary, dict]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "figuras.pdf"
    build_pdf(path)
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences(), ocr=reader or Reader(LABELS))
    return library, library.add(path)


def chunks(library: DocumentLibrary) -> list[sqlite3.Row]:
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        db.row_factory = sqlite3.Row
        return db.execute("""SELECT c.id, c.text, c.locator, c.page, c.method FROM chunks c
            JOIN documents d ON d.active_run=c.run_id ORDER BY c.rowid""").fetchall()


def answer(items, *, truncated=False, tokens=(1500, 300)) -> LLMResult:
    return LLMResult(json.dumps({"itens": items}), "fake", "modelo-teste", figures.TASK, structured_data={"itens": items},
                     usage=LLMUsage(tokens[0], tokens[1], sum(tokens), 0), truncated=truncated)


def test_captions_are_normalized():
    text = "Texto.\nFigure 2. Fault tree\n  Fig. 3 shows\nTabela 5.1 – Dados\nQuadro 4 lista\nGráfico 7: curva\nver a Figura 9 no texto"
    assert figures.captions(text) == ["fig 2", "fig 3", "tab 5.1", "qua 4", "gra 7"]  # a Figura 9 não começa a linha
    assert figures.captions("Table 7-2— Failure modes") == ["tab 7-2"] and figures.captions("sem legenda") == []


def test_page_signals_find_images_drawings_captions_and_scanned_pages(tmp_path):
    path = tmp_path / "figuras.pdf"
    build_pdf(path)
    sections = [{"page": 1, "method": "native", "text": "Texto.\nFigure 1. Diagrama de blocos do sistema."},
                {"page": 2, "method": "native", "text": "Segunda pagina."},
                {"page": 3, "method": "native", "text": "Table 2. Taxas de falha por componente."},
                {"page": 4, "method": "native", "text": "Quarta pagina."},
                {"page": 5, "method": "ocr", "text": "Figura 3. Curva da banheira."}]
    signals = figures.page_signals(path, sections)
    assert sorted(signals) == [1, 3, 4, 5]  # a página só de texto não entra
    assert signals[1]["imagens"] == [[100.0, 300.0, 400.0, 525.0]] and signals[1]["legendas"] == ["fig 1"]
    assert not signals[1]["digitalizada"] and not signals[1]["desenho"]
    assert signals[3] == {"tamanho": [612.0, 792.0], "imagens": [], "tracos": 0, "digitalizada": False,
                          "desenho": False, "legendas": ["tab 2"]}
    assert signals[4]["desenho"] and signals[4]["tracos"] == 200 and signals[4]["legendas"] == []
    # A imagem do tamanho da página é a própria página digitalizada: não é figura para recortar.
    assert signals[5]["digitalizada"] and signals[5]["imagens"] == [] and signals[5]["legendas"] == ["fig 3"]
    # Página lida por reconhecimento de texto: a imagem dela, com ou sem margem, é a página. Só entra pela legenda.
    scanned = [{"page": 1, "method": "ocr", "text": "Texto reconhecido, sem legenda."},
               {"page": 5, "method": "ocr", "text": "Outra pagina digitalizada, sem legenda."}]
    assert sorted(figures.page_signals(path, scanned)) == [4]  # sobra só o desenho vetorial
    scanned[0]["text"] = "Figura 2. Agora com legenda."
    again = figures.page_signals(path, scanned)
    assert again[1]["imagens"] == [] and again[1]["digitalizada"] and again[1]["legendas"] == ["fig 2"]


def test_figure_text_keeps_only_what_the_page_does_not_have():
    signal = {"tamanho": [612.0, 792.0], "imagens": [[100.0, 300.0, 400.0, 525.0]]}
    page = "O alfa do sistema aparece no diagrama desta pagina.\nFigure 1. Diagrama de blocos do sistema."
    lines = LABELS + [("Diagrama de blocos do sistema", 90.0), ("x", 99.0),
                      # O texto corrido em volta, lido com erro: um pedaço intacto de 12 letras basta para tirá-lo.
                      ("O alfa do sistena aparece no diagrana desta", 85.0), ("Barramento CC", 92.0)]
    local = figures.figure_text(Reader(lines), "arquivo.pdf", 1, signal, page)
    assert local == {"texto": "Inversor central\nBarramento CC\nFusivel de string", "confianca": 91.7}
    # Menos de 3 palavras novas: a figura fica sem texto.
    assert figures.figure_text(Reader([("36%", 99.0), ("DCB", 80.0)]), "a.pdf", 1, signal, page) == {"texto": "", "confianca": None}
    assert figures.figure_text(Reader(), "a.pdf", 1, signal, page) == {"texto": "", "confianca": None}


def test_library_indexes_the_text_inside_figures(tmp_path):
    reader, steps = Reader(LABELS), []
    path = tmp_path / "figuras.pdf"
    build_pdf(path)
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences(), ocr=reader)
    result = library.add(path, progress=lambda *step: steps.append(step))
    assert result["status"] == "ready" and ("figuras", 1, 1) in steps
    assert reader.regions == [(1, (100.0, 300.0, 400.0, 525.0))] and reader.pages == [5]
    figure = [row for row in chunks(library) if row["method"] == "figura"]
    assert [(row["locator"], row["page"], row["text"]) for row in figure] == [
        ("página PDF 1 · texto das figuras", 1, "Inversor central\nBarramento CC\nFusivel de string")]
    hits = library.search("Fusivel de string", limit=20)
    assert any(hit["method"] == "figura" and hit["locator"] == "página PDF 1 · texto das figuras" for hit in hits)
    files = library.document_files(result["id"])
    markdown = files["markdown"].read_text(encoding="utf-8")
    assert markdown.index("## página PDF 1 (native)") < markdown.index("## página PDF 1 · texto das figuras (texto reconhecido na figura)") \
        < markdown.index("## página PDF 2 (native)")
    assert "Inversor central" not in library.opening_text("figuras.pdf")  # o começo do documento é só o texto
    assert library.figures_summary()[result["sha256"]] == {
        "paginas": 4, "com_texto": 1, "descritas": 0, "itens": 0, "modelo": None, "data": None}
    # Reindexar não reconhece de novo: o texto das figuras vale pelo conteúdo do arquivo.
    again = library.reindex(result["id"])
    assert len(reader.regions) == 1 and again["chunks"] == result["chunks"]
    assert [row["text"] for row in chunks(library) if row["method"] == "figura"] == [figure[0]["text"]]
    assert library.verify()["ok"]


def test_without_region_reading_the_figures_wait_for_the_next_time(tmp_path):
    from types import SimpleNamespace

    plain = SimpleNamespace(extract=lambda path, page: ("Figura 3. Curva da banheira digitalizada.", 90.0))
    library, result = library_with(tmp_path, plain)
    assert result["status"] == "ready" and not [row for row in chunks(library) if row["method"] == "figura"]
    assert library.figures_summary()[result["sha256"]]["paginas"] == 4  # os sinais ficam guardados
    library.ocr = Reader(LABELS)
    library.reindex(result["id"])
    assert [row["locator"] for row in chunks(library) if row["method"] == "figura"] == ["página PDF 1 · texto das figuras"]

    class Broken(Reader):
        def extract_region(self, path, page, box, size):
            raise RuntimeError("reconhecimento falhou")

    other = DocumentLibrary(tmp_path / "outra", encoder=Sentences(), ocr=Broken())
    assert other.add(tmp_path / "figuras.pdf")["status"] == "ready"  # a falha na figura não derruba o texto
    assert not [row for row in chunks(other) if row["method"] == "figura"]


PAGE = ("Texto da pagina.\nFigure 2. Fault tree of the central inverter.\n"
        "Table 1. Failure rate per component\nInverter 26.7 4015\n")


def test_check_items_keeps_only_what_the_page_confirms():
    raw = {"itens": [
        {"tipo": "figura", "rotulo": "Figure 2", "legenda": "Figure 2. Fault tree of the central inverter.",
         "descricao": "Árvore de falhas com uma porta OU que liga 3 eventos.", "texto_visivel": ["Inverter", "Transformer", "26.7"]},
        {"tipo": "figura", "rotulo": "Figure 9", "legenda": "Legenda que o modelo inventou", "descricao": "Outro diagrama."},
        {"tipo": "tabela", "rotulo": "Table 1", "legenda": "Table 1. Failure rate per component",
         "descricao": "Taxas de falha por componente.", "tabela": "Component | Rate\nInverter | 26.7\n\nFan | 99.9"},
        {"tipo": "figura", "descricao": "   "}, "lixo",
        {"tipo": "figura", "rotulo": "Figure 2", "descricao": "A parte (b) da mesma figura."},
        {"tipo": "grafico", "descricao": "Tipo desconhecido vira figura.", "tabela": "a | b"}]}
    first, invented, table, second, unknown = figures.check_items(raw, PAGE)
    assert first["rotulo"] == "Figure 2" and first["legenda"] == "Figure 2. Fault tree of the central inverter."
    # A legenda e a descrição na mesma linha; do texto visível, só os itens com letras.
    assert first["texto"] == ("Figure 2. Fault tree of the central inverter. "
                              "Descrição automática da figura: Árvore de falhas com uma porta OU que liga 3 eventos.\n"
                              "Texto visível na figura: Inverter; Transformer")
    assert figures.item_text(first) == (first["texto"], len("Figure 2. Fault tree of the central inverter. "
                                                           "Descrição automática da figura: ") + 40)
    # "inverter" e 26.7 estão na página; "transformer" e o 3 da descrição, não.
    assert first["conferido"] == 50 and first["nao_conferidos"] == ["3"]
    assert invented["rotulo"] == "figura sem rótulo 1" and invented["legenda"] == ""
    assert invented["texto"] == "Descrição automática da figura: Outro diagrama." and invented["conferido"] is None
    assert table["tipo"] == "tabela" and table["rotulo"] == "Table 1" and table["tabela"] == "Component | Rate\nInverter | 26.7\nFan | 99.9"
    assert table["texto"].endswith("Transcrição automática da tabela:\nComponent | Rate\nInverter | 26.7\nFan | 99.9")
    assert table["conferido"] == 80 and table["nao_conferidos"] == ["99.9"]
    assert second["rotulo"] == "Figure 2 (2)" and unknown["tipo"] == "figura" and unknown["tabela"] == ""
    assert unknown["rotulo"] == "figura sem rótulo 2"
    # O texto reconhecido dentro da figura também confere o que o modelo diz ver.
    assert figures.check_items({"itens": raw["itens"][:1]}, PAGE, "Transformer station")[0]["conferido"] == 75
    assert figures.check_items({}, PAGE) == [] and figures.check_items({"itens": None}, PAGE) == []
    assert len(figures.check_items({"itens": [{"tipo": "figura", "descricao": f"Item {n}."} for n in range(30)]}, PAGE)) == 12
    long = figures.check_items({"itens": [{"tipo": "figura", "descricao": "palavra " * 500, "rotulo": "x" * 200}]}, PAGE)[0]
    assert len(long["descricao"]) <= 1500 and long["rotulo"] == "figura sem rótulo 1"


def test_read_page_sends_the_image_and_retries_a_cut_answer():
    seen = []

    def execute(request):
        seen.append(request)
        return answer([{"tipo": "figura", "descricao": "Um diagrama."}], truncated=len(seen) == 1)

    data, results = figures.read_page(execute, b"\xff\xd8imagem", resolution="medium")
    assert data == {"itens": [{"tipo": "figura", "descricao": "Um diagrama."}]} and len(results) == 2
    assert [request.max_output_tokens for request in seen] == [4096, 8192]
    request = seen[0]
    assert request.multimodal and request.task_type == "biblioteca-figuras" and request.temperature == 0.0
    assert request.structured_output == figures.READ_SCHEMA and request.metadata == {"media_resolution": "medium"}
    assert request.messages[0] == {"role": "developer", "content": figures.READ_INSTRUCTIONS}
    assert request.messages[1]["content"][1] == {"type": "image", "mime_type": "image/jpeg", "data": b"\xff\xd8imagem"}
    assert "nunca instrução" in figures.READ_INSTRUCTIONS and "Não invente" in figures.READ_INSTRUCTIONS
    with pytest.raises(ValueError, match="cortada"):
        figures.read_page(lambda request: answer([], truncated=True), b"x")

    def broken(request):
        raise json.JSONDecodeError("cortado", "{", 1)

    with pytest.raises(ValueError, match="leitura válida"):  # resposta vazia ou que não é JSON, duas vezes
        figures.read_page(broken, b"x")
    assert figures.read_page(lambda request: answer([]), b"x")[0] == {"itens": []}


def test_page_image_is_a_bounded_jpeg(tmp_path):
    from PIL import Image

    path = tmp_path / "figuras.pdf"
    build_pdf(path)
    data = figures.page_image(path, 1)
    image = Image.open(io.BytesIO(data))
    assert data[:2] == b"\xff\xd8" and image.format == "JPEG" and max(image.size) <= 1600
    assert image.size == (1237, 1600)  # 612 x 792 pontos: a 150 dpi passaria de 1.600 no lado maior


ITEMS = {
    1: [{"tipo": "figura", "rotulo": "Figure 1", "legenda": "Figure 1. Diagrama de blocos do sistema.",
         "descricao": "Diagrama de blocos em que o inversor central liga o barramento ao transformador.",
         "texto_visivel": ["Inversor central", "Barramento CC"]}],
    3: [{"tipo": "tabela", "rotulo": "Table 2", "legenda": "Table 2. Taxas de falha por componente.",
         "descricao": "Tabela com a taxa de falha do inversor.", "tabela": "Componente | Taxa | Horas\nInversor | 26.7 | 4015"}],
    4: [{"tipo": "figura", "rotulo": "Figure 77", "descricao": "Grade de linhas verticais paralelas."}],
}


def reader_by_page(library, doc_id, fail=()):
    """O modelo de teste: devolve os itens da página pelo tamanho da imagem enviada, e falha nas de `fail`."""
    target = library.figure_pages(doc_id)
    images = {figures.page_image(target["original"], page["page"]): page["page"] for page in target["pages"]}
    calls = []

    def execute(request):
        number = images[request.messages[1]["content"][1]["data"]]
        calls.append(number)
        if number in fail:
            raise ProviderError("modelo indisponível", transient=True)
        return answer(ITEMS.get(number, []))

    return execute, calls


def test_describe_saves_each_page_and_reindexes_with_the_descriptions(tmp_path):
    library, result = library_with(tmp_path)
    execute, calls = reader_by_page(library, result["id"], fail={5})
    recorded, steps = [], []
    counts = figures.describe(library, result["id"], execute, workers=1, record=recorded.append,
                              progress=lambda *step: steps.append(step))
    assert counts == {"paginas": 4, "lidas": 3, "falhas": 1, "itens": 3, "sem_figura": 0, "tokens_entrada": 4500,
                      "tokens_saida": 900, "interrompido": False}
    assert sorted(calls) == [1, 3, 4, 5] and len(recorded) == 3 and steps[-1] == ("descrevendo", 4, 4)
    described = [row for row in chunks(library) if row["method"] == "descricao"]
    assert {row["locator"] for row in described} == {
        "página PDF 1 · Figure 1", "página PDF 3 · Table 2", "página PDF 4 · figura sem rótulo 1"}
    rows = [row for row in described if row["page"] == 3]
    table = "\n".join(row["text"] for row in rows)
    assert "Table 2. Taxas de falha por componente." in table and "Inversor | 26.7 | 4015" in table
    assert rows[0]["text"].startswith("Table 2. Taxas de falha por componente.")
    # A passagem de um trecho de descrição leva a descrição inteira: uma tabela pela metade não serve.
    assert len(rows) >= 3 and library.expand([{"citation_id": rows[0]["id"], "text": rows[0]["text"]}])[0]["passagem"] == table
    # Na página descrita pelo modelo, o texto local das figuras sai do índice.
    assert not [row for row in chunks(library) if row["method"] == "figura"]
    hits = library.search("transformador barramento", limit=20)
    assert any(hit["method"] == "descricao" and hit["page"] == 1 for hit in hits)
    summary = library.figures_summary()[result["sha256"]]
    assert summary["descritas"] == 3 and summary["itens"] == 3 and summary["modelo"] == "modelo-teste" and summary["data"]
    pages = {page["page"]: page for page in library.figure_pages(result["id"])["pages"]}
    assert [number for number, page in pages.items() if not page["read"]] == [5]
    assert library.verify()["ok"]
    # Outra rodada lê só a página que faltou; a que não tem figura fica registrada como lida.
    execute, calls = reader_by_page(library, result["id"])
    counts = figures.describe(library, result["id"], execute, workers=1)
    assert calls == [5] and counts["lidas"] == 1 and counts["sem_figura"] == 1 and counts["itens"] == 0
    execute, calls = reader_by_page(library, result["id"])
    assert figures.describe(library, result["id"], execute)["paginas"] == 0 and calls == []
    # A extração nova continua a levar as descrições: elas valem pelo conteúdo do arquivo.
    library.reindex(result["id"])
    assert len([row for row in chunks(library) if row["method"] == "descricao"]) == len(described)


def test_describe_can_be_stopped_limited_and_redone(tmp_path):
    library, result = library_with(tmp_path)
    execute, calls = reader_by_page(library, result["id"])
    counts = figures.describe(library, result["id"], execute, stopped=lambda: True)
    assert calls == [] and counts["lidas"] == 0 and counts["interrompido"]
    assert not [row for row in chunks(library) if row["method"] == "descricao"]
    counts = figures.describe(library, result["id"], execute, workers=1, limit=2, reindex=False)
    assert calls == [1, 3] and counts["paginas"] == 2
    assert not [row for row in chunks(library) if row["method"] == "descricao"]  # sem reindexar, o índice não muda
    counts = figures.describe(library, result["id"], execute, workers=1, redo=True, limit=1)
    assert calls == [1, 3, 1] and counts["lidas"] == 1
    with pytest.raises(ValueError, match="não encontrado"):
        figures.describe(library, "inexistente", execute)


def test_deleting_the_document_removes_what_was_read_from_its_figures(tmp_path):
    library, result = library_with(tmp_path)
    execute, _ = reader_by_page(library, result["id"])
    figures.describe(library, result["id"], execute, workers=1)
    assert library.figures_summary()[result["sha256"]]["descritas"] == 4
    library.delete(result["id"])
    assert library.figures_summary() == {}
    with pytest.raises(ValueError):
        library.save_figure_reading(result["sha256"], 1, {"itens": []}, model="m")


# --- A rota da biblioteca -------------------------------------------------------------------------------

BASE = "http://127.0.0.1:8765"
HEADERS = {"x-aliado": "1"}


def web(tmp_path, reader=None, **extra):
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    from aliado.interfaces.web.app import WebSettings, create_app

    library, result = library_with(tmp_path)
    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=library.root, port=8765, stream=lambda *a, **k: iter(()),
                           models=[{"alias": "flash_lite", "model_id": "modelo-teste"}], library_factory=lambda: library,
                           figure_reader=reader, figure_model="Flash-Lite" if reader else None, **extra)
    return TestClient(create_app(settings), base_url=BASE), settings, library, result


def wait_job(client, job):
    import time

    for _ in range(200):
        status = client.get(f"/api/biblioteca/tarefas/{job}").json()
        if status["estado"] == "concluido":
            return status
        time.sleep(0.05)
    raise AssertionError("A tarefa não terminou")


def test_figures_route_describes_the_pages_and_records_the_usage(tmp_path):
    seen = []

    def reader(request):
        seen.append(request)
        return answer(ITEMS[1])

    client, settings, library, result = web(tmp_path, reader)
    doc = result["id"]
    listed = client.get("/api/biblioteca").json()[0]
    assert listed["figuras"] == {"paginas": 4, "com_texto": 1, "descritas": 0, "itens": 0, "modelo": None, "data": None}
    assert client.get(f"/api/biblioteca/{doc}/figuras").json() == {
        "paginas": 4, "por_ler": 4, "tarefa": None, "modelo": "Flash-Lite", "disponivel": True,
        "tokens_por_pagina": figures.TOKENS_PER_PAGE}
    assert client.post(f"/api/biblioteca/{doc}/figuras").status_code == 403  # sem o cabeçalho da página
    started = client.post(f"/api/biblioteca/{doc}/figuras", headers=HEADERS)
    assert started.status_code == 202 and started.json()["total"] == 4
    status = wait_job(client, started.json()["tarefa"])
    assert status["resultado"]["lidas"] == 4 and status["resultado"]["falhas"] == 0 and "erro" not in status
    assert len(seen) == 4 and all(request.multimodal for request in seen)
    usage = [json.loads(line) for line in settings.usage_log.read_text(encoding="utf-8").splitlines()]
    assert [entry["task_type"] for entry in usage] == ["biblioteca-figuras"] * 4 and usage[0]["input_tokens"] == 1500
    assert "imagem" not in settings.usage_log.read_text(encoding="utf-8")  # só tokens, nunca o conteúdo
    after = client.get(f"/api/biblioteca/{doc}/figuras").json()
    assert after["por_ler"] == 0 and after["tarefa"] is None
    assert client.get("/api/biblioteca").json()[0]["figuras"]["descritas"] == 4
    assert [row for row in chunks(library) if row["method"] == "descricao"]  # o índice foi refeito
    again = client.post(f"/api/biblioteca/{doc}/figuras", headers=HEADERS)
    assert again.status_code == 400 and "Não há páginas" in again.json()["erro"]
    assert client.delete(f"/api/biblioteca/{doc}/figuras", headers=HEADERS).status_code == 404
    assert client.get("/api/biblioteca/inexistente/figuras").status_code == 404


def test_figures_route_needs_a_reader_and_can_be_stopped(tmp_path):
    import threading

    client, _, _, result = web(tmp_path)
    info = client.get(f"/api/biblioteca/{result['id']}/figuras").json()
    assert info["disponivel"] is False and info["modelo"] is None
    refused = client.post(f"/api/biblioteca/{result['id']}/figuras", headers=HEADERS)
    assert refused.status_code == 400 and "não está configurada" in refused.json()["erro"]

    gate, entered = threading.Event(), threading.Event()

    def slow(request):
        entered.set()
        assert gate.wait(10)
        return answer([])

    client, _, library, result = web(tmp_path / "outra", slow)
    doc = result["id"]
    job = client.post(f"/api/biblioteca/{doc}/figuras", headers=HEADERS).json()["tarefa"]
    assert entered.wait(10)
    assert client.get(f"/api/biblioteca/{doc}/figuras").json()["tarefa"] == job
    assert client.post(f"/api/biblioteca/{doc}/figuras", headers=HEADERS).status_code == 409  # uma por vez
    blocked = client.delete(f"/api/biblioteca/{doc}", headers=HEADERS)
    assert blocked.status_code == 409  # o documento não é apagado no meio da leitura
    assert client.delete(f"/api/biblioteca/{doc}/figuras", headers=HEADERS).json() == {"parando": True}
    gate.set()
    status = wait_job(client, job)
    # As três páginas já em andamento terminam; a quarta nem começa.
    assert status["resultado"]["interrompido"] and status["resultado"]["lidas"] == 3
    assert client.get(f"/api/biblioteca/{doc}/figuras").json()["por_ler"] == 1


def test_rules_tell_the_model_how_to_use_figure_descriptions():
    from aliado.agent import LIBRARY_RULES

    for wanted in ('method "descricao" é a descrição automática', 'method "figura" é texto reconhecido',
                   "nenhum dos dois é texto do documento", "não os ponha entre aspas", "conferir no original"):
        assert wanted in LIBRARY_RULES, wanted


def test_page_images_can_be_asked_from_several_threads(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "figuras.pdf"
    build_pdf(path)
    expected = {number: figures.page_image(path, number) for number in (1, 3, 4)}
    sections = [{"page": 1, "method": "native", "text": "Figure 1. Diagrama."}]
    # O PDFium não aceita threads simultâneas: sem a trava, este teste derruba o processo de vez em quando.
    with ThreadPoolExecutor(max_workers=8) as pool:
        images = list(pool.map(lambda n: (n, figures.page_image(path, n)), [1, 3, 4] * 20))
        signals = list(pool.map(lambda _: figures.page_signals(path, sections), range(20)))
    assert all(image == expected[number] for number, image in images)
    assert all(signal == signals[0] for signal in signals)


def test_a_caption_found_in_the_text_leads_to_the_description(tmp_path):
    caption = "Figure 1. Diagrama beta do sistema."
    path = tmp_path / "figuras.pdf"
    build_pdf(path, first=(caption, "O alfa fica no bloco central."))
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences(), ocr=Reader())
    result = library.add(path)
    # Só o trecho da legenda fala em "alfa": é o primeiro resultado, com o encoder de teste.
    before = library.search("alfa", limit=2)
    assert before[0]["text"] == f"{caption}\nO alfa fica no bloco central." and before[0]["method"] == "native"
    # A descrição só fala em "beta": sozinha, ficaria atrás de todos os outros trechos nesta busca.
    item = {"tipo": "figura", "rotulo": "Figure 1", "legenda": caption,
            "descricao": "Blocos ligados em serie, do painel ao inversor."}
    figures.describe(library, result["id"], lambda request: answer([item]), workers=1, limit=1)
    found, linked = library.search("alfa", limit=2)
    # A legenda sozinha diz que a figura existe; a descrição, o que ela mostra. A descrição vem logo depois dela.
    assert found["text"] == before[0]["text"] and found["method"] == "native"
    assert linked["method"] == "descricao" and linked["locator"] == "página PDF 1 · Figure 1"
    assert linked["text"].startswith(caption) and linked["score"] == found["score"]
    assert "Blocos ligados em serie" in library.expand([found, linked])[1]["passagem"]
    # O limite continua valendo, e uma busca que não acha a legenda fica como era.
    assert [hit["method"] for hit in library.search("alfa", limit=1)] == ["native"]
    assert "Figure 1" not in " ".join(hit["locator"] for hit in library.search("pagina digitalizada", limit=2))


def test_figure_pages_can_scan_a_document_indexed_before(tmp_path):
    from types import SimpleNamespace

    plain = SimpleNamespace(extract=lambda path, page: ("Figura 3. Curva da banheira digitalizada.", 90.0))
    library, result = library_with(tmp_path, plain)
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        db.execute("DELETE FROM page_figures")  # como um catálogo anterior ao lote 29
        runs = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    assert library.figure_pages(result["id"])["pages"] == []
    reader, steps = Reader(LABELS), []
    library.ocr = reader
    pages = library.figure_pages(result["id"], scan=True, progress=lambda *step: steps.append(step))["pages"]
    assert [page["page"] for page in pages] == [1, 3, 4, 5] and steps == [("figuras", 1, 1)]
    assert pages[0]["local_text"]["texto"].startswith("Inversor central") and not any(page["read"] for page in pages)
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == runs  # nenhuma extração nova
    library.figure_pages(result["id"], scan=True)
    assert len(reader.regions) == 1  # o reconhecimento não se repete


def test_descriptions_do_not_compete_by_words(tmp_path):
    from aliado.knowledge import library as module

    library, result = library_with(tmp_path)
    item = {"tipo": "figura", "rotulo": "Figure 1", "legenda": "Figure 1. Diagrama de blocos do sistema.",
            "descricao": "O gama liga o barramento ao transformador."}
    figures.describe(library, result["id"], lambda request: answer([item]), workers=1, limit=1)
    assert module.SEARCH_SETTINGS["descricoes_por_palavras"] is False
    # "gama" só existe na descrição. Pela palavra ela seria a primeira; pelo significado, o encoder de teste não
    # a distingue dos outros trechos, e ela não ganha o bônus da palavra.
    plain = [hit["method"] for hit in library.search("gama", limit=1)]
    module.SEARCH_SETTINGS["descricoes_por_palavras"] = True
    try:
        boosted = library.search("gama", limit=1)
    finally:
        module.SEARCH_SETTINGS["descricoes_por_palavras"] = False
    assert boosted[0]["method"] == "descricao" and "gama" in boosted[0]["text"]
    assert library.search_settings["descricoes_por_palavras"] is False and len(plain) == 1
