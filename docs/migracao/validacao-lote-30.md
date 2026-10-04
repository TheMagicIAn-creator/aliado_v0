# Validação do lote 30 — leitura integral dos documentos e saída da aba Biblioteca

Verificação local em **03 e 04/10/2026**, sobre o commit `85dce50` (lotes 28 e 29). O assistente não fez
commit, push nem tag.

- A biblioteca real, `data/bibliotecas/principal`, foi usada só para leitura: a busca, o texto guardado das
  páginas e os PDFs originais. Nada foi gravado nela, e o registro de uso do aplicativo (`data/uso/`) não
  recebeu as chamadas do piloto.
- O piloto pago e as medições ficaram em `tmp/lote-30/`, fora do Git.

## Testes

29 testes novos:
- **`tests/test_reading.py` (22):**
  - a regra do teto: os fixados levam o que precisam, cada documento da busca recebe o seu mínimo, cresce até
    um quarto do teto e recebe a sobra na ordem; a soma nunca passa do teto, e uma regra que passasse é
    recusada;
  - documento pequeno num bloco só, documento grande em blocos fixos, documento de texto sempre inteiro;
  - os blocos achados pela busca primeiro, depois os vizinhos; blocos encostados descritos como um intervalo;
  - a biblioteca entrega o texto guardado de cada página, a página sem texto (lida pela imagem) e o
    documento de texto em seções;
  - a busca informa as melhores páginas de cada documento;
  - o pedido: uma mensagem por documento, com o que foi enviado, o PDF original (lido só se for preciso), a
    lista das páginas com o identificador e as primeiras palavras, as regras da leitura integral, os
    documentos antes da conversa; e a variante com o texto guardado junto;
  - o documento grande: os blocos em volta da página achada, um PDF por bloco com a chave das páginas, o
    recorte com as páginas certas, e o que não coube no teto dito à tela;
  - o PDF acima do limite de tamanho vai em partes;
  - a marca de página é aceita, a marca inventada bloqueia a resposta, e "a busca também trouxe" lista os
    trechos achados, e não as páginas lidas; o mesmo no fluxo;
  - o documento fixado vai inteiro sem busca; o fixado que saiu da biblioteca é ignorado; o fixado grande
    demais usa a busca para saber de onde partir; com a busca ligada, vem primeiro e não se repete;
  - fixados inteiros e trechos da busca no mesmo pedido, com as duas formas de citação aceitas;
  - o modo de trechos monta o mesmo pedido de antes do lote;
  - o comando `biblioteca arquivos` lista o registro, sem o endereço, e para apagar pede o `.env`;
  - o documento citado na mensagem volta à consulta reescrita que o perdeu, nos dois modos de leitura, e a
    consulta que já o cita não muda.
- **`tests/test_providers.py` (3):** o PDF só em mensagem do usuário de um pedido multimodal, com o conteúdo
  lido só se for preciso; o envio pelo serviço de arquivos, a espera do arquivo em recebimento, o
  reaproveitamento sem ler o documento de novo, o prazo, o registro sem o conteúdo, apagar, e o pedido sem
  registro; a falha do serviço classificada, sem chamada ao modelo.
- **`tests/test_web.py` (4):** o modo, o teto e os fixados chegam ao agente, com a biblioteca ligada ou não, e
  com a busca na web a leitura cai para trechos; a rota do serviço de arquivos conta só o que está no prazo,
  apaga, e não repassa o texto de uma falha; a página sem a aba Biblioteca, com o painel, os controles e uma
  trava por comportamento da tela; o estado com a hora de início e a página com o aviso de reinício.

**664 testes passaram** (635 do lote 29 e 29 novos), no Python 3.12.14. O Ruff não apontou problemas.

## Medições sem custo, na biblioteca real

- **Custo de um PDF no Gemini** (contagem de tokens do serviço, gratuita):

  | Documento | Páginas | Só o PDF | Só o texto guardado | Os dois |
  |---|---:|---:|---:|---:|
  | Artigo (Baschel et al., 2018) | 16 | 8.961 | 18.517 | 27.477 |
  | Livro digitalizado (10 páginas) | 10 | 5.601 | 3.229 | 8.829 |
  | Norma com tabelas (10 páginas) | 10 | 5.601 | 6.055 | 11.655 |

  Uma página de PDF custa 560 tokens, com pouco ou muito texto. O texto guardado dá de 2,4 a 3,7 letras por
  token.
- **Envio:** um PDF de 4,3 MB levou 1,8 s dentro do pedido e 3,0 s pelo serviço de arquivos.
- **Seleção para as 12 perguntas do piloto,** sem chamar o modelo (5 a 7 s por pergunta):

  | Regra | Documento esperado enviado | Página esperada enviada (6 perguntas) |
  |---|---:|---:|
  | Primeira versão: texto junto, sem mínimo por documento | 11 de 12 | 6 de 6 |
  | Sem o texto, com o mínimo, páginas soltas | 12 de 12 | 6 de 6 |
  | Blocos fixos de 20 páginas | 12 de 12 | 5 de 6 |
  | Blocos fixos de 10 páginas (a que ficou) | 12 de 12 | 6 de 6 |

  Com blocos de 20 páginas e o teto de 150 mil, a tabela pedida numa norma de 426 páginas ficava de fora: a
  página dela era a quinta do documento na busca.

## Piloto pago

Doze perguntas escolhidas antes de rodar: seis da lista de referência (P1, P4, P7, E2, E5 e E8) e seis sobre
figuras e tabelas (F1, F7, F10, F11, T1 e T3). O teto alternou entre 400 e 150 mil. Modelo: Flash
(`gemini-3.8-flash`), com a skill do mestrado e a pergunta direta, sem a consulta reescrita.

| Modo | Perguntas | Tokens de entrada (mediana) | Tempo (mediana) | Tempo (menor e maior) | Citou o documento esperado | Citou a página esperada |
|---|---:|---:|---:|---:|---:|---:|
| Só trechos | 12 | 11.366 | 10 s | 7 a 13 s | 12 de 12 | 5 de 6 |
| Documentos inteiros | 12 | 266.987 | 64 s | 31 s a 12,5 min | 12 de 12 | 6 de 6 |
| Inteiros, com o texto guardado junto | 2 | 137.170 | 23 s | 20 a 26 s | 2 de 2 | 1 de 2 |

- **Tokens de entrada:** tudo o que foi ao modelo na pergunta. **Página esperada:** só nas seis perguntas
  sobre figura ou tabela.
- **O que o modelo leu,** por pergunta:

  | Teto | Documentos | Inteiros | Páginas | Tokens de entrada |
  |---|---:|---:|---:|---:|
  | 150 mil | 9 a 11 | 6 a 9 | 234 a 242 | 147 a 152 mil |
  | 400 mil | 8 a 11 | 5 a 8 | 637 a 642 | 382 a 388 mil |

  Nenhum documento da busca ficou de fora por causa do teto.
- **Estimativa:** o uso real ficou de 2% a 5% abaixo da estimativa somada ao resto do pedido.
- **Respostas mais completas.** Em três perguntas o modo de trechos disse que o dado não estava no material
  ou trouxe só parte dele, e a leitura integral respondeu:
  - **E2** (escalas de Colli, 2015): por trechos, "não constam no material disponível"; inteiro, as três
    escalas de 1 a 5, nível por nível, das Tabelas 2 a 4;
  - **T1** (transformador em Baschel et al., 2018): por trechos, "não constam"; inteiro, as duas linhas da
    tabela (17,8 e 27,4 falhas por milhão de horas, 14 e 9,1 anos), que conferem com o texto da página 6;
  - **T3** (disjuntores na IEEE 493): por trechos, três valores e a página errada; inteiro, a tabela
    completa (9, 42, 32, 7, 5, 2, 1, 1 e 1%), que confere com o texto da página 202.
- **Figura em página digitalizada (F11):** a árvore de falhas foi descrita a partir da página, com as portas
  e as formas dos eventos. Por trechos, a resposta dependia da descrição automática do lote 29.
- **Fórmulas (P7):** por trechos, a fórmula do livro digitalizado chegou com as letras trocadas pelo
  reconhecimento de texto; inteiro, as fórmulas saíram limpas, lidas das páginas 91 a 106.
- **Citações diretas:** das 10 citações entre aspas com marca de página nas respostas inteiras, as 10 estão na
  página citada, pelo texto guardado. Nas duas respostas com o texto junto, 4 de 4.
- **Com o texto guardado junto** (T3 e F11, teto de 150 mil): o modelo leu de 89 a 97 páginas, 4 a 5 documentos
  ficaram de fora, e na T3 a página da tabela pedida não foi enviada. Por isso a lista leva só as primeiras
  palavras de cada página.

### Tempo de resposta

| Chamada | Teto | Tokens de entrada | Tempo |
|---|---:|---:|---:|
| P1, PDFs dentro do pedido | 60 mil | 61.606 | 361 s |
| P1 de novo, pelo serviço de arquivos | 60 mil | 61.606 | 43 s |
| P4 | 150 mil | 148.359 | 41 s |
| P1 | 400 mil | 384.086 | 95 s |
| P7 (cortada) | 400 mil | 382.661 | 94 s |
| E2 | 150 mil | 150.081 | 535 s |
| P7 de novo | 400 mil | 382.661 | 749 s |
| E5 | 400 mil | 385.223 | 286 s |
| E8 | 150 mil | 147.348 | 47 s |
| F1 (cortada) | 400 mil | 388.000 | 135 s |
| F7 | 150 mil | 151.581 | 97 s |
| F10 | 400 mil | 384.828 | 45 s |
| F11 | 150 mil | 151.107 | 40 s |
| T1 | 400 mil | 382.393 | 62 s |
| T3 | 150 mil | 151.392 | 31 s |
| F1 de novo | 400 mil | 388.000 | 66 s |

- O tempo não acompanha o tamanho do pedido. O mesmo pedido (P7) levou 94 s e, dez minutos depois, 749 s. As
  três chamadas mais lentas vieram em sequência, o que aponta para o serviço naquele momento.
- A primeira chamada, com os PDFs dentro do pedido, levou 6 minutos. Não dá para dizer se foi a forma de
  envio ou o momento: houve chamadas lentas também pelo serviço de arquivos.
- O envio dos PDFs levou de 3 a 34 s nas perguntas com arquivos novos, e nada nas que os reaproveitaram.

### Respostas cortadas

- **P7:** 6.162 tokens de raciocínio com o limite de 8.192. O limite da leitura integral subiu para 16.384.
- **F1:** 15.728 tokens de raciocínio com o limite de 16.384. O limite subiu para 32.768.
- As duas foram repetidas e saíram inteiras.

### Reaproveitamento pelo Gemini

- P1 repetida: 60.397 dos 61.606 tokens vieram do que o serviço já tinha lido.
- F1 repetida: 385.448 dos 388.000.
- Nas outras perguntas, com documentos diferentes, não houve reaproveitamento. Os documentos vão antes da
  memória e da conversa para o começo do pedido se repetir quando os documentos se repetem.

## No navegador

Servidor de teste com o agente e as rotas reais e o modelo simulado (`tmp/lote-30/servidor_teste.py`, porta
8778), com um livro de 45 páginas, um artigo de 3 e o PDF de figuras do lote 29:

- a barra lateral sem "Biblioteca"; os controles "Documentos inteiros" e o teto ao lado de "Usar biblioteca";
- a resposta com "leu 3 documentos (3 inteiros) · 53 páginas", e a janela de fontes com "O que o modelo leu",
  a página citada com o aviso "página lida inteira" e o link **Abrir página**;
- **Fixar nesta conversa** pela janela de fontes e pelo painel: a etiqueta aparece acima da caixa de mensagem,
  e o "×" solta;
- um arquivo enviado pela conversa fica fixado, e o aviso de envios diz isso;
- com a biblioteca desligada, os fixados continuam indo inteiros; com "Só trechos", fixados e trechos vão
  juntos; com a busca na web, a resposta avisa que a leitura foi por trechos;
- o painel **Documentos**: a lista com a referência, o arquivo e o estado, o documento fixado marcado, o
  detalhe com fixar, abrir, apagar, a ficha e as figuras, e a linha do que está guardado no Google com
  **Apagar de lá**;
- em 375 px de largura, o painel cabe na tela e a caixa de mensagem quebra em linhas; em 279 px ele saía
  pela esquerda, o que foi corrigido.

Um segundo servidor (`tmp/lote-30/servidor_real.py`, porta 8779) mostrou a tela com a biblioteca real, só
para leitura e com o modelo simulado:

- o painel listou os 26 documentos, e o detalhe mostrou a ficha e o quadro de figuras de um deles;
- uma pergunta com o teto de 150 mil montou o pedido em cerca de 10 s na primeira vez, com o modelo local de
  busca ainda por carregar, e a resposta mostrou "leu 11 documentos (8 inteiros e 3 em parte) · 239 páginas",
  com as páginas de cada livro na lista.

**O que não foi conferido:** o Gemini real não foi chamado pelo navegador. O piloto chamou o modelo pela via
sem fluxo; a tela usa a via com fluxo, que leva o mesmo pedido e está coberta só por testes com o serviço
simulado. A primeira pergunta do pesquisador com documentos inteiros é o teste dessa via.

## Primeiro uso pelo pesquisador (04/10)

O pesquisador pediu a definição de autoencoder e estranhou as respostas: uma disse que o documento de Pertile
(2023) não estava na busca, e a seguinte, que ele não menciona o termo.

- **O programa em execução era o antigo.** A página já era a do lote 30 (ela é lida do disco a cada carga),
  mas o servidor da porta 8765 não tinha sido reiniciado: o estado não trazia a leitura integral. As quatro
  respostas saíram por trechos, com 12,5 a 14,6 mil tokens de entrada, embora a tela mostrasse "Documentos
  inteiros".
- **"E o pertile?"** virou "autoencoder and percentil percentile thresholding" na consulta reescrita. A busca
  não trouxe o documento, e a resposta disse isso.
- **"Verifique nele."** trouxe 4 trechos das páginas 18, 19 e 22, e a resposta disse que "nos trechos
  recuperados" o termo não aparece.
- **O documento de Pertile não fala de autoencoder.** No texto guardado das 77 páginas e nas 63 descrições de
  figuras, "autoencoder", "autocodificador", "encoder" e "codificador" não aparecem nenhuma vez. O trabalho
  trata de classificação: rede neural de várias camadas, aprendizado profundo, árvore de decisão, J48,
  Random Forest e Naive Bayes.
- **Onde o termo aparece na biblioteca:** em 6 dos 26 documentos.

  | Documento | Vezes | Páginas |
  |---|---:|---|
  | Ibrahim et al., 2022 | 16 | 1 a 4, 15 e 17 |
  | Ahirwar e Nandanwar, 2025 | 14 | 1, 2, 3 e 6 |
  | Francisti et al., 2025 | 8 | 2, 3, 5, 10, 12 e 13 |
  | Kull et al., 2025 | 3 | 12 e 38 |
  | Sharma et al., 2026 | 2 | 3 e 4 |
  | Marangis et al., 2025 | 1 | 15 |

- **O que a leitura integral faria** com as mesmas quatro perguntas e as mesmas consultas, sem chamar o modelo
  (teto de 400 mil):

  | Pergunta | Documentos lidos | Dos 6 que falam de autoencoder | Pertile |
  |---|---:|---:|---|
  | O que são autoencoders | 11 (638 páginas) | 5 inteiros | inteiro |
  | Há literatura que explica | 11 (638 páginas) | 6 inteiros | inteiro |
  | E o pertile? (antes da correção) | 10 (636 páginas) | 2 inteiros | só as páginas 61 a 70 |
  | E o pertile? (depois da correção) | 10 (636 páginas) | 3 inteiros | inteiro, em primeiro |
  | Verifique nele | 9 (228 páginas) | 6 inteiros | inteiro |

- **Correções:** a referência do documento citado na mensagem volta à consulta reescrita que a perdeu; e a
  tela avisa quando o programa em execução é anterior à página, e esconde os controles de leitura.
  - Na tela real do pesquisador, com o programa antigo ainda em execução, o aviso apareceu e os controles
    sumiram. No servidor de teste, iniciado depois da página, o aviso não aparece.

## Pacote 0.4.1

- **Arquivo:** `dist/v0.4.1/aliado-0.4.1-py3-none-any.whl`, 97 arquivos, 764 kB, SHA-256
  `a3595dc13e2774e683aef9a34ae499f05bb298c9bd3b6fc874076b2adb09f4d1`.
- **Conteúdo, conferido arquivo por arquivo contra `src`:** os 92 arquivos do pacote têm o mesmo hash dos de
  `src`, nenhum ficou de fora, e `aliado/knowledge/reading.py` está nele. Nada de testes, documentação ou dados.
- **Teste fora do projeto:** instalado com `--target` em `tmp/lote-30/pkg` e rodado de outra pasta. O código
  carregado veio do pacote, e a versão lida foi 0.4.1.
  - `aliado skills` listou as 3 skills, e `aliado biblioteca arquivos` respondeu com o registro vazio.
  - A interface respondeu 200 em `/`, `app.js`, `app.css`, `/api/estado`, `/api/biblioteca` e
    `/api/biblioteca/arquivos`; a página veio sem a aba Biblioteca e com o painel de documentos, e o estado
    informou a leitura integral com o teto de 400 mil.

## Chamadas pagas

| O que | Chamadas | Tokens de entrada |
|---|---:|---:|
| Calibração (a mesma pergunta, duas vezes) | 2 | 123.212 |
| 12 perguntas por trechos | 12 | 137.832 |
| 12 perguntas com documentos inteiros | 12 | 3.207.059 |
| 2 respostas cortadas, repetidas acima | 2 | 770.661 |
| 2 perguntas com o texto guardado junto | 2 | 274.341 |
| **Total** | **30** | **4.513.105** |

- **Autorizado:** até 30 chamadas ao Flash e 5 milhões de tokens de entrada.
- **Saída:** 23.729 tokens, e mais 74.069 de raciocínio. **Reaproveitados pelo serviço:** 481.112 da entrada.
- Uma 31ª tentativa foi interrompida durante o envio dos arquivos, antes de chamar o modelo.
- O registro das chamadas está em `tmp/lote-30/uso.jsonl`.
- **Sem custo:** 13 contagens de tokens e 1 envio de teste. O piloto enviou 179 arquivos ao serviço de
  arquivos do Google; todos foram apagados de lá no fim.

## Pendências

- **O tempo de resposta** da leitura integral: de 31 s a 12,5 min no piloto. A tela avisa que pode levar
  alguns minutos, e o botão de parar continua valendo.
- **O custo:** cerca de 13 vezes o do modo de trechos com o teto de 150 mil, e 34 vezes com o de 400 mil.
- **A busca na web** com a leitura integral ficou fora do lote.
- **A lista do painel** não mostra o número de páginas de cada documento.
- **A consulta reescrita** ainda pode trocar palavras da mensagem; só o documento citado é garantido.
- **Uma contagem exata de um termo na biblioteca inteira,** para perguntas como "há alguma literatura sobre
  X?", não existe: a resposta vale para os documentos que a busca trouxe.
- **A via com fluxo,** que a tela usa, não foi exercitada com o Gemini real (veja "No navegador").
- **Com o pesquisador:** o teste no uso real, o commit do lote, a tag `v0.4.1` e o push; o aceite do lote 28
  no Obsidian.
