# Spec 0035 — chat com tela mínima e pedidos escritos

Estado: implementado e validado localmente em 18/10/2026; aguarda a revisão e o commit do pesquisador.
Spec de mudança: os requisitos vivos estão em [capacidades/roteador.md](capacidades/roteador.md) (ROT-01 a
ROT-06, novos; ROT-07, o teto e o aviso diário dos lotes 31 e 33, agora escrito como requisito).

## Propósito

O pesquisador achou desnecessários tantos botões no chat. O roteador local, que já escolhia a skill, o modelo e a
leitura (lote 31), passa a decidir também o que eram as chaves; quem quer escolher escreve o pedido na própria
mensagem. É o segundo lote da [revisão da modularização e das specs](../revisao/2026-10-modularizacao-e-specs.md).

## Decisões do pesquisador (17/10/2026)

- Tela mínima: saem os seletores de skill, modelo, leitura e teto e as chaves biblioteca, web, resultados e
  "+ confiabilidade".
- O pedido escrito vale como escolha dele.
- A leitura ampla só por pedido escrito, sempre com a confirmação do custo. Os limites de 30 mil tokens por
  pergunta e de 300 mil por dia não mudam.
- Uma mensagem que é só um pedido ("busque na web") refaz a pergunta anterior.
- Da revisão de projeto: a web só por pedido escrito, sem a regra de "fato recente", que erraria e custaria; o apoio
  da skill de confiabilidade vem da própria skill ou de um pedido escrito.

## O que muda

- **`routing.directives`:** acha os pedidos no começo ou no fim de cada oração, comparando sem acento, e devolve o
  texto sem eles e as escolhas, campo por campo. `routing.describe` diz as escolhas em palavras para a linha da rota.
  Não é pedido: no meio da frase, uma skill que não existe, ou a frase seguida de "de/do/da" ("Sem a biblioteca de
  componentes, ...").
- **Mensagens (`app.py`):**
  - sem os campos da tela, valem o roteador, a biblioteca e os resultados disponíveis, e a web desligada;
  - quem vence: o campo de um botão, o pedido escrito, a escolha aprendida e o roteador, nessa ordem;
  - o texto sem os pedidos vai ao roteador, à reescrita, à busca, ao modelo e às lições; a conversa guarda o que foi
    escrito;
  - a leitura ampla vai com teto 0, uma chave própria ("ampla") e sem lembrar a confirmação: pergunta todas as vezes;
  - "Ler mais fundo" para no documento inteiro: a leitura ampla não é mais oferecida por botão;
  - a mensagem que é só um pedido refaz a pergunta anterior, com os pedidos dela; sem pergunta anterior, o servidor
    responde "Escreva a pergunta junto do pedido.";
  - o aprendizado guarda o modelo, a skill e a leitura pedidos por escrito, nunca a leitura ampla nem a web, uma lição
    de cada vez.
- **Tela (`index.html`, `app.js`, `app.css`):**
  - saem os seletores, as chaves e o código deles; o rótulo da skill sai do próprio nome, sem lista fixa;
  - "Lembrar…" e os envios de documentos ficam com a skill da conversa (a da última resposta);
  - "Completar pesquisa" pede sempre as páginas inteiras; o texto guardado traz os pedidos escritos, que valem de novo;
  - a tela de boas-vindas e a dica da linha da rota dizem as frases que se podem escrever;
  - a linha da rota diz "pedido por você" e, com um pedido, "seguiu o seu pedido", com o que foi pedido na dica;
  - a confirmação da leitura ampla diz "Leitura ampla, como você pediu" e que ela pergunta todas as vezes.

## Fora deste lote

- Frases de pedido fora da lista: elas ficam no texto, e o roteador decide como antes.
- Um pedido no começo de uma oração que fala de outra coisa ("Usando o modelo maior, o MCC sobe?") ainda é lido como
  pedido.

## Aceitação

- `pytest` e `ruff`; testes novos em `tests/test_routing.py` (os pedidos e os casos que não são pedidos),
  `tests/test_web.py` (valores sem campo, quem vence, leitura ampla, mensagem só com o pedido) e
  `tests/test_learning.py` (o que se aprende do pedido escrito).
- A tela mínima conferida num servidor de teste, sem chamadas pagas.
