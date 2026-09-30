# Lote 22 — correções de confiança

Lote autorizado em 30/09/2026, junto com o roteiro da 0.3.0 (lotes 22 a 26), depois da 0.2.0
(`50c4a63`, tag `v0.2.0`). Corrige o que o agente dizia, mostrava ou deixava de achar sobre o mestrado,
antes da aba Ciência nova.

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Recortes do Lafraia | **Apagar de vez** o `7_cap_confiabilidade_sistemas.pdf` e o `Adobe Scan 11 de jan. de 2024.pdf`. O manual completo cobre os dois: capítulo 7 nas p. 91–95 e Weibull na p. 55. |
| Anotações tiradas deles | **Revogar** as 16 deduções. |
| Linguagem | As telas e as respostas apresentam dados em palavras, sem códigos internos (M09 a M14), "semente" ou "canônica" sem explicar, com uma nota em cada índice. A regra vale para toda a 0.3. |
| Busca em continuações (30/09, depois do caso da MCC) | **Reescrever a pergunta** com o modelo mais barato, **em português e inglês**, dentro do lote 22. Isso reabre a tradução da pergunta, que tinha ficado fora da 0.3. |
| "Mais opções de fontes" | Eram **fontes de texto**: um seletor de letra na interface. A mudança feita antes do esclarecimento (10 trechos por resposta e a opção de cada fonte) foi **mantida**. |

## Escopo implementado

- **Skill do mestrado** (`skills/builtin/pesquisa-inversores/SKILL.md`, versão 0.2.0). Ela ia para o modelo em toda conversa e dizia coisas que não valiam mais:
  - agora descreve a memória que existe (anotações e trocas de conversas);
  - diz que o preparo, o treino, a avaliação, a FMECA e a confiabilidade rodam na aba Ciência, com os resultados oficiais de 27/09;
  - registra a tabela e a página de cada taxa e das notas;
  - pede ao modelo que explique em palavras.
- **Diretrizes** (`references/diretrizes-aprovadas-2026-09-22.md`):
  - só a seção "Aplicação e limites atuais" foi reescrita, com a data de 30/09. Ela dizia que não havia executor, que o acervo estava vazio e que não havia acesso a Lafraia;
  - **o texto de M09 a M14 ficou idêntico** ao do commit `50c4a63`, e um teste confere o hash.
- **Taxas e notas conferidas nas páginas dos PDFs** (vistas como imagem, não só no texto extraído):

| Valor | Fonte | Resultado |
|---|---|---|
| Contator 8,31e-6/h; CCB 63,7e-6/h | Sarquis Filho et al. (2020), Tab. III, p. 3, ref. [3] = Gallardo-Saavedra et al. (2019) | Confere |
| IGBT 8,9e-6/h | Baschel et al. (2018), Tab. 1, p. 5 (também Sarquis, ref. [9]) | Confere. É o valor marcado [−], extrapolado dos relatórios de O&M da juwi; o valor em negrito, usado no estudo, é 11,4 [30]. MTBF de 28 anos com 4.015 h/ano. |
| Ventilador 26,7e-6/h | Baschel et al. (2018), Tab. 1 (continuação), p. 6 | Confere. Único valor da tabela, marcado [−]. MTBF de 9,3 anos. |
| Notas S/O/D e NPR | Cristaldi et al. (2017), Tab. 6, p. 6 | Conferem: IGBT 63, contatores 150, ventiladores 48, PCB 168. |

- **Registro da conferência:**
  - `fmeca.json` e os 8 cenários citam agora tabela e página;
  - a ressalva "não reconferidas" saiu;
  - **nenhum valor mudou.**
  - A legenda da Tab. 1 de Baschel converte o MTBF para anos com 4.015 h **de operação**, e isso ficou registrado. A hipótese dos cenários ("não se sabe se a taxa se refere a horas de operação ou de calendário") é do pesquisador e não foi alterada.
- **Apagar documento** (`Library.delete`, `DELETE /api/biblioteca/{doc}` e o botão **Apagar** na aba Biblioteca):
  - saem todas as versões do título, as extrações, os trechos do índice lexical e a ficha;
  - o original só sai se nenhum outro documento o usa;
  - as deduções da memória cuja fonte é o documento são revogadas (`MemoryStore.revoke_from_documents`), e as anotações do pesquisador ficam;
  - a janela de confirmação avisa quantas anotações serão revogadas e que não tem volta;
  - a rota exige o cabeçalho local, responde 409 enquanto um envio ou as fichas correm e passa pelo mesmo executor dos envios;
  - abrir o original de um documento apagado mostra uma página curta, e não um erro em JSON.
- **Biblioteca real:**
  - os dois recortes foram apagados sem cópia, e as 16 deduções foram revogadas;
  - as perguntas de referência P7 e E8, que aceitavam o recorte ou o manual, passaram a esperar só o manual.
- **Consulta da busca reescrita** (`knowledge/rewrite.py`).
  - **O caso:** o pesquisador perguntou o conceito de MCC e depois pediu "Traga a definição com base na literatura. Uma citação direta.". A continuação tinha 9 palavras, e só as de até 6 somavam a pergunta anterior. A busca procurou "definição, literatura, citação direta" e trouxe definições de dicionário. Somar a pergunta anterior também não bastava: com a sigla MCC, nenhum dos 6 trechos trazia a definição.
  - **A correção:** com a biblioteca ligada, o modelo mais barato reescreve cada mensagem numa consulta completa. Ele usa as 4 últimas mensagens da conversa, escreve as siglas por extenso e dá os termos em português e em inglês. Não responde à pergunta, e a consulta só escolhe os trechos.
  - **Se a reescrita falhar ou não trouxer trechos**, a busca segue pela regra antiga.
  - A chamada entra no registro de uso, e a consulta fica guardada na resposta. A janela de fontes mostra "Buscou na biblioteca: …".
  - **Medição:** `aliado biblioteca avaliar --reescrever --env-file .env` mede com a consulta reescrita, como no chat. O texto da instrução foi fixado antes de medir.
  - **Ajuste depois da primeira medição:** a consulta mantém só os autores e as normas que o pesquisador citou, e não os que só aparecem nas respostas do assistente. Assim a busca não se prende a uma fonte. A segunda medição está na validação.
- **Mais referências por resposta** (`agent.SEARCH_LIMIT = 10`):
  - a busca do chat traz até 10 trechos, e o teto por documento continua o do lote 19;
  - as regras do modo biblioteca pedem a opção de cada fonte, com a citação, quando documentos diferentes tratam do pedido;
  - a medição de referência continua nos 6 primeiros resultados, para comparar com os lotes anteriores.
- **Fonte do texto** (seletor **Aa** na barra do topo):
  - 8 opções: Padrão, Arial, Calibri, Verdana, Georgia, Cambria, Times New Roman e monoespaçada;
  - só fontes instaladas no sistema, com equivalentes livres para outros sistemas, e nada baixado da internet;
  - a escolha muda a letra de toda a interface e fica guardada no navegador;
  - as fórmulas continuam no KaTeX.

## Critérios de aceitação

- **Testes sem rede:**
  - apagar remove linhas e pastas de todas as versões, e `verify()` continua limpa;
  - um original compartilhado fica, e outro documento não é afetado;
  - só as deduções daquele documento são revogadas;
  - a rota exige o cabeçalho, recusa um documento desconhecido e responde 409 durante um envio;
  - a skill não tem mais as frases desatualizadas, e M09 a M14 conferem com o hash aprovado;
  - a FMECA e os cenários citam tabela e página.
- **Aceite no navegador**, numa cópia da biblioteca e da memória: apagar pela interface, conferir a janela, o aviso, a lista e a página do original apagado, e a tela estreita.
- **Na biblioteca real:** `verificar` sem problemas novos, 25 documentos, 16 anotações revogadas e as 16 perguntas de referência com o mesmo resultado do lote 19.
- **Consulta reescrita:**
  - testes sem rede para a reescrita e a recusa de consulta vazia ou longa;
  - a busca usa a consulta e volta à regra antiga sem trechos;
  - no chat, a chamada só acontece com a biblioteca ligada, entra no registro de uso e, se falhar, não derruba a resposta;
  - com o modelo real, o caso da MCC traz a definição, e as 16 perguntas de referência não pioram.
- A suíte completa e o Ruff passam.

## Fora do escopo

- A aba Ciência nova, a confiabilidade por componente e a disponibilidade (lotes 23 e 24).
- Mudar as hipóteses dos cenários ou os valores escolhidos, que são decisões do pesquisador.
