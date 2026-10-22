# Validação do lote 37 — páginas sem pendência falsa

Data: 18/10/2026; registrada em 19/10/2026, durante a preparação da 0.8.0; revisão final no lote 44. Escopo na
[spec 0037](../specs/0037-paginas-sem-leitura.md); requisitos vivos BIB-01 a BIB-03 em
[capacidades/biblioteca.md](../specs/capacidades/biblioteca.md). Nenhuma chamada paga.

## Bateria

| Conferência | Resultado |
|---|---|
| Testes do lote | os de `test_figures.py` que citam BIB-01, BIB-02 e BIB-03 passam |
| Bateria inteira | entra na conferência do lançamento da 0.8.0 |
| Requisitos vivos citados por testes | BIB-01 a BIB-03: todos (`test_specs.py`) |

## A biblioteca real (só leitura, 18/10/2026)

- **Páginas:** 2.239, das quais 2.237 com texto; as 2 sem texto estão em branco.
- **Figuras:** 1.304 páginas com figuras, 1.276 delas já descritas pelo modelo.
- **O limite da página em branco foi medido nas páginas reais:** as em branco ficaram abaixo de 0,002% de pontos
  visíveis, e a mais vazia das que tinham conteúdo, em 2,8%. O corte ficou em 0,1%.

## O que não foi feito

- **A reindexação da biblioteca real:** os avisos já gravados nos documentos só saem quando o pesquisador reindexar
  pela tela. O assistente não reindexa a biblioteca real por ele.
