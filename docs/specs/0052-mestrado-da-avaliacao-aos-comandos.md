# Spec 0052 — o mestrado da avaliação aos comandos em pastas

Estado: feito em 22/10/2026, com commits locais autorizados pelo pesquisador no plano de 21/10; push e tag ficam com
ele.

## Propósito e decisões

A segunda parte do mestrado em pastas com nomes em português, na ordem do método:
5. `avaliacao/`: a avaliação;
6. `inicio_das_falhas/`: o início das falhas;
7. `reanalise/`: a reanálise;
- `comandos/`: os comandos do terminal.

`evaluation.py`, `onset.py`, `reanalysis.py` e `commands.py` mudaram de lugar, e os três primeiros foram repartidos. As
funções têm os nomes de antes.

**As exceções, decididas no plano de 21/10:**
- **A pasta da avaliação oficial (`gpvs-avaliacao-001`):** virou `avaliacao/oficial.EVALUATION`, só com a biblioteca
  padrão. A reanálise e o terminal já a usam; o experimento e os resultados passam a usá-la no lote 53.
- **`onset.CLASSES`:** nunca era usada e saiu.

## Requisitos vivos

Nenhum muda.

## Implementação

**Dois commits, para o Git seguir o histórico:**
1. **A mudança de lugar**, com os arquivos inteiros:
   - `evaluation.py` → `avaliacao/resumo.py`;
   - `onset.py` → `inicio_das_falhas/estimativa.py`;
   - `reanalysis.py` → `reanalise/reanalise.py`;
   - `commands.py` → `comandos/terminal.py`.
2. **A divisão:**

| Pasta | Arquivos | O que tem |
|---|---|---|
| `avaliacao/` | `configuracao.py` | `EvaluationConfig` |
| `avaliacao/` | `treino_congelado.py` | `TrainedDetectors`, `load_thresholds` e `load_training` |
| `avaliacao/` | `pontuacao.py` | `segment_errors`, `score_segment` e `score_all` |
| `avaliacao/` | `decisao.py` | `run_metrics`: alarmes falsos, detecção e métricas por janela |
| `avaliacao/` | `incerteza.py` | os intervalos e a comparação pareada |
| `avaliacao/` | `resumo.py` | `summarize` |
| `avaliacao/` | `relatorio.py` | o Markdown |
| `avaliacao/` | `artefatos.py` | `export_evaluation` |
| `avaliacao/` | `oficial.py` | `EVALUATION` |
| `inicio_das_falhas/` | `pontos_de_mudanca.py` | `pelt`, `penalty` e `robust_z` |
| `inicio_das_falhas/` | `estimativa.py` | `OnsetConfig`, `choose_penalty`, `classify` e `estimate` |
| `reanalise/` | `reanalise.py` | `relabel`, `reanalyze`, `load_scores` e `run` |
| `reanalise/` | `relatorio.py` | o Markdown e o aviso |
| `reanalise/` | `artefatos.py` | `export_reanalysis` |
| `comandos/` | `terminal.py` | `add_commands` e os 4 comandos |

**As chamadas por módulo:** passaram a citar o arquivo novo de cada nome.
- `onset.NOME` virou `estimativa.NOME` ou `pontos_de_mudanca.NOME`.
- `reanalysis.NOME` virou `reanalise.NOME`.

## Aceitação

- A bateria completa passando, com os testes com os dados reais: a avaliação de 27/09 e a reanálise de 30/09
  reproduzidas.
- A equivalência sem nenhuma diferença contra a referência do lote 49.
- NUC-01, NUC-02, NUC-04 e Ruff.
- As conferências extras: importações, pastas, caminhos antigos, comandos e wheel.
