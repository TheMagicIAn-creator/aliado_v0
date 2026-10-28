"""Lote 31: roteador local, escada de leitura, parte fixa enxuta, contagem de termos e trilhas, sem rede."""

from __future__ import annotations

import json
import re
from types import SimpleNamespace

import pytest
from test_figures import Sentences

from aliado import routing
from aliado.agent import (
    MENTIONS_NOTE,
    NAMES_NOTE,
    TRAIL_RULES,
    Agent,
    estimate_tokens,
    prepare_request,
    reading_key,
)
from aliado.knowledge import reading
from aliado.knowledge.library import DocumentLibrary
from aliado.memory.store import TRAIL_STRONG, MemoryStore, trail_pages

CARDS = {"baschel.pdf": {"ficha": {"titulo": "Impact of component reliability on large scale photovoltaic systems",
                                    "autores": ["Baschel, S."], "ano": 2018},
                         "referencia": "Baschel et al., 2018"},
         "nasa.pdf": {"ficha": {"titulo": "Reliability-Centered Maintenance Guide",
                                "autores": ["National Aeronautics and Space Administration"], "ano": 2008},
                      "referencia": "National Aeronautics and Space Administration, 2008"}}
SKILLS = ["pesquisa-inversores", "confiabilidade", "engenharia"]


class Words:
    """Encoder de teste: cada palavra cai numa de 64 posições; frases com as mesmas palavras ficam parecidas."""

    fingerprint = "palavras-de-teste"

    def split(self, text):
        return [text] if text.strip() else []

    def encode(self, texts):
        vectors = []
        for text in texts:
            vector = [0.0] * 64
            for word in re.findall(r"\w+", text.lower()):
                vector[sum(map(ord, word)) % 64] += 1.0
            vectors.append(vector)
        return vectors


def go(text, **options):
    return routing.route(text, cards=CARDS, skills=SKILLS, **({"results": True} | options))


def test_rules_decide_what_the_message_needs_before_any_paid_call():
    for text in ("Oi, tudo bem?", "Quais foram nossas últimas conversas?", "Obrigado, era isso."):
        found = go(text)
        assert (found.intent, found.rung, found.model, found.skill) == ("conversa", routing.NONE, routing.CHEAP, None), text
        assert found.reasoning == "low" and not found.catalog and not found.results
    collection = go("Há alguma literatura que explica explicitamente sobre autoencoder?")
    assert (collection.intent, collection.rung, collection.catalog, collection.model) == (
        "acervo", routing.PASSAGES, True, routing.CHEAP)
    figure = go("O que mostra a Figura 2 sobre a curva da banheira?")
    assert (figure.intent, figure.rung, figure.model) == ("visual", routing.PAGES, routing.STRONG)
    results = go("Me explique os resultados de F1 do GPVS.")
    assert (results.intent, results.rung, results.results, results.skill) == (
        "resultados", routing.NONE, True, "pesquisa-inversores")
    assert go("Compare os nossos resultados com a literatura.").rung == routing.PASSAGES  # pede os dois
    assert not go("Me explique os resultados de F1 do GPVS.", results=False).results  # resultados desligados na tela
    code = go("Corrija este traceback do meu script em Python.")
    assert (code.intent, code.rung, code.model) == ("tarefa", routing.NONE, routing.STRONG)
    assert go("Faça uma busca na web sobre notícias da empresa.").model == routing.CHEAP
    # Biblioteca desligada: nada sobe a escada, seja qual for a pergunta.
    assert go("O que mostra a Figura 2 sobre a curva da banheira?", library=False).rung == routing.NONE


def test_a_named_document_and_a_short_follow_up_keep_the_subject():
    named = go("Segundo Baschel et al. (2018), qual é a taxa de falha dos ventiladores?")
    assert (named.intent, named.rung, named.named) == ("documento", routing.DOCUMENT, ("baschel.pdf",))
    assert "Baschel et al., 2018" in named.reasons[0]
    assert go("Verifique no documento da NASA, por favor.").named == ("nasa.pdf",)  # a sigla de um autor institucional
    # Depois de uma resposta com a biblioteca, a mensagem curta continua a leitura dela.
    after = go("Traga outra fonte.", previous={"rung": routing.PAGES})
    assert (after.intent, after.rung, after.references) == ("continuacao", routing.PAGES, True)
    assert go("Traga outra.", previous={"rung": routing.NONE}).intent != "continuacao"
    deeper = go("Leia mais fundo, por favor.", previous={"rung": routing.PASSAGES})
    assert deeper.deeper and deeper.rung == routing.PASSAGES
    # Depois de uma resposta com os resultados, a mensagem curta continua neles.
    follow = go("E o LSTM?", previous={"rung": routing.NONE, "results": True})
    assert (follow.intent, follow.results) == ("resultados", True)
    assert go("Obrigado!", previous={"rung": routing.NONE, "results": True}).intent == "conversa"


def test_without_the_local_model_the_rules_still_route_and_doubt_goes_to_the_cheap_path():
    assert go("Com base na literatura, o que é a taxa de falha?").intent == "sintese"
    assert go("Qual o protocolo de partição dos dados?").intent == "metodo"
    plain = go("Qual é a vida útil do capacitor do barramento do inversor?")
    assert (plain.intent, plain.rung) == ("consulta", routing.PASSAGES)  # sem sinal claro, só trechos


def test_example_sentences_classify_through_the_local_encoder_and_the_skill_follows_the_subject():
    encoder = Words()
    assert routing.route("Qual o tempo de reparo de um transformador?", encoder=encoder, cards=CARDS,
                         skills=SKILLS).intent == "fato"
    assert routing.route("Me ajude a organizar o meu dia.", encoder=encoder, cards=CARDS, skills=SKILLS).rung == routing.NONE
    # A skill da conversa fica; uma mensagem curta não a troca.
    kept = routing.route("E o pertile?", encoder=encoder, cards=CARDS, skills=SKILLS, current_skill="engenharia",
                         previous={"rung": routing.PASSAGES})
    assert kept.skill == "engenharia"
    assert routing.route("Oi!", encoder=encoder, skills=SKILLS, current_skill="engenharia").skill is None
    # Um encoder que falha não derruba a rota: valem as regras.
    broken = SimpleNamespace(fingerprint="x", encode=lambda texts: (_ for _ in ()).throw(RuntimeError("sem modelo")))
    assert routing.route("Com base na literatura, o que é MTBF?", encoder=broken, skills=SKILLS).intent == "sintese"


def test_route_view_is_plain_data_and_terms_keep_only_the_subject():
    view = go("Segundo Baschel et al. (2018), qual é a taxa de falha dos ventiladores?").view()
    assert json.loads(json.dumps(view))["leitura"] == "documento inteiro" and view["named"] == ["baschel.pdf"]
    assert routing.terms("Há alguma literatura que explica explicitamente sobre autoencoder?") == ["autoencoder"]
    assert routing.terms("Quais documentos falam de manutenção centrada em confiabilidade?") == [
        "manutenção", "centrada", "confiabilidade"]
    assert routing.terms("E o Pertile? E o PERTILE?") == ["Pertile"] and routing.terms("O que é?") == []


DIGEST = {"blocos": [
    {"texto": "| Indicador | Denso | Recorrente X |\n|---|---|---|\n| Ensaios detectados, de 14 | 10 | 8 |",
     "notas": [{"nome": "Sensibilidade", "texto": "..."}, {"nome": "Atraso mediano", "texto": "..."}]},
    {"texto": "| Ensaio | Falha |\n|---|---|\n| F1L | IGBT |\n| G9 | Sensor |"},
    {"texto": "| Tipo de falha | Denso: detectou | Novo-AE: MCC |\n|---|---|---|\n| IGBT | 1 de 2 | 0,8 |"}]}


def test_results_vocabulary_comes_from_the_results_digest():
    names = routing.results_vocabulary(DIGEST)
    assert {"denso", "recorrente x", "novo-ae", "ae-lstm"} <= names["modelos"]
    assert names["ensaios"] == {"f1l", "g9"} and {"sensibilidade", "atraso mediano"} <= names["metricas"]
    assert "ensaios detectados, de 14" not in names["modelos"]  # título de linha não é modelo
    # O ensaio "G9" e o modelo "Novo-AE" só são reconhecidos com os nomes do resumo.
    assert go("E o G9?").intent != "resultados" and go("Como foi no G9?", vocabulary=names).intent == "resultados"
    assert go("Qual o MCC do Novo-AE?", vocabulary=names).intent == "resultados"


def test_a_question_about_the_harmonics_at_the_alarm_goes_to_the_results():
    """EXP-14 (lote 55): a pergunta sobre os harmônicos no primeiro alarme vai aos resultados pela frase de exemplo da
    especialização."""
    question = "O que os harmônicos mostram no primeiro alarme da falha de IGBT?"
    assert routing.route(question, encoder=Words(), cards=CARDS, skills=SKILLS, results=True).intent == "resultados"


def test_results_questions_without_the_word_results_go_to_the_results():
    for text in ("Quantas falhas o LSTM detectou?", "Qual a sensibilidade do autoencoder denso?",
                 "O que eu consegui até agora no mestrado?", "Em quanto tempo o Denso percebe a falha F3?",
                 "Qual componente tem a maior criticidade?", "Qual modelo errou menos?", "Os autoencoders funcionaram?"):
        found = go(text)
        assert (found.intent, found.results, found.rung) == ("resultados", True, routing.NONE), text
    # Conceito e literatura continuam na biblioteca, mesmo com o nome de uma métrica ou de um modelo.
    for text in ("Segundo a literatura, o que é um autoencoder LSTM?", "O que é a sensibilidade de um detector?",
                 "Como funciona uma rede LSTM?", "Qual a confiabilidade estimada do regulador?",
                 "Qual é o limite usado para o NPR?", "Como um autoencoder detecta anomalias?",
                 # "denso" como adjetivo, sem métrica nem palavra da pesquisa
                 "Esse capítulo é denso, explique de forma simples.", "O texto ficou denso demais, resuma."):
        assert go(text).intent != "resultados", text
    assert go("Qual foi melhor, o Denso ou o AE-LSTM?").intent == "resultados"  # dois modelos da pesquisa


def test_how_to_compute_and_other_peoples_theses_go_to_the_library(monkeypatch):
    """ROT-08: "como se calcula" é pergunta de conceito, e a tese, o TCC ou a monografia de outro autor é material da
    biblioteca, mesmo com palavras dos resultados. No lote 46, a P7 e a E3 das perguntas reais iam aos resultados."""
    p7 = go("Como se calcula a confiabilidade de um sistema com componentes em série e em paralelo?")
    assert p7.intent != "resultados" and p7.rung == routing.PASSAGES
    # O classificador por exemplos marca "resultados", como o modelo de busca real fez na E3; a obra citada vence.
    monkeypatch.setattr(routing, "_scores", lambda encoder, name, groups, text: (
        {"resultados": 0.9, "sintese": 0.5} if name == "intents" else {}))
    e3 = go("Which machine learning models were used to predict failures in frequency inverters in the UFSC "
            "undergraduate thesis?")
    assert (e3.intent, e3.rung, e3.results) == ("sintese", routing.PASSAGES, False)
    for text in ("Faça um resumo dos resultados da avaliação.", "Mostre os resultados da avaliação oficial."):
        assert go(text).intent == "resultados", text


def test_after_a_library_answer_small_talk_stays_out_and_a_complaint_reads_deeper():
    after = {"rung": routing.PASSAGES}
    for text in ("Cara, como você tá tão sabido assim? kkkkk", "relaxa, pode adotar uma conversa mais descontraída agora.",
                 "Valeu, ficou claro!"):
        found = go(text, previous=after)
        assert (found.intent, found.rung) == ("conversa", routing.NONE), text
    for text in ("Traga outra fonte.", "Valeu! E a segunda fonte?", "Mas e a FMECA?",
                 "Nossa, que interessante. E a FMECA?"):
        assert go(text, previous=after).intent == "continuacao", text
    assert go("Show. E sobre a NASA?", previous=after).rung >= routing.PASSAGES  # cita o documento da NASA
    complaint = go("Você não conseguiu me trazer nenhuma definição.", previous=after)
    assert (complaint.intent, complaint.rung, complaint.complaint) == ("aprofundar", routing.PAGES, True)
    assert go("Faltou a parte da FMECA.", previous={"rung": routing.PAGES}).rung == routing.PAGES
    # Sem resposta da biblioteca antes, não há do que reclamar: a mensagem segue as outras regras.
    assert not go("Você não conseguiu me trazer nenhuma definição.").complaint


@pytest.mark.parametrize("typed, text, choices", [
    ("Use o modelo maior. O que é MCC?", "O que é MCC?", {"modelo": routing.STRONG}),
    ("Oi, tudo bem? Use o modelo menor.", "Oi, tudo bem?", {"modelo": routing.CHEAP}),
    ("O que é MCC, só com trechos?", "O que é MCC?", {"leitura": routing.PASSAGES}),
    ("Explique o MCC usando as páginas inteiras", "Explique o MCC", {"leitura": routing.PAGES}),
    # O documento inteiro fica no texto: ele diz qual é o documento.
    ("Leia o artigo inteiro do Pertile.", "Leia o artigo inteiro do Pertile.", {"leitura": routing.DOCUMENT}),
    ("Faça a leitura ampla. Quais métodos detectam falhas?", "Quais métodos detectam falhas?", {"leitura": routing.WIDE}),
    ("Sem biblioteca e busque na web: qual a taxa de falha de um IGBT?", "Qual a taxa de falha de um IGBT?",
     {"biblioteca": False, "web": True}),
    ("Sem os resultados, o que diz a literatura sobre limiar?", "O que diz a literatura sobre limiar?",
     {"resultados": False}),
    ("Use a skill engenharia. Como dimensionar o cabo?", "Como dimensionar o cabo?", {"skill": "engenharia"}),
    ("Busque na web, por favor", "", {"web": True}),  # só o pedido: a tela refaz a pergunta anterior
    # Não são pedidos: no meio da frase, uma skill que não existe, ou seguido de "de/do/da".
    ("O modelo maior detectou mais falhas?", "O modelo maior detectou mais falhas?", {}),
    ("Por que buscar na web custa mais?", "Por que buscar na web custa mais?", {}),
    ("Quais trechos do artigo falam de MCC?", "Quais trechos do artigo falam de MCC?", {}),
    ("Use a skill inventada. Como dimensionar o cabo?", "Use a skill inventada. Como dimensionar o cabo?", {}),
    ("Sem a biblioteca de componentes, como fica a FMECA?", "Sem a biblioteca de componentes, como fica a FMECA?", {}),
    ("Use o modelo maior do artigo para comparar.", "Use o modelo maior do artigo para comparar.", {}),
])
def test_written_requests_leave_the_text_and_become_choices(typed, text, choices):
    """ROT-01: o pedido escrito vale no começo ou no fim de uma oração; sai do texto e vira escolha."""
    written = routing.directives(typed, ("engenharia", "confiabilidade"))
    assert (written.text, written.choices) == (text, choices)


def test_written_choices_are_described_in_words_for_the_route_line():
    said = routing.describe({"modelo": routing.STRONG, "leitura": routing.WIDE, "web": True, "skill": "nenhuma"})
    assert said == ["o modelo maior", "leitura ampla", "com busca na web", "sem skill"]
    assert routing.describe({"leitura": routing.PASSAGES}) == ["leitura: trechos"]


# --- biblioteca: contagem exata de termos e páginas soltas ---

pytest.importorskip("pypdf")
pytest.importorskip("pypdfium2")
from test_reading import make_pdf, texts  # noqa: E402


@pytest.fixture
def shelf(tmp_path):
    """Um livro de 12 páginas, com o alfa nas páginas 7 e 9, e um artigo de 3 páginas, com o beta na 2."""
    make_pdf(tmp_path / "livro.pdf", texts(12, {7: "O alfa aparece aqui.", 9: "Os alfas voltam aqui."}))
    make_pdf(tmp_path / "artigo.pdf", texts(3, {2: "O beta aparece aqui."}))
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Sentences())
    book, article = library.add(tmp_path / "livro.pdf"), library.add(tmp_path / "artigo.pdf")
    return SimpleNamespace(library=library, book=book, article=article, root=tmp_path)


def test_mentions_count_documents_and_pages_from_the_word_index(shelf):
    found = shelf.library.mentions(["alfa", "beta", "gama", "sobre manutencao", " "])
    assert found["alfa"]["documentos"] == 1 and found["alfa"]["onde"][0]["title"] == "livro.pdf"
    assert found["alfa"]["onde"][0]["paginas"] == [7, 9] and found["alfa"]["onde"][0]["locais"] == 2  # "alfas" também
    assert found["beta"]["onde"][0]["paginas"] == [2] and found["gama"] == {"documentos": 0, "onde": []}
    assert found["sobre manutencao"]["documentos"] == 2  # expressão: as duas palavras, em sequência
    assert " " not in found and "" not in found
    assert DocumentLibrary(shelf.root / "vazia", encoder=Sentences()).mentions(["alfa"]) == {}


def documents(request) -> list[list[dict]]:
    return [message["content"] for message in request.messages if isinstance(message["content"], list)]


def test_pages_rung_sends_single_pages_from_the_search_and_from_a_trail(shelf):
    options = {"budget": 60_000, "fixed": [], "whole": False, "search": True, "pages": 2}
    request = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=options)
    summary = request.metadata["reading"]
    assert summary["paginas_soltas"] and sum(item["paginas"] for item in summary["documentos"]) == 2
    marks = {hit["citation_id"] for hit in request.metadata["citations"]}
    assert f"K{shelf.book['sha256'][:8]}p7" in marks and len(marks) == 2
    assert all(part["type"] in {"text", "document"} for message in documents(request) for part in message)
    # A trilha entra primeiro; sem busca, só ela vai, e o índice não é varrido.
    calls = []
    search = shelf.library.search
    shelf.library.search = lambda *args, **kwargs: calls.append(args) or search(*args, **kwargs)
    trail = options | {"search": False, "pages": 6, "priority": [(shelf.article["id"], 2), ("0" * 32, 1), (shelf.book["id"], 99)]}
    request = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=trail)
    assert [hit["citation_id"] for hit in request.metadata["citations"]] == [f"K{shelf.article['sha256'][:8]}p2"]
    assert calls == [] and request.metadata["search_query"] is None
    first = prepare_request("Onde aparece o alfa?", library=shelf.library,
                            reading=options | {"pages": 3, "priority": [(shelf.article["id"], 2)]})
    assert first.metadata["citations"][0]["title"] == "artigo.pdf" and len(first.metadata["citations"]) == 3
    assert len(calls) == 1
    # Do documento citado na mensagem, as páginas dele vêm antes das dos outros.
    focused = prepare_request("Onde aparece o alfa ou o beta?", library=shelf.library,
                              reading=options | {"pages": 3, "focus": [shelf.article["id"]]})
    assert {hit["title"] for hit in focused.metadata["citations"]} == {"artigo.pdf"}
    # Páginas de respostas parecidas ficam com um lugar reservado, depois das melhores da busca.
    kept = prepare_request("Onde aparece o alfa?", library=shelf.library,
                           reading=options | {"pages": 3, "reserve": [(shelf.article["id"], 3)]})
    marks = {hit["citation_id"] for hit in kept.metadata["citations"]}
    assert f"K{shelf.article['sha256'][:8]}p3" in marks and f"K{shelf.book['sha256'][:8]}p7" in marks and len(marks) == 3
    # Uma página custa a imagem dela e a sua linha na lista: a estimativa soma só o que vai.
    assert first.metadata["reading"]["tokens_estimados"] <= 3 * (reading.PAGE_TOKENS + 60)


def test_document_rung_takes_the_best_document_of_the_search_when_none_is_named(shelf):
    options = {"budget": 60_000, "fixed": [], "whole": False, "search": True, "top": 1}
    request = prepare_request("Onde aparece o beta?", library=shelf.library, reading=options)
    summary = request.metadata["reading"]
    assert [(item["titulo"], item["inteiro"]) for item in summary["documentos"]] == [("artigo.pdf", True)]
    named = prepare_request("Onde aparece o beta?", library=shelf.library, reading=options | {"fixed": [shelf.book["id"]]})
    assert [item["titulo"] for item in named.metadata["reading"]["documentos"]] == ["livro.pdf"]  # o citado vale


def test_route_options_slim_the_fixed_part_and_keep_the_order_stable(shelf):
    full = prepare_request("Onde aparece o alfa?", library=shelf.library, skill_name="pesquisa-inversores")
    slim = prepare_request("Onde aparece o alfa?", library=shelf.library, skill_name="pesquisa-inversores",
                           catalog=False, references=False, reasoning_level="low")
    text = lambda request: [m["content"] for m in request.messages if isinstance(m["content"], str)]  # noqa: E731
    assert any(part.startswith("Catálogo da biblioteca") for part in text(full))
    assert any(part.startswith("Material de referência") for part in text(full))
    assert not any(part.startswith(("Catálogo da biblioteca", "Material de referência")) for part in text(slim))
    names = next(part for part in text(slim) if part.startswith(NAMES_NOTE))
    assert "livro.pdf" in names and "artigo.pdf" in names and slim.reasoning_level == "low" and full.reasoning_level is None
    assert estimate_tokens(slim) < estimate_tokens(full)
    # O que se repete fica no começo: as regras da biblioteca e os nomes vêm antes da memória e da conversa.
    memory = [{"id": "m1", "kind": "fato", "origin": "feedback", "text": "Prefiro respostas curtas."}]
    ordered = prepare_request("Onde aparece o alfa?", library=shelf.library, catalog=False, memories=memory,
                              history=[{"role": "user", "content": "Oi"}, {"role": "assistant", "content": "Olá"}])
    parts = text(ordered)
    position = lambda start: next(index for index, part in enumerate(parts) if part.startswith(start))  # noqa: E731
    assert position("Modo biblioteca") < position(NAMES_NOTE) < position("Memória do AL-IAdo") < position("Oi") \
        < position("Trechos recuperados")


def test_trail_and_mentions_reach_the_model_as_data(shelf):
    trail = {"created_at": "2026-10-04T12:00:00+00:00", "question": "Onde está o alfa?",
             "answer": "O alfa está na página 7 [Kabc123p7]. Também na 9 [Kzzz]."}
    request = prepare_request("Onde aparece o alfa?", library=shelf.library, trail=trail,
                              mentions={"alfa": {"documentos": 1, "onde": ["livro.pdf: 2 página(s) (7, 9)"]}})
    developer = [m["content"] for m in request.messages if m["role"] == "developer"]
    data = [m["content"] for m in request.messages if m["role"] == "user" and isinstance(m["content"], str)]
    assert TRAIL_RULES in developer
    old = next(part for part in data if part.startswith("Pergunta já respondida"))
    assert "O alfa está na página 7. Também na 9." in old and "[K" not in old  # as marcas antigas não valem mais
    assert any(part.startswith(MENTIONS_NOTE) and "livro.pdf: 2 página(s)" in part for part in data)


def test_a_request_above_the_ceiling_asks_before_calling_the_provider(shelf):
    from aliado.llm.contracts import LLMStreamChunk

    called = []

    def stream(request, **_):
        called.append(request)
        yield LLMStreamChunk("Sem citação.", "fake", "test", request.task_type)

    agent = Agent(SimpleNamespace(stream=stream))
    options = {"budget": 400_000, "fixed": [], "whole": True, "search": True}
    ask = lambda **extra: list(agent.stream_answer(  # noqa: E731
        "Onde aparece o alfa?", provider="fake", model_alias="test", library=shelf.library, append_sources=False,
        reading=options, **extra))
    (kind, estimate), = ask(ceiling=1000)
    assert kind == "confirmar" and estimate["tokens"] > 1000 and not called
    assert estimate["chave"] == reading_key(estimate["leitura"]) and len(estimate["leitura"]["documentos"]) == 2
    confirmed = ask(ceiling=1000, confirmed=estimate["chave"])
    assert [kind for kind, _ in confirmed] == ["inicio", "texto", "final"] and len(called) == 1
    assert confirmed[0][1]["tokens"] == estimate["tokens"]  # o pedido que segue é anunciado antes da resposta
    # Depois do aviso diário, a chave muda: a confirmação anterior não vale.
    (kind, later), = ask(ceiling=0, confirmed=estimate["chave"], salt="dia")
    assert kind == "confirmar" and later["chave"] != estimate["chave"]
    assert ask(ceiling=10_000_000)[-1][0] == "final" and [kind for kind, _ in ask()] == ["texto", "final"]


# --- trilhas na memória de conversas ---

def test_trails_keep_the_cited_pages_and_find_a_similar_question(tmp_path):
    store = MemoryStore(tmp_path / "memoria", encoder=Words())
    pages = [{"sha256": "a" * 64, "page": 7, "title": "Livro"}, {"sha256": "a" * 64, "page": 7, "title": "Livro"},
             {"sha256": "b" * 64, "page": 2, "title": "Artigo"}, {"sha256": None, "page": 1}, {"sha256": "c" * 64, "page": None}]
    question = "Com base na literatura, o que são autoencoders e para que servem?"
    assert store.remember_exchange(conversation_id="c1", message_id="m1", question=question, answer="Resposta [K1].",
                                   pages=pages, created_at="2026-10-01T10:00:00+00:00")
    store.remember_exchange(conversation_id="c1", message_id="m2", question="Oi, tudo bem com você hoje?", answer="Tudo.")
    (match,) = store.trail("O que são autoencoders e para que servem, com base na literatura?")
    assert match["message_id"] == "m1" and match["similaridade"] >= TRAIL_STRONG
    assert [(page["sha256"][0], page["page"]) for page in match["pages"]] == [("a", 7), ("b", 2)]  # sem repetição
    assert store.trail("Qual é o tempo de reparo do transformador de potência?") == []  # outro assunto
    assert store.trail("Oi, tudo bem com você hoje?") == []  # troca sem páginas não é trilha
    # A memória de conversas (lote 18) continua igual: sem as colunas novas.
    assert "pages" not in store.recall(question)[0] and "qvector" not in store.recall(question)[0]
    # Uma troca já guardada sem trilha ganha a dela; a esquecida sai.
    assert not store.remember_exchange(conversation_id="c1", message_id="m2", question="x", answer="y", pages=pages[:1])
    assert store.trail("Oi, tudo bem com você hoje?")[0]["pages"][0]["page"] == 7
    store.forget_conversation("c1")
    assert store.trail(question) == []
    # A trilha é achada pela consulta de busca (o assunto); a frase da pergunta diz se o pedido é o mesmo.
    store.remember_exchange(conversation_id="c2", message_id="m9", question="Qual é a definição dele, com citação?",
                            answer="R.", pages=pages[:1], key="autoencoder definição definition")
    (match,) = store.trail("definição de autoencoder definition", question="Quais são os princípios disso tudo?")
    assert match["message_id"] == "m9" and match["similaridade"] >= TRAIL_STRONG and match["pergunta_parecida"] < 0.5
    (match,) = store.trail("definição de autoencoder definition", question="Qual é a definição dele, com citação direta?")
    assert match["pergunta_parecida"] >= 0.75
    assert store.trail("Qual é a definição dele, com citação?") == []  # a frase sozinha não acha: vale o assunto


def test_trail_pages_rise_when_cited_again_and_old_databases_gain_the_columns(tmp_path):
    older = {"created_at": "2026-10-01", "similaridade": 0.9, "pages": [{"sha256": "a", "page": 1}, {"sha256": "a", "page": 2}]}
    newer = {"created_at": "2026-10-03", "similaridade": 0.8, "pages": [{"sha256": "a", "page": 2}, {"sha256": "b", "page": 5}]}
    order = [(page["sha256"], page["page"]) for page in trail_pages([older, newer])]
    assert order == [("a", 2), ("b", 5), ("a", 1)]  # citada de novo sobe; a que deixou de ser citada desce
    assert trail_pages([]) == [] and len(trail_pages([older, newer], limit=1)) == 1
    # Um banco anterior ao lote 31 ganha as colunas e os vetores das perguntas, sem perder as trocas.
    import sqlite3

    root = tmp_path / "antiga"
    old = MemoryStore(root, encoder=Words())
    old.remember_exchange(conversation_id="c1", message_id="m1", question="Qual a taxa de falha do ventilador?", answer="X.")
    with sqlite3.connect(root / "memoria.sqlite3") as db:
        db.execute("ALTER TABLE exchanges DROP COLUMN pages")
        db.execute("ALTER TABLE exchanges DROP COLUMN qvector")
    again = MemoryStore(root, encoder=Words())
    assert again.exchange_count() == 1 and again.trail("Qual a taxa de falha do ventilador?") == []
    again.fill_missing_vectors()
    again.remember_exchange(conversation_id="c1", message_id="m1", question="x", answer="y",
                            pages=[{"sha256": "a" * 64, "page": 3}])
    assert again.trail("Qual a taxa de falha do ventilador?")[0]["pages"][0]["page"] == 3


def test_translation_short_explanation_and_lists_go_straight_to_the_model():
    """ROT-09 (lote 70): tradução, explicação para leigo ou curta e lista vão direto ao modelo, sem a biblioteca; com
    pedido de fonte, continuam na biblioteca, e as perguntas aprovadas que não citam documento também."""
    for text in ("Traduza para o inglês: o inversor falhou por sobreaquecimento.",
                 "Liste 3 causas comuns de falha em inversores, em tópicos.",
                 "Explique o que é FMECA para um leigo, em até 3 frases.",
                 "Resuma em uma frase o que é um inversor fotovoltaico."):
        found = go(text)
        assert (found.intent, found.rung) == ("tarefa", routing.NONE), text
    for text in ("Liste as fontes que tratam de MPPT.", "Explique para um leigo, com citação, o que é MTBF.",
                 # P5, P6, P7, P8, E4 e E8 das perguntas aprovadas, que ficam em data/avaliacao-busca.
                 "Como o aprendizado por reforço ajusta a taxa de contaminação do Isolation Forest em usinas solares?",
                 "Como funciona o rastreamento do ponto de máxima potência (MPPT) em sistemas fotovoltaicos?",
                 "Como se calcula a confiabilidade de um sistema com componentes em série e em paralelo?",
                 "Qual a confiabilidade estimada dos reguladores de tensão de bateria em sistemas fotovoltaicos?",
                 "When did FMEA originate, and which military procedure introduced it?",
                 "What causes random failures in the bathtub curve, such as stress-strength interference or an "
                 "insufficient safety factor?"):
        assert go(text).rung >= routing.PASSAGES, text
