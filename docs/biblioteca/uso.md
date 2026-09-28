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
consulta; OCR, extração e embeddings não enviam o acervo a uma API.

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

`verificar` confere hashes dos originais e artefatos, trechos, vetores e índice
lexical. Processamentos antigos continuam auditáveis. Fórmulas, tabelas, colunas
e figuras não são interpretadas com garantia; compare com o original.

## Busca e limites

O [MiniLM multilíngue](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
usa a revisão `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, ONNX quantizado, 384
dimensões, média dos tokens e normalização. Os hashes dos dois artefatos são
conferidos. Trechos têm até 110 tokens, sobreposição de 20, sem atravessar seção
ou página; consultas longas combinam os vetores de seus trechos.

BM25/FTS5 e cosseno são combinados por soma de posições recíprocas, constante 60.
Sem coincidência lexical, exige-se cosseno de pelo menos 0,30: é uma heurística
inicial de recuperação, sem validação no novo acervo, não um limiar científico.
Índices de processamento antigo não entram no ranqueamento lexical ativo.
Os vetores ficam no SQLite; a comparação é exaustiva e adequada ao acervo inicial.
Escala e qualidade deverão ser medidas quando as referências forem fornecidas.

A resposta recebe fontes locais reais. O verificador bloqueia ausência de
identificadores e identificadores desconhecidos; **não prova** que o texto gerado
interpretou corretamente a fonte nem impede toda referência inventada em prosa.
Ausência de trechos evita a chamada ao provedor. Documentos são dados de consulta,
não instruções; o agente não possui ferramentas autônomas de execução neste fluxo.

O isolamento atual é por diretório escolhido pelo usuário, não uma fronteira de
autenticação entre contas. Não exponha esta CLI como serviço multiusuário sem a
camada de acesso a ser definida no módulo web. Sessões e triagem privada não são acervo.
