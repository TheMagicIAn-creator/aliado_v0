# Validação do lote 16

Verificação local em **27/09/2026**, Windows/Python 3.12. Nenhum commit, push ou PR; nenhuma
chamada paga.

## Resultado

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **331 testes passaram** (320 anteriores + 11 novos). O único aviso vem do `starlette.testclient`. |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| Origem | `mestrado-utfpr` sem alterações; `docs/fmeca.md` foi só lido. |

## FMECA

Relatório em `data/resultados/fmeca-001` (fora do Git).

| Grupo | S | O | D | NPR | Posição pelo NPR | Posição pela taxa |
|---|---:|---:|---:|---:|---:|---:|
| CCB (item "PCB" na fonte) | 7 | 4 | 6 | 168 | 1 | 1 |
| Contatores CA/CC | 6 | 5 | 5 | 150 | 2 | 4 |
| Módulo IGBT | 3 | 3 | 7 | 63 | 3 | 3 |
| Ventiladores | 4 | 3 | 4 | 48 | 4 | 2 |

**Leitura pelas taxas** (operação, 4.015 h/ano; calendário, 8.760 h/ano):

| Grupo | MTBF (h) | Chance de falhar em 1 ano | Em 20 anos | Falhas esperadas em 20 anos |
|---|---:|---|---|---|
| CCB | 15.699 | 22,6% / 42,8% | 99,4% / > 99,9% | 5,1 / 11,2 |
| Ventiladores | 37.453 | 10,2% / 20,9% | 88,3% / 99,1% | 2,1 / 4,7 |
| IGBT | 112.360 | 3,5% / 7,5% | 51,1% / 79,0% | 0,7 / 1,6 |
| Contatores | 120.337 | 3,3% / 7,0% | 48,7% / 76,7% | 0,7 / 1,5 |

## Observações

- **As duas leituras concordam no extremo e divergem no meio.** A CCB é a primeira nas duas. Os contatores são os 2º pelo NPR e os últimos pela taxa, e os ventiladores, os últimos pelo NPR e os 2º pela taxa.
  - A divergência vem da ocorrência: os contatores têm o maior O (5) e a menor taxa.
  - Ficam três pares discordantes, todos com os contatores.
- **As notas continuam a reconferir.** S, O e D vêm do documento da origem, que as atribui a Cristaldi et al. (2017). O PDF ainda não está no acervo, e a correspondência "PCB" → CCB é uma suposição registrada.
- **Falhas esperadas e chance de falhar respondem a perguntas diferentes.**
  - As falhas esperadas supõem reparo ou troca por um componente equivalente, com a mesma taxa.
  - A chance de falhar é a de ao menos uma falha, sem reparo.
  - Não há disponibilidade calculada.
