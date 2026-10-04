# Validação do lote 29 — indexação: figuras, tabelas e trechos por frase

Verificação local em **03/10/2026**, sobre o commit `436582a` (lote 27) e o lote 28, ainda sem commit. O
commit dos lotes 28 e 29 foi feito pelo assistente com a autorização do pesquisador, no formato dele, sem
tag e sem push.

- **Etapas A e B** (limpeza, frases, texto das figuras e piloto pago): medidas numa cópia da biblioteca em
  `tmp/lote-29/biblioteca`.
- **Etapa C** (leitura completa das figuras e reindexação), autorizada pelo pesquisador em 03/10 com o Flash:
  feita na biblioteca real, `data/bibliotecas/principal`, com cópia de segurança do catálogo em
  `tmp/lote-29/backup/`.

## Testes

44 testes novos:
- **`tests/test_chunking.py` (22):**
  - cabeçalhos e rodapés repetidos saem, só nas bordas; com menos de 4 páginas nada sai;
  - o cabeçalho de capítulo com o número da página sai mesmo aparecendo em poucas páginas; a legenda no pé
    da página e o título de tabela continuada ficam;
  - página de sumário marcada; uma linha pontilhada não faz um sumário;
  - lista de referências marcada até a última entrada; a de um capítulo não leva o capítulo seguinte; a lista
    no padrão da ABNT; um título "References" solto no texto, ou com menos de 3 entradas, não conta;
  - códigos de glifo fora dos trechos;
  - frases: abreviações, iniciais e pedaços curtos; trechos dentro do limite, com tamanhos equilibrados, sem
    perder nem repetir texto; a frase longa cortada na quebra de linha e depois por tokens, sem partir
    palavra; o título curto que fecha um bloco; a legenda que abre um trecho, e a menção que não abre;
  - a descrição de uma figura em trechos de tamanho parecido, com o corte no fim de uma linha ou de uma
    frase, e o primeiro trecho com a legenda e o começo da descrição;
  - a biblioteca com o esquema novo: cabeçalho fora dos trechos, texto guardado inteiro, registro da limpeza;
  - referências fora da busca comum e de volta quando pedidas;
  - passagem unida por quebra de linha, parando na borda da página e da parte de referências;
  - extrações antigas e novas no mesmo índice; reindexar guarda a extração anterior e não chama o modelo
    local na segunda vez; outro modelo de vetores continua barrado;
  - só a versão mais recente é reindexada; o trecho repetido entra uma vez.
- **`tests/test_figures.py` (18):**
  - rótulos de legenda normalizados; sinais da página (imagem embutida, desenho, legenda, digitalizada);
  - o texto das figuras só com o que a página ainda não tem; menos de 3 palavras novas, nada;
  - a biblioteca indexa o texto das figuras, mostra a etapa no envio e não o refaz ao reindexar; sem
    reconhecimento de texto, ou com falha dele, o documento entra só com o texto;
  - a conferência do que o modelo propõe: rótulo inventado descartado, legenda não confirmada descartada,
    parcela conferida e números não encontrados, rótulo repetido, limite de itens e de tamanho;
  - o pedido leva a imagem e repete uma vez a resposta cortada; cortada ou inválida duas vezes, a página não
    é gravada;
  - a imagem da página é um JPEG com o lado maior em até 1.600 pixels;
  - a descrição grava cada página, reindexa, tira o texto local das páginas descritas, retoma só o que faltou
    e não paga de novo; pode ser parada, limitada e refeita;
  - apagar o documento remove o que foi lido das suas figuras;
  - a legenda achada no texto traz a descrição junto; a passagem leva a descrição inteira;
  - as descrições não ganham o bônus da busca por palavras;
  - um documento indexado antes do lote tem as páginas com figura achadas sem uma extração nova;
  - as rotas: contagens, início, uso registrado só com tokens, uma leitura por vez, parar, e o documento que
    não é apagado no meio da leitura;
  - 60 imagens de página pedidas por 8 threads ao mesmo tempo, sem derrubar o processo.
- **`tests/test_providers.py` (4):** imagem só em mensagem do usuário de um pedido multimodal; os dois modelos
  Gemini com a capacidade multimodal; um cliente só com várias threads; a resposta cortada no meio do JSON
  volta com os tokens.

**635 testes passaram** (591 do lote 28 e 44 novos), no Python 3.12.14. O Ruff não apontou problemas.

## Etapa A: limpeza, frases e texto das figuras (na cópia)

26 documentos, 2.218 páginas. A primeira reindexação da cópia levou 877 s: 15 minutos, dos quais cerca de 3
no reconhecimento do texto das figuras e o resto no modelo local de busca. Uma reindexação seguinte, com os
vetores aproveitados, levou 116 s.

| Medida | Antes | Depois |
|---|---:|---:|
| Trechos no índice | 13.953 | 14.156 |
| Trechos de texto, fora o sumário e as referências | 13.953 | 12.712 |
| Trechos de sumário e de referências, fora da busca comum | 0 | 1.187 |
| Trechos com o texto reconhecido nas figuras | 0 | 257 |
| Trechos de texto sem pontuação no fim | 11.938 (86%) | 3.143 (25%) |
| Trechos com linha de borda repetida, pela conta da investigação | 1.579 | 399 |
| Palavras por trecho, em média | 63,5 | 50,5 |
| Trechos com menos de 15 palavras | 130 (0,9%) | 458 (3,6%) |

- **Sem pontuação no fim:** os 25% que restam são linhas de tabela e de fórmula, legendas e a última frase de
  uma página que continua na seguinte.
- **Linha de borda:** dos 399, 394 são números com hífen no meio do texto ("5-4" em "Table 5-4"), que a conta
  da investigação toma pela linha "3-12" do rodapé de um guia. Linhas de borda de verdade restaram 5.
- **Linhas tiradas das bordas:** 3.292 em 2.216 páginas.
- **Trechos curtos:** aumentaram porque a legenda passou a abrir um trecho. É o preço de a pergunta sobre uma
  figura achar a página dela.
- **Páginas com conteúdo visual:** 1.293 das 2.218 têm figura, desenho, tabela ou legenda: 353 com imagem
  embutida, 363 com desenho vetorial, 1.084 com legenda e 206 digitalizadas (uma página pode ter mais de um
  sinal). O reconhecimento local rodou nas 353 com imagem embutida e achou texto novo em 221.
- **Exemplo do reconhecimento local:** no diagrama do sistema fotovoltaico de Colli (2015), leu "Fuse 1",
  "String 1", "Disconnect 1" e "switchboard". Nas árvores de falhas de Baschel et al. (2018), não leu nada
  novo: os poucos nomes que elas trazem já estão no texto, e o resto são símbolos.

## Etapa B: piloto da descrição pelo modelo

20 páginas, escolhidas antes de rodar: as 16 das perguntas de figura e mais 4 (um fluxograma, uma página
digitalizada com tabelas, um esquema elétrico e uma página de texto que cita uma figura). Cada página foi
enviada aos dois modelos. O relatório, com a página ao lado das duas descrições, está em
`tmp/lote-29/piloto/relatorio-piloto.html` e foi enviado ao pesquisador, que escolheu o Flash.

| Medida | Flash | Flash-Lite |
|---|---:|---:|
| Páginas lidas | 20 | 20 |
| Figuras e tabelas encontradas | 32 | 32 |
| Sem rótulo confirmado na página | 1 | 1 |
| Conferência local, mediana | 84% | 82% |
| Itens com menos de 50% conferido | 5 | 4 |
| Tokens de entrada por página | 1.496 | 1.498 |
| Tokens de saída por página | 691 | 656 |
| Tokens de raciocínio por página | 551 | 0 |
| Segundos por página | 5,6 | 3,4 |

- **Conferência local:** de cada 100 palavras e números que o modelo disse ver, quantos o computador também
  achou no texto da página. Número baixo não quer dizer erro: rótulos de um diagrama e valores de um gráfico
  estão só na imagem.
- **Diferenças vistas no texto das descrições:** o Flash copiou as legendas inteiras e transcreveu as tabelas
  sem lacunas; o Flash-Lite abreviou algumas legendas e deixou "?" em células da primeira coluna de uma
  tabela. Nas árvores de falhas, os dois descreveram os eventos e as portas.
- **Falhas na primeira rodada, 3 em 40:**
  - 2 por um defeito do programa: com 4 pedidos simultâneos, a conexão de um era fechada pelo outro. Não
    chegaram a ser enviadas. Corrigido, com teste;
  - 1 do Flash-Lite, que passou do limite de saída ao transcrever um formulário em branco, nas duas
    tentativas. O pedido ganhou uma regra: até 40 linhas por tabela, e formulário em branco é descrito como
    figura. As 3 foram repetidas e deram certo.
- **Respostas com as descrições do piloto** (3 perguntas, nos dois modelos, pelo caminho do chat):

| Pergunta | Flash | Flash-Lite |
|---|---|---|
| Árvore de falhas do inversor central (Baschel et al.) | Usou as descrições das duas figuras, com citação, e avisou que são descrições automáticas a conferir no original | Usou as descrições, com citação, sem o aviso |
| Colunas do formulário de FMECA | A busca não trouxe a página; disse que os trechos não tratam disso | A busca não trouxe a página; disse isso e listou colunas "em geral", de conhecimento próprio |
| Taxa de falha do transformador na tabela de Baschel et al. | Achou a tabela, viu que o transformador não estava nas linhas recebidas e mandou conferir no original | O mesmo |

  - Nenhuma resposta pôs texto de descrição entre aspas.
  - A terceira pergunta levou a uma correção: a passagem de um trecho de descrição passou a levar a
    descrição inteira, e não só os vizinhos.

## Etapa C: a biblioteca real

### Leitura completa das figuras, com o Flash

| Medida | Resultado |
|---|---:|
| Páginas com figura, desenho, tabela ou legenda | 1.293 |
| Páginas descritas | 1.291 |
| Figuras e tabelas descritas | 1.539 |
| Páginas em que o modelo não achou figura nem tabela | 102 (8%) |
| Páginas sem resposta válida, em duas rodadas | 2 |
| Chamadas registradas | 1.301 |
| Tokens de entrada | 2,02 milhões |
| Tokens de saída e de raciocínio | 1,41 milhão (0,74 e 0,67) |
| Tempo, com 3 páginas por vez | 42 min |

- **As 2 páginas sem descrição:** página 4 de `Artigo_FMEA.pdf` e página 25 de `nasa-rcmguide.pdf`. Nas duas
  rodadas o modelo devolveu uma resposta vazia ou que não era o formato pedido. Elas ficam como estavam antes
  do lote: com o texto da página no índice, sem a descrição.
- **Chamadas:** as 1.301 registradas são as 1.291 páginas e 10 repetições depois de uma resposta cortada.
  Cerca de 10 tentativas sem resposta válida não ficaram no registro de uso.
- **A estimativa do piloto** era de 1,93 milhão de tokens de entrada e 1,61 milhão de saída: a entrada ficou
  5% acima e a saída 13% abaixo.

### O índice depois da reindexação

| Medida | Antes do lote | Agora |
|---|---:|---:|
| Trechos no índice | 13.953 | 20.000 |
| Trechos de texto | 13.953 | 12.712 |
| Trechos de sumário e de referências, fora da busca comum | 0 | 1.187 |
| Trechos de descrição de figuras e tabelas | 0 | 6.098 |
| Trechos com o texto reconhecido nas figuras (páginas não descritas) | 0 | 3 |

`biblioteca verificar` conferiu os originais, as extrações, os trechos e os vetores: as únicas pendências são
as duas de antes do lote (uma página de reconhecimento de texto com baixa confiança no manual de Lafraia e uma
página sem texto no guia da NASA).

### A busca

| Medida | Antes do lote | Agora |
|---|---:|---:|
| Perguntas de referência, pergunta direta: acertos em 16 | 13 | 14 |
| Pergunta direta: posição do primeiro acerto (1 é sempre em primeiro) | 0,78 | 0,80 |
| Perguntas de referência, consulta reescrita: acertos em 16 | 16 | 16 |
| Consulta reescrita: posição do primeiro acerto | 0,94 | 0,84 |
| Perguntas de figura, diretas: a página esperada nos 10 primeiros | 12 | 12 |
| Perguntas de figura, diretas: o conteúdo da figura nos 10 primeiros | 0 | 12 |
| Perguntas de figura, reescritas: a página esperada nos 10 primeiros | 11 | 10 |
| Perguntas de figura, reescritas: o conteúdo da figura nos 10 primeiros | 0 | 9 |
| Segundos por busca | 2,65 | 3,9 |

- **Perguntas de referência:** as 16 do lote 19, com o acerto pelo documento esperado. Com a consulta
  reescrita, que é a do chat, as 16 continuam acertando; em 3 delas o documento esperado desceu de posição:
  - taxas de falha em Sarquis Filho et al., de 2º para 3º. Antes, os 4 trechos do artigo que a busca trazia
    eram entradas da lista de referências dele. Agora são o texto e a tabela de taxas de falha. A posição
    caiu e o conteúdo melhorou;
  - confiabilidade em série e em paralelo, de 1º para 5º: passaram à frente trechos de outros três documentos
    que tratam do mesmo cálculo, e a descrição de um diagrama de blocos em série;
  - origem da FMEA, de 1º para 3º: os dois primeiros lugares ficaram com a legenda de uma figura sobre a
    FMEA, de outro livro, e a descrição dela, que não respondem à pergunta. É o efeito dos trechos curtos.
- **Perguntas de figura:** 16 perguntas novas (12 de figura e 4 de tabela), em
  `data/avaliacao-busca/perguntas-figuras.json`, escritas a partir das legendas antes de olhar a busca. O
  acerto é pela página esperada. "O conteúdo da figura" quer dizer que um trecho com a descrição dela, ou
  com o texto reconhecido nela, veio entre os resultados.
- **O ganho do lote está nas linhas do conteúdo:** antes, nenhuma pergunta sobre uma figura trazia o que a
  figura mostra, só a legenda. Agora 12 das 16 trazem com a pergunta direta, e 9 com a consulta reescrita.
- **O que ainda falha:**
  - com a pergunta direta, 4 das 16: um diagrama de blocos, que perde para outras páginas do mesmo
    documento, e três tabelas;
  - a consulta reescrita troca a referência específica à figura por termos gerais (em "colunas do formulário
    de FMECA adaptado da SAE", ela busca FMECA em geral). Por isso, mais 2 perguntas perdem a página e 1
    perde a descrição.
- **As descrições fora da lista por palavras.** Escritas em português, as descrições ganhavam de todo o acervo
  em inglês na parte da busca que compara palavras, numa pergunta em português. Medido nas duas formas: fora
  da lista, a posição do primeiro acerto das perguntas de referência sobe de 0,77 para 0,80 (direta) e de 0,80
  para 0,84 (reescrita); nas de figura, o conteúdo vai de 13 para 12 (direta) e fica em 9 (reescrita). Ficou
  fora: a descrição concorre pelo significado e chega junto com a legenda achada no texto.
- **Tempo de busca:** subiu na proporção dos trechos, de 2,65 s para 3,9 s. A busca compara a pergunta com
  todos os trechos, um a um.

### Espaço em disco

| Pasta | Antes do lote | Depois das três reindexações | Depois da limpeza |
|---|---:|---:|---:|
| Catálogo | 154 MB | 786 MB | 367 MB |
| Extrações | 184 MB | 991 MB | 446 MB |
| Originais | 192 MB | 192 MB | 192 MB |

- A biblioteca real foi reindexada três vezes, e não uma, como previa o plano: depois da primeira, a medição
  mostrou que as descrições estavam sendo divididas em pedaços ruins (trechos só com o título, cortes no meio
  de palavras), e a correção pediu mais duas. As reindexações são gratuitas e não repetem a leitura das
  figuras.
- Cada reindexação guarda a extração anterior. As duas intermediárias de 03/10 somavam 52 extrações, 41.685
  trechos no catálogo e 546 MB em arquivos.
- **Limpeza autorizada pelo pesquisador em 03/10:** as 52 extrações intermediárias foram apagadas, e o
  catálogo, compactado. Ficaram, de cada documento, a extração original e a atual. Antes, o catálogo foi
  copiado para `tmp/lote-29/backup/`.
- Depois da limpeza, `biblioteca verificar` contou 26 documentos e 52 extrações, com as mesmas duas
  pendências de antes do lote; o índice continua com 20.000 trechos e 1.291 páginas descritas.

## No navegador

Servidor de teste com a interface e as rotas reais, uma biblioteca de um PDF de cinco páginas e o modelo
simulado, sem custo:
- o quadro "Figuras e tabelas" mostra 4 páginas, 1 com texto lido nas figuras e "0 de 4" descritas, com uma
  nota em cada linha;
- o botão abre o aviso com o número de chamadas, o modelo, a estimativa de tokens e a frase "cada página é
  enviada como imagem";
- durante a leitura aparecem "Descrevendo: 0 de 4 páginas" e "Parar"; ao fim, "4 de 4", o modelo, a data e o
  aviso "4 páginas descritas, com 3 figuras ou tabelas";
- a extração em Markdown passa a mostrar as seções "página PDF 1 · Figure 1 (descrição automática)";
- numa resposta, a legenda da tabela vem seguida da descrição dela; a janela de fontes mostra "descrição
  automática de figura ou tabela: conferir no original", com a nota ao passar o mouse, e "Abrir página" leva
  à página do PDF.

## Pacote 0.4.0

- **Arquivo:** `dist/v0.4.0/aliado-0.4.0-py3-none-any.whl`, 96 arquivos, 744 kB, SHA-256
  `f697292ef8b1b470cdfb146601576a0cef0d9206b4a6fedfe8bb9d433a196195`.
- **Conteúdo, conferido arquivo por arquivo contra `src`:**
  - os 91 arquivos do pacote têm o mesmo hash dos de `src`, e nenhum arquivo de `src` ficou de fora;
  - entraram a limpeza e os trechos por frase, as figuras e o espelho do Obsidian;
  - nada de testes, documentação ou dados.
- **Teste fora do projeto:** instalado com `--target` em `tmp/lote-29/pkg` e rodado de outra pasta. O código
  carregado veio do pacote, e a versão lida foi 0.4.0.
  - `aliado skills` listou as 3 skills.
  - A interface respondeu 200 em `/`, `app.js`, `app.css`, `/api/estado` e `/api/biblioteca`, e a página traz
    o quadro "Figuras e tabelas".

## Chamadas pagas

| Uso | Chamadas | Modelo | Registro |
|---|---:|---|---|
| Consultas reescritas das 16 perguntas de referência e das 16 de figura | 32 | Flash-Lite | `tmp/lote-29/uso.jsonl` |
| Piloto: 20 páginas em cada modelo | 40 | Flash e Flash-Lite | `tmp/lote-29/uso.jsonl` |
| Piloto: as duas tentativas cortadas do formulário em branco | 2 | Flash-Lite | não registradas |
| Respostas a 3 perguntas | 6 | Flash e Flash-Lite | `tmp/lote-29/uso.jsonl` |
| Leitura completa das figuras | 1.301 | Flash | `data/uso/chamadas.jsonl` |
| Leitura completa: tentativas sem resposta válida | cerca de 10 | Flash | não registradas |

- **Etapas A e B:** 80 chamadas, o total autorizado com o plano. O plano previa 16 consultas reescritas; foram
  32, porque as 16 perguntas de figura também foram reescritas. Para caber nas 80, as respostas foram 6, e
  não 12, e a conferência no navegador usou o modelo simulado.
- **Etapa C:** a leitura completa, autorizada em 03/10.
- As tentativas não registradas vieram de respostas que o adapter recusava antes de devolver os tokens. O
  adapter foi corrigido para a resposta cortada; a resposta vazia continua sem registro.

## Pendências

- **Com o pesquisador:** a tag `v0.4.0` e o push; o aceite do lote 28 no Obsidian.
- **O servidor aberto antes do fim do lote** precisa ser reiniciado para carregar a versão final.
- **Para um próximo lote:** a busca mais rápida (cada pergunta leva 3,9 s só na busca) e a consulta reescrita
  nas perguntas sobre uma figura específica.
