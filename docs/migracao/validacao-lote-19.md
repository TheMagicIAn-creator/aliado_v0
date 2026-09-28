# Validação do lote 19 — qualidade da busca da biblioteca

Verificação local em **28/09/2026**, sobre o commit `f23855d` (lote 18). Nenhum commit, push ou tag.

## Testes

`tests/test_search_quality.py` traz 11 testes novos, todos sem rede:
- palavras vazias e limite por documento;
- documento citado pelo autor;
- conferência da ficha no texto e referência curta;
- edição sobre a inferida e catálogo sem a tabela nova;
- catálogo e contexto do agente;
- medição e comando `avaliar`;
- rotas da ficha na interface: envio, "Completar fichas" e edição.

**354 testes passaram** (343 do lote 18 e 11 novos), o Ruff não apontou problemas e o
`app.js` passou na checagem de sintaxe, no Python 3.12.14.

## Perguntas de referência

- **Composição:** 16 perguntas, 8 em português e 8 em inglês, propostas pelo assistente e aprovadas pelo pesquisador antes de qualquer medição.
- **Documento esperado:** escolhido pelo conteúdo e conferido no texto (por exemplo, a Tabela 1 de Baschel na p. 6 e os tempos de reparo do IEEE 493 na p. 76), sem olhar o que a busca devolvia.
- **Tipos:**
  - 4 perguntas citam o autor;
  - 10 cruzam idiomas;
  - 4 apontam para os documentos grandes.
- **Onde ficam:** em `data/avaliacao-busca/perguntas.json`, fora do Git, porque descrevem o acervo.

## Medição

As três rodadas usaram a biblioteca real (27 documentos e 13.946 trechos). Os relatórios estão
em `data/resultados/busca-*-lote-19/`. Cada célula dá os acertos entre os 6 resultados e o MRR.

| Grupo | Antes | Sem fichas | Depois |
|---|---|---|---|
| **Todas** | 12/16 · 0,661 | 12/16 · 0,656 | **13/16 · 0,781** |
| Português | 5/8 · 0,542 | 5/8 · 0,531 | 6/8 · 0,750 |
| Inglês | 7/8 · 0,781 | 7/8 · 0,781 | 7/8 · 0,812 |
| Citam o autor | 3/4 · 0,396 | 3/4 · 0,375 | **4/4 · 0,875** |
| Conteúdo | 9/12 · 0,750 | 9/12 · 0,750 | 9/12 · 0,750 |
| Mesmo idioma | 6/6 · 0,875 | 6/6 · 0,875 | 6/6 · 0,917 |
| Outro idioma | 6/10 · 0,533 | 6/10 · 0,525 | 7/10 · 0,700 |
| Documentos distintos (média) | 2,56 | 4,31 | 3,75 |

"Sem fichas" é a busca nova antes das fichas, com palavras vazias, pesos e limite. A rodada
separa o efeito de cada parte, e nenhum parâmetro mudou depois dela.

**Leitura:**
- **O ganho em acertos veio das fichas.** P1 ("segundo Baschel") passou de fora dos 6 para o 1º lugar, P2 (Cristaldi) do 3º para o 1º e E1 (Sarquis Filho) do 4º para o 2º.
- **As mudanças locais melhoraram a diversidade**, de 2,6 para 4,3 documentos por pergunta. Elas não mudaram os acertos das perguntas de conteúdo, que ficaram em 9/12 nas três rodadas. Na rodada final, a diversidade é 3,8, porque o documento citado pode ocupar até 4 posições.
- **Continuam fora dos 6 três perguntas de conteúdo em outro idioma:**
  - P4, o intervalo de manutenção do ventilador de tiragem induzida;
  - P8, a confiabilidade dos reguladores de tensão de bateria;
  - E8, as causas das falhas casuais no manual de Lafraia.
  Nesses casos, a busca por significado não cruza bem os idiomas. A tradução da pergunta, deixada de fora, é a opção que responde a esses casos.
- **Limites:**
  - 16 perguntas é pouco para diferenças pequenas;
  - o conjunto foi proposto por quem implementou a busca, embora os documentos esperados tenham sido fixados antes de medir.

## Aceite com chamadas reais

Interface de teste em `127.0.0.1:8768`, com os dados em `tmp/lote-19/dados` e a biblioteca real.
Modelo `gemini-3.5-flash-lite`.

| Critério | Resultado |
|---|---|
| Cópia de segurança | `catalog.sqlite3` copiado para `tmp/lote-19/backup` antes de qualquer gravação, com o mesmo SHA-256. |
| Fichas | O botão mostrou "Completar fichas (27)" e pediu confirmação com o número de chamadas. Foram 25 fichas na primeira rodada. Os 2 documentos com erro do provedor (Baschel e Ibrahim) ficaram pendentes e foram completados em mais 3 rodadas, até **27 de 27**. |
| Conferência das fichas | Revisadas uma a uma contra o texto. Um erro do assistente foi corrigido: nomes em maiúsculas eram tratados como instituição ("P. R. MISHRA e J. C. JOSHI"), e agora saem "Mishra e Joshi, 1996". Um ponto fica para o pesquisador: em Ibrahim et al. (2022), a ficha pegou o título da linha de citação ("Solar Power Plants Anomaly Detection Using Machine Learning"), mas o cabeçalho do PDF diz "Machine Learning Schemes for Anomaly Detection in Solar Power Plants". |
| "Segundo Baschel" | "Segundo Baschel et al. (2018), qual é a taxa de falha dos ventiladores de refrigeração?" teve como resposta 26,7, da Tabela 1 na p. 6. A janela de fontes mostrou "Baschel et al., 2018 · energies-11-01579.pdf". |
| Português → inglês | "Como o aprendizado por reforço ajusta a taxa de contaminação do Isolation Forest em usinas solares?" citou 2 trechos de "Sharma et al. (2026)". |
| Acervo pelas fichas | "Quais documentos da biblioteca foram publicados em 2018 ou antes?" listou os 8 com ano até 2018, com autor e ano, e a faixa de "sem citação". |
| Ficha na interface | A lista mostra a referência sob cada arquivo, e o visualizador mostra a ficha "inferida: confira no original". A edição abriu com os dados e foi cancelada sem gravar. A gravação é coberta pelos testes. |
| Uso | **35 chamadas registradas:** 29 fichas (2 delas do diagnóstico), 3 respostas e 3 revisões de memória. Foram 79.488 tokens de entrada e 3.691 de saída, sem busca na web. As 5 tentativas com erro do provedor não geram registro. |

## Defeitos encontrados e corrigidos

1. **Erro do provedor nas fichas.** O Gemini respondeu com erro de servidor em Baschel e Ibrahim.
   - Os dois PDFs, da MDPI, trazem sequências `/gid00030/…`, glifos sem texto. Ibrahim falhou 2 vezes com elas e saiu nas 2 tentativas sem elas, e a remoção passou a ser feita antes do envio.
   - Baschel, com poucas dessas sequências, falhou 3 vezes em 5 tentativas, com e sem elas: é falha passageira do provedor.
   - Como uma falha não grava nada, o documento fica pendente e pode ser completado depois.
2. **Nomes em maiúsculas na referência curta.** Um nome inteiro em maiúsculas era tratado como instituição. Agora só uma sigla sem espaço, como "IEEE", fica inteira.
3. **Guia da biblioteca desatualizado desde o lote 18.** Ele ainda dizia que a ausência de trechos evitava a chamada ao provedor, e foi corrigido.

## Estado final

- **Biblioteca real:**
  - documentos, versões e trechos iguais aos da cópia de segurança;
  - a tabela `document_cards` foi acrescentada, com 27 fichas inferidas;
  - `biblioteca verificar` só aponta as 2 extrações parciais já conhecidas (Lafraia e o guia da NASA).
- **Configuração de pré-visualização:** `.claude/launch.json` ganhou a entrada `aliado-web-lote-19` para o servidor de teste.
- **Pasta temporária:** `tmp/lote-19` guarda a cópia de segurança e os dados do aceite, e pode ser apagada depois da revisão.
