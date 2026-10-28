# Spec 0067 — a hora e os nomes

## Propósito e decisões

**A origem:** no teste sem internet de 24/10/2026, à noite, o modelo local respondeu "Olá, aliado." com "Bom dia",
chamou o pesquisador de "aliado" e não soube o nome dele.

- **"Bom dia" à noite:** o pedido não levava data nem hora; o modelo chutava.
- **"aliado" como nome do pesquisador:** as instruções só diziam "Você é o AL-IAdo", e o modelo local não ligava
  "aliado" a esse nome.
- **O nome dele:** a memória tem três anotações de perfil e nenhuma com o nome. Não foi esquecimento: nunca foi
  anotado. Basta ele dizer o nome no chat e guardá-lo como perfil (botão Lembrar…).

**A decisão (pesquisador, 24/10/2026):** o plano do lote 67 aprovado como proposto.

## O que muda

- **A hora (NUC-05, novo):** uma mensagem curta, "Agora: sábado, 24/10/2026, 21h, noite (hora local).", depois da
  memória e antes da conversa. Os nomes dos dias ficam no código, sem depender do locale do Windows. Fica fora do
  começo fixo do pedido, que o provedor reaproveita; custa cerca de 15 tokens.
- **Os nomes:** três linhas a mais nas instruções do núcleo: "aliado" é o próprio AL-IAdo; o nome do usuário só vem
  do perfil; sem ele, nenhum nome, e uma pergunta só; cumprimento de acordo com o horário. Cerca de 60 tokens.

## Requisitos vivos

- **NUC-05 (novo), em `nucleo.md`:** quem fala e quando.

## Aceitação

- **O teste do NUC-05** (`tests/test_skills_agent.py`): 21h de sábado dá "noite" e o dia certo, 0h30 dá
  "madrugada", a mensagem fica antes da pergunta e as instruções dizem quem é "aliado".
- **A bateria:** 854 passando (853 da 0066 e o do NUC-05), 196 s, com `OPENBLAS_NUM_THREADS=1` (sem isso, o
  OpenBLAS ficou sem memória com o modelo local carregado). Cinco testes que contavam as mensagens do pedido passaram
  a contar a da hora; nenhum outro mudou.
- **O Ruff:** sem apontamentos.
- **Fica de fora:** a medição com o modelo real (pede autorização) e mandar menos memória e conversas num simples
  cumprimento.
- **Junto:** o commit do lote 66 (2f3bdaa) fica registrado no roteiro.
