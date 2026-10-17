"""Lote 33: aprendizado com o uso, local e sem tokens: escolhas da tela, pergunta refeita e reclamação."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from test_routing import Words
from test_web import BASE, SOURCE, ask, env, fim, new_conversation  # noqa: F401 (fixture env)

from aliado.interfaces.web.app import create_app
from aliado.memory.store import MemoryStore

QUESTION = "Com base na literatura, o que são autoencoders e para que servem?"


def test_a_choice_is_found_again_for_a_very_similar_message_and_forgotten_with_its_conversation(tmp_path):
    memory = MemoryStore(tmp_path / "memoria", encoder=Words())
    assert memory.route_lessons(QUESTION) == {}
    assert memory.learn_route(question=QUESTION, field="rung", value="2", conversation_id="c1")
    assert memory.learn_route(question=QUESTION, field="model", value="flash_lite", conversation_id="c2")
    lessons = memory.route_lessons("O que são autoencoders e para que servem, com base na literatura?")
    assert lessons["rung"]["value"] == "2" and lessons["model"]["value"] == "flash_lite"
    assert memory.route_lessons("Qual o tempo de reparo de um transformador?") == {}
    memory.forget_conversation("c1")
    assert set(memory.route_lessons(QUESTION)) == {"model"}
    with pytest.raises(ValueError):
        memory.learn_route(question=QUESTION, field="cor", value="azul")
    # Sem o modelo local, nada é guardado, e nada falha.
    assert not MemoryStore(tmp_path / "sem", encoder=None).learn_route(question=QUESTION, field="rung", value="2")


def test_a_weak_trail_still_helps_the_search_but_is_no_longer_a_shortcut(tmp_path):
    memory = MemoryStore(tmp_path / "memoria", encoder=Words())
    memory.remember_exchange(conversation_id="c1", message_id="m1", question=QUESTION, answer="Resposta.",
                             pages=[{"sha256": "a" * 64, "page": 5, "title": "Baschel"}])
    assert memory.trail(QUESTION)[0]["fraca"] is False
    assert memory.weaken_trail("m1") and not memory.weaken_trail("m1")  # a data da primeira vez fica
    assert memory.trail(QUESTION)[0]["fraca"] is True


@pytest.fixture
def learning(env):  # noqa: F811
    env["settings"].memory = memory = MemoryStore(env["tmp"] / "aprendizado", encoder=Words())
    env["settings"].models = [{"alias": "flash", "model_id": "a"}, {"alias": "flash_lite", "model_id": "b"}]
    env["library"].documents = lambda: [{"id": "d1", "title": "Baschel 2018", "version": 1, "status": "ready",
                                         "issues": [], "sha256": "a" * 64, "created_at": "2026-10-03T00:00:00+00:00"}]
    env["reply"]["sources"] = (SOURCE | {"sha256": "a" * 64, "page": 5},)
    # Os modelos são lidos quando o servidor começa: com dois, o servidor é refeito.
    client = TestClient(create_app(env["settings"]), base_url=BASE)
    return env | {"memory": memory, "client": client}


def auto(client, cid, text, **extra):
    return fim(ask(client, cid, text, skill="auto", modelo="auto", leitura="auto", **extra)[1])["mensagens"][1]


def test_a_reading_or_model_fixed_on_screen_is_repeated_for_a_similar_message(learning):
    client, calls = learning["client"], learning["calls"]
    auto(client, new_conversation(client), "Oi, tudo bem?")
    assert calls[-1]["model_alias"] == "flash_lite"
    # Fixados na tela, diferentes da escolha automática: ficam guardados para a mensagem.
    ask(client, new_conversation(client), "Oi, tudo bem?", skill="auto", modelo="flash", leitura="auto")
    ask(client, new_conversation(client), QUESTION, skill="auto", modelo="auto", leitura="paginas")
    reply = auto(client, new_conversation(client), "Oi, tudo bem?")
    assert calls[-1]["model_alias"] == "flash" and reply["rota"]["aprendido"][0]["campo"] == "modelo"
    reply = auto(client, new_conversation(client), "O que são autoencoders e para que servem, com base na literatura?")
    # A leitura aprendida é a das páginas; a resposta de antes, que bastou, ainda serve de atalho (lote 31).
    assert "reading" in calls[-1] and reply["rota"]["rung"] == 2
    assert [item["campo"] for item in reply["rota"]["aprendido"]] == ["leitura"]
    # Fixado de novo na tela, vale a escolha da tela, e a rota não diz que repetiu.
    reply = fim(ask(client, new_conversation(client), "Oi, tudo bem?", skill="auto", modelo="flash_lite",
                    leitura="auto")[1])["mensagens"][1]
    assert calls[-1]["model_alias"] == "flash_lite" and reply["rota"]["aprendido"] == []


def test_a_reading_fixed_on_screen_never_sends_small_talk_to_the_library(learning):
    client, calls = learning["client"], learning["calls"]
    # O seletor fica guardado na tela: um "Oi" enviado com ele não ensina o modo automático a ler páginas.
    ask(client, new_conversation(client), "Oi, tudo bem?", skill="auto", modelo="auto", leitura="paginas")
    reply = auto(client, new_conversation(client), "Oi, tudo bem?")
    assert "reading" not in calls[-1] and reply["rota"]["leitura"] == "sem a biblioteca"
    assert reply["rota"]["aprendido"] == []


def test_a_complaint_reads_deeper_weakens_the_trail_and_teaches_the_previous_question(learning):
    client, calls, memory = learning["client"], learning["calls"], learning["memory"]
    cid = new_conversation(client)
    auto(client, cid, QUESTION)
    assert "reading" not in calls[-1] and memory.trail(QUESTION)[0]["fraca"] is False
    reply = auto(client, cid, "Você não conseguiu me trazer nenhuma definição.")
    assert reply["rota"]["intent"] == "aprofundar" and calls[-1]["reading"]["pages"] == 10
    assert memory.trail(QUESTION)[0]["fraca"] is True and memory.route_lessons(QUESTION)["rung"]["origin"] == "reclamacao"
    # A mesma pergunta em outra conversa: a trilha fraca não serve de atalho, e a leitura começa nas páginas.
    reply = auto(client, new_conversation(client), "O que são autoencoders e para que servem, com base na literatura?")
    assert reply["rota"]["leitura"] == "páginas inteiras" and calls[-1]["reading"]["search"] is True
    assert "apoiam uma nova busca" in reply["rota"]["reasons"][-1]


def test_the_deeper_button_weakens_the_trail_of_the_answer_it_replaces(learning):
    client, memory = learning["client"], learning["memory"]
    cid = new_conversation(client)
    auto(client, cid, QUESTION)
    ask(client, cid, QUESTION, skill="auto", modelo="auto", leitura="paginas")  # "Ler mais fundo"
    weak = [match["fraca"] for match in memory.trail(QUESTION, limit=5)]
    assert True in weak and memory.route_lessons(QUESTION)["rung"]["origin"] == "refeita"
