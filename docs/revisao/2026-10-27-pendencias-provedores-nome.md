# Revisão de 27/10/2026 — pendências, Gemini × Ollama e o nome do pesquisador

**O pedido:** avaliar o que ficou das últimas análises do Claude, as inconsistências na integração do Gemini com o
Ollama e por que o AL-IAdo não gravou o nome do pesquisador; antes de tudo, refazer os arquivos de orientação do
assistente.

**O que foi visto:** o código e os testes desde o commit `2f3bdaa` (24/10), as specs 0067 a 0070, os registros das
baterias em `tmp/lote-69/` e `tmp/lote-70/`, o roteiro e, só para a pergunta do nome, a memória e as conversas em
`data/` (sem copiar conteúdo para cá). Três levantamentos por subagentes de leitura; cada achado abaixo foi conferido
no código. Nenhum modelo real foi chamado.

**O ponto de partida:** os lotes 67 a 70 e uma primeira versão da orientação do Claude estavam sem commit desde 24/10.
Em 26/10, o Codex começou esta mesma avaliação, reescreveu o registro de estado e parou; nenhum outro arquivo mudou.

## 1. O que ficou das últimas análises

| Item | Situação |
|---|---|
| NUC-05: data e período no pedido; "aliado" é o agente (lote 67) | Implementado e testado |
| Cumprimento só quando cumprimentado, data só quando perguntada (lote 69) | Implementado; no modelo real, ainda falha em C01, C02, C12 e C21 |
| PRV-09: sem rede, o modo sem internet entra sozinho (lote 68) | Implementado e testado; sem teste com a rede desligada de verdade |
| PRV-07: revisor de memória sem raciocínio (lote 70) | Implementado, testado e medido: de 83 s para 4 s |
| ROT-09: tradução, explicação curta e lista sem a biblioteca (lote 70) | Implementado, testado e medido: de 31–121 s para 7–19 s |
| Rodada de validação do lote 70 | **Medida e não registrada**: rodou em 24/10, e a spec dizia que não; registrada agora na spec 0070 |
| Mensagem simples com menos memória e conversa (spec 0067) | Não implementado |
| Lote 69, achados 4, 5 e 7: respostas longas, marcas inventadas, troca de idioma | Não implementados |
| C11 ("E o MTBF?") indo ao Gemini; C17 traduzindo ao contrário | Novos, da rodada do lote 70; não corrigidos |
| P6 e E3 mais lentos (207 e 282 s): uma chamada local com 4.700 e 6.444 tokens de saída | Novo; não corrigido |
| E6: falta de memória do Python ao ler o JSON das páginas (`library.py:308`) | Novo; a bateria contou como sem erro |
| README e CHANGELOG sem os lotes 67 a 70 | Corrigido nesta revisão |

## 2. Gemini × Ollama

Toda chamada que responde passa pelo gateway, e o Ollama fora do ar nunca leva ao Gemini (PRV-04 se mantém). As
inconsistências estão nas bordas.

### Corrigidas no lote 72 ([spec 0071](../specs/0071-nome-e-provedores.md))

1. **As fichas no local pensavam até o teto:** `reading_card` e `extract_card` não pediam raciocínio baixo, o mesmo
   defeito que o lote 70 corrigiu no revisor, e a saída cortada virava ficha vazia.
2. **Apagar os arquivos do Google sem internet chamava o Google:** a rota não passava pela checagem de rede.
3. **A reescrita local descontava do teto pago:** os tokens dela saíam dos 30 mil da segunda leitura.
4. **O modo forçado dava a mensagem errada:** sem o Flash configurado, a tela pedia a chave do Gemini, em vez de dizer
   que o modo sem internet estava ligado.
5. **O terminal dava sempre a dica do modo forçado,** mesmo quando o motivo era a falta de rede.
6. **O streaming estruturado do Gemini perdia o uso e o corte** (o local os passa). Nenhum chamador usa esse caminho
   hoje.
7. **O `.env.example` não trazia** `AL_IADO_OFFLINE`, `AL_IADO_FIGURE_MODEL` e `AL_IADO_EMBEDDINGS_DIR`.

### Registradas, para decisão

| Achado | Onde | Efeito | Proposta |
|---|---|---|---|
| A escalada vai sempre ao Flash e é decidida em três lugares | `gateway.py:22`, `agent.py` (`_stray`), `app.py` (`_local_missed`) | Com só o Flash-Lite configurado, o limite do local vira "O Gemini não respondeu" | Uma única regra no gateway, que use o modelo pedido quando o Flash faltar |
| A regra de "sem internet" está escrita duas vezes | `gateway.disconnected`, `app._offline` | Mudar uma sem a outra separa a tela do que o gateway faz | O app usar a do gateway |
| O local depende dos modelos do Gemini na tela | `app.py` (lista de modelos) | Sem chave do Gemini, o chat recusa, mesmo com o Ollama pronto | Decisão da spec 0038; rever se o uso só local passar a valer |
| JSON inválido: no local escala, no Gemini é erro | `local.py`, `gemini.py` | A mesma falha tem dois efeitos | Alinhar quando a escalada for unificada |
| Nenhum provedor define tempo limite | `local.py`, `gemini.py` | Uma chamada travada espera até 600 s (padrão do SDK) | Um tempo limite por tipo de tarefa, medido na bateria |

**Falso alarme descartado:** as checagens `provider == "local"` do app parecem esquecer o Ollama, mas são dos avisos
respondidos sem modelo; o provedor do Ollama se chama `ollama` de propósito (spec 0038).

## 3. O nome do pesquisador

- **O que os dados mostram:** nenhuma das 20 conversas guardadas traz o nome; em duas, o pesquisador perguntou qual
  era. Não havia anotação de nome na memória. Em 24/10, cinco chamadas do revisor no local bateram no teto de 2.048
  tokens e devolveram nada, em silêncio; nenhuma delas tinha o nome.
- **Por quê:** o NUC-05 (lote 67) proíbe o agente de pedir o nome, e o revisor só anota o que o usuário diz. Sem o
  pesquisador dizer o nome, ele nunca entraria. A falha do revisor também não aparecia na tela.
- **A correção (NUC-06, decidida pelo pesquisador):** sem o nome no perfil, o app pergunta uma única vez, no fim de
  uma resposta, e o revisor anota a resposta no perfil. A resposta vai como conversa, sem a biblioteca e sem chamada
  paga; se o revisor falhar, a tela diz que o nome não foi anotado, e a pergunta volta uma vez.
- **Não medido:** a pergunta e a anotação no modelo real. Na rodada do lote 70, o revisor local já anotou "O usuário
  se chama Rodolfo." quando o nome foi dito.

## 4. A orientação do assistente

A primeira versão (24/10) foi refeita do zero a pedido do pesquisador: `CLAUDE.md`, `WORKFLOW.md`, `ESTADO.md`,
`workflows/` e um subagente revisor. O registro está em
[skills-desenvolvimento.md](../migracao/skills-desenvolvimento.md); a versão antiga, em `tmp/lote-71-antigo/`.

## 5. Próximos passos propostos

1. **O commit dos lotes 67 a 72,** pelo pesquisador: tudo está sem commit desde 24/10.
2. **Uma rodada da bateria do local** (com autorização e teto de chamadas): a pergunta do nome, as fichas, os
   cumprimentos fora de hora, a C11 e a C17, com o método do lote 70 para comparar.
3. **A escalada numa regra só,** no gateway, com a regra de sem internet do app vindo dele.
4. **A E6:** por que ler o JSON das páginas esgota a memória com o modelo carregado.
5. **Um tempo limite para os provedores** e o teste com a internet desligada de verdade.
