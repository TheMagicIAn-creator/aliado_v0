# Validação do lote 64 — o lançamento da 0.9.2

Data: 24/10/2026. Escopo na [spec 0064](../specs/0064-lancamento-0-9-2.md). Nenhum modelo foi chamado, e nada em
`data/` foi gravado.

| Conferência | Resultado |
|---|---|
| A versão instalada (`importlib.metadata`) | 0.9.2, depois da reinstalação editável, sem downloads |
| A bateria completa (`ferramentas/bateria.py`), com os testes com os dados reais | **871 passando** (os 868 da 0.9.1 e os 3 do lote 63), nenhum falhou nem foi ignorado; 36 grupos; 18 treinos; 231,8 s; pico de 559,2 MiB |
| A equivalência contra a referência do lote 49 | 28 de 28 arquivos iguais, nenhuma diferença; `erros.npz` e a evidência espectral à parte, como desde os lotes 54 e 55 |
| Toda importação de `aliado…` resolve | sim, em `src`, `tests` e `ferramentas` |
| Pastas vazias ou só com `__pycache__` | nenhuma |
| `ciencia treinar-gpvs --help`, `experimento listar` e `experimento pdf`, numa cópia dos resultados | saída 0 nos três |
| O wheel de uma cópia limpa | 197 arquivos, com os 156 módulos `.py`; 154 importados do próprio wheel, sem erro |
| Ruff | sem apontamentos |

## O pacote

- **O arquivo:** `dist/v0.9.2/aliado-0.9.2-py3-none-any.whl`, com 900.524 bytes.
- **SHA-256:** `824e3b53a6113b8e801ebff9c8de87787293e523283c734a727b2830773c867a`.

## Registros

Ficam fora do Git:
- a bateria, em `tmp/lote-64/bateria/` e `tmp/lote-64/bateria.log`;
- a equivalência, em `tmp/lote-64/equivalencia.log`;
- as conferências extras, em `tmp/lote-64/verificacao.json`.
