# Biblioteca documental local

A biblioteca aceita somente arquivos PDF, Markdown e JSON explicitamente
selecionados. Na interface, os documentos entram arrastados para a conversa ou pelo
clipe, na biblioteca `data/bibliotecas/principal`, e ficam fixados naquela conversa
(lote 30). O botão **Adicionar documento**, no painel **Documentos**, põe na biblioteca
sem fixar. Os comandos abaixo fazem o mesmo pela linha de comando.

## Preparação

Instale o extra `knowledge`: `python -m pip install -e ".[knowledge]"` no ambiente
virtual. O download do encoder é explícito:

```powershell
.\.venv\Scripts\python.exe -m aliado biblioteca preparar-modelo
```

O encoder fica em `data/models/minilm`, fora do Git. A instalação local de OCR fica
em `data/tools/tesseract`; português e inglês foram preparados nesta máquina.
Em outra máquina, instale o [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html)
e os idiomas `por`/`eng`. `AL_IADO_TESSERACT_CMD` seleciona o executável e
`AL_IADO_EMBEDDINGS_DIR` seleciona os arquivos do encoder. Esses caminhos são
relativos ao diretório de execução; use caminhos absolutos fora da pasta do projeto.
O CLI documental usa variáveis do processo; não procura arquivos `.env`.

## Uso

```powershell
.\.venv\Scripts\python.exe -m aliado biblioteca adicionar "C:\caminho\referencia.pdf" --biblioteca data/bibliotecas/mestrado
.\.venv\Scripts\python.exe -m aliado biblioteca listar --biblioteca data/bibliotecas/mestrado
.\.venv\Scripts\python.exe -m aliado biblioteca buscar "tempo médio de reparo" --biblioteca data/bibliotecas/mestrado
.\.venv\Scripts\python.exe -m aliado biblioteca verificar --biblioteca data/bibliotecas/mestrado
.\.venv\Scripts\python.exe -m aliado preparar "Explique o tempo médio de reparo" --biblioteca data/bibliotecas/mestrado
```

`preparar` mostra o pedido sem enviá-lo. `perguntar` usa as mesmas opções e exige
provedor, alias e configuração. Pela linha de comando, somente os trechos recuperados são
incluídos na consulta; OCR, extração e embeddings não enviam o acervo a uma API. Duas coisas
enviam mais que trechos, e só na interface ou por comando próprio:
- a descrição das figuras e tabelas pelo modelo (lote 29) envia páginas como imagem, quando você pede;
- a leitura de páginas e de documentos inteiros (lotes 30 e 31) envia os PDFs das páginas escolhidas. Veja
  "Leitura dos documentos", abaixo.

Cada biblioteca contém `originals/`, `extracted/` e `catalog.sqlite3`. O nome do
arquivo identifica o documento por padrão; `--titulo` permite um identificador
lógico estável. Reutilize-o quando uma edição nova tiver outro nome de arquivo.
Conteúdo idêntico não cria duplicata. Conteúdo alterado do mesmo documento cria
uma versão nova; a busca consulta apenas a versão mais recente e o processamento
ativo. Uma versão nova ilegível não faz a versão antiga reaparecer silenciosamente.

`--reprocessar` refaz a extração da mesma versão, mantendo os artefatos anteriores.
`--forcar-ocr` também reprocesa e aplica OCR a todas as páginas, útil quando um PDF
mistura cabeçalho textual e corpo digitalizado. Por padrão, OCR atua em páginas
com menos de 20 caracteres alfanuméricos extraídos ou caracteres de substituição.
Essa heurística não identifica toda perda de conteúdo. Há limite de 100 MiB por arquivo.

## Estados e referências

- `ready`: processamento concluído sem falhas detectadas; não é revisão humana.
- `partial`: trechos disponíveis, mas páginas ou OCR têm problemas sinalizados.
- `failed`: nenhum trecho indexável. O original e os textos já extraídos ficam
  preservados; corrija a causa e reprocesse.

Adição parcial/falha e verificação com problemas retornam código de saída 2.
O OCR registra sua confiança média, que não é probabilidade de correção da fonte.
Página significa posição física no PDF, iniciando em 1; pode diferir da numeração
impressa. Markdown usa linhas, JSON usa caminhos JSON Pointer. Não se inventam
autor, DOI ou título bibliográfico a partir do nome do arquivo.

## Ficha do documento

Desde o lote 19, cada documento pode ter uma ficha com título, autores, ano e DOI.
- Na interface, o modelo mais barato lê o começo do texto extraído ao indexar. Para
  os documentos antigos, há o botão **Completar fichas** no painel **Documentos**.
- O código confere cada campo no próprio texto: título e sobrenomes precisam
  aparecer nele, o DOI precisa ter o formato certo e o ano precisa ser plausível. O
  que não passa fica em branco.
- A ficha fica marcada "inferida" até ser editada no painel **Documentos**. A edição vale
  sobre a inferida, que continua guardada.
- A ficha entra no catálogo enviado ao modelo e nas fontes da resposta, como
  "Baschel et al., 2018". Uma pergunta que cita o autor, o título ou o DOI puxa os
  trechos daquele documento.
- Uma falha do provedor não grava nada, e o documento continua pendente para uma
  nova tentativa.

## Apagar um documento

Desde o lote 22, o botão **Apagar** tira um documento de vez. Desde o lote 30, ele fica no painel
**Documentos**, aberto pelo botão ao lado de **Usar biblioteca**:
- saem todas as versões do título, as extrações, os trechos do índice e a ficha;
- o original só sai quando nenhum outro documento o usa;
- as anotações que o agente deduziu do documento são revogadas e ficam no histórico
  da memória; as anotações do pesquisador não mudam;
- não há cópia nem lixeira, e a janela de confirmação avisa quantas anotações serão
  revogadas;
- enquanto um envio ou as fichas estão em andamento, a biblioteca pede para esperar.

Respostas antigas que citavam o documento continuam no histórico; abrir a fonte mostra
que ele não está mais na biblioteca.

`verificar` confere hashes dos originais e artefatos, trechos, vetores e índice
lexical. Processamentos antigos continuam auditáveis. Fórmulas, tabelas, colunas
e figuras não são interpretadas com garantia; compare com o original.

## Limpeza, trechos por frase e figuras

Desde o lote 29, o que vira trecho de busca passa por três cuidados. O texto guardado de cada
página continua inteiro, e a extração anterior fica preservada.

- **Limpeza (PDFs):**
  - as linhas de cabeçalho e de rodapé que se repetem nas bordas das páginas saem dos trechos: as que
    aparecem em 30% das páginas ou mais, e as que trazem o número da página;
  - o sumário e a lista de referências ficam marcados no local ("página PDF 5 · sumário",
    "página PDF 14 · referências") e fora da busca comum. Eles voltam quando a pergunta os pede por
    palavra (sumário, capítulos, referências, bibliografia, cita);
  - um trecho repetido palavra por palavra no mesmo documento entra uma vez.
- **Trechos por frase:** frases inteiras até 110 tokens. Uma tabela ou lista sem pontuação é cortada
  nas quebras de linha. A legenda de figura ou de tabela começa sempre um trecho novo.
- **Texto dentro das figuras:** nas páginas com imagem embutida, o Tesseract lê o recorte de cada
  figura, e o que a página ainda não tem entra como trecho próprio ("página PDF 3 · texto das
  figuras"). Roda no envio, sem custo. Sem Tesseract, a etapa é pulada.
- **Descrição pelo modelo:** na ficha do documento, o quadro **Figuras e tabelas** mostra quantas
  páginas têm figura, desenho, tabela ou legenda, e o botão **Descrever figuras e tabelas** envia
  cada uma ao modelo, como imagem, numa chamada por página.
  - O aviso antes de enviar diz o número de chamadas, o modelo e a estimativa de tokens. Dá para
    parar no meio: cada página é gravada ao chegar.
  - O código confere o que o modelo propõe: o rótulo ("Figure 2") e a legenda só ficam se estiverem
    no texto da página.
  - Cada figura ou tabela tem o seu local ("página PDF 3 · Figure 2") e é marcada como descrição
    automática. Na busca, a legenda achada no texto traz a descrição junto. As descrições não entram na
    parte da busca que compara palavras: concorrem pelo significado.
  - A resposta trata a descrição como descrição: sem aspas, e com o aviso de conferir no original.
  - O modelo é o Flash; `AL_IADO_FIGURE_MODEL=flash_lite` troca pelo mais barato.

```powershell
.\.venv\Scripts\python.exe -m aliado biblioteca reindexar --biblioteca data/bibliotecas/principal
.\.venv\Scripts\python.exe -m aliado biblioteca figuras --biblioteca data/bibliotecas/principal
.\.venv\Scripts\python.exe -m aliado biblioteca figuras --biblioteca data/bibliotecas/principal --documento ID --executar --env-file .env
```

- **`reindexar`** refaz os trechos a partir do texto de página já guardado: não lê o arquivo de novo,
  não repete o reconhecimento de texto e aproveita o vetor dos trechos que não mudaram. Com
  `--documento`, só um. Serve para uma biblioteca indexada antes do lote 29.
- **`figuras`** sem `--executar` só mostra as páginas por descrever e a estimativa de tokens; nada é
  enviado. Com `--executar`, chama o modelo (`--modelo flash` ou `flash_lite`) e reindexa o
  documento no fim. `--paginas N` limita as páginas por documento.

A descrição é feita por um modelo e pode errar: confira a figura no original, pelo link
**Abrir página** da janela de fontes.

## Leitura dos documentos

Desde o lote 31, o padrão é a **Leitura automática**: antes de qualquer chamada paga, um roteador local
decide o que a mensagem precisa, e a leitura começa pelo degrau mais barato. O seletor ao lado de **Usar
biblioteca** fixa um degrau.

| Degrau | O que vai ao modelo | Quando, na leitura automática | Tokens de entrada |
|---|---|---|---:|
| Sem a biblioteca | Nada dos documentos | Conversa, memória, tarefa, resultados da pesquisa | menos de 1 mil na conversa |
| **Só trechos** | Até 10 trechos da busca, com os vizinhos da página | Consulta de texto | 5 a 8 mil |
| **Páginas inteiras** | As 10 páginas mais próximas da pergunta, em PDF | Figura, tabela, gráfico ou fórmula; ou quando os trechos não bastaram | 11 a 12 mil |
| **Documento inteiro** | O documento citado ou fixado, inteiro; os outros, por trechos | A pergunta cita um documento pequeno, ou há um fixado | 11 a 17 mil num artigo |
| **Leitura ampla** | Os documentos que a busca escolher, inteiros | Só por escolha sua | 150 a 400 mil |

- **Subida de degrau:** se a resposta por trechos não cita nenhum documento, a pergunta é refeita com as
  páginas inteiras, desde que as duas chamadas caibam em 30 mil tokens. A tela avisa.
- **Documento citado que é grande** (um livro, uma norma): vão as 10 páginas dele mais próximas da pergunta.
- **Confirmação:** acima de 30 mil tokens estimados, a tela mostra o custo e os documentos e pergunta "Ler
  assim" ou "Responder só com os trechos". Na mesma conversa, a mesma leitura não pergunta de novo. Depois
  de 300 mil tokens no dia, toda leitura acima dos trechos pergunta, toda vez.
- **Ler mais fundo:** o botão sob a resposta refaz a pergunta no degrau seguinte, com o custo estimado.
- **Perguntas já respondidas:** com o mesmo assunto e o mesmo pedido de uma pergunta anterior, o modelo
  recebe aquela troca e até 6 páginas que ela citou, sem nova busca, e escreve uma resposta nova.
- **Contagem exata de termos:** nas perguntas sobre o acervo e nas que citam um documento, o modelo recebe
  em quais documentos e páginas cada termo da pergunta aparece, pelo índice de palavras. Ela não acha
  sinônimos nem traduções.

Medição de 04/10/2026, com as 12 perguntas do piloto do lote 30 pela leitura automática:

| Forma | Tokens de entrada nas 12 | Tempo por pergunta | Documento esperado | Página esperada |
|---|---:|---:|---:|---:|
| Só trechos (lote 30) | 138 mil | 7 a 13 s | 12 de 12 | 5 de 6 |
| Leitura ampla (lote 30) | 3,2 milhões | 31 s a 12,5 min | 12 de 12 | 6 de 6 |
| Leitura automática (lote 31) | 144 mil | 10 a 35 s | 12 de 12 | 6 de 6 |

Nas três perguntas em que os trechos não traziam o dado (as escalas de Colli, a linha do transformador em
Baschel et al. e a tabela dos disjuntores na IEEE 493, de 426 páginas), a leitura automática trouxe a
resposta completa, como a leitura ampla.

Uma pergunta já respondida parte das páginas que a resposta anterior citou. Se aquela resposta ficou
incompleta, a nova também fica: refazer a pergunta em seguida, na mesma conversa, ou **Ler mais fundo** fazem
uma leitura nova.

### Leitura ampla (lote 30)

A busca escolhe os documentos, e o modelo recebe o PDF das páginas inteiras, com figuras, tabelas e
fórmulas. Como ela escolhe o que vai:

- A busca pede 20 resultados, e deles sai a ordem dos documentos.
- Um documento de até 40 páginas vai inteiro ou fica de fora. Um documento maior é dividido em blocos fixos
  de 10 páginas, e vão os blocos em que a busca achou algo e os vizinhos.
- O **teto** limita o que vai por pergunta: 150 mil tokens, 400 mil (padrão) ou o limite do modelo. Uma
  página de PDF custa 560 tokens, mais a linha dela na lista.
  - Os documentos fixados na conversa entram primeiro.
  - Todo documento que a busca trouxe recebe pelo menos o bloco do melhor trecho achado.
  - Depois cada um cresce até um quarto do teto, na ordem da busca, e a sobra volta para quem ficou cortado.
- Com o teto de 150 mil, o piloto leu de 234 a 242 páginas por pergunta; com o de 400 mil, de 637 a 642.

O que o modelo recebe de cada documento: uma frase com o que foi enviado e o que ficou de fora, o PDF das
páginas e a lista delas, com um identificador por página e as primeiras palavras de cada uma. A resposta cita
a página, e a janela de fontes mostra o texto extraído dela e o link **Abrir página**. O texto guardado
inteiro só segue quando não há PDF para anexar (Markdown e JSON).

**Documentos fixados:** um arquivo solto na conversa fica fixado nela e vai inteiro em todas as perguntas,
com a biblioteca ligada ou não. As etiquetas acima da caixa de mensagem mostram os fixados; o painel
**Documentos** e a janela de fontes também fixam. Uma conversa fixa até 12 documentos.

**O que fica no Google:** os PDFs lidos sobem para o serviço de arquivos do Google, que os guarda por até 48
horas. Cada um sobe uma vez e serve às perguntas seguintes enquanto durar. O registro local fica em
`data/uso/arquivos-google.json`, sem o conteúdo. O painel **Documentos** mostra quantos arquivos estão lá e
tem o botão **Apagar de lá**; pela linha de comando:

```powershell
.\.venv\Scripts\python.exe -m aliado biblioteca arquivos
.\.venv\Scripts\python.exe -m aliado biblioteca arquivos --apagar --env-file .env
```

**Custo e tempo,** medidos no piloto de 03/10/2026 com 12 perguntas:

| Modo | Tokens de entrada por pergunta | Tempo |
|---|---:|---:|
| Só trechos, com a parte fixa de antes do lote 31 | cerca de 11 mil | 7 a 13 s |
| Leitura ampla, teto de 150 mil | cerca de 150 mil | 31 s a 9 min |
| Leitura ampla, teto de 400 mil | cerca de 385 mil | 45 s a 12,5 min |

O tempo não acompanha o tamanho: o mesmo pedido levou 94 s numa vez e 12,5 min em outra. Cada pergunta da
conversa lê os documentos de novo; quando o pedido se repete igual, o Gemini reaproveita o que já leu.

Limites: a busca continua escolhendo os documentos; de um livro, só os blocos escolhidos são lidos, e a
resposta deve dizer isso; com **Buscar na web** ligada, a leitura segue por trechos e os fixados não são
enviados.

## Busca e limites

O [MiniLM multilíngue](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
usa a revisão `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, ONNX quantizado, 384
dimensões, média dos tokens e normalização. Os hashes dos dois artefatos são
conferidos. Desde o lote 29, os trechos são frases inteiras, com até 110 tokens e sem
sobreposição, sem atravessar seção ou página. Um documento indexado antes continua com as
fatias de 110 tokens e sobreposição de 20 até ser reindexado, e os dois convivem na busca.
Consultas longas combinam os vetores de suas fatias.

BM25/FTS5 e cosseno são combinados por soma de posições recíprocas, constante 60.
Os parâmetros abaixo são do lote 19 e foram fixados antes da medição:
- a busca por palavras ignora palavras vazias em português e em inglês ("de",
  "segundo", "the") e pesa metade da busca por significado;
- um documento citado na pergunta pela ficha forma uma terceira lista, com peso 1;
- cada documento ocupa no máximo 2 dos resultados (4 se for citado), e o limite só
  é passado quando faltam candidatos de outros documentos.

No chat, desde o lote 22, a busca não usa a mensagem como veio.
- O modelo mais barato a reescreve numa consulta completa, olhando as 4 últimas mensagens da conversa.
- O assunto vem da conversa, para que "a definição" diga de quê.
- As siglas vão por extenso, e os termos principais vão em português e em inglês.
- A consulta só escolhe os trechos, sem responder à pergunta, e a janela de fontes a mostra.
- No modo **Só trechos**, o chat recebe até 10 trechos. Nas leituras por páginas e por documentos, a consulta escolhe as páginas e os documentos. Quando documentos diferentes tratam do pedido, a resposta mostra a opção de cada fonte.
- Se a chamada falhar ou a consulta não trouxer trechos, vale a regra anterior: pela própria mensagem, e, nas de até 6 palavras ou sem resultado, junto com a pergunta anterior.

Sem coincidência lexical nem citação, exige-se cosseno de pelo menos 0,30: é uma
heurística de recuperação, não um limiar científico. Índices de processamento antigo
não entram no ranqueamento lexical ativo. Os vetores ficam no SQLite, e a comparação
é exaustiva, adequada ao acervo atual.

A qualidade é medida com perguntas de referência, cada uma com o documento
esperado, escolhido pelo conteúdo. As perguntas ficam fora do Git, porque descrevem
o acervo:

```powershell
.\.venv\Scripts\python.exe -m aliado biblioteca avaliar --biblioteca data/bibliotecas/principal --saida data/resultados/busca-001
```

O relatório dá, por idioma, por tipo de pergunta e por cruzamento de idioma, o
número de acertos entre os 6 resultados, a posição do primeiro acerto (MRR) e os
documentos distintos. Com `--reescrever --env-file .env`, cada pergunta passa antes
pela consulta reescrita, como no chat, e o relatório guarda a consulta usada. São 16
chamadas ao modelo mais barato, e cada uma entra no registro de uso.

A resposta recebe fontes locais reais. O verificador bloqueia ausência de
identificadores e identificadores desconhecidos; **não prova** que o texto gerado
interpretou corretamente a fonte nem impede toda referência inventada em prosa.
Desde o lote 18, sem trecho recuperado o modelo é chamado assim mesmo, com o aviso de
que nada foi encontrado, e a resposta sem citação aparece marcada. Documentos são dados de consulta,
não instruções; o agente não possui ferramentas autônomas de execução neste fluxo.

O isolamento atual é por diretório escolhido pelo usuário, não uma fronteira de
autenticação entre contas. Não exponha esta CLI como serviço multiusuário sem a
camada de acesso a ser definida no módulo web. Sessões e triagem privada não são acervo.
