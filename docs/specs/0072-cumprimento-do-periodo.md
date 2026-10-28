# Spec 0072 — o cumprimento certo do período

## Propósito e decisões

**O pedido (28/10/2026):** a rodada do lote 73 ([spec 0071](0071-nome-e-provedores.md)) mostrou que o modelo local
ainda erra o cumprimento:
- "Olá, aliado." às 21h recebeu "Bom dia, aliado." (C22);
- "Tchau, até amanhã!" às 23h recebeu "Bom dia! Boa noite para o próximo dia." (C21, que também falhou no lote 70).

Entre os achados da rodada, o pesquisador escolheu corrigir este primeiro.

**As decisões do pesquisador, na mesma conversa:**
- dizer ao modelo a palavra certa do período, em vez de deixá-lo deduzir pela hora;
- de madrugada (da 0h às 5h59), "Boa noite", como se fala no dia a dia.

## O que muda

- **NUC-05 (alterado):** a mensagem da hora, que desde o lote 67 diz a data, o dia, a hora e o período, passa a dizer
  também o cumprimento dele:
  - "Bom dia" de manhã (6h às 11h59);
  - "Boa tarde" à tarde (12h às 17h59);
  - "Boa noite" à noite (18h às 23h59) e de madrugada.

  A mensagem pede ao modelo que só cumprimente quando o usuário cumprimentar ou se despedir, e então com esse
  cumprimento, mesmo que o usuário tenha usado outro ("Bom dia!" dito à noite).
  - O "só" continua: no lote 67, a frase sem ele levou a 14 cumprimentos fora de hora
    ([spec 0069](0069-bateria-do-local.md)).
- **A instrução fixa do começo do pedido** passa de "Só cumprimente quando o usuário cumprimentar, e então de acordo
  com o horário informado" para "Só cumprimente quando o usuário cumprimentar ou se despedir, e então com o cumprimento
  informado". Assim, as duas regras dizem o mesmo sobre a despedida. A palavra, que muda com a hora, fica só na
  mensagem da hora, fora do começo fixo; o começo fixo muda uma vez.

## O que fica igual, de propósito

- Os limites dos períodos são os do lote 67 (a hora dividida em quatro partes de seis horas).
- O AL-IAdo continua sem conferir nem corrigir o cumprimento depois da resposta: a mudança só informa o modelo.
- O "aliado" usado como se fosse o nome do usuário (C22) não é tratado aqui. A instrução do lote 67 continua valendo, e
  o C01 da bateria confere isso.

## Requisitos vivos

- **NUC-05 (alterado), em `nucleo.md`.**

## Aceitação

- **Os testes, sem o modelo:**
  - a mensagem da hora traz o cumprimento de cada período, com os limites (5h59, 6h, 11h59, 12h, 17h59 e 18h);
  - a madrugada fica com "Boa noite";
  - a mensagem não traz o cumprimento dos outros períodos;
  - ela mantém o "só", cita a despedida e o cumprimento trocado pelo usuário;
  - a instrução fixa cita a despedida.
- **Revisão independente:** o subagente revisor não achou defeito de código. Ele apontou que a primeira versão da
  mensagem tinha perdido o "só", com o risco do lote 67. Apontou também que a instrução fixa e a mensagem divergiam na
  despedida, e que a rodada proposta não tinha casos sem cumprimento. Os 7 pontos foram corrigidos.
- **A bateria e o Ruff:** 882 testes passando (eram 881) e o Ruff sem apontamentos, em 28/10/2026.
- **No modelo real:** a rodada curta abaixo.

## A rodada curta no modelo local (28/10/2026)

Autorizada pelo pesquisador com teto de 35 chamadas locais ("Autorizo 35"): só o local, Gemini simulado, nenhum token
pago. Usou 30 chamadas locais e 1 ao Gemini simulado; pico da placa de 5.385 MiB. Os casos rodaram com três sementes
(70, 71 e 72), no método do lote 73. Script e resultados ficam em `tmp/lote-74/`; a saída das tentativas que caíram
fica em `medicao-falhou-openblas/`. Há dois grupos de casos:
- os de cumprimento e despedida: C01 a C04, C16 e C21;
- os de controle, mensagens sem cumprimento em que o modelo não deve cumprimentar: C12 ("Obrigado!"), C13, C14 e C19.

**As duas primeiras tentativas caíram antes de chamar o modelo.** O Windows estava sem memória: o Firefox ocupava
6 GB, e o modelo carregado, 7,5 GB. A rodada foi feita depois que o pesquisador fechou o Firefox. O cuidado foi
registrado no [workflow da bateria](../../workflows/bateria-modelo-local.md).

| | Lote 70 (mensagem antiga) | Lote 73 (mensagem antiga) | Lote 74 (mensagem nova, 3 sementes) |
|---|---|---|---|
| Cumprimento e despedida sem falha | 3 de 6 | 5 de 6 | 15 de 18 |
| Controle sem falha | 4 de 4 | 3 de 3 (o C19 parou com o Ollama) | 11 de 12 |
| Controle com cumprimento sem o usuário pedir | 1 (C12) | nenhum | 2 (C12, sementes 70 e 71) |
| Respostas que comentam as instruções | 1 de 10 (C02) | 1 de 10 (C02) | 11 de 30 |

- **A despedida foi corrigida.** "Tchau, até amanhã!" às 23h recebeu "Até amanhã! Boa noite." nas três sementes; tinha
  falhado nos lotes 70 e 73.
- **Os cumprimentos acertaram em 15 de 18.** As três falhas:
  - o C02 na semente 70 foi refeito pelo Gemini simulado, como no lote 70;
  - o C03 na semente 72 respondeu "Saudações" em vez de "Bom dia";
  - o C16 na semente 72 não cumprimentou.
- **O "Obrigado!" (C12) ainda varia.**
  - Na semente 70, a resposta citou a regra e o "Boa noite": "a resposta apropriada seria \"Boa noite\", mas seguirei a
    regra…".
  - Na semente 71, "Você é bem-vindo", que a conferência conta como cumprimento.
  - No lote 70, o C12 também falhou.
- **Achado novo: respostas que falam das instruções** em vez de só responder, em 11 de 30. Exemplos: "Notado o
  cumprimento de despedida \"tchau\"", "Observação de contexto: A informação da nota \"Agora: …\"" e "Não tenho nenhum
  nome anotado para o usuário".
  - **Não dá para atribuí-las à mudança.** Dez das onze vieram das sementes 71 e 72, que nunca rodaram com a mensagem
    antiga. Na semente 70, a única comparável com os lotes 70 e 73, só o C12 teve isso.
  - O vocabulário de várias ("cumprimento de despedida", "condições de cumprimento") lembra o da mensagem nova, mas é
    um indício, não uma prova.
  - Para separar, falta rodar a mensagem antiga com as sementes 71 e 72: são 20 chamadas, além do teto desta rodada.

