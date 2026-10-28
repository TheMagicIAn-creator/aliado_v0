# Spec 0069 — a bateria grande do modelo local

## Propósito e decisões

**A origem:** depois do teste sem internet de 24/10/2026, o pesquisador pediu "uma BAITA bateria de testes" no modelo
local, com o objetivo de deixá-lo "mais rápido, mais inteligente e mais eficiente".

**As decisões (pesquisador, 24/10/2026):**
- só o modelo local, com o Gemini simulado: nenhum token pago;
- 24 mensagens novas de conversa e as 16 perguntas de pesquisa já aprovadas, até 60 chamadas locais;
- o que der errado fica evidenciado depois, para avaliação.

**O método:** o mesmo das medições dos lotes 46, 48 e 58:
- o servidor HTTP real e o modelo local real (`aliado-local`, contexto de 32 mil tokens);
- as cópias da biblioteca e dos resultados do lote 46;
- memória nova e um processo por caso.

Cada caso de conversa fixa a hora do pedido e, quando pede, uma anotação de perfil ou a falta de rede. As conferências
de cada resposta foram fixadas antes da bateria, em `tmp/lote-69/conversa.json`. O script é `tmp/lote-69/bateria.py`,
e os resultados ficam em `tmp/lote-69/medicao/`.

## O que a bateria mostrou

Medida em 24/10/2026, das 18h45 às 19h19. Foram 55 chamadas locais e 7 ao Gemini simulado. Com o modelo carregado, a
placa usou 5.377 MiB, com pico de 5.393 MiB.

**A conversa (21 casos, 24 mensagens):**

| Indicador | Valor | Nota |
|---|---|---|
| Conferências que passaram | 33 de 35 | Cada resposta tinha de 1 a 3 conferências fixadas antes, como "diz boa noite às 21h" ou "cabe em 300 letras". |
| Casos sem falha | 19 de 21 | Os dois que falharam escreveram demais (C12 e C17). |
| Respondidas pelo local | 23 de 24 | A que faltou é a busca na web sem rede, recusada na hora, como deveria. |
| Tempo até a resposta (mediana) | 7,5 s | Do envio ao fim da resposta. A metade das mensagens levou menos que isso. |
| Resposta mais lenta | 121 s | C20 (FMECA para leigo): o roteador mandou para a biblioteca. |

Acertos: o cumprimento certo para a hora (C01, C03, C04, C16), a data e a hora (C08, C09), o nome guardado no perfil
(C05), o nome dito na conversa (C10), a continuação MTTF → MTBF (C11), a conta (C19) e o modo sem rede (C15, C16).

**A pesquisa (16 perguntas):**

| Indicador | Lote 69 | Lote 58 | Nota |
|---|---|---|---|
| Respondidas pelo local | 12 | 13 | De 16. As outras foram ao Gemini simulado. |
| Citaram o documento esperado, no local | 8 | 12 | Das respondidas pelo local. É a medida de acerto da fonte. |
| Tempo até a resposta (mediana) | 68,6 s | 73,8 s | Do envio ao fim da resposta. |
| Fora do alcance do local | P1, E1 | P1, E1 | O documento inteiro passa de 32 mil tokens. |

A queda de 12 para 8 não tem uma causa só. Entre duas rodadas iguais, a temperatura do modelo já variou 2 respostas
(lote 43). Nesta bateria, porém, 4 respostas de pesquisa abriram com cumprimento ou com a data (achado 1). Só uma
rodada nova, com a correção, separa as duas coisas.

## Os achados, para avaliação

1. **Regressão do lote 67, corrigida aqui:** a frase "cumprimente de acordo com o horário" fez o local cumprimentar e
   dizer a data em respostas que não pediam isso. Aconteceu em 14 respostas, 4 delas de pesquisa. Em E6, em inglês,
   saiu "Aliado, bom dia" às 21h. Em C02, saiu "Boa tarde, pois são 21h (noite)". Sem o nome no perfil, ele também
   pediu o nome em toda conversa nova, até no "Obrigado!".
   **A correção (NUC-05, alterado):** só cumprimenta quando o usuário cumprimenta; só diz a data e a hora quando ele
   pergunta; sem o nome no perfil, não o pede. A mensagem da hora diz o mesmo. A correção ainda não foi medida com o
   modelo.
2. **O revisor de memória ocupa o local por 83 s:** ele rodou em 4 das 24 mensagens, sempre por 82 a 83 s, depois da
   resposta. A resposta já saiu, mas a próxima pergunta espera o modelo ficar livre. Isso dá 5,4 min em 24 mensagens,
   mais do que todas as respostas de conversa juntas.
3. **Conversa simples indo à biblioteca:** a tradução (C17), a lista de causas (C18), a FMECA para leigo (C20) e o
   MTBF (C11) foram à skill da pesquisa, com trechos ou páginas.
   - **C17:** levou 53 s e 3 chamadas para traduzir uma frase, e a resposta veio com uma nota sem sentido sobre
     citação.
   - **C20:** levou 121 s.
   Na conversa, o local respondeu em 6 a 9 s o que não foi à biblioteca.
4. **Respostas longas para mensagens curtas:** o "Obrigado!" virou 350 letras ("estou pronto para servir… existe
   algum projeto…"), e a tradução, 361.
5. **Marcas de citação inventadas na pesquisa:** P3 e P5 pararam cedo numa marca que não foi enviada e foram ao Gemini,
   como nos lotes 46 a 58.
6. **A segunda leitura repete o local:** em P6 e E3, o local errou, o Gemini simulado "refez" e o degrau seguinte voltou
   ao local. Com o Gemini de verdade, a resposta dele teria ficado, e as duas levariam cerca de 60 a 80 s, não 158 e
   167 s.
7. **Um deslize de idioma:** "messaggio" em vez de "mensagem" (C10).

## Requisitos vivos

- **NUC-05 (alterado), em `nucleo.md`:** só cumprimenta quando cumprimentado; a data e a hora só quando perguntadas; o
  nome não é pedido.

## Aceitação

- **O teste do NUC-05** confere a regra nova.
- **A bateria completa e o Ruff.**
- **Fica de fora:** medir a correção do achado 1 e atacar os achados 2 a 4. Cada um pede uma rodada nova com o modelo e
  a autorização do pesquisador.
