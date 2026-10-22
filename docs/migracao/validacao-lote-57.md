# Validação do lote 57 — as regras de citação sem identificador de exemplo

Data: 22/10/2026. Escopo na [spec 0057](../specs/0057-regras-sem-exemplo.md). Sem commit: o commit fica com o
pesquisador. Nenhum modelo foi chamado.

## Testes

| Conjunto | Resultado |
|---|---|
| Os arquivos do chat: o provedor local, os trechos, a leitura, as figuras e a biblioteca | 123 passando |
| A seleção rápida do pedido de 22/10: specs, isolamento, contratos, gateway e provedor local | 44 passando (eram 43; mais o teste novo) |
| A bateria rápida (`ferramentas/bateria.py --rapida`) | 36 grupos e 830 testes passando (eram 829), nenhum ignorado; nenhum treino; 128,0 s; pico de 559,1 MiB, na busca |
| Os 33 testes que treinam ou leem os dados reais | não rodaram de novo: o lote 57 não toca a ciência, e eles passaram no lote 56, com o mesmo código dela |

São 863 testes no total, 1 a mais que no lote 56.

## Conferências

| Conferência | Resultado |
|---|---|
| O teste novo contra o texto de antes | reprova as duas regras: as duas tinham `[K1][K2]` |
| Identificadores de exemplo em tudo o que vai ao modelo (código e skills) | nenhum `[K` seguido de letra ou número; ficam o `[K...]` do formato, o `[K]` do catálogo e o `[R1]` dos resultados, que é um bloco real |
| Ruff | passando |

**A medição com o modelo real não foi feita.** Ela depende da autorização do pesquisador, com o número de chamadas
combinado. Sem ela, o lote fica validado sem modelo, como o lote 47.

## Conferência posterior do lote 56

O lote 56 entrou no commit 2155b87, feito pelo pesquisador. A validação e o manifesto dele já estavam nesse commit e
ficam como registro da entrega. Por isso, a conferência feita depois fica registrada aqui.

**O commit:** tem exatamente os 17 arquivos da lista preparada. Os 16 hashes do manifesto conferem com os arquivos.

**Os 12 testes com os dados reais:** rodaram com a autorização do pesquisador, em 22/10/2026, depois do commit. Os 12
passaram, em 100,5 s, com 6 treinos de rede e pico de 510,3 MiB.

| O que o lote 56 mudou | O teste com os dados reais | O que ele conferiu |
|---|---|---|
| A regra do comissionamento, num lugar só | `test_real_onsets_are_the_ones_reported_on_30_09` | os inícios observados das 8 falhas de mudança clara, iguais aos de 30/09 (de 337 a 446 janelas) |
| As janelas por hora, informadas pelo mestrado | `test_real_reanalysis_keeps_detection_and_moves_delay_and_sensitivity` | a reanálise de 30/09 refeita, com a taxa estimada de alarmes falsos do Denso em 19,4 por hora |
| `from_counts` na ciência geral | `test_real_gpvs_reproduces_the_origin_window_metrics` e `test_real_views_repeat_the_official_evaluation` | as métricas por janela da origem e as da avaliação de 27/09, pelas contagens |

Os outros 8 testes também passaram: o treino idêntico ao da origem, os atributos, os exploradores, os painéis, o
resumo do chat, o início nominal, o PDF da rodada oficial e o experimento de ponta a ponta.

**Nada em `data/` mudou.** Os testes leem a base por ligação e copiam os resultados oficiais para pastas temporárias.
Depois da execução, nenhum arquivo de `data/` tinha data de modificação posterior à marca do início.

A saída fica em `tmp/lote-56/dados-reais/`, fora do Git: o registro do pytest e a medição.
