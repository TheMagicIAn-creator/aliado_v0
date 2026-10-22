# Validação do lote 50 — a ciência geral em pastas

Data: 22/10/2026. Escopo na [spec 0050](../specs/0050-ciencia-geral-em-pastas.md). Commits locais autorizados pelo
pesquisador no plano de 21/10; o push e a tag ficam com ele.

## Os dois commits

| Commit | O que fez | Bateria completa | Equivalência |
|---|---|---|---|
| e4e59ab (mudança de lugar) | `git mv` dos 9 arquivos inteiros e as importações apontando para o lugar novo | 836 testes passando, 210,7 s | 28 de 28 arquivos iguais |
| o seguinte (divisão) | as definições repartidas por 15 pastas, as importações nome por nome, o NUC-04 e os documentos | 837 testes passando (o NUC-04 é o novo), 201,0 s, 18 treinos | 28 de 28 arquivos iguais |

Notas:
- **Equivalência:** a rodada inteira do experimento no GPVS sintético comparada com a referência gravada no lote 49
  (`tmp/equivalencia/referencia`). Só as datas, a duração e a versão ficam fora da comparação.
- **Git:** o histórico seguiu cada arquivo. Os 9 aparecem como mudança de nome no 1º commit, com 98% a 100% de
  semelhança.

## Conferências

| Conferência | Resultado |
|---|---|
| Toda importação de `aliado…` resolve, inclusive as de dentro das funções (`src`, `tests` e `ferramentas`) | sim, nenhuma falha |
| Pastas vazias ou só com `__pycache__` | nenhuma |
| Caminhos antigos fora dos registros | nenhum |
| `aliado ciencia treinar-gpvs --help` e `aliado experimento listar` | saída 0 |
| `aliado experimento pdf ae-denso-lstm`, numa cópia de `data/resultados` | saída 0; PDF de 235 KB |
| O wheel montado de uma cópia limpa dos arquivos do Git | os 101 arquivos `.py` de `src/aliado` presentes |
| Os módulos importados do próprio wheel, sem o atalho editável do ambiente | 99 de 99, sem erro (fora `aliado.__main__`, que é a linha de comando) |
| `import aliado.science` | não carrega numpy nem PyTorch |
| NUC-01, NUC-02 e NUC-04 | passando |
| Ruff | sem erro |

**Registros que mantêm os caminhos antigos:** os mapas datados de `docs/arquitetura/2026-10-05/`, as specs antigas e
`docs/migracao/`.

## O que não muda

- Nenhuma conta: as funções e as classes são as mesmas, com o mesmo código, como prova a equivalência.
- Os nomes gravados em disco, os comandos, o extra `science`, `science_routes` e `interfaces/web/science.py`.
