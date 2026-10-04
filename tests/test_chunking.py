"""Lote 29: limpeza das páginas, trechos por frase e a biblioteca com os dois esquemas de trechos."""

from __future__ import annotations

import json
import re
import sqlite3

import pytest

from aliado.knowledge import chunking
from aliado.knowledge.chunking import REFERENCES, SUMMARY, clean_pages, pack, sentences
from aliado.knowledge.library import DocumentLibrary


def tokens(text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in re.finditer(r"\S+", text)]


class Sentences:
    """Encoder de teste que informa a posição dos tokens: cada palavra é um token, 12 por trecho."""

    fingerprint = "synthetic-window-encoder-v1"
    chunk_tokens = 12

    def __init__(self):
        self.calls = []

    def token_spans(self, text):
        return tokens(text)

    def split(self, text):
        return [text] if text.strip() else []

    def encode(self, texts):
        self.calls.append(len(texts))
        return [[float("alfa" in text.lower()), float("beta" in text.lower()), 1.0] for text in texts]


class Fixed:
    """O mesmo modelo, com a divisão antiga: fatias de 12 palavras com passo de 8."""

    fingerprint = "synthetic-window-encoder-v1"

    def split(self, text):
        words, pieces = tokens(text), []
        for start in range(0, len(words), 8):
            end = min(start + 12, len(words))
            pieces.append(text[words[start][0]:words[end - 1][1]])
            if end == len(words):
                break
        return pieces

    def encode(self, texts):
        return [[float("alfa" in text.lower()), float("beta" in text.lower()), 1.0] for text in texts]


def make_pdf(path, pages: list[list[str]]) -> None:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica"),
                             NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
    for lines in pages:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        body = " T* ".join("({}) Tj".format(line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)"))
                           for line in lines)
        stream.set_data(f"BT /F1 9 Tf 11 TL 40 770 Td {body} ET".encode("cp1252"))
        page[NameObject("/Contents")] = stream
    writer.write(path)


def kept(text: str, parts) -> list[tuple[str, str | None]]:
    return [(text[a:b], kind) for a, b, kind in parts]


def word(number: int) -> str:
    """Um nome sem algarismos para cada página: linhas que só mudam nos números contam como repetidas."""
    letters = ""
    while True:
        letters, number = "abcdefghijklmnopqrstuvwxyz"[number % 26] + letters, number // 26
        if not number:
            return "pg" + letters


def prose(prefix: str, lines: int = 6) -> list[str]:
    return [f"{prefix} linha {n} do corpo da pagina, com texto corrido." for n in range(1, lines + 1)]


def test_repeated_headers_and_footers_leave_the_pieces():
    pages = []
    for number in range(1, 9):
        head = ["Revista de Testes 2024, 5, 100", f"{number} of 8"]
        pages.append("\n".join(head + prose(f"Pagina {word(number)}") + ["www.exemplo.org/revista"]))
    parts, record = clean_pages(pages)
    assert record["linhas_de_borda"] == 24 and record["padroes_de_borda"] == [
        "# of #", "revista de testes #, #, #", "www.exemplo.org/revista"]
    for number, (text, part) in enumerate(zip(pages, parts), 1):
        (piece, kind), = kept(text, part)
        assert kind is None and piece == "\n".join(prose(f"Pagina {word(number)}"))  # uma fatia só, sem as bordas
    # Com menos de 4 páginas não há como saber o que se repete: nada sai.
    assert clean_pages(pages[:3])[1]["linhas_de_borda"] == 0


def test_only_the_lines_at_the_edge_leave():
    pages = []
    for number in range(1, 9):
        body = prose(f"Pagina {word(number)}")
        body.insert(3, "Revista de Testes 2024, 5, 100")  # a mesma linha no meio do texto fica
        pages.append("\n".join(["Revista de Testes 2024, 5, 100"] + body))
    parts, record = clean_pages(pages)
    assert record["linhas_de_borda"] == 8
    assert all(text[part[0][0]:part[0][1]].count("Revista de Testes") == 1 for text, part in zip(pages, parts))


def test_a_chapter_header_with_the_page_number_leaves_and_captions_stay():
    pages = []
    for number in range(1, 41):
        lines = prose(f"Pagina {word(number)}")
        if 10 <= number < 20:  # cabeçalho do capítulo em 10 das 40 páginas: menos de 30%
            lines.insert(0, f"{number + 95} 3 Control Technology of Systems")
        if 20 <= number < 30:  # título de tabela continuada, sem número de página: não é cabeçalho
            lines.insert(0, "Equipamento Taxa de falha Horas de reparo")
        if number % 3 == 0:  # legenda no pé da página
            lines.append(f"Figura 4.{number}")
        pages.append("\n".join(lines))
    parts, record = clean_pages(pages)
    assert record["padroes_de_borda"] == ["# # control technology of systems"] and record["linhas_de_borda"] == 10
    text = lambda number: pages[number - 1][parts[number - 1][0][0]:parts[number - 1][0][1]]  # noqa: E731
    assert text(12).startswith(f"Pagina {word(12)} linha 1") and text(12).endswith("Figura 4.12")
    assert text(21).startswith("Equipamento Taxa de falha")
    # O número que não acompanha a página (uma figura por página, numerada por capítulo) não vira rodapé.
    numbered = ["\n".join(prose(f"Pagina {word(n)}") + [f"Nota {n % 4}"]) for n in range(1, 41)]
    assert clean_pages(numbered)[1]["linhas_de_borda"] == 40  # repete em todas: sai pela regra dos 30%
    sparse = ["\n".join(prose(f"Pagina {word(n)}") + ([f"Etapa {n // 7}"] if n % 5 == 0 else [])) for n in range(1, 41)]
    assert clean_pages(sparse)[1]["linhas_de_borda"] == 0


def test_summary_pages_are_marked():
    summary = "\n".join(["Sumario"] + [f"{n}.1 Secao numero {n} " + ". " * 20 + str(n * 3) for n in range(1, 9)])
    body = "\n".join(prose("Corpo"))
    dotted = "\n".join(prose("Corpo") + ["Assinatura " + "." * 30])  # uma linha pontilhada não faz um sumário
    parts, record = clean_pages([summary, body, dotted, body])
    assert record["sumario"] == [0]
    assert [kind for _, _, kind in parts[0]] == [SUMMARY] and [kind for _, _, kind in parts[2]] == [None]


def test_reference_list_is_marked_until_the_entries_stop():
    entries = [f"[{n}] A. Autor, B. Outro, Titulo do artigo numero {n}, Revista, vol. 3, 201{n}." for n in range(1, 8)]
    last = "\n".join(prose("Conclusao", 3) + ["References"] + entries[:4])
    following = "\n".join(entries[4:] + ["Appendix A"] + prose("Apendice", 12))
    parts, record = clean_pages(["\n".join(prose("Inicio")), last, following])
    assert record["referencias"] == [1, 2]
    (body, none), (references, kind) = kept(last, parts[1])
    assert none is None and body.strip().endswith("Conclusao linha 3 do corpo da pagina, com texto corrido.")
    assert kind == REFERENCES and references.startswith("References") and references.endswith("2014.")
    (references, kind), (appendix, none) = kept(following, parts[2])
    assert kind == REFERENCES and references.startswith("[5]") and references.endswith("2017.")
    assert none is None and appendix.strip().startswith("Appendix A") and "Apendice linha 12" in appendix


def test_references_per_chapter_do_not_take_the_next_chapter():
    entries = [f"{n}. Silva, J. Titulo do livro numero {n}. Editora, 200{n}." for n in range(1, 6)]
    chapter = ["2 Segundo capitulo", "1. Introducao do capitulo", *prose("Capitulo dois", 10)]
    page = "\n".join(prose("Capitulo um", 3) + ["Referências"] + entries + chapter)
    parts, _ = clean_pages([page])
    pieces = kept(page, parts[0])
    assert [kind for _, kind in pieces] == [None, REFERENCES, None]
    assert pieces[1][0].endswith("2005.") and pieces[2][0].strip().startswith("2 Segundo capitulo")
    # Lista por autor, no padrão da ABNT, e o fim do documento.
    abnt = ["LAFRAIA, J. R. B. Manual de confiabilidade. Qualitymark, 2001.", "NBR 5462. Confiabilidade. ABNT, 1994.",
            "MOUBRAY, John. Reliability-centered maintenance. Industrial Press, 1997.",
            "SMITH, A. M. RCM: gateway to world class maintenance. Elsevier, 2004.", "Nota final sem ano nem autor."]
    page = "\n".join(prose("Texto", 3) + ["REFERÊNCIAS BIBLIOGRÁFICAS"] + abnt)
    parts, _ = clean_pages([page])
    assert kept(page, parts[0])[-1] == ("\n".join(["REFERÊNCIAS BIBLIOGRÁFICAS"] + abnt), REFERENCES)


def test_a_loose_references_title_is_not_a_list():
    page = "\n".join(prose("Antes", 3) + ["References"] + prose("As referencias de 2019 e 2020 foram revistas", 12))
    parts, record = clean_pages([page])
    assert record["referencias"] == [] and [kind for _, _, kind in parts[0]] == [None]
    two = "\n".join(["Referências", "[1] A. Autor, Titulo, 2019.", "[2] B. Autor, Outro titulo, 2020."] + prose("Depois", 10))
    assert clean_pages([two])[1]["referencias"] == []  # menos de 3 entradas


def test_glyph_codes_leave_the_pieces():
    page = "\n".join(prose("Antes", 2) + ["/gid00030/gid00035/gid00032"] + prose("Depois", 2))
    parts, record = clean_pages([page])
    assert record["glifos"] == 1 and "gid" not in "".join(piece for piece, _ in kept(page, parts[0]))
    assert len(parts[0]) == 2


def test_sentences_keep_abbreviations_initials_and_short_pieces_together():
    text = ("A confiabilidade é dada por R(t). Segundo Baschel et al. (2018), a taxa é 26,7. A Fig. 3 mostra o resultado. "
            "J. R. B. Lafraia define o MTBF. Fim.")
    found = [text[a:b] for a, b in sentences(text)]
    assert found == ["A confiabilidade é dada por R(t).", "Segundo Baschel et al. (2018), a taxa é 26,7.",
                     "A Fig. 3 mostra o resultado.", "J. R. B. Lafraia define o MTBF. Fim."]
    # Um pedaço curto no começo segue com a frase seguinte; a linha em branco separa parágrafos.
    text = "1. Introdução geral ao tema da confiabilidade.\n\nsegundo parágrafo, sem maiúscula no começo"
    assert [text[a:b] for a, b in sentences(text)] == ["1. Introdução geral ao tema da confiabilidade.",
                                                       "segundo parágrafo, sem maiúscula no começo"]
    assert sentences("") == [] and [("Só uma frase."[a:b]) for a, b in sentences("Só uma frase.")] == ["Só uma frase."]


def test_pack_keeps_whole_sentences_within_the_limit():
    text = " ".join(f"Frase {n} tem seis palavras aqui." for n in range(1, 6))
    spans = pack(text, 0, len(text), tokens(text), 12)
    pieces = [text[a:b] for a, b in spans]
    assert pieces == ["Frase 1 tem seis palavras aqui. Frase 2 tem seis palavras aqui.",
                      "Frase 3 tem seis palavras aqui. Frase 4 tem seis palavras aqui.", "Frase 5 tem seis palavras aqui."]
    # Tamanhos equilibrados: 4 frases de 6 palavras e uma de 3 viram 3 trechos, sem sobra de uma frase só no fim.
    text = "Um dois tres quatro cinco seis sete. " * 3 + "Oito nove dez onze doze treze catorze."
    pieces = [text[a:b] for a, b in pack(text, 0, len(text), tokens(text), 12)]
    assert [len(piece.split()) for piece in pieces] == [7, 7, 7, 7]
    assert "".join(pieces).replace(" ", "") == text.replace(" ", "")  # nada se perde nem se repete


def test_a_long_sentence_is_cut_at_line_breaks_and_then_by_tokens():
    table = "\n".join(f"Componente {n} 0.1 0.2 0.3 0.4" for n in range(1, 6))  # 5 linhas de 6 palavras, sem pontuação
    pieces = [table[a:b] for a, b in pack(table, 0, len(table), tokens(table), 12)]
    assert pieces == ["\n".join(table.splitlines()[0:2]), "\n".join(table.splitlines()[2:4]), table.splitlines()[4]]
    line = " ".join(f"p{n:02d}" for n in range(1, 31))  # uma linha só, com 30 palavras
    pieces = [line[a:b] for a, b in pack(line, 0, len(line), tokens(line), 12)]
    assert [len(piece.split()) for piece in pieces] == [12, 12, 6] and " ".join(pieces) == line
    # Um título curto fecha o bloco: a frase que vem depois não é cortada no meio.
    block = ("valor a 1\nvalor b 2\nvalor c 3\nvalor d 4\nvalor e 5\nParte tres\n"
             "Para demonstrar o efeito das leis de controle no laco\nde potencia do lado alternado usa-se o modelo.")
    pieces = [block[a:b] for a, b in pack(block, 0, len(block), tokens(block), 20)]
    assert pieces[-1].startswith("Para demonstrar") and pieces[-1].endswith("usa-se o modelo.")


def test_a_long_line_is_cut_at_the_start_of_a_word():
    def halves(text: str) -> list[tuple[int, int]]:
        """Dois tokens por palavra, como um tokenizador de subpalavras."""
        spans = []
        for start, end in tokens(text):
            middle = (start + end) // 2
            spans += [(start, middle), (middle, end)] if end - start > 1 else [(start, end)]
        return spans

    line = " ".join(f"palavra{n:02d}" for n in range(1, 21))  # 20 palavras, 40 tokens, sem pontuação
    pieces = [line[a:b] for a, b in pack(line, 0, len(line), halves(line), 15)]
    # 15 tokens por trecho cairiam no meio da 8ª palavra: o corte recua para o começo dela.
    assert all(piece == " ".join(piece.split()) and not piece.startswith("ra") for piece in pieces)
    assert [len(piece.split()) for piece in pieces] == [7, 7, 6] and " ".join(pieces) == line
    assert all(re.fullmatch(r"palavra\d\d", word) for piece in pieces for word in piece.split())


def test_a_caption_always_starts_a_new_piece():
    text = ("A taxa de falha vem da equacao dez.\nA confiabilidade vem da equacao onze.\n"
            "Fig. 3. Fault tree diagram of a household PV system [12].\n"
            "Figure 5 explains the availability further in the text.\n"
            "Table 7-2— Failure modes of circuit breakers\nFechou sem comando 5 por cento\n"
            "Figura 4.3 – Formulário de FMECA adaptado da SAE.")
    pieces = [text[a:b] for a, b in pack(text, 0, len(text), tokens(text), 40)]
    # Sem a regra, a legenda da figura iria no mesmo trecho das duas frases de cima.
    assert pieces == ["A taxa de falha vem da equacao dez.\nA confiabilidade vem da equacao onze.",
                      "Fig. 3. Fault tree diagram of a household PV system [12].\n"
                      "Figure 5 explains the availability further in the text.",  # a menção no texto não abre trecho
                      "Table 7-2— Failure modes of circuit breakers\nFechou sem comando 5 por cento",
                      "Figura 4.3 – Formulário de FMECA adaptado da SAE."]
    for caption in ("Fig. 3.2 The configuration of the system", "TABLE 3 | Summary of methods", "Quadro 4.1 – Modo de falha",
                    "Figure 1: Series branch", "Tabela 6 – Classificação", "Gráfico 2. Curva"):
        text = f"Uma frase qualquer antes da legenda.\n{caption}"
        assert [text[a:b] for a, b in pack(text, 0, len(text), tokens(text), 40)][-1] == caption, caption
    for mention in ("Table 1 summarises the failure rates used here.", "figure 2 shows the layout.", "Tabela de valores medidos."):
        text = f"Uma frase qualquer antes.\n{mention}"
        assert len(pack(text, 0, len(text), tokens(text), 40)) == 1, mention


def test_a_description_is_split_into_pieces_of_similar_size():
    class Wide(Sentences):
        chunk_tokens = 20

    text = ("Figure 2. Fault tree of the inverter. Descrição automática da figura: A árvore liga o evento de topo a "
            "três ramos por uma porta OU. O primeiro ramo trata do lado de corrente contínua. O segundo ramo trata "
            "do lado de corrente alternada e da rede.\n"
            "Texto visível na figura: Inverter; DC side; AC side; Grid; Fuse; Switch\n"
            "Transcrição automática da tabela:\nComponente | Taxa\nInversor | 26.7\nFusível | 0.5")
    # 71 palavras em trechos de até 20. O corte fica perto do tamanho ideal: no fim de uma linha, se houver;
    # senão no fim de uma frase; senão entre duas palavras, como no primeiro trecho.
    assert chunking.filled(text, Wide()) == [
        "Figure 2. Fault tree of the inverter. Descrição automática da figura: A árvore liga o evento de topo",
        "a três ramos por uma porta OU. O primeiro ramo trata do lado de corrente contínua.",
        "O segundo ramo trata do lado de corrente alternada e da rede.",
        "Texto visível na figura: Inverter; DC side; AC side; Grid; Fuse; Switch",
        "Transcrição automática da tabela:\nComponente | Taxa\nInversor | 26.7\nFusível | 0.5"]
    assert chunking.filled("Uma descrição curta.", Wide()) == ["Uma descrição curta."]
    assert chunking.filled("", Wide()) == [] and chunking.filled(text, Fixed()) is None
    # Sem fim de frase nem de linha por perto, o corte fica entre duas palavras, e nenhum trecho fica só com a sobra.
    words = " ".join(f"p{n:02d}" for n in range(1, 46))
    assert [len(piece.split()) for piece in chunking.filled(words, Wide())] == [15, 15, 15]


def test_the_first_piece_of_a_description_reaches_the_description():
    class Wide(Sentences):
        chunk_tokens = 30

    opening = "Table 2. Taxas de falha por componente do inversor central. Descrição automática da tabela: "
    text = opening + ("Valores medidos em campo para cada componente do sistema, com a fonte de cada um "
                      "e a data da medida.")
    # A legenda termina em ponto, perto do tamanho ideal: sem a posição mínima, o primeiro trecho seria só ela.
    assert chunking.filled(text, Wide())[0] == "Table 2. Taxas de falha por componente do inversor central."
    first, second = chunking.filled(text, Wide(), head=len(opening) + 40)
    assert first == opening + "Valores medidos em campo para cada componente"
    assert second == "do sistema, com a fonte de cada um e a data da medida."
    # Se a posição mínima não cabe no limite, vale a regra comum.
    assert chunking.filled(text, Wide(), head=len(text))[0] == "Table 2. Taxas de falha por componente do inversor central."


def test_pieces_respect_the_parts_and_fall_back_without_token_positions():
    text = "Primeira frase do corpo da página. Segunda frase do corpo.\nReferences\n[1] A. Autor, Título, 2019."
    cut = text.index("References")
    parts = [(0, cut, None), (cut, len(text), REFERENCES)]
    found = chunking.pieces(text, parts, Sentences())
    assert found == [("Primeira frase do corpo da página. Segunda frase do corpo.", None),
                     ("References\n[1] A. Autor, Título, 2019.", REFERENCES)]
    assert all(piece in text for piece, _ in found)
    assert chunking.pieces(text, parts, Fixed()) is None and chunking.scheme(Fixed()) is None
    assert chunking.scheme(Sentences()) == "frases12-v1"
    assert chunking.marked("página PDF 3", REFERENCES) == "página PDF 3 · referências"
    assert chunking.support("página PDF 3 · referências") and chunking.support("página PDF 5 · sumário")
    assert not chunking.support("página PDF 3") and not chunking.support("página PDF 3 · Figura 2")
    assert chunking.asks_support("Quais referências o artigo cita?") and chunking.asks_support("Show the table of contents")
    assert not chunking.asks_support("Qual a taxa de falha do inversor?")


BODY = ["O alfa mede a confiabilidade do inversor em campo.", "A taxa de falha foi estimada com dados reais.",
        "O beta descreve o reparo do equipamento.", "A manutencao preventiva reduz as paradas."]
ENTRIES = [f"[{n}] A. Autor, Estudo alfa numero {n}, Revista, vol. 2, 201{n}." for n in range(1, 6)]


def document(tmp_path, name="artigo.pdf", closing="Conclusao do estudo sobre o gama."):
    pages = [["Revista de Testes 2024", f"{number} of 5", *(f"Pagina {word(number)}: {line}" for line in BODY)]
             for number in range(1, 5)]
    pages.append(["Revista de Testes 2024", "5 of 5", closing, "References", *ENTRIES])
    path = tmp_path / name
    make_pdf(path, pages)
    return path


def rows(library: DocumentLibrary, title: str) -> list[sqlite3.Row]:
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        db.row_factory = sqlite3.Row
        return db.execute("""SELECT c.id, c.text, c.locator, c.page, r.encoder FROM chunks c JOIN runs r ON r.id=c.run_id
            JOIN documents d ON d.active_run=r.id WHERE d.title=? ORDER BY c.rowid""", (title,)).fetchall()


def test_library_cleans_and_splits_by_sentence(tmp_path):
    pytest.importorskip("pypdf")
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences())
    result = library.add(document(tmp_path))
    assert result["status"] == "ready"
    stored = rows(library, "artigo.pdf")
    assert {row["encoder"] for row in stored} == {"synthetic-window-encoder-v1:frases12-v1"}
    texts = [row["text"] for row in stored]
    assert not any("Revista de Testes" in text or " of 5" in text for text in texts)  # cabeçalho fora dos trechos
    assert all(len(text.split()) <= 12 for text in texts)
    first = [row["text"] for row in stored if row["page"] == 1]
    assert first == [f"Pagina {word(1)}: {line}" for line in BODY]
    marked = [row for row in stored if row["locator"].endswith("referências")]
    assert marked and all(row["page"] == 5 for row in marked) and marked[0]["text"].startswith("References")
    # O texto guardado da página continua inteiro, com o cabeçalho; o registro diz o que saiu.
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        path = db.execute("SELECT json_path FROM runs").fetchone()[0]
    metadata = json.loads((library.root / path).read_text(encoding="utf-8"))
    assert metadata["sections"][0]["text"].startswith("Revista de Testes 2024\n1 of 5")
    assert metadata["limpeza"] == {"trechos_repetidos": 0, "linhas_de_borda": 10,
                                  "padroes_de_borda": ["# of #", "revista de testes #"], "paginas_de_sumario": [],
                                  "paginas_com_referencias": [5], "glifos": 0}
    assert metadata["encoder"] == "synthetic-window-encoder-v1:frases12-v1" and library.verify()["ok"]


def test_references_stay_out_of_the_search_until_asked(tmp_path):
    pytest.importorskip("pypdf")
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences())
    library.add(document(tmp_path))
    hits = library.search("alfa", limit=20)
    assert hits and not any("referências" in hit["locator"] or "Autor" in hit["text"] for hit in hits)
    asked = library.search("Quais referências citam o alfa?", limit=20)
    assert any(hit["locator"] == "página PDF 5 · referências" for hit in asked)
    # Só referências combinam com a pergunta: a busca comum volta vazia, em vez de trazê-las.
    only = DocumentLibrary(tmp_path / "outra", encoder=Sentences())
    path = tmp_path / "lista.pdf"
    make_pdf(path, [["References", *ENTRIES]])
    only.add(path)
    assert only.search("alfa") == [] and only.search("referências sobre alfa")


def test_passage_joins_sentence_pieces_with_a_line_break(tmp_path):
    pytest.importorskip("pypdf")
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences())
    library.add(document(tmp_path))
    page = [row for row in rows(library, "artigo.pdf") if row["page"] == 2]
    hit = {"citation_id": page[1]["id"], "text": page[1]["text"]}
    passage = library.expand([hit])[0]["passagem"]
    assert passage == "\n".join(row["text"] for row in page[:3])
    # Na borda da página a passagem para; e a parte de referências não se junta ao corpo.
    assert library.expand([{"citation_id": page[0]["id"], "text": page[0]["text"]}])[0]["passagem"] == \
        "\n".join(row["text"] for row in page[:2])
    last = [row for row in rows(library, "artigo.pdf") if row["page"] == 5]
    body = [row for row in last if not row["locator"].endswith("referências")]
    assert library.expand([{"citation_id": body[-1]["id"], "text": body[-1]["text"]}])[0]["passagem"] == \
        "\n".join(row["text"] for row in body)


def test_old_and_new_pieces_are_searched_together_and_reindex_keeps_history(tmp_path):
    pytest.importorskip("pypdf")
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Fixed())
    old = library.add(document(tmp_path))
    other = library.add(document(tmp_path, "outro.pdf", "Conclusao de outro estudo sobre o delta."))
    assert {row["encoder"] for row in rows(library, "artigo.pdf")} == {"synthetic-window-encoder-v1"}
    assert any("Revista de Testes" in row["text"] for row in rows(library, "artigo.pdf"))  # sem limpeza, como antes
    encoder = Sentences()
    library.encoder = encoder
    steps = []
    new = library.reindex(old["id"], progress=lambda *step: steps.append(step))
    assert new["id"] == old["id"] and new["version"] == 1 and new["run_id"] != old["run_id"] and new["status"] == "ready"
    assert {row["encoder"] for row in rows(library, "artigo.pdf")} == {"synthetic-window-encoder-v1:frases12-v1"}
    assert {row["encoder"] for row in rows(library, "outro.pdf")} == {"synthetic-window-encoder-v1"}
    assert steps[0][0] == "indexando" and steps[-1] == ("indexando", steps[-1][2], steps[-1][2])
    # Os dois esquemas no mesmo índice: a busca traz trechos dos dois documentos.
    assert {hit["title"] for hit in library.search("alfa", limit=20)} == {"artigo.pdf", "outro.pdf"}
    # A passagem de um trecho antigo ainda se une pela parte repetida, sem a quebra de linha.
    before, piece, after = rows(library, "outro.pdf")[:3]
    passage = library.expand([{"citation_id": piece["id"], "text": piece["text"]}])[0]["passagem"]
    assert passage.startswith(before["text"]) and passage.endswith(after["text"]) and piece["text"] in passage
    assert len(passage) < len(before["text"]) + len(piece["text"]) + len(after["text"])  # a parte comum não se repete
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 3  # a extração anterior continua guardada
        assert db.execute("SELECT COUNT(*) FROM chunks WHERE run_id=?", (old["run_id"],)).fetchone()[0] > 0
    assert library.verify()["ok"]
    # Reindexar de novo não chama o modelo: todo trecho tem o vetor da extração anterior.
    encoder.calls.clear()
    again = library.reindex(old["id"])
    assert encoder.calls == [] and again["chunks"] == new["chunks"] and library.verify()["ok"]
    assert other["id"] != old["id"]
    with pytest.raises(ValueError, match="não encontrado"):
        library.reindex("inexistente")
    # Um encoder de outro modelo continua barrado.
    library.encoder.fingerprint = "outro-modelo-v1"
    with pytest.raises(ValueError, match="Encoder"):
        library.search("alfa")


def test_reindex_only_the_latest_version_and_keeps_page_issues(tmp_path):
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences())
    source = tmp_path / "nota.md"
    source.write_text("# Nota\nO alfa mede a confiabilidade. O beta mede o reparo.", encoding="utf-8")
    first = library.add(source)
    source.write_text("# Nota\nO alfa agora é outro. O beta também mudou bastante.", encoding="utf-8")
    second = library.add(source)
    with pytest.raises(ValueError, match="mais recente"):
        library.reindex(first["id"])
    done = library.reindex(second["id"])
    assert done["version"] == 2 and library.search("alfa")[0]["text"].startswith("# Nota\nO alfa agora")
    assert library.verify()["ok"]


def test_a_repeated_piece_enters_once(tmp_path):
    pytest.importorskip("pypdf")
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences())
    path = tmp_path / "repetido.pdf"
    notice = "Aviso legal: o uso deste material segue a licenca do editor."
    make_pdf(path, [[BODY[0], notice], [BODY[2], notice], [notice]])
    library.add(path)
    texts = [row["text"] for row in rows(library, "repetido.pdf")]
    assert texts == [BODY[0], notice, BODY[2]]
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        path = db.execute("SELECT json_path FROM runs").fetchone()[0]
    assert json.loads((library.root / path).read_text(encoding="utf-8"))["limpeza"]["trechos_repetidos"] == 2
    # Num documento com mais páginas, a linha que se repete na borda já sai como rodapé.
    longer = tmp_path / "rodape.pdf"
    make_pdf(longer, [[f"Pagina {word(n)}: {BODY[0]}", notice] for n in range(1, 7)])
    library.add(longer)
    assert not any(notice in row["text"] for row in rows(library, "rodape.pdf"))
