"""Memória persistente (lote 11): regras de origem, conflito, versões, busca e revisor, sem rede."""

from __future__ import annotations

import json

import pytest

from aliado.agent import prepare_request
from aliado.llm.contracts import LLMResult
from aliado.memory.reviewer import reading_card, review_exchange
from aliado.memory.store import MemoryStore


class Encoder:
    """Vetores por grupos de palavras: suficiente para testar semelhança sem o modelo local."""

    groups = (("igbt", "módulo"), ("resposta", "frases", "curta"), ("reparo", "mttr"))

    def encode(self, texts):
        return [[1.0 if any(w in t.lower() for w in group) else 0.0 for group in self.groups] + [0.01]
                for t in texts]


@pytest.fixture
def store(tmp_path):
    return MemoryStore(tmp_path / "memoria", encoder=Encoder())


def test_user_feedback_supersedes_and_history_is_kept(store):
    old = store.add(kind="decisao", text="Usar 8,9e-6/h para o IGBT.", origin="feedback", skill="pesquisa-inversores")
    new = store.add(kind="decisao", text="Usar 16,6e-6/h para o IGBT.", origin="feedback",
                    skill="pesquisa-inversores", supersedes=old["id"])
    assert store.get(old["id"])["status"] == "superada" and new["status"] == "ativa"
    assert [m["id"] for m in store.history(new["id"])] == [old["id"], new["id"]]
    assert {m["id"] for m in store.list(status="ativa")} == {new["id"]}


def test_inference_never_overrides_user_note_and_conflict_is_resolved_by_user(store):
    mine = store.add(kind="correcao", text="MTTR do inversor é 4 h.", origin="feedback")
    guess = store.add(kind="correcao", text="MTTR do inversor é 2 h.", origin="inferido", supersedes=mine["id"])
    assert guess["status"] == "conflito" and guess["conflict_with"] == mine["id"]
    assert store.get(mine["id"])["status"] == "ativa"  # a sua continua valendo
    assert store.resolve(guess["id"], accept=False)["status"] == "revogada"
    assert store.get(mine["id"])["conflict_with"] is None
    other = store.add(kind="correcao", text="MTTR do inversor é 3 h.", origin="inferido", supersedes=mine["id"])
    accepted = store.resolve(other["id"], accept=True)
    assert accepted["status"] == "ativa" and store.get(mine["id"])["status"] == "superada"


def test_inference_supersedes_inference_and_edit_creates_user_version(store):
    first = store.add(kind="fato", text="Reparo levou 2 h.", origin="inferido")
    second = store.add(kind="fato", text="Reparo levou duas horas.", origin="inferido", supersedes=first["id"])
    assert store.get(first["id"])["status"] == "superada"
    edited = store.edit(second["id"], "Reparo levou duas horas no exemplo sintético.")
    assert edited["origin"] == "feedback" and edited["source"]["editada_de"] == second["id"]
    assert store.get(second["id"])["status"] == "superada"
    assert store.revoke(edited["id"])["status"] == "revogada"
    with pytest.raises(ValueError):
        store.edit(edited["id"], "de novo")


def test_divergence_only_for_user_decisions(store):
    assert store.add(kind="decisao", text="IGBT 16,6e-6/h.", origin="feedback", diverges_skill=True)["diverges_skill"]
    assert not store.add(kind="decisao", text="IGBT 16,6e-6/h.", origin="inferido", diverges_skill=True)["diverges_skill"]
    assert not store.add(kind="fato", text="Taxa x.", origin="comando", diverges_skill=True)["diverges_skill"]


def test_relevant_keeps_preferences_filters_skill_and_ranks(store):
    store.add(kind="preferencia", text="Prefiro resposta curta, em até três frases.", origin="feedback",
              skill="engenharia")
    igbt = store.add(kind="decisao", text="Usar 8,9e-6/h para o módulo IGBT.", origin="feedback",
                     skill="pesquisa-inversores")
    store.add(kind="fato", text="Reparo levou duas horas.", origin="inferido", skill="engenharia")
    found = store.relevant("Qual a taxa do IGBT?", skill="pesquisa-inversores")
    assert [m["kind"] for m in found] == ["preferencia", "decisao"]  # preferência vale em qualquer skill
    assert found[0]["skill"] is None and found[1]["id"] == igbt["id"]
    assert [m["kind"] for m in store.relevant("Qual a taxa do IGBT?", skill="engenharia")] == ["preferencia"]


def test_memory_survives_without_encoder_and_reopens(tmp_path):
    store = MemoryStore(tmp_path / "m")
    store.add(kind="decisao", text="Sem modelo local.", origin="comando")
    reopened = MemoryStore(tmp_path / "m")
    assert [m["text"] for m in reopened.relevant("qualquer", skill=None)] == ["Sem modelo local."]
    with pytest.raises(ValueError):
        store.add(kind="outro", text="x", origin="feedback")
    with pytest.raises(ValueError):
        store.add(kind="fato", text="  ", origin="inferido")


def fake_execute(payload):
    calls = []

    def execute(request):
        calls.append(request)
        return LLMResult(json.dumps(payload), "google", "flash-lite", request.task_type,
                         structured_data=payload)

    return execute, calls


def test_reviewer_validates_types_origins_citations_and_replacements():
    payload = {"anotacoes": [
        {"tipo": "preferencia", "texto": "Prefiro tabelas.", "origem": "feedback"},
        {"tipo": "fato", "texto": "Reparo de 2 h.", "origem": "feedback", "citacao": "Kok"},
        {"tipo": "fato", "texto": "Inventado.", "origem": "inferido", "citacao": "Kfalso"},
        {"tipo": "decisao", "texto": "IGBT 16,6.", "origem": "feedback", "substitui": "m1", "diverge_da_skill": True},
        {"tipo": "correcao", "texto": "Quarta nota além do limite.", "origem": "feedback"},
    ]}
    execute, calls = fake_execute(payload)
    sources = [{"citation_id": "Kok", "document_id": "d1", "title": "Doc", "page": 3, "text": "Reparo..."}]
    existing = [{"id": "m1", "kind": "decisao", "origin": "feedback", "text": "IGBT 8,9."}]
    notes, _ = review_exchange(execute, question="Q", answer="A", skill="pesquisa-inversores",
                               skill_text="Instruções", sources=sources, existing=existing)
    assert [n["kind"] for n in notes] == ["preferencia", "fato"]  # só as três primeiras são lidas
    assert notes[1]["origin"] == "inferido" and notes[1]["source"]["page"] == 3
    request = calls[0]
    assert request.structured_output and request.task_type == "memoria-revisor"
    sent = json.loads(request.messages[-1]["content"])
    assert sent["anotacoes_existentes"][0]["id"] == "m1" and sent["fontes"][0]["citation_id"] == "Kok"


def test_reviewer_explicit_command_and_divergence():
    execute, calls = fake_execute({"anotacoes": [
        {"tipo": "decisao", "texto": "IGBT 16,6.", "origem": "feedback", "substitui": "m1", "diverge_da_skill": True},
        {"tipo": "decisao", "texto": "Inferida.", "origem": "inferido", "diverge_da_skill": True},
    ]})
    notes, _ = review_exchange(execute, question="Lembre que o IGBT agora é 16,6", answer="Ok", skill=None,
                               existing=[{"id": "m1", "kind": "decisao", "origin": "feedback", "text": "IGBT 8,9"}],
                               explicit=True)
    assert notes[0]["origin"] == "comando" and notes[0]["supersedes"] == "m1" and notes[0]["diverges_skill"]
    assert notes[1]["origin"] == "inferido" and not notes[1]["diverges_skill"]
    assert "explicitamente" in calls[0].messages[0]["content"]


def test_reading_card_keeps_only_traceable_pages():
    execute, calls = fake_execute({"resumo": "Estudo sintético.", "fatos": [
        {"texto": "Reparo levou duas horas.", "pagina": 1},
        {"texto": "Página inexistente.", "pagina": 9},
        {"texto": "Sem página.", "pagina": None},
    ]})
    notes, _ = reading_card(execute, title="doc.pdf", markdown="## página PDF 1 (ocr)\n\ntexto",
                            document_id="d1", pages=1)
    assert [n["text"] for n in notes] == ["Resumo de doc.pdf: Estudo sintético.", "Reparo levou duas horas."]
    assert all(n["origin"] == "inferido" and n["source"]["ficha"] for n in notes)
    assert notes[1]["source"]["page"] == 1
    assert json.loads(calls[0].messages[-1]["content"])["truncado"] is False


def test_memories_enter_context_as_data_with_rules():
    memories = [{"id": "a" * 32, "kind": "decisao", "origin": "feedback", "text": "IGBT 16,6e-6/h.",
                 "diverges_skill": True, "source": {}},
                {"id": "b" * 32, "kind": "fato", "origin": "inferido", "text": "Reparo de 2 h.",
                 "source": {"title": "doc.pdf", "page": 1}}]
    request = prepare_request("Qual a taxa?", skill_name="pesquisa-inversores", memories=memories,
                              history=[{"role": "user", "content": "oi"}, {"role": "assistant", "content": "olá"}])
    contents = [m["content"] for m in request.messages]
    rules = next(i for i, c in enumerate(contents) if c.startswith("Memória do AL-IAdo"))
    assert request.messages[rules]["role"] == "developer"
    data = request.messages[rules + 1]
    assert data["role"] == "user" and "diverge_da_skill" in data["content"] and "doc.pdf, p. 1" in data["content"]
    assert "a" * 8 not in data["content"] and "b" * 8 not in data["content"]  # sem identificadores internos
    assert contents.index("oi") > rules  # memória antes do histórico e da pergunta
    assert request.metadata["memories"] == ["a" * 32, "b" * 32]
    assert "Memória do AL-IAdo" not in "\n".join(m["content"] for m in prepare_request("Oi").messages)
