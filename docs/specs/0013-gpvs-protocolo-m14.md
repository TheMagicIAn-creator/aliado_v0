# Lote 13 — dados GPVS e protocolo M14 executável

Primeiro lote do experimento de detecção no [roteiro da v0](../roteiro-v0.md),
autorizado em 27/09/2026. Não treina modelos nem escolhe limiares: isso fica para os
lotes 14 e 15.

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Dados | Copiar os 16 CSVs para `data/gpvs/` (fora do Git), conferidos pelo SHA-256 do manifesto de origem. |
| Código | Reescrever de forma modular, sem pandas nem scikit-learn, e **provar** a reprodução numérica do contrato antigo. |
| Dependência temporal | A verificação do M14 **só relata**. A separação de 2 janelas fica como aprovada; mudá-la é decisão do pesquisador antes da avaliação final. |

## Escopo implementado

- `aliado.science.detection.protocol`, geral e só com numpy:
  - `temporal_split`: blocos 50/15/15/20 com fronteiras int(n × fração acumulada) e separação configurável;
  - `robust_center_scale` e `RobustScaler`: mediana e IQR, com piso opcional;
  - `sequences_from_flow` e `sequences_for_blocks`: 8 passos, repetição só no início de cada bloco, sem atravessar blocos;
  - `autocorrelation` e `decorrelation_report`, para a verificação do M14.
- `aliado.science.detection.gpvs`: os 16 ensaios, com colunas, amostragem (~10 kHz) e
  hashes validados; 24 variáveis por ciclo de 50 Hz (200 amostras); fases pré-falha,
  transição e pós-falha com fronteira no meio nominal do registro; divisão por ensaio
  saudável; linha de base por ensaio ajustada no treino (piso de 10% do IQR do treino);
  escala robusta ajustada no treino normalizado; comissionamento de cada ensaio com
  falha pela primeira metade do próprio pré-falha (mínimo de 30 janelas), com a segunda
  metade reservada para os negativos; cache `.npz` invalidado se os hashes mudarem.
- **Sem mapeamento para a FMECA:** o contrato antigo associava falhas do GPVS a grupos
  da FMECA. Pelo M11, as análises são independentes; ficou só a descrição nativa de
  cada falha e se ela é física.
- Comando `aliado ciencia preparar-gpvs --saida <pasta nova>`: gera `relatorio.json`,
  `relatorio.md` e `normalizacao.npz` (linhas de base, piso, escala e índices dos papéis).

## Critérios de aceitação

- Divisão 711/209/210/281, 1.423 janelas saudáveis e 9.391 com falha, iguais à origem.
- As 24 variáveis reproduzem as estatísticas de referência com tolerância relativa de 1e-5.
- Testes sem dados reais cobrem o protocolo, as variáveis em sinais conhecidos, a
  ausência de vazamento do teste para a normalização, o comissionamento, o cache, a
  proveniência e o comando.
- Suite completa e Ruff passam.
