# Lote 15 — avaliação M13 do Denso × AE-LSTM

Terceiro lote do experimento de detecção no [roteiro da v0](../roteiro-v0.md), autorizado em
27/09/2026. É a abertura do teste saudável e dos ensaios com falha, com as escolhas de treino
e de avaliação congeladas antes. A partir daqui, o teste está **consultado**: pelo M14,
qualquer mudança posterior de protocolo exige avaliação independente.

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Épocas | A validação decide a parada (paciência 20, teto de segurança de 2.000). Nova rodada canônica `gpvs-modelos-002`; ver a revisão na [spec 0014](0014-autoencoders-limiar.md). |
| Regra de alarme | **3 janelas seguidas** acima do limiar (no mínimo cerca de 60 ms). Grade m ∈ {1, 2, 3, 5} só relatada. |
| Falsos alarmes | Contados no teste saudável (5,3 s) e no pré-falha dos 14 ensaios (47 s), **separados**, mais o limite superior dos 52 s juntos. |
| Métricas | **Principais:** falsos alarmes por hora com limite superior, ensaios detectados, atraso em ms, sensibilidade e especificidade por janela. **Secundárias, descritivas:** precisão, F1, acurácia balanceada, MCC, AUC-ROC e AUC-PR. |
| Incerteza | Bootstrap em blocos de 12 janelas para as proporções; limite exato de Poisson para as contagens de alarme. |
| Sementes | A 42 como referência, com a faixa das 5 ao lado. |
| Comparação | Diferença Denso − AE-LSTM pareada por ensaio, com bootstrap sobre os ensaios e o sinal nas 5 sementes. Conclusão separada por objetivo (menos falsos alarmes, mais falhas detectadas, detecção mais rápida), **sem vencedor geral** (M13). |

## Escopo implementado

- `aliado.science.detection.metrics`, só com numpy:
  - `alarm_starts` e `first_alarm`: a m-ésima janela seguida dispara, e um novo alarme exige voltar abaixo do limiar.
  - `window_metrics`: as métricas por janela da origem, sem scikit-learn, com a mesma curva PR.
  - `block_bootstrap_indices` e `proportion_interval`: blocos móveis de Künsch (1989).
  - `poisson_upper`: limite unilateral exato de Garwood (1936), que com zero eventos é a regra do três.
  - `paired_interval` e `verdict`.
- `aliado.science.detection.evaluation`:
  - `load_training` confere o hash da configuração e de cada peso.
  - `score_all` exige os mesmos hashes de dados e a mesma divisão do treino. Pontua o teste saudável por ensaio e cada ensaio com falha inteiro; no AE-LSTM, a sequência só repete a 1ª janela no início do trecho.
  - `run_metrics`:
    - a detecção começa a contar na janela de transição;
    - o atraso vai do meio nominal do registro até o fim da janela que completa a confirmação;
    - a janela de transição fica fora das métricas por janela.
  - `summarize` e `export_evaluation` geram `configuracao.json` (com a data da consulta), `relatorio.json`, `relatorio.md`, `metricas_por_ensaio.csv` e `escores.npz`.
- `EvaluationConfig` congelada com hash: m = 3, a grade {1, 2, 3, 5}, bloco 12, 20.000 reamostragens e semente 20260927.
- Comando: `aliado ciencia avaliar-gpvs --modelos <rodada de treino> --saida <pasta nova>`.

## Critérios de aceitação

- Conferência com a origem (separação 2, 150 épocas, semente 42): os escores das 14.064 janelas da E3 e as 8 métricas por janela dos 28 pares de modelo e ensaio coincidem.
- Pesos ou configuração alterados são recusados, e dados com outros hashes ou outra divisão também.
- Os testes cobrem:
  - a regra de alarme no exemplo dos 8 ciclos;
  - as métricas calculadas à mão;
  - a regra do três;
  - o bootstrap em blocos, reprodutível e mais largo numa série correlacionada;
  - o pareamento e a leitura;
  - a exportação e o comando;
  - a conferência real, pulada sem `data/gpvs/`.
- A suíte completa e o Ruff passam.
