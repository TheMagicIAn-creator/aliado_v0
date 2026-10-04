# Lote 30 — leitura integral dos documentos e saída da aba Biblioteca

Lote autorizado em 03/10/2026, sobre o commit `85dce50` (lotes 28 e 29). O pedido: "vocês indexam, têm
acesso às imagens, leem elas pelo conteúdo, não fracionam qualquer trecho de qualquer anexo entregue, não
truncam chunks. Queria que ele fizesse essas coisas, pois são necessárias para mim, mesmo que isso elevasse
seu custo. Ademais, acho que para uma versão 0.4.1 poderíamos tirar a aba de 'biblioteca' dali."

## O que a investigação mostrou

- **O modelo lia pouco.** A busca escolhia cerca de 10 trechos de até 110 tokens, e só eles iam ao modelo:
  cerca de 11 mil tokens por pergunta, com as regras. As figuras chegavam como um texto escrito por outro
  modelo (lote 29), e não como imagem.
- **A biblioteca inteira não cabe num pedido, mas os documentos cabem.** São 26 documentos e 2.216 páginas.
  Dos 26, 22 têm até 38 páginas; os outros 4 são livros e normas, de 369 a 541 páginas, e há um trabalho de
  77 páginas.
- **Uma página de PDF custa 560 tokens no Gemini,** com pouco ou muito texto (medido pela contagem de tokens
  do serviço, que é gratuita). O texto extraído da mesma página, enviado à parte, custa de duas a três
  vezes isso: de 2,4 a 3,7 letras por token.
- **O trecho pequeno é um limite da busca, e não da leitura.** O modelo local que compara significados lê
  até 128 tokens por vez; o que o modelo de resposta lê pode ser outra coisa.

## Decisões do pesquisador (03/10)

| Tema | Decisão |
|---|---|
| Leitura | Documentos inteiros: a busca escolhe os documentos; artigos vão inteiros, livros e normas vão em blocos de páginas inteiras. |
| Imagens | De todas as páginas enviadas. |
| Teto por pergunta | 400 mil tokens, ajustável na tela. |
| Aba Biblioteca | Sai; um painel no chat fica com a lista, apagar e editar a ficha. |
| Regra que reparte o teto | Deixada com o assistente. |

A leitura integral muda o que sai do computador: os PDFs dos documentos lidos são enviados ao Gemini e ficam
guardados no serviço de arquivos do Google por até 48 horas. Antes, só trechos de texto iam, e nada ficava
guardado.

## Escopo implementado

### A busca escolhe os documentos

- A busca continua como está, com trechos pequenos, e passa a pedir 20 resultados. Deles sai a ordem dos
  documentos. Ela informa também, por documento, as páginas dos melhores candidatos.
- **Documento pequeno** (até 40 páginas, ou que não seja PDF): vai inteiro ou fica de fora.
- **Documento grande:** é dividido em blocos fixos de 10 páginas (1–10, 11–20…). Vão os blocos em que a busca
  achou algo, na ordem dela, e depois os vizinhos, enquanto houver teto. Os blocos são fixos para o envio de
  cada um ser reaproveitado de uma pergunta para a outra.
- **O teto** é uma estimativa de tokens dos documentos: 560 por página de PDF, mais a linha da página na
  lista. A regra que o reparte (`reading.share`):
  1. os documentos fixados na conversa levam o que precisam;
  2. todo documento que a busca trouxe recebe o seu mínimo: o bloco do melhor trecho achado (o documento
     inteiro, se for pequeno);
  3. cada documento da busca cresce até um quarto do teto, na ordem da busca;
  4. o que sobra volta, na mesma ordem, para quem ficou cortado.
- O que não cabe é dito à tela ("Não couberam no teto").

### O que vai ao modelo

Uma mensagem por documento, antes da memória e da conversa:

- uma frase com a referência, o arquivo, a versão e o que foi enviado ("Enviado inteiro: 16 páginas", ou
  "Enviado em parte: páginas 41–60 e 201–210, de 426; as outras páginas não foram enviadas e não foram lidas");
- o PDF dessas páginas: o original, quando o documento é um bloco só, ou um recorte por bloco;
- a lista das páginas, na ordem do PDF: o identificador de cada uma e as primeiras palavras dela (até 120
  letras), para o modelo reconhecer a página que está citando.

O texto guardado inteiro só segue quando não há PDF para anexar (Markdown, JSON, ou um PDF que não pôde ser
recortado). As regras ao modelo (`READING_RULES`) dizem para ler pelo PDF, que mostra cada página como ela é, e
para avisar quando a resposta puder estar nas páginas que ficaram de fora.

A descrição automática das figuras (lote 29) não vai ao modelo neste modo: a página vai como ela é. Ela
continua servindo à busca.

### Citações por página

- Cada página enviada tem um identificador próprio, tirado do conteúdo do arquivo e do número da página
  (`K9c4cd858p6`): é o mesmo em toda pergunta e em toda conversa.
- A conferência é a de sempre: um identificador que não foi enviado bloqueia a resposta.
- Na janela de fontes, a página citada aparece com o aviso "página lida inteira", o texto extraído dela e o
  link **Abrir página**. "A busca também trouxe" lista os trechos que a busca achou e a resposta não citou; as
  páginas lidas e não citadas não entram (podem ser centenas).
- O limite de tamanho da resposta sobe para 32.768 tokens neste modo, porque o modelo raciocina mais.

### Envio pelo serviço de arquivos do Google

- Todo PDF lido sobe pelo serviço de arquivos, que o guarda por até 48 horas. Cada arquivo sobe uma vez e
  serve às perguntas seguintes enquanto durar; quatro envios correm ao mesmo tempo.
- O AL-IAdo registra o que subiu em `data/uso/arquivos-google.json`: a chave do conteúdo (o resumo do arquivo
  e as páginas), o nome dado pelo serviço, o tamanho e a validade. Nunca o conteúdo.
- O painel de documentos mostra quantos arquivos estão lá, o tamanho e até quando, com o botão **Apagar de
  lá**. O comando `aliado biblioteca arquivos` lista, e com `--apagar --env-file .env` apaga.
- Sem o registro (uso direto do adaptador), o PDF segue dentro do pedido, até cerca de 12 MB.

### Documentos fixados na conversa

- Um arquivo solto na conversa, ou anexado pelo clipe, entra na biblioteca, como antes, e fica fixado
  naquela conversa: vai inteiro em todas as perguntas dela, com a biblioteca ligada ou não.
- Os fixados aparecem em etiquetas acima da caixa de mensagem, com o "×" para soltar. Um documento da
  biblioteca pode ser fixado pelo painel de documentos ou pela janela de fontes.
- Uma conversa fixa até 12 documentos. Se um fixado é grande demais para o teto, vão os blocos em volta do
  que a busca achar nele.

### Na tela

- **Modo de leitura,** ao lado de "Usar biblioteca": "Documentos inteiros" (padrão) ou "Só trechos", o modo
  anterior. **Teto:** 150 mil, 400 mil (padrão) ou o limite do modelo (900 mil). As duas escolhas ficam no
  navegador.
- Com "Só trechos" e sem documentos fixados, o pedido é o mesmo de antes do lote. Com documentos fixados, eles
  vão inteiros e a busca segue por trechos.
- Cada resposta mostra "leu 9 documentos (7 inteiros e 2 em parte) · 512 páginas"; o link abre a lista do que
  foi lido, com as páginas de cada documento e o que não coube.
- **A aba Biblioteca saiu.** O botão **Documentos**, na caixa de mensagem, abre um painel com a lista e, por
  documento: fixar na conversa, abrir o original, a ficha, as figuras e apagar. A visualização da extração em
  Markdown saiu da tela; a rota continua.

### Correções depois do primeiro uso (04/10)

O pesquisador usou a tela antes de reiniciar o programa e viu dois problemas. Veja a
[validação](../migracao/validacao-lote-30.md).

- **O documento citado na mensagem fica na consulta.** "E o pertile?" virou "autoencoder and percentil
  percentile thresholding" na consulta reescrita, e a busca não trouxe o documento de Pertile. Agora, quando a
  mensagem cita um documento pelo autor, pelo título ou pelo DOI e a consulta reescrita o perde, a referência
  dele é acrescentada à consulta (`agent._keep_named`). Vale nos dois modos de leitura, e a janela de fontes
  mostra a consulta como ficou.
- **Aviso de reinício.** A página é lida do disco a cada carga, e o programa em execução só muda quando é
  reiniciado. Com a página nova e o programa antigo, a tela mostrava "Documentos inteiros", e as respostas
  saíam por trechos, sem aviso. Agora o estado informa a hora em que o programa começou, e a página avisa
  quando o arquivo dela é mais novo, ou quando o programa nem conhece a leitura integral. Nesse caso os
  controles de leitura somem.

## O que mudou em relação ao plano aprovado

O plano foi aprovado antes das medições. Cinco pontos mudaram, todos por causa do que foi medido:

| No plano | Como ficou | Por quê |
|---|---|---|
| O texto guardado de cada página segue junto com o PDF | Só as primeiras palavras de cada página | O texto repetido seria dois terços do custo: num artigo de 16 páginas, 9 mil tokens do PDF e 18,5 mil do texto. No piloto, com o teto de 150 mil, o modelo leu de 234 a 242 páginas sem o texto e de 89 a 97 com ele, e a tabela pedida numa norma ficou de fora na variante com o texto. As citações diretas conferidas apontaram todas a página certa. |
| Blocos em volta das páginas achadas | Blocos fixos de 10 páginas | Recortes diferentes a cada pergunta teriam de ser enviados de novo (de 20 a 96 MB por pergunta). |
| PDF pelo serviço de arquivos só acima de 20 MB | Todo PDF pelo serviço de arquivos | As leituras do piloto tinham de 18 a 93 MB; o envio é feito uma vez e reaproveitado. |
| Documentos na ordem da busca até o teto acabar | Todo documento da busca recebe um mínimo | Sem o mínimo, numa das 12 perguntas o documento esperado ficava de fora. |
| A lista do painel mostra as páginas de cada documento | Mostra a referência, o arquivo, o estado, a versão e a data | A contagem de páginas pede a leitura da extração de cada documento a cada abertura do painel. |

## Limites assumidos

- **O tempo de resposta varia muito.** No piloto, de 31 segundos a 12 minutos, sem relação com o tamanho do
  pedido: o mesmo pedido levou 94 segundos numa vez e 12 minutos em outra. O modo de trechos levou de 7 a
  13 segundos.
- **O custo por pergunta sobe de cerca de 11 mil para 150 a 390 mil tokens de entrada,** e cada pergunta da
  conversa lê os documentos de novo. Quando o pedido se repete igual, o Gemini reaproveita o que já leu.
- **Os documentos lidos ficam no Google por até 48 horas,** até serem apagados pelo botão ou pelo comando.
- **A busca continua escolhendo.** Um documento que a busca não traz não é lido, a menos que esteja fixado. De
  um livro, só os blocos escolhidos são lidos, e a resposta deve dizer isso.
- **A consulta reescrita pode trocar outras palavras da mensagem.** Só o documento citado é garantido na
  consulta; o resto continua como o modelo mais barato escreveu.
- **Nenhuma resposta percorre a biblioteca inteira.** "Há alguma literatura sobre X?" é respondida com os
  documentos que a busca trouxe. Uma contagem exata do termo em todos os documentos não foi feita neste lote.
- **O modelo pode citar a página errada** ou ler mal uma figura. A conferência do código garante que a página
  citada foi enviada; ela não prova que a afirmação está nela.
- **O teto é uma estimativa.** No piloto, o uso real ficou de 2% a 5% abaixo dela.
- **Com a busca na web ligada,** a leitura segue por trechos, e os fixados não são enviados; a resposta avisa.
- **A busca não ficou mais rápida:** a seleção leva de 5 a 7 segundos por pergunta, antes da chamada ao modelo.
- **Só o Gemini.** O adaptador da OpenAI não recebe documentos.

## Fora do escopo

- Busca mais rápida e a consulta reescrita do chat.
- Leitura integral junto com a busca na web.
- Ler a biblioteca inteira de uma vez, e outro provedor além do Gemini.
- Fórmulas: o modelo passa a vê-las na página, mas nada é conferido.

## Critérios de aceitação

- **Testes sem rede:**
  - a regra do teto: fixados primeiro, mínimo por documento, limite por documento, sobra de volta, e o teto
    nunca é passado;
  - documento pequeno inteiro, documento grande em blocos fixos, blocos vizinhos, o que não coube;
  - o pedido: uma mensagem por documento, o PDF, a lista das páginas com o identificador, as regras, os
    documentos antes da conversa, e o modo de trechos igual ao de antes;
  - citações: identificador de página aceito, identificador inventado bloqueia, fixados sem busca, fixados
    junto com trechos;
  - adaptador: PDF só em mensagem do usuário de pedido multimodal, envio pelo serviço de arquivos,
    reaproveitamento sem ler o documento de novo, prazo, apagar, e falha do serviço;
  - servidor: modo, teto, fixados, a web, e a rota do serviço de arquivos;
  - o documento citado na mensagem e perdido na consulta reescrita volta a ela;
  - o estado informa a hora de início, e a página traz o aviso de reinício.
- **Piloto pago,** até 30 chamadas ao Flash e 5 milhões de tokens: 12 perguntas nos dois modos, com tokens,
  tempo, documento e página citados, e relatório para o pesquisador.
- **No navegador,** num servidor de teste com modelo simulado: fixar e soltar, envio que fixa, os modos, o
  teto, o painel de documentos e a janela de fontes, em tela larga e estreita.
