# Validação do lote 61 — o intervalo de páginas abreviado nas citações

Data: 23/10/2026. Escopo na [spec 0061](../specs/0061-intervalo-abreviado.md). Sem commit. Nenhum modelo foi chamado.

| Conferência | Resultado |
|---|---|
| O teste do BIB-05 antes da mudança | os 2 casos válidos da forma abreviada falharam; os 3 que devem reprovar e os 6 da forma inteira passaram |
| O teste do BIB-05 depois da mudança | 11 passando |
| Os testes do chat: biblioteca, leitura, trechos, provedor local, specs, isolamento, contratos e gateway | 133 passando |
| A bateria rápida (`ferramentas/bateria.py --rapida`) | 36 grupos e 835 testes passando (eram 830, mais os 5 casos novos), nenhum ignorado; 112,6 s |
| Ruff | sem apontamentos |

Os testes com os dados reais não rodaram: o lote não toca a ciência.

**O que não foi conferido:** se, na P2 de 22/10, as 8 páginas estavam todas entre as enviadas. Só os identificadores
citados ficam no registro da medição, e não os enviados. Se faltar alguma, a marca continua reprovando, como manda o
BIB-05.
