# Validação do lote 51 — o mestrado do dado ao treino em pastas

Data: 22/10/2026. Escopo na [spec 0051](../specs/0051-mestrado-do-dado-ao-treino.md). Commits locais autorizados pelo
pesquisador no plano de 21/10; o push e a tag ficam com ele.

## Os dois commits

| Commit | O que fez | Bateria completa |
|---|---|---|
| cd5115d (mudança de lugar) | `gpvs.py` → `preparo/preparacao.py` e `training.py` → `treino/detectores.py`, com as importações no lugar novo | 837 testes passando, 204,7 s, 18 treinos |
| o seguinte (divisão) | `base/`, `atributos/`, `preparo/` e `treino/`; as 3 cópias que viraram uma | 837 testes passando, 198,6 s, 18 treinos |

**O Git seguiu os dois arquivos:** `gpvs.py` com 100% de semelhança e `training.py` com 99%.

## Conferências

| Conferência | Resultado |
|---|---|
| Equivalência contra a referência do lote 49 (a rodada inteira no GPVS sintético) | 28 de 28 arquivos iguais |
| Testes com os dados reais: o treino da origem bit a bit, a avaliação de 27/09 e a reanálise de 30/09 | passando |
| Toda importação de `aliado…` resolve | sim |
| Pastas vazias ou só com `__pycache__` | nenhuma |
| Caminhos antigos (`mestrado.gpvs`, `mestrado.training`, `evaluation._onset`) fora dos registros | nenhum |
| Os comandos e o PDF do experimento, numa cópia dos resultados | saída 0; PDF de 235 KB |
| O wheel de uma cópia limpa | 117 arquivos `.py` presentes; 115 módulos importados do próprio wheel, sem erro |
| O terminal e o experimento abrem sem numpy nem PyTorch | sim |
| NUC-01, NUC-02, NUC-04 e Ruff | passando |

## As cópias que viraram uma

| O quê | Antes | Agora |
|---|---|---|
| Início nominal da falha | `evaluation._onset`, `reanalysis._nominal` e `summary.onset`, com o mesmo corpo | `preparo/inicio_nominal.nominal_onset` |
| Caminho do cache dos atributos | o terminal, o experimento, o explorador e os painéis | `atributos/cache.features_cache` |
| Pasta da base | o terminal e o experimento | `base/ensaios.DATA_DIR` |

A equivalência e os testes dos painéis (`alarme_deteccao` e o início de cada ensaio) confirmam que a regra é a mesma.
