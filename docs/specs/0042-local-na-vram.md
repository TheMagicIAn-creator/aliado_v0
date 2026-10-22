# Spec 0042 — o modelo local quase todo na VRAM

Estado: aplicado e medido localmente em 19/10/2026; aguarda a revisão e o commit do pesquisador. Não muda código nem
requisitos vivos.

## Propósito

O limite de 4 GB na placa partia da ideia de que, passando dele, o modelo iria para a RAM e depois para o SSD, sem
perder muito. A medição mostrou que só a VRAM dá velocidade: a placa calcula o que está nela, e o resto é calculado
pelo processador. A memória virtual no SSD funciona, mas como reserva de espaço, não como velocidade. O pesquisador
decidiu dar ao modelo toda a VRAM e manter o `qwen3.5:9b`.

## O que muda

- **`aliado-local`** (`tmp/lote-38/Modelfile`): `num_gpu 32`, no lugar de 20. O resto segue igual: `num_ctx 32768`,
  `use_mmap true` e o `.env` com `AL_IADO_LOCAL_CONTEXT=32768`.
- **README:** o Modelfile, a memória explicada como foi medida e os números novos.

## Resultado

- **Placa, com 32 mil de contexto e uma entrada de 27 mil tokens:**

| Camadas | Placa carregada | Pico | Na placa | Escrita (pouco contexto / quase cheio) | Leitura |
|---|---|---|---|---|---|
| 20 (lote 40) | 3.973 MiB | 3.999 MiB | 59% | 14,8 / 8,7 tokens/s | 769 tokens/s |
| 30 | 5.353 MiB | 5.361 MiB | 80% | 22,7 / 20,7 tokens/s | 1.004 tokens/s |
| 32 (escolhida) | 5.635 MiB | 5.641 MiB | 85% | 25,3 / 23,0 tokens/s | 1.089 tokens/s |

  As 33 não cabem: com o texto todo na placa, o Ollama põe também o leitor de imagens (0,9 GB).
- **RAM:** não foi poupada. Com o modelo carregado, a memória reservada subiu 7,8 GB, contra 6,4 GB com 20 camadas, e
  o processo reserva cerca de 8,2 GB. No Windows, o que um programa reserva na placa também conta na memória reservada
  do sistema.
- **As 16 perguntas, sem custo:**
  - o tempo médio por pergunta caiu para 102 s, contra 158 s no lote 41 e 265 s no lote 40;
  - o local respondeu 10, 7 delas com a citação certa, contra 9 e 7 no lote 41: o mesmo patamar, dentro do sorteio
    da temperatura 1;
  - 6 foram refeitas pelo Gemini, pela conferência, e 2 foram ao Gemini por passarem de 32 mil tokens.

Os números estão na [validação do lote 42](../migracao/validacao-lote-42.md).

## Riscos

- **Folga na placa de cerca de 360 MiB:** um programa que use a placa NVIDIA (um jogo, ou vídeo acelerado por ela) pode
  fazer o modelo não carregar. Neste notebook, a tela usa a placa da Intel, e a NVIDIA fica em 0 MiB parada.

## Fora deste lote

- a temperatura do local, que segue como a maior fonte de variação entre as rodadas;
- respostas mais curtas;
- o raciocínio nas páginas inteiras;
- o `qwen3.5:4b`.
