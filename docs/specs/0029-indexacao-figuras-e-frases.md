# Lote 29 — indexação: figuras, tabelas e trechos por frase

Lote autorizado em 03/10/2026, sobre o commit `436582a` (lote 27) e o lote 28, ainda sem commit. O pedido:
"quero que seja melhorada a indexação dos arquivos. Existem muitos, mas muitos trechos mesmos, inclusive as
imagens que não são consideradas ou lidas, de todos os documentos."

## O que a investigação mostrou

Medição da biblioteca real, só em leitura: 26 documentos, 2.218 páginas, 13.953 trechos.

| O que foi medido | Resultado |
|---|---:|
| Páginas em que o texto corrido se perdeu na leitura | 0 |
| Páginas com figura, desenho, tabela ou legenda cujo conteúdo visual não estava no índice | 60% |
| Trechos que terminavam sem pontuação final (cortados no meio da frase) | 86% |
| Trechos que carregavam uma linha de cabeçalho ou rodapé repetida | 1.579 (11%) |
| Trechos de sumário pontilhado e de lista de referências | 215 e 214 |
| Trechos repetidos palavra por palavra | 106 |

- **O texto corrido estava todo no índice.** O que faltava era o conteúdo visual. Exemplo: a página 3 de
  Baschel et al. (2018) tem duas árvores de falhas, e o índice guardava só as legendas.
- **Os trechos eram fatias de 110 tokens, com passo de 90,** sem olhar onde a frase termina.
- **Cabeçalhos e rodapés entravam nos trechos:** "Energies 2018, 11, 1579 3 of 16", o aviso de licença de uso em
  cada página de uma norma, o título do capítulo com o número da página.
- **Sumários e listas de referências** são cheios de palavras-chave e vazios de conteúdo: combinam com muitas
  perguntas e ocupam o lugar de trechos que respondem.

## Decisões do pesquisador (03/10)

| Tema | Decisão |
|---|---|
| Escopo | Ler figuras e tabelas, trechos por frase e limpar o índice. "Busca mais rápida" ficou de fora. |
| Imagens | As duas coisas: reconhecer no computador o texto dentro das figuras e pedir a descrição ao modelo. |
| Lote 28 | Junta-se a este: um commit só no fim. |
| Versão | 0.4.0, com os lotes 27 a 29. |

A descrição pelo modelo muda o que sai do computador: páginas dos documentos passam a ser enviadas ao Gemini
como imagem. Antes, só trechos de texto iam. Por isso ela nunca é automática.

## Escopo implementado

### Índice limpo

Vale para PDFs. O texto guardado de cada página continua inteiro; muda só o que vira trecho de busca.

- **Cabeçalhos e rodapés.** Só as linhas das bordas da página são avaliadas: até 3 no topo e 3 no pé, seguidas
  a partir da borda. O que fica é sempre uma fatia só do texto da página. Uma linha sai quando:
  - se repete em 30% das páginas ou mais, com os números trocados ("3 of 16" e "4 of 16" são a mesma linha); ou
  - traz o número da página: aparece em 5 páginas ou mais, e um dos seus números cresce junto com a página em
    60% das vezes, entre ocorrências próximas. É o caso do título de capítulo de um livro ("106 3 Control
    Technology…"), que se repete em poucas páginas.
- **O que não sai:** a legenda de figura ou tabela no pé da página; a linha só de números de uma tabela (com 3
  números ou mais); o título de tabela continuada, que não acompanha a página.
- **Sumário.** A página em que 40% das linhas ou mais têm pontilhado (e pelo menos 5) é marcada no local do
  trecho: "página PDF 5 · sumário".
- **Lista de referências.** Começa numa linha de título ("References", "Referências", "Bibliografia") e segue
  enquanto aparecem começos de entrada: a numeração seguida ou "Sobrenome, I.". Termina depois de 8 linhas
  sem entrada, ou quando a numeração recomeça do 1, e só vale com 3 entradas ou mais. Um livro com
  referências por capítulo não perde o capítulo seguinte. O local fica "página PDF 14 · referências".
- **Fora da busca comum.** Os trechos de sumário e de referências continuam no índice, e a busca os deixa de
  fora. Eles voltam quando a pergunta os pede por palavra (sumário, capítulos, referências, bibliografia,
  cita, e os mesmos termos em inglês).
- **Repetidos e lixo.** Um trecho repetido palavra por palavra no mesmo documento entra uma vez. Os códigos de
  glifo sem texto (`/gid00030…`) não entram.
- O registro da extração (`metadata.json`, campo `limpeza`) diz o que saiu de cada documento.

### Trechos por frase

- Um trecho junta frases inteiras até 110 tokens, com tamanhos equilibrados e sem repetir o fim do anterior.
- A frase termina em ponto, exclamação, interrogação ou reticências, seguida de espaço e de maiúscula ou
  número, ou numa linha em branco. Abreviações ("et al.", "Fig.", "p.") e iniciais de nomes não cortam. Um
  pedaço com menos de 20 letras segue com a frase vizinha.
- Uma frase que sozinha passa do limite (tabela, fórmula, lista sem pontuação) é cortada nas quebras de
  linha, de preferência depois de uma linha curta ou terminada em pontuação; uma linha que ainda passa, a
  cada 110 tokens.
- **A legenda começa um trecho.** A linha de legenda de figura ou tabela ("Fig. 3. Fault tree…", "Table 7-2—
  Failure modes…") abre sempre um trecho novo. Junta ao parágrafo de cima, ela se perdia na busca. A menção
  no meio do texto ("Figure 5 explains…") não conta.
- Cada trecho continua sendo uma fatia exata do texto da página.
- **A passagem** enviada ao modelo continua sendo o trecho com os vizinhos da mesma página, agora unidos por
  uma quebra de linha.
- **Compatibilidade.** Os vetores são do mesmo modelo local. O registro da extração passa a terminar em
  `frases110-v1`; a busca compara só a parte que identifica os vetores e aceita os dois esquemas no mesmo
  índice. A memória e as perguntas continuam com a divisão antiga, de tamanho fixo.

### Texto dentro das figuras

- **Sinais de conteúdo visual por página:** imagem embutida que ocupa 4% da página ou mais; desenho vetorial
  (150 traços ou mais acima do comum do documento); legenda de figura, tabela, quadro ou gráfico no texto.
- Numa página digitalizada, a imagem é a própria página: ela só entra pela legenda.
- Nas páginas com imagem embutida, o recorte de cada figura passa pelo reconhecimento de texto local
  (Tesseract, texto esparso, palavras com confiança de 60 ou mais). O que já está no texto da página sai: uma
  linha inteira, ou um pedaço de 12 letras de uma linha longa.
- Com 3 palavras novas ou mais, o texto entra como trecho próprio: "página PDF 3 · texto das figuras".
- O resultado fica na tabela `page_figures`, pelo conteúdo do arquivo: não é refeito ao reindexar.
- Roda em cada envio, com a etapa "lendo o texto das figuras" no pop-up. Sem Tesseract, ou com uma falha
  dele, o documento é indexado só com o texto.

### Descrição pelo modelo

- **Só por pedido:** o botão "Descrever figuras e tabelas" na ficha do documento, ou o comando
  `biblioteca figuras --executar`. O aviso antes de enviar diz o número de chamadas, o modelo e a estimativa
  de tokens.
- **Uma chamada por página** com conteúdo visual, com a imagem da página inteira (JPEG, 150 dpi, lado maior
  em até 1.600 pixels). Três páginas por vez.
- **O modelo devolve** uma lista de itens, cada um com o tipo (figura ou tabela), o rótulo impresso, a legenda,
  a descrição em português, as palavras visíveis e, nas tabelas, até 40 linhas transcritas.
- **O código confere,** no padrão da ficha do documento:
  - o rótulo ("Figure 2") só fica se a página tiver uma legenda com ele; senão o item entra como "figura sem
    rótulo";
  - a legenda só fica se estiver escrita na página;
  - **conferência local:** de cada 100 palavras e números que o modelo disse ver, quantos o computador também
    encontrou no texto da página ou no texto reconhecido nas figuras. Os números não encontrados ficam
    listados. Número baixo não quer dizer erro: o que está só na imagem não tem como ser conferido no texto.
- **No índice,** cada item tem o seu local ("página PDF 3 · Figure 2") e é marcado como descrição
  automática. Na página já descrita, o texto local das figuras sai do índice.
  - O texto do item junta a legenda e a descrição na mesma linha, depois o texto visível (os itens com
    letras, até cerca de um trecho) e a tabela.
  - A descrição é dividida em trechos de tamanho parecido, e não por frase: o que falta é repartido por
    igual, e o corte fica no fim de uma linha, de uma frase ou de um item, perto do tamanho ideal, sem
    partir palavra. O primeiro trecho leva sempre a legenda e o começo da descrição.
- **Na busca:**
  - a legenda achada no texto leva junto a descrição da figura, quando ela existe; um trecho que é só a
    legenda dá lugar à descrição, que já a traz;
  - a passagem de um trecho de descrição leva a descrição inteira;
  - as descrições ficam fora da lista por palavras da busca. Escritas em português, elas ganhavam de todo o
    acervo em inglês nessa lista, numa pergunta em português. Concorrem pelo significado e chegam junto com
    a legenda.
- **Na resposta,** as regras da biblioteca dizem que a descrição automática e o texto reconhecido não são
  texto do documento: servem para dizer o que a figura mostra, com o aviso de conferir no original, e não vão
  entre aspas.
- **Na tela:**
  - o quadro "Figuras e tabelas" na ficha do documento: páginas com figura ou tabela, com texto lido nas
    figuras e descritas pelo modelo, cada linha com a sua nota;
  - o andamento e o "Parar". Cada página é gravada ao chegar: parar ou cair não perde nem paga de novo;
  - na janela de fontes, "descrição automática de figura ou tabela: conferir no original" e "texto
    reconhecido dentro de figura: conferir no original", com nota ao passar o mouse, e o link "Abrir página".
- **Registro de uso:** cada chamada entra em `data/uso/chamadas.jsonl` com a tarefa `biblioteca-figuras`,
  só com os tokens. Uma resposta cortada pelo limite de tamanho também entra.

### Reindexar

- `aliado biblioteca reindexar` refaz os trechos a partir do texto de página já guardado. Não lê o arquivo de
  novo, não repete o reconhecimento de texto das páginas nem a leitura das figuras, e aproveita o vetor de
  todo trecho que não mudou.
- `aliado biblioteca figuras` procura as páginas com conteúdo visual de um documento indexado antes do lote,
  sem refazer a extração; sem `--executar`, só mostra as páginas por descrever e a estimativa de tokens.
- A extração anterior continua guardada, como em qualquer reprocessamento.
- Vale para a versão mais recente de cada documento.

### Outras correções

- **O PDFium não aceita threads simultâneas.** O envio, o reconhecimento de texto e a descrição das figuras
  passam todos por uma trava. Sem ela, o processo caía de vez em quando.
- **O cliente do Gemini é criado uma vez só.** Com várias threads no primeiro pedido, cada uma criava o seu, e
  o que era descartado fechava a conexão de um pedido em andamento.

## Limites assumidos

- **A descrição é de um modelo, e pode errar.** A conferência local diz onde olhar com mais cuidado; ela não
  prova que a descrição está certa. A ligação entre os elementos de um diagrama não tem como ser conferida no
  texto.
- **Páginas digitalizadas sem legenda** não entram na descrição: não há como saber, pelo arquivo, que há uma
  figura ali.
- **Tabelas com mais de 40 linhas** são transcritas até a 40ª; a descrição diz que continuam.
- **Com a consulta reescrita do chat,** que troca siglas por extenso e junta termos em dois idiomas, algumas
  perguntas sobre uma figura específica deixam de achar a página. A reescrita não foi alterada neste lote.
- **A busca ficou mais lenta.** Cada pergunta compara os vetores de todos os trechos, um a um. Com as
  descrições da biblioteca de hoje, os trechos foram de 13.953 para 20.000, e a busca de 2,65 s para 3,9 s.
- **Duas páginas ficaram sem descrição** na biblioteca de hoje: o modelo devolveu uma resposta vazia ou fora
  do formato nas duas tentativas. Uma resposta assim é cobrada e não entra no registro de uso.
- **As descrições estão em português,** e os documentos, em boa parte, em inglês. Uma pergunta em inglês
  combina menos com a descrição do que com a legenda.
- **Trechos curtos.** A legenda que abre um trecho deixa mais trechos pequenos (menos de 15 palavras: de 0,9%
  para 3,6% dos trechos de texto). Um deles pode combinar com a pergunta só pelas palavras da legenda.
- **Palavras quebradas por hífen no fim da linha** (0,4% das palavras) continuam quebradas no índice.
- **O limite entre frases** não atravessa a página: a frase que continua na página seguinte fica em dois
  trechos.
- **Uma biblioteca anterior a este lote** continua funcionando sem reindexar; ganha a limpeza, as frases e o
  texto das figuras quando for reindexada.

## Fora do escopo

- Busca mais rápida, e o número de trechos por resposta.
- Fórmulas.
- Um botão para descrever todos os documentos de uma vez.
- Ligações entre documentos pelas listas de referências.
- Apagar as extrações antigas substituídas pela reindexação.

## Critérios de aceitação

- **Testes sem rede:**
  - limpeza: cabeçalhos de páginas pares e ímpares, cabeçalho de capítulo com o número da página, legenda e
    título de tabela que ficam, sumário, referências por capítulo, título "Referências" solto no texto;
  - frases: nenhum trecho passa do limite, todo trecho é fatia do texto, abreviações não cortam, a frase
    longa cai na quebra de linha, a legenda abre um trecho;
  - busca com extrações antigas e novas juntas; passagem nos dois esquemas; sumário e referências fora da
    busca comum e de volta quando pedidos;
  - figuras: página sem reconhecimento de texto, rótulo inventado descartado, número não conferido listado,
    resposta cortada que não é gravada, parar e retomar sem repetir página, apagar o documento limpa as leituras;
  - adapter: imagem só em mensagem do usuário de um pedido marcado como multimodal.
- **Medição numa cópia da biblioteca,** antes e depois: as 16 perguntas de referência; 16 perguntas novas
  sobre figuras e tabelas, medidas pela página esperada; os trechos; o tempo de busca; o espaço em disco.
- **Piloto pago** com 20 páginas nos dois modelos, com relatório para o pesquisador escolher o modelo.
- **No navegador,** num servidor de teste com modelo simulado: o quadro, o botão com o aviso, o andamento e
  os avisos na janela de fontes.
- **Leitura completa e reindexação da biblioteca real** só com nova autorização do pesquisador, dada em
  03/10/2026 com o Flash.
