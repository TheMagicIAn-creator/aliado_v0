# Validação do lote 56 — as duplicatas da ciência

Data: 22/10/2026. Escopo na [spec 0056](../specs/0056-duplicatas-da-ciencia.md). Sem commit: o commit fica com o
pesquisador.

## Testes

| Conjunto | Resultado |
|---|---|
| Os arquivos afetados (métricas, alarmes, preparo, início das falhas, resultados e reanálise), sem os dados reais | 27 passando; 5 com os dados reais ficaram de fora |
| A seleção rápida do pedido de 22/10 (specs, isolamento, contratos, gateway e provedor local) | 43 passando |
| A bateria rápida (`ferramentas/bateria.py --rapida`) | 36 grupos e 829 testes passando, nenhum ignorado; nenhum treino; 124,5 s; pico de 559,3 MiB, na busca |
| Os testes que treinam só com dados sintéticos | 21 passando, em 35,7 s |
| Os testes com os dados reais | 12, não rodados: eles treinam com a base real e esperam o OK do pesquisador |

São 862 testes no total, 2 a mais que no lote 55: o das métricas de contagem e o da regra do comissionamento.

## Conferências

| Conferência | Resultado |
|---|---|
| Equivalência de uma rodada no GPVS sintético contra a referência do lote 49 | 28 de 28 arquivos iguais, nenhuma diferença, nenhum faltando |
| Arquivos novos, listados à parte | os mesmos do lote 55: `avaliacao/erros.npz` e `evidencia_espectral/evidencia.json` |
| O fator das janelas por hora | `ensaios.WINDOWS_PER_HOUR` = 180.000,0; o produto dá os mesmos bits com 180.000 inteiro, em 10 mil valores |
| Toda importação de `aliado…` resolve | sim, em `src`, `tests` e `ferramentas` |
| Pastas vazias ou só com `__pycache__` | nenhuma |
| Os nomes que saíram (`taxa.WINDOWS_PER_HOUR`, `estimativa.commissioning_windows` e a 2ª `from_counts`) fora dos registros | nenhum; a única definição de `from_counts` é a da ciência geral |
| Ruff | passando |

A equivalência passa pelas três contas: pelo preparo, com o comissionamento; pelas métricas por janela e por tipo de
falha; e pela reanálise, com a taxa de alarmes por hora.

Nenhum arquivo de `data/` foi lido ou gravado. A rodada da equivalência roda numa pasta temporária, com o GPVS
sintético.
