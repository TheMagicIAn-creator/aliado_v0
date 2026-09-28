# Validação do lote 13

Verificação local em **27/09/2026**, Windows/Python 3.12, numpy 2.5.3. Nenhum commit,
push ou PR; nenhuma chamada paga.

## Resultado

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **295 testes passaram** (280 anteriores + 15 novos, um deles com os dados reais). |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| Cópia dos dados | 16 CSVs, 493.425.214 bytes, cada um conferido pelo SHA-256 do manifesto da origem; `data/gpvs/proveniencia.json` registra a cópia. |
| Origem | `mestrado-utfpr` sem alterações (só leitura). |

## Reprodução do contrato antigo

| Grandeza | Origem | AL-IAdo |
|---|---|---|
| Janelas saudáveis (F0L + F0M) | 1.423 | 1.423 (718 + 705) |
| Janelas com falha (F1L–F7M) | 9.391 | 9.391 |
| Treino / validação / calibração / teste | 711 / 209 / 210 / 281 | 711 / 209 / 210 / 281 |
| Estatísticas das 24 variáveis (média, desvio, mínimo, quartis, máximo) | `features_gpvs_stats.csv` | diferença relativa máxima de **6,0 × 10⁻⁷** |

O arquivo de referência foi copiado para `tests/data/gpvs_estatisticas_referencia.csv`.
O teste com os dados reais é pulado em máquinas sem `data/gpvs/`.

Tempo de preparo: 8,7 s na primeira extração e 0,5 s com o cache.

## Achado da verificação do M14

A autocorrelação das variáveis no treino escalado é alta:

| Ensaio | ACF mediana, lags 1 a 5 | Lag em que \|ACF\| < 0,2 em 90% das variáveis |
|---|---|---:|
| F0L | 0,92; 0,85; 0,79; 0,71; 0,63 | 12 |
| F0M | 0,89; 0,77; 0,72; 0,67; 0,60 | 12 |

A separação aprovada (2 janelas) afasta os blocos em 3 janelas. Por este critério, a
separação **não é suficiente**: janelas vizinhas de blocos diferentes continuam
correlacionadas, e o teste saudável pode ficar otimista. Parte da autocorrelação pode
vir de variações lentas das condições de operação, e não só de memória do processo.

Como decidido, a separação foi mantida; o relatório registra o achado. A escolha é do
pesquisador e precisa ser congelada antes da avaliação do lote 15: manter 2 janelas,
ou separar 11 (distância 12), o que descarta 54 janelas saudáveis a mais (9 em cada
uma das 3 fronteiras dos 2 ensaios).

## Observações

- A fronteira de falha continua no meio nominal de cada registro; os CSVs não trazem
  canal de disparo. Cada ensaio com falha tem 1 janela de transição.
- F3M é o ensaio mais curto: 87 janelas de comissionamento, 87 de pré-teste e 174 de pós-falha.
- A trava Git bloqueou de novo um comando só de leitura. A remoção pedida pelo
  pesquisador foi barrada pelo modo automático do Claude Code, por ser mudança na
  configuração do próprio assistente; ela depende de ação do pesquisador.
