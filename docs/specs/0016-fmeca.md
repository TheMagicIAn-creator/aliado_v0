# Lote 16 — FMECA dos quatro grupos

Lote de FMECA do [roteiro da v0](../roteiro-v0.md), autorizado em 27/09/2026. Revê o NPR dos
quatro grupos físicos e acrescenta, **separada**, a leitura pelas taxas de falha decididas no
lote 07. Pelo M11, a FMECA é independente do GPVS.

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Ocorrência e NPR | **Não misturar.** O NPR é o das notas de Cristaldi, Khalil e Soulatiantork (2017), Acta IMEKO, Tab. 6. O ranking pelas taxas vem ao lado, sem nota agregada, e a divergência entre O e λ é relatada. |
| S e D | Os da fonte, registrados como percepção do levantamento de campo. Os detectores não os alteram (M09), e o relatório não cita o GPVS (M11). |
| CCB | Herda as notas do item "PCB" da fonte, com a ressalva de reconferir no PDF. |
| Reparos | Entram o MTBF e as falhas esperadas (λ × horas) em 1 e 20 anos, nas duas bases. As taxas não determinam o tempo de reparo, então a disponibilidade só entra com fonte de MTTR. |

## Escopo implementado

- `docs/pesquisa-inversores/fmeca.json`: a tabela versionada.
  - Para cada grupo: S, O, D, o nome do item na fonte e as ressalvas.
  - Referências aos 8 cenários que já existem, sem duplicar as taxas.
- `aliado.science.fmeca`, geral e sem dependências externas:
  - **Validação:** exige notas inteiras de 1 a 10 e recusa um NPR fornecido pronto, porque o NPR é sempre calculado.
  - **Ordenação:** ordena por NPR, com empates na mesma posição.
  - **Leitura pelas taxas:** cada cenário passa pelo serviço RAM, que dá o MTBF em horas e anos e, em cada horizonte, a chance de falhar e as falhas esperadas.
  - **Consistência:** recusa cenários do mesmo item com taxas diferentes e cenários que não sejam exponenciais com taxa horária.
  - **Comparação:** posições pelo NPR, pela ocorrência e pela taxa, e a lista de pares em que O e λ apontam em sentidos opostos.
- Comando: `aliado ciencia fmeca [--tabela <arquivo>] --saida <pasta nova>`, que gera `fmeca.json`, `fmeca.csv` e `fmeca.md`.
- Skill `pesquisa-inversores` 0.1.5, `docs/ciencia/confiabilidade.md`, `docs/ciencia/procedimentos.md` e README com as decisões.

## Critérios de aceitação

- A tabela decidida dá os NPR 168 (CCB), 150 (contatores), 63 (IGBT) e 48 (ventiladores). A ordem pelas taxas é CCB, ventiladores, IGBT e contatores.
- São relatados três pares discordantes, todos com os contatores (O = 5 e a menor taxa).
- As falhas esperadas da CCB em 20 anos de operação são 63,7 × 10⁻⁶ × 4.015 × 20 ≈ 5,1.
- A chance de falhar confere com o serviço RAM.
- As notas não mudam com as taxas.
- A suíte completa e o Ruff passam.
