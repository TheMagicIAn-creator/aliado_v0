# Validação do lote 43 — temperatura 0,6 no modelo local

Data: 19/10/2026. Escopo na [spec 0043](../specs/0043-temperatura-local.md). Nenhuma chamada paga e nenhum download.
Sem código novo.

## Configuração

- **`aliado-local`:** `temperature 0.6`, `num_ctx 32768`, `num_gpu 32` e `use_mmap true`. O `ollama show --parameters`
  confirma o valor. O `top_k` (20), o `top_p` (0,95) e o `presence_penalty` (1,5) seguem do `qwen3.5`.
- **Rodadas:** duas rodadas das 16 perguntas reais, com o Gemini falso e uma cópia nova da biblioteca em cada uma
  (`tmp/lote-43/rodada-1` e `rodada-2`). As cópias são iguais às dos lotes anteriores.

## Comparação

A comparação é com as duas rodadas anteriores, com os mesmos pedidos e a temperatura 1.

| | Temperatura 1, lote 41 | Temperatura 1, lote 42 | 0,6, rodada 1 | 0,6, rodada 2 |
|---|---|---|---|---|
| Respondidas pelo local, no fim | 9 | 10 | 13 | 11 |
| Citaram o documento esperado | 7 | 7 | 8 | 8 |
| Refeitas pelo Gemini | 5 | 6 | 2 | 3 |
| Chamadas ao Gemini | 7 | 8 | 4 | 5 |
| Tempo médio por pergunta | 158 s | 102 s | 90 s | 96 s |
| Mediana das respostas do local | 131 s | 136 s | 98 s | 78 s |

### Estabilidade

| Par de rodadas | Perguntas com o mesmo desfecho |
|---|---|
| Temperatura 1 (lote 41 e lote 42) | 7 de 16 |
| Temperatura 0,6 (rodadas 1 e 2) | 13 de 16 |

- **O que trocou com 0,6:**
  - a P2: o local citou na rodada 1 e foi refeita na 2;
  - a E2: o contrário;
  - a E8: o local respondeu na rodada 1 e foi refeita na 2.
- **O "desfecho"** é a combinação de quem respondeu primeiro (o local, o local depois de refeita, ou direto o Gemini)
  e de ter citado ou não o documento esperado.

## Conferências

| Conferência | Resultado |
|---|---|
| `pytest tests/test_specs.py` | 2 passaram (sem código novo; a bateria inteira é a do lote 41: 808) |
| `ruff check .` e `git diff --check` | sem apontamentos |

## O que não foi conferido

- **A qualidade das respostas em si:** foi conferida só a citação do documento esperado.
- **Outros valores de temperatura,** como 0,3 ou 0,8.
