# Spec 0051 — o mestrado do dado ao treino em pastas

Estado: feito em 22/10/2026, com commits locais autorizados pelo pesquisador no plano de 21/10; push e tag ficam com
ele.

## Propósito e decisões

É a primeira parte do mestrado em pastas com nomes em português, na ordem do método:
1. `base/`: a base;
2. `atributos/`: os atributos;
3. `preparo/`: o preparo;
4. `treino/`: o treino.

`gpvs.py` e `training.py` foram repartidos. As funções e as classes têm os nomes de antes.

**As exceções, decididas no plano de 21/10, são cópias de mesmo conteúdo que viram uma só:**
- **A regra do início nominal da falha:** estava em 3 cópias, `evaluation._onset`, `reanalysis._nominal` e
  `summary.onset`. Virou `preparo/inicio_nominal.nominal_onset`.
- **O caminho do cache dos atributos:** estava em 4 cópias. Virou `atributos/cache.features_cache`, só com a
  biblioteca padrão, para o terminal e o experimento não carregarem o numpy.
- **A pasta da base:** estava em 2 cópias. Virou `base/ensaios.DATA_DIR`. O experimento continua declarando
  `DATASET_DIR`, agora igual a ela.

## Requisitos vivos

Nenhum muda. O NUC-04 passa a valer também para estas pastas.

## Implementação

**Dois commits, para o Git seguir o histórico:**
1. **A mudança de lugar** (cd5115d): `gpvs.py` → `preparo/preparacao.py` e `training.py` → `treino/detectores.py`. As
   importações passaram a apontar para o lugar novo, com o mesmo apelido.
2. **A divisão:**

| Pasta | Arquivos | O que tem |
|---|---|---|
| `base/` | `ensaios.py` | os 16 ensaios, as colunas, as falhas, os modos, a amostragem, a janela e a pasta da base |
| `base/` | `leitura.py` | os arquivos, a proveniência, os CSVs e a conferência da amostragem |
| `atributos/` | `variaveis.py` | as 24 variáveis de uma janela |
| `atributos/` | `extracao.py` | a extração por ensaio e o cache |
| `atributos/` | `cache.py` | o lugar do cache |
| `preparo/` | `preparacao.py` | a divisão, a normalização e o comissionamento (`prepare`, `PreparedGPVS`) |
| `preparo/` | `resumo.py` | `report` |
| `preparo/` | `artefatos.py` | `save_normalization` e `export_preparation` |
| `preparo/` | `inicio_nominal.py` | `nominal_onset` |
| `treino/` | `configuracao.py` | `ExperimentConfig` |
| `treino/` | `detectores.py` | `train_detectors`, `training_blocks`, `model_inputs` e `Run` |
| `treino/` | `resumo.py` | `summarize` |
| `treino/` | `relatorio.py` | o Markdown |
| `treino/` | `artefatos.py` | `export_training` e `environment` |

**As chamadas:**
- As chamadas `gpvs.NOME` viraram `<módulo novo>.NOME`, por exemplo `ensaios.HEALTHY`, `preparacao.prepare` e
  `extracao.extract_all`.
- Os apelidos novos não colidem com variáveis locais (conferido antes).

## Aceitação

- A bateria completa passando, com os testes com os dados reais: o treino bit a bit da origem e a avaliação de 27/09
  e a reanálise de 30/09 reproduzidas.
- A equivalência sem nenhuma diferença contra a referência do lote 49.
- NUC-01, NUC-02, NUC-04 e Ruff.
- O terminal e o experimento importando sem numpy nem PyTorch.
- As conferências extras: importações, pastas, caminhos antigos, comandos e wheel.
