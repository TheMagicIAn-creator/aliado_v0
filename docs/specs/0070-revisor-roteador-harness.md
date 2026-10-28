# Spec 0070 — o revisor de memória, a conversa simples e o Gemini simulado

## Propósito e decisões

**A origem:** a bateria do lote 69 ([spec 0069](0069-bateria-do-local.md)) deixou 7 achados. A revisão que o
pesquisador trouxe pede atacar os três primeiros e medi-los numa rodada só, junto com a correção do NUC-05, dentro de
60 chamadas locais.

**A decisão (pesquisador, 24/10/2026):** o plano do lote 70 aprovado como proposto.

**O diagnóstico, conferido nos dados do lote 69 antes do plano:**
- **O revisor de memória:** recebia de 436 a 577 tokens de entrada e devolvia 2.048 de saída, o teto, em 3 das 4
  chamadas. Com o raciocínio ligado, ele gastava o teto pensando, cerca de 83 s, e a saída cortada perdia o JSON. Na
  C10, "Meu nome é Rodolfo." não virou anotação nenhuma. A reescrita da busca tinha o mesmo defeito antes do lote 41
  (PRV-07). O filtro antes dele deixou passar "Olá, aliado.", "Tchau, até amanhã!" e "Como eu me chamo?".
- **O roteador:** o roteador real, local e sem tokens, mandou à biblioteca a tradução, a lista, a explicação para
  leigo e o resumo em uma frase (C17, C18, C20 e C14), pelas frases de exemplo da síntese.
  - **Por que a regra é de "responda direto":** as 16 perguntas aprovadas vão à biblioteca, e quatro delas (P6, P7,
    E4 e E8) não pedem fonte de forma explícita. Exigir um sinal explícito para usar a biblioteca as tiraria de lá.
- **As marcas inventadas (P3 e P5):** o provedor local não tem sequência de parada. O "parou cedo" é a trava do lote
  46 na primeira marca inventada: a causa é o modelo, não a configuração.

## O que muda

- **O revisor sem raciocínio (PRV-07, alterado):** `review_exchange` pede raciocínio baixo, e o local recebe
  `reasoning_effort="none"`. A saída cortada vira erro, e a tela diz "O revisor de memória não respondeu.", em vez de
  uma lista vazia calada.
  - **Sem preempção:** sem raciocínio, a chamada deve levar segundos. Se a rodada mostrar outra coisa, a preempção vira
    lote próprio.
- **O filtro do revisor:** aceita o vocativo ("aliado") e as despedidas como conversa; "me chamo" numa pergunta ("como
  eu me chamo?") não conta como declaração. "Meu nome é Rodolfo." continua acionando o revisor.
- **A conversa simples (ROT-09, novo):** tradução, explicação para leigo ou curta e "liste…" vão direto ao modelo,
  sem a biblioteca, quando a mensagem não pede fonte nem cita documento.
  - **O que fica igual:** a regra vem depois das continuações, que não mudam. Pedido de definição ("O que é MTTF?")
    continua indo à biblioteca, como desde o lote 27.
- **O harness (`tmp/lote-70/bateria.py`):** o produto não muda aqui.
  - O Gemini simulado devolve uma resposta final válida, que cita o primeiro trecho enviado. No lote 69, a resposta
    dele sem citação fazia a escada voltar ao local e inflava P6 e E3 para 158 e 167 s.
  - O local roda com semente fixa e com a temperatura de produção.

## Requisitos vivos

- **ROT-09 (novo), em `roteador.md`:** tradução, explicação curta e lista vão direto ao modelo.
- **PRV-07 (alterado), em `provedores.md`:** o revisor de memória também vai sem raciocínio.

## Aceitação

- **Os testes, sem o modelo:**
  - ROT-09: as 4 mensagens vão sem a biblioteca; as que pedem fonte e as 6 perguntas aprovadas que não citam documento
    continuam na biblioteca;
  - o filtro do revisor;
  - o revisor com raciocínio baixo e a saída cortada como erro.
- **A bateria e o Ruff:** 862 testes passando e nenhum apontamento.
- **A rodada de validação:** a primeira tentativa, em 24/10/2026, não carregou o modelo (o Ollama não reservou os
  4,9 GB na placa com o app do ChatGPT/Codex aberto) e não fez chamada. A segunda rodou no mesmo dia, das 21h47 às
  22h11, com 47 chamadas locais (teto de 60) e 9 ao Gemini simulado, nenhum token pago. Ela só foi registrada aqui em
  27/10/2026, no lote 72, a partir de `tmp/lote-70/medicao/` (`comparacao.json`, `resultado.json`, `processos.log`).

### O resultado da rodada, contra o lote 69

| O que se mediu | Lote 69 | Lote 70 |
|---|---|---|
| Revisor de memória | 4 chamadas, mediana de 83 s | 1 chamada, 4 s; a C10 anotou "O usuário se chama Rodolfo." |
| ROT-09 (C14, C17, C18, C20) | todas pela biblioteca, de 31 a 121 s | todas sem a biblioteca, de 7 a 19 s |
| Cumprimento ou data fora de hora | 6 casos | 1 caso pela conta automática (C12) |
| Conferências da conversa | 33 de 35; 19 casos sem falha | 30 de 35; 16 casos sem falha |
| P6 e E3 | 158 e 167 s | 207 e 282 s |
| Pesquisa respondida pelo local | 12 de 16 | 8 de 16, as 8 citando o documento esperado |

- **O que melhorou:** o revisor e o ROT-09 fizeram o que o lote prometia.
- **O que continua ou piorou:**
  - o cumprimento fora de hora ainda aparece na leitura caso a caso: C01 ("Bom dia, Boa tarde, Boa noite…"), C12,
    C21 ("Tchau" à noite respondido com "Bom dia!"); a C02 fala das anotações de perfil e pede o nome;
  - a C11 ("E o MTBF?") foi ao Gemini simulado, e a C17 traduziu no sentido errado (para o português);
  - P6 e E3 deixaram de voltar ao local, mas cada um fez uma chamada local longa, com 4.700 e 6.444 tokens de saída;
  - a E6 caiu por falta de memória do Python ao ler o JSON das páginas (`library.py:308`), e o script contou a
    pergunta como sem erro.
- **O que não é comparável:** com o Gemini simulado dando resposta válida, P8, E4, E5 e E8 pararam nele; por isso a
  pesquisa pelo local caiu de 12 para 8 sem que o local tenha piorado. A conta de "fora de hora" do lote 69 (14
  respostas, na seção dele) usou outro método que a desta tabela (6).
- **Próximo passo:** corrigir esses achados pede outra rodada no modelo real, com o teto de chamadas a combinar.
