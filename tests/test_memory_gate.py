"""O filtro poupa consultas sem perder feedback, perfil e decisões explícitas."""

import pytest

from aliado.memory.reviewer import needs_review


@pytest.mark.parametrize("text", [
    "Oi!", "Bom dia", "Obrigado!", "Entendi.", "Qual a taxa?", "E em 20 anos?",
    "O que é um autoencoder?", "Há alguma literatura sobre isso?", "Traga outra fonte.",
    "Explique a tabela 4.", "Por favor, compare os métodos.", "Você lembra nossa conversa?",
    "Verifique nele.", "Continue", "Pode resumir esse artigo?", "Qual estudo trata de autoencoder?",
    "Qual trabalho usa esse método?", "Qual é o meu nome?",
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
