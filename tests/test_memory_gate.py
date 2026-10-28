"""O filtro poupa consultas sem perder feedback, perfil e decisões explícitas."""

import pytest

from aliado.memory.reviewer import NAME_QUESTION, name_reply, needs_review


@pytest.mark.parametrize("text", [
    "Oi!", "Bom dia", "Obrigado!", "Entendi.", "Qual a taxa?", "E em 20 anos?",
    "O que é um autoencoder?", "Há alguma literatura sobre isso?", "Traga outra fonte.",
    "Explique a tabela 4.", "Por favor, compare os métodos.", "Você lembra nossa conversa?",
    "Verifique nele.", "Continue", "Pode resumir esse artigo?", "Qual estudo trata de autoencoder?",
    "Qual trabalho usa esse método?", "Qual é o meu nome?",
    # Lote 70 (PRV-07): da bateria do lote 69, onde acionavam o revisor.
    "Olá, aliado.", "Tchau, até amanhã!", "Como eu me chamo?", "Bom dia, Aliado.",
])
def test_queries_and_greetings_skip_paid_review(text):
    assert not needs_review(text)


@pytest.mark.parametrize("text", [
    "Prefiro tabelas.", "Responda curto, por favor.", "Meu nome é Rodolfo.", "Me chamo Rodolfo.",
    "Sou mestrando na UTFPR.", "Minha orientadora é Ana.", "O prazo é amanhã.",
    "Corrigindo: o valor é 12.", "Vamos adotar o método B.", "Não use mais essa hipótese.",
    "Consegue comparar? Decidimos usar o modelo menor.", "A partir de agora, responda em português.",
    "Lembre que a defesa será em dezembro.", "Guarde a definição com a fonte.",
    "Rodolfo", "O laboratório mudou de instituição.", "Pode me chamar de Rodolfo?", "Sou Rodolfo, tudo bem?",
])
def test_user_information_and_ambiguous_statements_are_reviewed(text):
    assert needs_review(text)


def test_explicit_request_and_short_decision_override_the_filter():
    assert needs_review("Qual a taxa?", explicit=True)
    assert needs_review("Sim", history=[{"role": "assistant", "content": "Vamos usar o modelo menor?"}])
    assert not needs_review("Sim", history=[{"role": "assistant", "content": "Entendeu a definição?"}])


def test_the_answer_to_the_name_question_and_asking_to_save_the_name_are_reviewed():
    """NUC-06 (lote 72): a resposta à pergunta do nome vai ao revisor, mesmo com jeito de pergunta; e "anotar meu
    nome" também, que antes caía no "pode" de uma consulta."""
    asked = [{"role": "assistant", "content": f"A taxa é 8,9e-6/h.\n\n{NAME_QUESTION}"}]
    assert needs_review("Pode ser só Rodolfo?", history=asked)
    assert not needs_review("Pode ser só Rodolfo?")
    assert needs_review("Pode anotar meu nome? Rodolfo.")


@pytest.mark.parametrize(("text", "expected"), [
    ("Rodolfo", True), ("Rodolfo Torres.", True), ("Pode me chamar de Rô.", True), ("Sou o Rodolfo", True),
    ("Não era isso.", False), ("Continue", False), ("Qual a taxa do IGBT?", False), ("Mais detalhes", False),
    ("Resuma o artigo do Baschel.", False),
])
def test_a_name_reply_is_a_name_and_not_a_complaint_or_a_question(text, expected):
    """NUC-06 (lote 72): só a resposta que é um nome, ou diz o nome, vira conversa; o resto segue o roteador."""
    asked = [{"role": "assistant", "content": f"Resposta.\n\n{NAME_QUESTION}"}]
    assert name_reply(text, asked) is expected
    assert name_reply(text) is False  # sem a pergunta antes, nada muda
