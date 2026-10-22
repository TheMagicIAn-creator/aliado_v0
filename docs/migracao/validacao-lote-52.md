# Validação do lote 52 — o mestrado da avaliação aos comandos em pastas

Data: 22/10/2026. Escopo na [spec 0052](../specs/0052-mestrado-da-avaliacao-aos-comandos.md). Commits locais
autorizados pelo pesquisador no plano de 21/10; o push e a tag ficam com ele.

## Os dois commits

| Commit | O que fez | Bateria completa |
|---|---|---|
| 20d4b66 (mudança de lugar) | `evaluation.py`, `onset.py`, `reanalysis.py` e `commands.py` nas pastas novas, com as importações no lugar novo | 837 testes passando, 202,5 s, 18 treinos |
| o seguinte (divisão) | `avaliacao/` (9 arquivos), `inicio_das_falhas/` (2), `reanalise/` (3) e `comandos/`; a pasta oficial num lugar só | 837 testes passando, 233,2 s, 18 treinos (depois da correção abaixo) |

**O Git seguiu os 4 arquivos**, com 97% a 100% de semelhança.

## O que a bateria achou na divisão, e a correção

**Na 1ª bateria depois da divisão:** 2 falhas e 9 erros, todos no mesmo ponto.
- A reanálise deixou de definir a pasta oficial e passou a importá-la de `avaliacao/oficial.py`.
- Como a reanálise não a usava mais, a limpeza de importações sem uso (Ruff) a tirou.
- Os testes e o comando `reanalisar-gpvs`, que liam a pasta oficial pela reanálise, quebraram.

**A correção:** os testes e o comando passaram a ler `avaliacao/oficial.EVALUATION`, o lugar único. A conferência das
importações, rodada antes da 2ª bateria, já não acha nenhuma importação que não resolve.

## Conferências

| Conferência | Resultado |
|---|---|
| Equivalência contra a referência do lote 49 | 28 de 28 arquivos iguais |
| Testes com os dados reais: a avaliação de 27/09 e a reanálise de 30/09 reproduzidas | passando |
| Toda importação de `aliado…` resolve | sim |
| Os comandos e o PDF do experimento, numa cópia dos resultados | saída 0 |
| O wheel de uma cópia limpa | 132 arquivos `.py` presentes; 130 módulos importados do próprio wheel, sem erro |
| O terminal e o pacote do mestrado abrem sem numpy nem PyTorch | sim |
| NUC-01, NUC-02, NUC-04 e Ruff | passando |

## A pasta oficial

`gpvs-avaliacao-001` estava escrito em 3 lugares: no experimento, na reanálise e no padrão do comando. Agora está só em
`avaliacao/oficial.py`. A reanálise e o comando já o leem de lá; o experimento e os resultados passam a ler no lote 53.
