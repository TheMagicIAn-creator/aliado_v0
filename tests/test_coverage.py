"""Lote 33: plano por partes, conferência por parte e reescrita seletiva, sem rede."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_web import ask, env, fim, new_conversation  # noqa: F401  (env é a fixture do chat)

from aliado.knowledge.coverage import (
    ResearchLibrary,
    check_coverage,
    explicit_units,
    has_parts,
    make_plan,
)
from aliado.knowledge.rewrite import rewrite_kind, rewrite_query
from aliado.llm.contracts import LLMResult, LLMUsage

QUESTIONS = json.loads((Path(__file__).parents[1] / "docs" / "migracao" / "perguntas-lote-33.json")
                       .read_text(encoding="utf-8"))
FIRST = {"role": "user", "content": QUESTIONS["continuacao_partes"]["antes"]}


def test_lists_comparisons_and_each_one_are_parts_and_simple_questions_are_not():
    for case in QUESTIONS["partes"]:
        parts = len(explicit_units(case["pergunta"])) if has_parts(case["pergunta"]) else 1
        assert parts >= case["minimo"] and parts <= case.get("maximo", 99), case
    # "como MCC": a palavra que liga o item à frase sai do nome da parte.
    assert "MCC" in explicit_units("Traga os conceitos de confiabilidade, como MCC, FMEA e FMECA")
    # "Para cada um" recupera a lista do pedido anterior; sem lista antes, não há partes.
    after = QUESTIONS["continuacao_partes"]["depois"]
    assert has_parts(after, [FIRST, {"role": "assistant", "content": "..."}]) and not has_parts(after)
    plan = make_plan(after, [FIRST])
    assert len(plan["unidades"]) >= QUESTIONS["continuacao_partes"]["minimo"] and plan["decomposicao"] == "local"


def test_the_plan_merges_the_model_parts_with_the_local_list_without_repeating_them():
    raw = {"consulta": "MCC FMEA FMECA", "conjunta": False, "unidades": [
        {"nome": "Manutenção Centrada na Confiabilidade", "consulta": "MCC RCM", "aliases": ["MCC", "RCM"]},
        {"nome": "FMEA", "consulta": "FMEA", "aliases": []}, {"nome": "FMECA", "consulta": "FMECA", "aliases": []}]}
    plan = make_plan("Compare MCC, FMEA e FMECA", (), raw)
    assert [unit["nome"] for unit in plan["unidades"]] == ["Manutenção Centrada na Confiabilidade", "FMEA", "FMECA"]
    assert plan["decomposicao"] == "modelo" and [unit["id"] for unit in plan["unidades"]] == ["u1", "u2", "u3"]
    assert make_plan("Compare FMEA e FMECA usando duas fontes")["fontes"] == 2


class Shelf:
    """Biblioteca de teste: cada consulta traz os trechos do documento com o mesmo nome."""

    def __init__(self):
        self.queries = []

    def search(self, query, *, limit=10, pool=None):
        self.queries.append(query)
        hits = [{"citation_id": f"K{query[:4]}{n}", "document_id": query, "title": query, "page": n, "locator": None}
                for n in (1, 2)] if query != "nada" else []
        if pool is not None:
            pool.extend(hits)
        return hits


def test_each_part_is_searched_and_the_report_says_which_part_got_a_citation():
    shelf = Shelf()
    plan = make_plan("Compare FMEA e nada")
    research = ResearchLibrary(shelf, plan)
    hits = research.search("pergunta", limit=10)
    assert shelf.queries == ["FMEA", "nada"] and {hit["document_id"] for hit in hits} == {"FMEA"}
    report = research.coverage(hits)
    assert [unit["estado"] for unit in report["unidades"]] == ["sem_citacao", "sem_candidato"]
    content = "### FMEA\nO FMEA prioriza os modos de falha [KFMEA1].\n\n### nada\nSem fonte no material selecionado."
    checked = check_coverage(content, report, ["KFMEA1"])
    assert [unit["estado"] for unit in checked["unidades"]] == ["citada", "sem_candidato"] and not checked["completa"]


def test_a_section_counts_only_for_the_part_whose_name_it_carries():
    hit = {"citation_id": "K1", "document_id": "d", "title": "t", "page": 1, "locator": None}
    report = {"unidades": [unit("u1", "Confiabilidade", "sem_citacao") | {"enviados": [hit]},
                           unit("u2", "Manutenção Centrada na Confiabilidade", "sem_citacao") | {"enviados": [hit]}],
              "completa": False, "decomposicao": "modelo"}
    content = ("### Confiabilidade\nSem fonte no material selecionado.\n\n"
               "### Manutenção Centrada na Confiabilidade\nA MCC organiza a manutenção [K1].")
    checked = check_coverage(content, report, ["K1"])
    assert [u["estado"] for u in checked["unidades"]] == ["sem_citacao", "citada"] and not checked["completa"]


def test_both_and_each_one_recover_the_previous_list_even_without_the_model():
    prior = [{"role": "user", "content": "Compare FMEA e FMECA."}, {"role": "assistant", "content": "..."}]
    for question in ("Agora traga uma fonte para ambos.", "Traga uma fonte para cada um."):
        assert has_parts(question, prior), question
        assert [u["nome"] for u in make_plan(question, prior)["unidades"]][:2] == ["FMEA", "FMECA"], question


def test_the_rewrite_is_skipped_when_the_question_already_says_the_subject():
    for question in QUESTIONS["reescrita"]["dispensa"]:
        assert rewrite_kind(question) == "nenhuma", question
    for case in QUESTIONS["reescrita"]["precisa"]:
        history = [{"role": "user", "content": case["antes"]}, {"role": "assistant", "content": "..."}]
        assert rewrite_kind(case["pergunta"], history) == "simples", case
    assert rewrite_kind("O que é MTBF?") == "simples"  # a sigla vai por extenso e em inglês
    assert rewrite_kind("Mas e a FMECA?", intent="continuacao") == "simples"
    assert rewrite_kind(QUESTIONS["partes"][0]["pergunta"]) == "plano"


def test_only_the_plan_asks_the_model_for_parts_and_a_longer_answer():
    seen = []

    def execute(request):
        seen.append(request)
        data = {"consulta": "FMEA FMECA", "conjunta": True, "unidades": []} if request.max_output_tokens > 512 \
            else {"consulta": "Manutenção Centrada na Confiabilidade (MCC) definição"}
        return LLMResult("{}", "google", "lite", "biblioteca-consulta", usage=LLMUsage(500, 30, 530), structured_data=data)

    query, _ = rewrite_query(execute, question="Traga outra fonte.", history=[FIRST])
    assert query.startswith("Manutenção") and seen[-1].max_output_tokens == 512
    assert "pedidos_anteriores" not in seen[-1].messages[1]["content"]
    plan, _ = rewrite_query(execute, question="Compare FMEA e FMECA.", plan=True)
    assert seen[-1].max_output_tokens == 2048 and [unit["nome"] for unit in plan["unidades"]] == ["FMEA", "FMECA"]


# --- no chat ---

def unit(uid, name, state, cited=()):
    return {"id": uid, "nome": name, "candidatos": 2, "enviados": [], "citados": list(cited), "estado": state}


@pytest.fixture
def chat(env):  # noqa: F811
    seen = []

    def rewriter(*, question, history, plan=False):
        seen.append(plan)
        data = {"consulta": "FMEA FMECA", "conjunta": True, "unidades": [
            {"nome": "FMEA", "consulta": "FMEA", "aliases": []}, {"nome": "FMECA", "consulta": "FMECA", "aliases": []}]}
        return (make_plan(question, history, data) if plan else "consulta reescrita"), \
            LLMResult("{}", "google", "lite", "biblioteca-consulta", usage=LLMUsage(500, 30, 530))

    env["settings"].query_rewriter = rewriter
    return env | {"rewrites": seen}


def route_of(client, cid, text):
    reply = fim(ask(client, cid, text, skill="auto", modelo="auto", leitura="auto")[1])["mensagens"][1]
    return reply


def test_the_chat_rewrites_only_when_it_helps_and_plans_only_with_parts(chat):
    client, calls, rewrites = chat["client"], chat["calls"], chat["rewrites"]
    cid = new_conversation(client)
    reply = route_of(client, cid, "Como se calcula a disponibilidade de um sistema reparável?")
    assert rewrites == [] and calls[-1]["search_query"] is None and reply["rota"]["busca"] == "nenhuma"
    assert "search_plan" not in calls[-1]  # uma parte só: sem plano e sem regra de títulos
    reply = route_of(client, cid, "Traga outra fonte.")
    assert rewrites == [False] and calls[-1]["search_query"] == "consulta reescrita" and reply["rota"]["busca"] == "simples"
    reply = route_of(client, cid, "Compare FMEA e FMECA.")
    assert rewrites[-1] is True and [u["nome"] for u in calls[-1]["search_plan"]["unidades"]] == ["FMEA", "FMECA"]
    assert reply["rota"]["busca"] == "plano" and reply["rota"]["partes"] == ["FMEA", "FMECA"]


def test_the_second_call_happens_only_when_a_part_has_something_new_to_read(chat):
    client, calls, reply = chat["client"], chat["calls"], chat["reply"]
    reply["sources"] = ()
    # Uma parte com material que a busca achou e não enviou: a segunda chamada completa, dentro do teto.
    reply["extra"] = {"coverage": {"unidades": [unit("u1", "FMEA", "citada", ["Kabc"]), unit("u2", "FMECA", "nao_enviado")],
                                   "completa": False, "decomposicao": "modelo"}}
    before = len(calls)
    answer = route_of(client, new_conversation(client), "Compare FMEA e FMECA.")
    assert len(calls) == before + 2 and calls[-1]["supplement"]["sem_citacao"] == ["FMECA"]
    assert calls[-1]["reading"]["pages"] == 10 and calls[-1]["ceiling"] == 30_000 - 320 - 530
    assert "completou a pesquisa" in answer["rota"]["reasons"][-1]
    # Uma parte para a qual a busca não achou nada: não há o que ler de novo, e não há segunda chamada.
    reply["extra"] = {"coverage": {"unidades": [unit("u1", "FMEA", "citada", ["Kabc"]), unit("u2", "FMECA", "sem_candidato")],
                                   "completa": False, "decomposicao": "modelo"}}
    before = len(calls)
    answer = route_of(client, new_conversation(client), "Compare FMEA e FMECA.")
    assert len(calls) == before + 1 and answer["cobertura"]["completa"] is False
    # Acima do teto, a segunda chamada pede confirmação: a resposta fica, com o botão para completar.
    reply["extra"] = {"coverage": {"unidades": [unit("u1", "FMEA", "citada", ["Kabc"]), unit("u2", "FMECA", "nao_enviado")],
                                   "completa": False, "decomposicao": "modelo"}}
    reply["confirm"] = 40_000
    answer = route_of(client, new_conversation(client), "Compare FMEA e FMECA.")
    assert answer["cobertura"]["complemento"] == "confirmacao_necessaria" and answer["cobertura"]["tokens_complemento"] == 40_000


def test_a_local_rewrite_does_not_spend_the_paid_ceiling(chat):
    """PRV-05 (lote 72): a reescrita feita pelo modelo local não desconta do teto da segunda chamada."""
    from dataclasses import replace

    client, calls, reply, settings = chat["client"], chat["calls"], chat["reply"], chat["settings"]
    paid = settings.query_rewriter

    def local(**kwargs):
        query, result = paid(**kwargs)
        return query, replace(result, provider="ollama")

    settings.query_rewriter = local
    reply["sources"] = ()
    reply["extra"] = {"coverage": {"unidades": [unit("u1", "FMEA", "citada", ["Kabc"]), unit("u2", "FMECA", "nao_enviado")],
                                   "completa": False, "decomposicao": "modelo"}}
    route_of(client, new_conversation(client), "Compare FMEA e FMECA.")
    assert calls[-1]["ceiling"] == 30_000 - 320
