# Spec 0054 — a identidade e o contrato da rodada

Estado: feito em 22/10/2026, com commit local autorizado pelo pesquisador no plano de 21/10; push e tag ficam com ele.

## Propósito e decisões

É o lote 49 do relatório em LaTeX de 21/10 (regra 2 da seção 7.1: nenhum valor padrão silencioso), com as correções
da [conferência](../revisao/2026-10-21-relatorio-latex-conferido.md). Cada rodada nova passa a gravar:
- **a identidade:** com que código, com que pesos e com que convenção de tempo ela rodou;
- **a matriz de erros por variável:** de onde saem os escores, conferida bit a bit.

Quem lê esses arquivos exige cada campo e nunca supõe o que falta.

**Decisões do plano de 21/10:**
- **O formato:** NPZ com metadados em JSON, e não HDF5. O HDF5 pediria baixar o h5py, e o NPZ com os hashes dá a mesma
  garantia.
- **A convenção de tempo, que já estava no código e agora fica gravada:**
  - a janela é datada pela primeira amostra;
  - a janela i de um ensaio começa na amostra i × 200 do CSV;
  - o alarme fica no fim da janela que completa a confirmação.
- **As rodadas anteriores** (a avaliação de 27/09/2026, a rodada-001 e a rodada-002) não ganham campos inventados. São
  "anteriores ao contrato" e continuam abrindo, comparando e virando PDF.
- **`FORMAT` não muda:** nada o lê, e a comparação de PDFs e JSONs antigos continua funcionando.

**Decisões tomadas na implementação:**
- **A conferência dos escores:** `score_all` não mudou. A avaliação recalcula a matriz à parte (`errors_all`), e os k
  maiores dela precisam dar os escores bit a bit, nos da avaliação e nos da calibração gravados pelo treino. Assim a
  conferência compara duas contas, e não uma conta com ela mesma. O custo é uma passada a mais dos modelos sobre os
  dados, sem treino.
- **O código da matriz em `resultado.json`:** é o do conteúdo (nome, tipo, formato e bytes de cada matriz, na ordem dos
  nomes), e não o do arquivo. O arquivo compactado guarda a hora em que foi gravado, e o hash dele mudaria a cada
  rodada, mesmo com as mesmas matrizes.
- **Os 5 pontos que tratam `ValueError` de forma ampla** foram conferidos um a um. O erro de contrato é um
  `ValueError`, e a mensagem dele aparece onde ele pode surgir:
  - o "Preparar" do explorador (`tela/rotas.py`) já mostra a mensagem do erro;
  - o PDF na interface e no terminal (`interfaces/web/experiments.py` e `cli.py`) também;
  - a rodada oficial (`rodada/consolidacao.legacy`), os painéis (`tela/rotas.py`), o resumo do chat
    (`resumo_para_o_chat/blocos.py`) e `same_parameters` (`experiments/__init__.py`) não leem nenhum arquivo do
    contrato. Por isso, nada foi acrescentado neles.

## Requisitos vivos

- **EXP-13 (novo), em `experimentos.md`:** a identidade e o contrato da rodada, sem valor padrão silencioso.

## Implementação

**Ciência geral, `science/identidade/`** (só a biblioteca padrão, sem domínio):

| Arquivo | O que tem |
|---|---|
| `hashes.py` | `sha256_file` (em blocos de 1 MiB), `config_digest` (as três cópias de `digest()` viraram esta) e `arrays_digest` (o código do conteúdo de matrizes) |
| `contrato.py` | `ContractViolationError` (um `ValueError`), `require`, `check_version` e os textos "anterior ao contrato" e "não gravado" |
| `codigo.py` | `code_version`: o commit do Git e as alterações locais em `src` e no `pyproject.toml`, sempre com um estado explícito |

**As cópias que saíram:**
- `sha256_file` de `base/leitura.py`;
- os `_sha256` de `avaliacao/treino_congelado.py` e de `treino/artefatos.py`;
- os três corpos de `digest()`, nas configurações do treino, da avaliação e do início das falhas;
- o hash do nome do cache do explorador.

Os valores não mudaram: `ExperimentConfig()` continua dando be9e54fa…, `EvaluationConfig()` ce8b06e4… e
`OnsetConfig()` 1510880c….

**Mestrado:**
- **`avaliacao/pontuacao.errors_all`:** a matriz de cada modelo e repetição, na calibração, no teste saudável e nos
  ensaios com falha. É o laço que estava no explorador, com os mesmos nomes de matriz.
- **`avaliacao/artefatos.py`:**
  - `export_evaluation` grava `erros.npz` depois de conferir os escores;
  - os metadados trazem a versão do contrato, as 24 variáveis na ordem, os hashes dos pesos, do treino, da avaliação
    e dos dados, a convenção da janela e os trechos de cada matriz (ensaio, primeira janela e fim);
  - `load_errors` confere cada campo, a ordem das variáveis, a convenção, o nome, o tipo e o formato de cada matriz.
- **`avaliacao/treino_congelado.weight_hashes`:** os hashes dos pesos, lidos do relatório do treino. Servem à
  avaliação e ao explorador.
- **O explorador:**
  - com `erros.npz`, usa a matriz gravada, sem recalcular nem gravar cache;
  - se ela não for da rodada (treino, dados ou pesos diferentes), recusa com o erro de contrato;
  - sem ela, nas rodadas anteriores, segue o cache de antes, com os mesmos nomes de arquivo.
- **A rodada:**
  - `run` registra a versão do código antes de preparar os dados;
  - `collect` recebe a identidade como argumento obrigatório e a grava em `resultado.json`: o contrato, o código, os
    pesos, as variáveis, a janela e o código da matriz;
  - a rodada oficial recebe a marca `{"contrato": null, "estado": "anterior ao contrato"}`.
- **O PDF:** a tabela "Conferência dos arquivos" ganha a versão do programa, os pesos e a matriz de erros, com uma
  nota para cada. Nas rodadas anteriores, as três linhas dizem "não gravado (anterior ao contrato)".

**Testes:**
- `tests/science/test_identidade.py`:
  - os hashes, inclusive num arquivo de mais de 1 MiB;
  - o código das matrizes, igual com o arquivo regravado e diferente com um bit, um tipo ou um formato diferente;
  - o contrato;
  - os cinco estados da versão do código, num repositório temporário.
- `tests/mestrado/test_artefato_de_erros.py`:
  - os três hashes de configuração de antes;
  - a matriz reproduzindo os escores em todo modelo, repetição e k;
  - oito alterações do arquivo recusadas;
  - um escore diferente impedindo a gravação;
  - o explorador sem recalcular e recusando a matriz de outra rodada;
  - as linhas do PDF;
  - com os dados reais, a avaliação de 27/09 e a rodada-002 comparando, com todos os indicadores iguais, e virando
    PDF.
- **A rodada real** de `tests/test_experiments.py` confere a identidade gravada.

## Aceitação

- A bateria completa passando, com os testes com os dados reais.
- A equivalência sem diferença nos arquivos que já existiam; `erros.npz` e a chave `identidade` aparecem à parte, como
  novos.
- NUC-01, NUC-02, NUC-04 e Ruff.
- As conferências extras: importações, pastas, caminhos antigos, comandos e wheel.
