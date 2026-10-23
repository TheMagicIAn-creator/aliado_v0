# Validação do lote 60 — o fechamento da 0.9.0

Data: 23/10/2026. Escopo na [spec 0060](../specs/0060-fechamento-0-9-0.md). Sem commit: o commit, a tag `v0.9.0` e o
push ficam com o pesquisador. Nenhum modelo foi chamado, e nada em `data/` foi gravado.

## Conferências

| Conferência | Resultado |
|---|---|
| A versão instalada (`importlib.metadata`) | 0.9.0, depois da reinstalação editável, sem downloads |
| A bateria completa (`ferramentas/bateria.py`), com os testes com os dados reais | **863 passando**, nenhum falhou nem foi ignorado; 36 grupos; 18 treinos; 226,2 s; pico de 559,3 MiB, na busca |
| O mestrado, com o treino real idêntico ao da origem e a reanálise de 30/09 | 65 passando, 8 treinos, 97,9 s |
| A ciência geral | 128 passando, 6 treinos, 7,0 s |
| Os experimentos, com a rodada real de ponta a ponta | 11 passando, 4 treinos, 36,0 s |
| A equivalência contra a referência do lote 49 | 28 de 28 arquivos iguais, nenhuma diferença; `erros.npz` e a evidência espectral listados à parte, como desde os lotes 54 e 55 |
| O autoteste da equivalência, depois do ajuste da data curta | duas rodadas iguais sem diferença em 30 arquivos; a alterada mostrou a diferença |
| Toda importação de `aliado…` resolve | sim, em `src`, `tests` e `ferramentas` |
| Pastas vazias ou só com `__pycache__` | nenhuma |
| `ciencia treinar-gpvs --help`, `experimento listar` e `experimento pdf`, numa cópia dos resultados | saída 0 nos três; o PDF da rodada atual tem 238.735 bytes |
| O wheel de uma cópia limpa | 197 arquivos, com os 156 módulos `.py`; 154 importados do próprio wheel, sem erro |
| A seleção rápida do pedido de 22/10 | 44 passando |
| Ruff e `git diff --check` | sem apontamentos |

## A primeira equivalência

A primeira comparação acusou um arquivo diferente: o relatório do início das falhas.
- **A causa:** a única diferença era a data curta da rodada, num cabeçalho de coluna: `meio (22/10)` na referência,
  `meio (23/10)` na rodada nova. A ferramenta escondia as datas com ano, mas não essa forma.
- **Por que só agora:** foi a primeira comparação feita em outro dia que não o da referência.
- **Como foi conferido:** numa rodada guardada à parte, a comparação linha a linha não mostrou outra diferença.
- **O ajuste:** a ferramenta passou a esconder a data curta entre parênteses, com dia e mês válidos. As frações como
  `(13/16)` e a data fixa `27/09` continuam aparecendo.
- **O resultado:** a comparação completa, de novo, deu 28 de 28 iguais.

## O pacote

- **O arquivo:** `dist/v0.9.0/aliado-0.9.0-py3-none-any.whl`, com 899.358 bytes.
- **SHA-256:** `ab2025b1eb978dad2c8a46c4c480408a09b9479d01c431df7bfea214aabcee2d`.
- **As notas da versão:** `tmp/releases/v0.9.0.md`.
- **Os wheels anteriores** ficam em `dist/v0.8.0/` e `dist/v0.8.0-fechamento/`.

## Registros

Ficam fora do Git:
- a bateria, em `tmp/lote-60/bateria/` e `tmp/lote-60/bateria.log`;
- a equivalência e o autoteste, em `tmp/lote-60/equivalencia.log` e `tmp/lote-60/autoteste.log`;
- as conferências extras, em `tmp/lote-60/verificacao.json`.
