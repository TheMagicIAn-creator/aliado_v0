# Validação do lote 62 — o lançamento da 0.9.1

Data: 23/10/2026. Escopo na [spec 0062](../specs/0062-lancamento-0-9-1.md). Nenhum modelo foi chamado, e nada em
`data/` foi gravado.

| Conferência | Resultado |
|---|---|
| A versão instalada (`importlib.metadata`) | 0.9.1, depois da reinstalação editável, sem downloads |
| A bateria completa (`ferramentas/bateria.py`), com os testes com os dados reais | **868 passando** (os 863 da 0.9.0 e os 5 do lote 61), nenhum falhou nem foi ignorado; 36 grupos; 18 treinos; 223,5 s; pico de 559,1 MiB |
| A equivalência contra a referência do lote 49 | 28 de 28 arquivos iguais, nenhuma diferença; `erros.npz` e a evidência espectral à parte, como desde os lotes 54 e 55 |
| Toda importação de `aliado…` resolve | sim, em `src`, `tests` e `ferramentas` |
| Pastas vazias ou só com `__pycache__` | nenhuma |
| `ciencia treinar-gpvs --help`, `experimento listar` e `experimento pdf`, numa cópia dos resultados | saída 0 nos três |
| O wheel de uma cópia limpa | 197 arquivos, com os 156 módulos `.py`; 154 importados do próprio wheel, sem erro |
| A seleção rápida do pedido de 22/10 | 44 passando |
| Ruff | sem apontamentos |

## O pacote

- **O arquivo:** `dist/v0.9.1/aliado-0.9.1-py3-none-any.whl`, com 899.427 bytes.
- **SHA-256:** `3d546b1fb17905f0c73ee9579f5b39764b8144a845b29df56b9528a460bd0485`.

## Registros

Ficam fora do Git:
- a bateria, em `tmp/lote-62/bateria/` e `tmp/lote-62/bateria.log`;
- a equivalência, em `tmp/lote-62/equivalencia.log`;
- as conferências extras, em `tmp/lote-62/verificacao.json`.
