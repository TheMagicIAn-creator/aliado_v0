# Validação do lote 40 — contexto de 32 mil tokens no modelo local

Data: 18/10/2026. Escopo na [spec 0040](../specs/0040-contexto-32k.md). Nenhuma chamada paga e nenhum download. Sem
código novo.

## Placa e RAM

As medidas são com `num_ctx 32768` e `use_mmap true`, com uma entrada de 26.779 tokens (92 mil letras das specs) e a
placa lida a cada meio segundo.

| Camadas na placa | Placa carregada | Pico na entrada longa | Leitura | Escrita (pouco contexto / contexto quase cheio) |
|---|---|---|---|---|
| 21 | 4.113 MiB | 4.133 MiB, acima dos 4 GB | 789 tokens/s | 15,5 / 9,0 tokens/s |
| 20 | 3.973 MiB | 3.999 MiB, abaixo dos 4 GB | 769 tokens/s | 14,8 / 8,7 tokens/s |

- **O `ollama ps` com 20 camadas:** 6,9 GB, 41% no processador e 59% na placa, contexto 32768.
- **RAM:** com o modelo carregado, a memória comprometida subiu de 20,0 para 26,4 GB, e a RAM livre caiu de 6,8 para
  0,45 GB.

## As 16 perguntas reais, sem custo

São as mesmas do lote 38 e do lote 39, pelo mesmo script, com o Gemini falso. Foram feitas numa cópia nova da
biblioteca e numa pasta de dados nova (`tmp/lote-40/medicao`), com `AL_IADO_LOCAL_CONTEXT=32768`.

| Desfecho | Lote 38 | Lote 39 | Lote 40 |
|---|---|---|---|
| Respondidas pelo local | 3 | 6 | 14 |
| Citaram o documento esperado | 1 | 3 | 10 |
| Direto ao Gemini | 8 | 7 | 2 (P1 e E1, que passam de 32 mil) |
| Refeitas pelo Gemini | 3 | 3 | 0 |
| Chamadas ao Gemini | 13 | 12 | 2 |
| Respostas cortadas | — | — | 0 |
| Tempo médio por pergunta | 105 s | 130 s | 265 s |

- **Entrada real das 14 chamadas locais:** de 6.914 a 20.679 tokens, e saída de até 5.911.
- **Tempo das respostas do local:** de 38 s a 730 s, com mediana de 301 s. As mais longas foram as das páginas
  inteiras e do documento: P3 com 597 s, E6 com 730 s e E8 com 587 s.
- **Citações:** nenhuma resposta saiu sem as marcas, mas a temperatura 1 do modelo deixa margem de sorteio entre as
  rodadas.

## Conferências

| Conferência | Resultado |
|---|---|
| `pytest tests/test_specs.py tests/test_local_provider.py` | 16 passaram (sem código novo, a bateria inteira é a do lote 39: 806) |
| `ruff check .` e `git diff --check` | sem apontamentos |

## O que não foi conferido

- **A qualidade das respostas em si:** foi conferida só a citação do documento esperado.
- **O tempo na tela:** no uso, a resposta só aparece depois do raciocínio; com o contexto cheio, pode passar de 10
  minutos.
