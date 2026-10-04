# Biblioteca documental local

A biblioteca aceita somente arquivos PDF, Markdown e JSON explicitamente
selecionados. Na interface, os documentos entram arrastados para a conversa ou pelo
clipe, na biblioteca `data/bibliotecas/principal`. Os comandos abaixo fazem o mesmo
pela linha de comando.

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
provedor, alias e configuração. Somente os trechos recuperados são incluídos na
consulta; OCR, extração e embeddings não enviam o acervo a uma API. A descrição das figuras e
tabelas pelo modelo (lote 29) é diferente: envia páginas como imagem, e só quando você pede.

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
  os documentos antigos, há o botão **Completar fichas** na aba Biblioteca.
- O código confere cada campo no próprio texto: título e sobrenomes precisam
  aparecer nele, o DOI precisa ter o formato certo e o ano precisa ser plausível. O
  que não passa fica em branco.
- A ficha fica marcada "inferida" até ser editada na aba Biblioteca. A edição vale
  sobre a inferida, que continua guardada.
- A ficha entra no catálogo enviado ao modelo e nas fontes da resposta, como
  "Baschel et al., 2018". Uma pergunta que cita o autor, o título ou o DOI puxa os
  trechos daquele documento.
- Uma falha do provedor não grava nada, e o documento continua pendente para uma
  nova tentativa.

## Apagar um documento

Desde o lote 22, o botão **Apagar** da aba Biblioteca tira um documento de vez:
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
- O chat recebe até 10 trechos. Quando documentos diferentes tratam do pedido, a resposta mostra a opção de cada fonte.
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
