# Validação do lote 42 — o modelo local quase todo na VRAM

Data: 19/10/2026. Escopo na [spec 0042](../specs/0042-local-na-vram.md). Nenhuma chamada paga e nenhum download. Sem
código novo.

## Placa, RAM e velocidade

As medidas são com `num_ctx 32768` e `use_mmap true`, numa entrada de 26.779 tokens, com a placa lida a cada meio
segundo.

| Camadas | Placa carregada | Pico | `ollama ps` | Escrita curta | Escrita com contexto quase cheio | Leitura |
|---|---|---|---|---|---|---|
| 20 (lote 40) | 3.973 MiB | 3.999 MiB | 41%/59% | 14,8 tokens/s | 8,7 tokens/s | 769 tokens/s |
| 30 | 5.353 MiB | 5.361 MiB | 20%/80% | 22,7 tokens/s | 20,7 tokens/s | 1.004 tokens/s |
| 32 | 5.635 MiB | 5.641 MiB | 15%/85% | 25,3 tokens/s | 23,0 tokens/s | 1.089 tokens/s |

- **Livre na placa, com ela parada:** 6.002 MiB. Com 32 camadas sobram cerca de 360 MiB.
- **As 33 camadas não foram testadas:** com o texto todo na placa, o Ollama põe também o leitor de imagens (0,9 GB), que
  não cabe.
- **RAM com 32 camadas:**
  - a memória reservada subiu de 21,9 para 29,7 GB com o modelo carregado;
  - o processo do modelo reserva 8,2 GB e usa 6,3 GB de RAM;
  - a RAM livre caiu para 0,3 GB.
  - Com 20 camadas, a reserva tinha subido 6,4 GB: pôr mais na placa não poupou RAM.

## As 16 perguntas reais, sem custo

São as mesmas perguntas, com o mesmo script, o Gemini falso e uma cópia nova da biblioteca, idêntica às anteriores, em
`tmp/lote-42/medicao`.

| | Lote 40 (20 camadas) | Lote 41, final (20 camadas) | Lote 42 (32 camadas) |
|---|---|---|---|
| Tempo médio por pergunta | 265 s | 158 s | 102 s |
| Mediana das respostas do local | 301 s | 131 s | 136 s |
| Respondidas pelo local, no fim | 14 | 9 | 10 |
| Citaram o documento esperado | 10 | 7 | 7 |
| Refeitas pelo Gemini | 0 | 5 | 6 |
| Chamadas ao Gemini | 2 | 7 | 8 |

- **Respostas mais rápidas:**
  - a P3 levou 144 s, contra 237 a 597 s antes;
  - a P5, 62 s, e a E3, 55 s;
  - a mais longa das respondidas pelo local levou 244 s, contra 481 a 730 s nas rodadas anteriores.
- **A mediana do local quase não mudou** (136 contra 131 s), porque o conjunto respondido muda entre as rodadas.
  Desta vez entraram a P2, a P5, a P8 e a E5 e saíram a E2, a E6 e a E8. A P4 e a E4 subiram de degrau antes de o
  local responder.
- **Sorteio:** com temperatura 1, a E2 e a E6 foram refeitas desta vez, e a P5 e a E5 voltaram a citar.

## Conferências

| Conferência | Resultado |
|---|---|
| `pytest tests/test_specs.py` | 2 passaram (sem código novo; a bateria inteira é a do lote 41: 808) |
| `ruff check .` e `git diff --check` | sem apontamentos |

## O que não foi conferido

- **A qualidade das respostas em si:** foi conferida só a citação do documento esperado.
- **O modelo com programas que usem a placa NVIDIA ao mesmo tempo.**
