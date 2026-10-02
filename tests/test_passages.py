"""Lote 27: passagem com os trechos vizinhos, indexação em fatias, trechos agrupados por documento e
o que a busca trouxe e a resposta não citou."""

from __future__ import annotations

import json
import re
import sqlite3
from types import SimpleNamespace

import pytest

from aliado.agent import LIBRARY_RULES, Agent, prepare_request
from aliado.knowledge.embeddings import ENCODE_BATCH, MODEL_FILE, LocalEncoder
from aliado.knowledge.library import INDEX_SLICE, MIN_OVERLAP, DocumentLibrary, _join
from aliado.llm.contracts import LLMResult


class Windows:
    """Encoder de teste: fatias de 12 palavras com passo de 8, como o real faz com tokens (110 e 90)."""

    fingerprint = "synthetic-window-encoder-v1"

    def __init__(self):
        self.calls = []

    def split(self, text):
        words = [(match.start(), match.end()) for match in re.finditer(r"\S+", text)]
        pieces = []
        for start in range(0, len(words), 8):
            end = min(start + 12, len(words))
            pieces.append(text[words[start][0]:words[end - 1][1]])
            if end == len(words):
                break
        return pieces

    def encode(self, texts):
        self.calls.append(len(texts))
        return [[float("alfa" in text), float("beta" in text), 1.0] for text in texts]


def words(prefix: str, count: int) -> str:
    return " ".join(f"{prefix}{n:02d}" for n in range(1, count + 1))


def add(library: DocumentLibrary, tmp_path, name: str, text: str) -> dict:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return library.add(path)


def pieces(library: DocumentLibrary, title: str) -> list[dict]:
    """Os trechos da versão mais recente do documento, na ordem de gravação, no formato que a busca devolve."""
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        rows = db.execute("""SELECT c.id, c.text, c.locator FROM chunks c JOIN runs r ON r.id=c.run_id
            JOIN documents d ON d.active_run=r.id WHERE d.title=?
            AND d.version=(SELECT MAX(v.version) FROM documents v WHERE v.title=d.title)
            ORDER BY c.rowid""", (title,)).fetchall()
    return [{"citation_id": row[0], "text": row[1], "locator": row[2]} for row in rows]


def test_join_removes_only_the_repeated_part():
    assert _join("a definição de confiabilidade é a", "confiabilidade é a probabilidade") == \
        "a definição de confiabilidade é a probabilidade"
    assert _join("o fim deste trecho", "outro começo, sem nada em comum") is None
    # Uma coincidência curta não basta: os textos têm de se sobrepor de verdade.
    assert MIN_OVERLAP == 12 and _join("termina em abc", "abc começa aqui") is None
    # Texto repetitivo: mais de um tamanho de sobreposição serve, e unir cortaria repetições.
    assert _join("x" * 30, "x" * 30) is None
    row = "Falhas por mês do inversor 7: " + "0 " * 40
    assert _join(row, "0 " * 40 + "total 0") is None
    assert _join("início " + "0 1 2 3 4 5 6 7 8 9 ", "1 2 3 4 5 6 7 8 9 fim") == "início 0 1 2 3 4 5 6 7 8 9 fim"


def test_two_possible_overlaps_are_settled_by_splitting_the_joined_text_again(tmp_path):
    encoder = Windows()
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=encoder)
    # A parte comum dos dois trechos (4 palavras) começa e termina com o mesmo termo: dois encaixes servem.
    term = "manutencaopreditiva"
    text = " ".join([f"a{n:02d}" for n in range(1, 9)] + [term, "b01", "b02", term] + [f"c{n:02d}" for n in range(1, 9)])
    add(library, tmp_path, "prosa.md", text)
    left, right = (piece["text"] for piece in pieces(library, "prosa.md"))
    assert left.endswith(f"{term} b01 b02 {term}") and right.startswith(f"{term} b01 b02 {term}")
    assert _join(left, right) is None  # sem a divisão para desempatar, não une
    assert _join(left, right, split=encoder.split) == text  # o encaixe maior, confirmado pela divisão
    assert _join(left, right, split=lambda joined: [joined]) is None  # a divisão não devolve os dois trechos
    assert library.expand(pieces(library, "prosa.md")[:1])[0]["passagem"] == text
    # Pontilhado de sumário: muitos encaixes, e aqui a divisão também não devolve os dois trechos.
    dots = ". " * 30
    assert _join("Figura 7 " + dots.strip(), dots + "24", split=encoder.split) is None
    # Quatro encaixes e a divisão devolve os dois trechos: quem recusa é a regra de três ou mais.
    word = "abcdefghijkl"
    repeated = " ".join([f"a{n:02d}" for n in range(1, 9)] + [word] * 4 + [f"c{n:02d}" for n in range(1, 9)])
    left, right = encoder.split(repeated)
    assert encoder.split(left + right[51:]) == [left, right] and _join(left, right, split=encoder.split) is None
    # A divisão indisponível (modelo local ausente) não une.
    left, right = f"antes {term} b01 b02 {term}", f"{term} b01 b02 {term} depois"

    def broken(joined):
        raise ValueError("Modelo local ausente.")

    assert _join(left, right, split=lambda joined: [left, right]) == f"antes {term} b01 b02 {term} depois"
    assert _join(left, right, split=broken) is None


def test_a_piece_already_inside_a_better_passage_is_not_expanded(tmp_path):
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Windows())
    # A extração repetiu o mesmo parágrafo na página: o 1º e o 3º trechos têm o mesmo texto.
    block = [f"r{n:02d}" for n in range(1, 13)]
    text = " ".join(block + [f"y{n}" for n in range(1, 5)] + block + [f"z{n:02d}" for n in range(1, 9)])
    add(library, tmp_path, "repetido.md", text)
    p = pieces(library, "repetido.md")
    assert p[0]["text"] == p[2]["text"] == " ".join(block)
    first, third = library.expand([p[0], p[2]])
    assert first["passagem"].startswith(p[0]["text"]) and first["passagem"].endswith(p[1]["text"])
    assert third["passagem"] == third["text"]  # já vai inteiro na passagem do primeiro: não é ampliado


def test_expand_adds_the_previous_and_next_piece_of_the_same_section(tmp_path):
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Windows())
    text = f"# Um\n{words('a', 39)}\n# Dois\n{words('b', 20)}"
    add(library, tmp_path, "manual.md", text)
    first, second = [p for p in pieces(library, "manual.md") if p["locator"] == "linhas 1–2"], \
        [p for p in pieces(library, "manual.md") if p["locator"] != "linhas 1–2"]
    assert len(first) == 5 and len(second) == 3
    section = text.split("\n# Dois")[0]
    middle = library.expand([first[2]])[0]
    assert middle["text"] == first[2]["text"]  # o trecho indexado continua como a busca o achou
    assert middle["passagem"] == section[section.index(first[1]["text"][:6]):section.index(first[3]["text"]) + len(first[3]["text"])]
    assert middle["passagem"] in section and len(middle["passagem"]) > len(middle["text"])
    # Na borda da seção, a passagem para: o trecho seguinte é de outra parte do documento.
    last = library.expand([first[-1]])[0]["passagem"]
    assert last.endswith("a39") and "b01" not in last and last in section
    start = library.expand([second[0]])[0]["passagem"]
    assert start.startswith("# Dois") and "a39" not in start
    wide = library.expand([first[2]], neighbours=2)[0]["passagem"]
    assert wide == section  # dois vizinhos de cada lado cobrem a seção inteira
    assert library.expand([first[2]], neighbours=0)[0]["passagem"] == first[2]["text"]


def test_expand_never_reuses_a_hit_or_a_used_neighbour(tmp_path):
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Windows())
    add(library, tmp_path, "manual.md", f"# Um\n{words('a', 39)}")
    p = pieces(library, "manual.md")
    # Dois resultados vizinhos: nenhum repete o outro.
    one, two = library.expand([p[1], p[2]])
    assert one["passagem"].startswith(p[0]["text"]) and one["passagem"].endswith(p[1]["text"])
    assert two["passagem"].startswith(p[2]["text"]) and two["passagem"].endswith(p[3]["text"])
    # O vizinho usado pelo primeiro resultado não entra de novo no seguinte.
    one, three = library.expand([p[0], p[2]])
    assert one["passagem"].endswith(p[1]["text"]) and three["passagem"].startswith(p[2]["text"])
    assert three["passagem"].endswith(p[3]["text"])


def test_expand_survives_deleted_documents_new_versions_and_unknown_ids(tmp_path):
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Windows())
    old = add(library, tmp_path, "antigo.md", f"# Antigo\n{words('z', 30)}")
    add(library, tmp_path, "manual.md", f"# Um\n{words('a', 39)}")
    gone = pieces(library, "antigo.md")
    library.delete(old["id"])  # abre um vão na ordem de gravação, antes do manual
    add(library, tmp_path, "manual.md", f"# Um\n{words('c', 39)}")  # versão 2: outra extração
    current = pieces(library, "manual.md")
    assert len(current) == 5 and not any(re.search(r"\ba\d\d\b", piece["text"]) for piece in current)
    passage = library.expand([current[2]])[0]["passagem"]
    assert passage.startswith(current[1]["text"]) and passage.endswith(current[3]["text"]) and "a0" not in passage
    # Trecho de documento apagado e biblioteca sem catálogo: a passagem é o próprio trecho.
    assert library.expand([gone[1]])[0]["passagem"] == gone[1]["text"]
    empty = DocumentLibrary(tmp_path / "vazia", encoder=Windows())
    assert empty.expand([gone[1]])[0]["passagem"] == gone[1]["text"] and empty.expand([]) == []


def test_indexing_reports_progress_per_slice(tmp_path):
    encoder, steps = Windows(), []
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=encoder)
    path = tmp_path / "longo.md"
    path.write_text(f"# Longo\n{words('p', 562)}", encoding="utf-8")  # 70 trechos: duas fatias cheias e o resto
    result = library.add(path, progress=lambda *step: steps.append(step))
    assert result["chunks"] == 70 and INDEX_SLICE == 32 and INDEX_SLICE % ENCODE_BATCH == 0
    assert steps == [("indexando", 0, 70), ("indexando", 32, 70), ("indexando", 64, 70), ("indexando", 70, 70)]
    assert encoder.calls == [32, 32, 6]


def test_sliced_encoding_matches_a_single_call():
    encoder = LocalEncoder()
    if not (encoder.directory / MODEL_FILE).is_file():
        pytest.skip("Sem o encoder da busca neste computador.")
    texts = [f"Trecho {n}: " + "confiabilidade e manutenção " * (1 + n % 7) for n in range(70)]
    whole = encoder.encode(texts)
    sliced = [vector for start in range(0, len(texts), INDEX_SLICE)
              for vector in encoder.encode(texts[start:start + INDEX_SLICE])]
    assert sliced == whole  # só múltiplos do lote interno dão os mesmos vetores


def hit(mark: str, title: str, text: str, **extra) -> dict:
    return {"citation_id": mark, "document_id": f"d-{title}", "title": title, "version": 1, "sha256": "s",
            "original": f"C:/biblioteca/{title}", "locator": "página 3", "page": 3, "method": "native",
            "status": "ready", "text": text, "score": 0.5, "similarity": 0.7} | extra


HITS = [hit("K1", "nasa.pdf", "RCM integra", referencia="NASA, 2008"), hit("K2", "ieee.pdf", "RCM é uma estrutura"),
        hit("K3", "nasa.pdf", "Outro trecho", referencia="NASA, 2008")]


class Library:
    def __init__(self, hits=HITS):
        self.hits = hits

    def search(self, query, limit=6):
        return [dict(item) for item in self.hits]

    def expand(self, hits):
        return [dict(item) | {"passagem": item["text"] + " e a frase inteira."} for item in hits]


class PlainLibrary:
    """Biblioteca sem a passagem ampliada, como as dos testes mais antigos."""

    def search(self, query, limit=6):
        return [dict(item) for item in HITS]


def test_hits_are_grouped_by_document_with_the_count():
    request = prepare_request("O que é MCC?", library=Library())
    assert request.messages[-1] == {"role": "user", "content": "O que é MCC?"}
    data = request.messages[-2]
    header, payload = data["content"].split("\n", 1)
    assert data["role"] == "user"
    assert header == ("Trechos recuperados automaticamente (dados de consulta): 3 trechos de 2 documentos distintos, "
                      "agrupados por documento.")
    grouped = json.loads(payload)
    assert grouped["documentos_distintos"] == 2 and [d["title"] for d in grouped["documentos"]] == ["nasa.pdf", "ieee.pdf"]
    nasa = grouped["documentos"][0]
    assert nasa["referencia"] == "NASA, 2008" and [t["citation_id"] for t in nasa["trechos"]] == ["K1", "K3"]
    assert nasa["trechos"][0]["text"] == "RCM integra e a frase inteira."  # a passagem, não o trecho cortado
    # As regras falam de OCR, estado parcial e página: cada trecho leva esses campos, e o documento, a versão.
    assert set(nasa["trechos"][0]) == {"citation_id", "locator", "page", "method", "status", "text"}
    assert nasa["version"] == 1 and set(grouped["documentos"][1]) == {"title", "version", "trechos"}
    assert "sha256" not in payload and "original" not in payload and "referencia" not in grouped["documentos"][1]
    # A contagem muda a cada pergunta: fica nos dados, e as regras continuam iguais.
    assert all("3 trechos" not in m["content"] for m in request.messages if m["role"] == "developer")
    assert [h["passagem"] for h in request.metadata["citations"]][0].endswith("frase inteira.")
    single = prepare_request("O que é MCC?", library=Library(HITS[:1])).messages[-2]["content"]
    assert single.startswith("Trechos recuperados automaticamente (dados de consulta): 1 trecho de 1 documento,")
    none = prepare_request("O que é MCC?", library=Library([])).messages[-2]["content"]
    assert none == "Nenhum trecho dos documentos foi recuperado para esta pergunta."


def test_rules_ask_for_every_document_and_verbatim_quotes():
    assert LIBRARY_RULES.startswith("Modo biblioteca: os trechos recuperados chegam agrupados por documento")
    for wanted in ("apresente o que diz cada um que trata do pedido", "é o mínimo, não o limite", "Não mencione, não comente e não cite os documentos",
                   "diga que foi o único", "no idioma original", "identificada como tradução",
                   "Não crie identificadores, autores, páginas ou referências"):
        assert wanted in LIBRARY_RULES, wanted
    request = prepare_request("O que é MCC?", library=Library())
    assert [m["content"] for m in request.messages if m["role"] == "developer"][-1] == LIBRARY_RULES


def answer(content: str, library=None, **kwargs) -> LLMResult:
    def execute(request, **_):
        return LLMResult(content, "fake", "test", request.task_type)

    return Agent(SimpleNamespace(execute=execute)).answer(
        "O que é MCC?", provider="fake", model_alias="test", library=library or Library(), append_sources=False, **kwargs)


def test_uncited_hits_are_returned_as_retrieved():
    cited = answer("Segundo a NASA, a RCM integra as manutenções [K1].")
    assert cited.validation_status == "citation_ids_verified" and [s["citation_id"] for s in cited.sources] == ["K1"]
    assert [r["citation_id"] for r in cited.retrieved] == ["K2", "K3"]
    kept = cited.retrieved[0]
    assert kept["title"] == "ieee.pdf" and kept["page"] == 3 and kept["passagem"].endswith("frase inteira.")
    # O cartão da janela de fontes abre a página e avisa de OCR e de extração parcial com estes campos.
    assert {"document_id", "locator", "method", "status", "version", "text"} <= set(kept)
    assert cited.sources[0]["passagem"].endswith("frase inteira.") and cited.sources[0]["text"] == "RCM integra"
    assert not {"sha256", "original", "score", "similarity", "referencia"} & set(kept)  # só o que a tela mostra
    assert cited.retrieved[1]["referencia"] == "NASA, 2008"
    uncited = answer("Não encontrei a definição.")
    assert uncited.validation_status == "uncited" and len(uncited.retrieved) == 3 and uncited.sources == ()
    invented = answer("Definição [Kfalso].")
    assert invented.validation_status == "invalid_citations" and len(invented.retrieved) == 3
    with_sources = Agent(SimpleNamespace(execute=lambda request, **_: LLMResult(
        "Definição [K2].", "fake", "test", request.task_type))).answer(
        "O que é MCC?", provider="fake", model_alias="test", library=Library())
    assert "Fontes recuperadas" in with_sources.content and [r["citation_id"] for r in with_sources.retrieved] == ["K1", "K3"]
    no_library = Agent(SimpleNamespace(execute=lambda request, **_: LLMResult(
        "Sem biblioteca.", "fake", "test", request.task_type))).answer("Oi", provider="fake", model_alias="test")
    assert no_library.retrieved == ()


def test_library_without_expand_still_answers():
    request = prepare_request("O que é MCC?", library=PlainLibrary())
    grouped = json.loads(request.messages[-2]["content"].split("\n", 1)[1])
    assert grouped["documentos"][0]["trechos"][0]["text"] == "RCM integra"
    result = answer("Definição [K2].", library=PlainLibrary())
    assert result.validation_status == "citation_ids_verified" and "passagem" not in result.retrieved[0]


def test_request_allows_long_answers_and_a_cut_answer_is_flagged():
    from aliado.llm.contracts import LLMStreamChunk

    # O raciocínio conta no teto de saída; 4096 cortou uma resposta por documento no meio da frase.
    assert prepare_request("O que é MCC?", library=Library()).max_output_tokens == 8192

    def stream(request, **_):
        yield LLMStreamChunk("Definição [K1] e a frase que fic", "fake", "test", request.task_type)
        yield LLMStreamChunk("", "fake", "test", request.task_type, truncated=True)

    final = list(Agent(SimpleNamespace(stream=stream)).stream_answer(
        "O que é MCC?", provider="fake", model_alias="test", library=Library(), append_sources=False))[-1][1]
    assert final.truncated is True and final.validation_status == "citation_ids_verified"
    assert answer("Definição [K1].").truncated is False


def test_an_invalid_result_mark_keeps_everything_the_search_brought():
    blocks = {"cabecalho": "c", "faltando": [], "blocos": [{
        "citation_id": "R1", "titulo": "Bloco", "fonte": "Avaliação", "data": "2026-09-27", "estatuto": "oficial",
        "secao": "resumo", "texto": "| Denso | 10 de 14 |", "notas": []}]}
    blocked = answer("O manual define [K1] e são 5 casos [R9].", results=blocks)
    # A resposta foi trocada por um aviso: o trecho que ela citava volta para a lista do que a busca trouxe.
    assert blocked.validation_status == "invalid_result_refs" and blocked.sources == ()
    assert [hit["citation_id"] for hit in blocked.retrieved] == ["K1", "K2", "K3"]


def test_the_same_paragraph_elsewhere_is_still_expanded(tmp_path):
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Windows())
    block = " ".join(f"r{n:02d}" for n in range(1, 13))
    # Em outro documento: a regra do trecho repetido vale só dentro da mesma página.
    add(library, tmp_path, "um.md", f"{block} {words('y', 8)}")
    add(library, tmp_path, "dois.md", f"{block} {words('z', 8)}")
    one, two = pieces(library, "um.md"), pieces(library, "dois.md")
    assert one[0]["text"] == two[0]["text"] == block
    first, second = library.expand([one[0], two[0]])
    assert first["passagem"].endswith("y08") and second["passagem"].endswith("z08")
    # Em outra seção do mesmo documento, também.
    short = " ".join(f"r{n:02d}" for n in range(1, 11))
    add(library, tmp_path, "nota.md", f"# Nota\n{short} {words('y', 8)}\n# Nota\n{short} {words('z', 8)}")
    heads = [piece for piece in pieces(library, "nota.md") if piece["text"].startswith("# Nota")]
    assert len(heads) == 2 and heads[0]["text"] == heads[1]["text"] and heads[0]["locator"] != heads[1]["locator"]
    first, second = library.expand(heads)
    assert first["passagem"].endswith("y08") and second["passagem"].endswith("z08")


def test_passage_stays_inside_its_section_and_its_version_even_when_the_texts_overlap(tmp_path):
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Windows())
    add(library, tmp_path, "manual.md", f"# Um\n{words('a', 20)} # Resumo geral\n# Resumo geral\n{words('b', 20)}")
    p = pieces(library, "manual.md")
    first = [piece for piece in p if piece["locator"] == p[0]["locator"]]
    second = [piece for piece in p if piece["locator"] != p[0]["locator"]]
    assert first[-1]["text"].endswith("# Resumo geral") and second[0]["text"].startswith("# Resumo geral\nb01")
    assert _join(first[-1]["text"], second[0]["text"]) is not None  # os textos se sobrepõem de verdade
    assert "b01" not in library.expand([first[-1]])[0]["passagem"]
    assert library.expand([second[0]])[0]["passagem"].startswith("# Resumo geral\nb01")
    # O último trecho da versão antiga se sobrepõe ao primeiro da nova, mas é de outra extração.
    phrase = "manutencao preditiva"
    add(library, tmp_path, "ciclo.md", f"{phrase} {words('a', 20)} {phrase}")
    old = pieces(library, "ciclo.md")
    add(library, tmp_path, "ciclo.md", f"{phrase} {words('c', 20)}")
    new = pieces(library, "ciclo.md")
    assert old[-1]["locator"] == new[0]["locator"] and _join(old[-1]["text"], new[0]["text"]) is not None
    assert library.expand([new[0]])[0]["passagem"].startswith(f"{phrase} c01")


def test_a_valid_result_mark_keeps_the_cited_piece_out_of_what_was_not_cited():
    blocks = {"cabecalho": "c", "faltando": [], "blocos": [{
        "citation_id": "R1", "titulo": "Bloco", "fonte": "Avaliação", "data": "2026-09-27", "estatuto": "oficial",
        "secao": "resumo", "texto": "| Denso | 10 de 14 |", "notas": []}]}
    ok = answer("O manual define [K1] e são 10 de 14 [R1].", results=blocks)
    assert ok.validation_status == "citation_ids_verified" and [s["citation_id"] for s in ok.sources] == ["K1"]
    assert [hit["citation_id"] for hit in ok.retrieved] == ["K2", "K3"]


def test_an_answer_cut_before_any_text_is_reported_instead_of_failing():
    from aliado.llm.contracts import LLMStreamChunk, LLMUsage

    def stream(request, **_):
        # O raciocínio consumiu o teto inteiro: nenhum texto, e o provedor avisa o corte no último pedaço.
        yield LLMStreamChunk("", "fake", "test", request.task_type, usage=LLMUsage(9000, 0, 17192, 8192), truncated=True)

    events = list(Agent(SimpleNamespace(stream=stream)).stream_answer(
        "O que é MCC?", provider="fake", model_alias="test", library=Library(), append_sources=False))
    final = events[-1][1]
    assert [kind for kind, _ in events] == ["final"] and final.truncated is True
    assert final.content.startswith("A resposta foi interrompida pelo limite de tamanho antes de começar")
    assert final.usage.reasoning_tokens == 8192  # a chamada foi cobrada: o uso segue para o registro

    def silent(request, **_):
        yield LLMStreamChunk("", "fake", "test", request.task_type)

    with pytest.raises(Exception, match="encerrou sem texto"):
        list(Agent(SimpleNamespace(stream=silent)).stream_answer("Oi", provider="fake", model_alias="test"))
