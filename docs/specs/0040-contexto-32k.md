# Spec 0040 — contexto de 32 mil tokens no modelo local, com a placa abaixo de 4 GB

Estado: aplicado e medido localmente em 18/10/2026; aguarda a revisão e o commit do pesquisador. Não muda código nem
requisitos vivos: o comportamento de [capacidades/provedores.md](capacidades/provedores.md) é o mesmo, e só o número
do contexto muda.

## Propósito

No lote 39, das 7 perguntas que foram ao Gemini, todas foram pelo contexto de 16 mil tokens. O pesquisador pediu 32 mil,
com a placa abaixo de 4 GB, medindo a placa, a RAM e as 16 perguntas.

## O que muda

- **`aliado-local`** (`tmp/lote-38/Modelfile`): `num_ctx 32768`, `num_gpu 20` e `use_mmap true`.
- **`.env` do pesquisador:** `AL_IADO_LOCAL_CONTEXT=32768`, acrescentado com a autorização dele. O padrão do código
  segue 16.384, o lado seguro.
- **README e `.env.example`:** o Modelfile, a linha do `.env` e os números.

## Resultado

- **Placa, com 32 mil de contexto e uma entrada de 27 mil tokens:**
  - com 21 camadas, 4.113 MiB carregada e 4.133 MiB no pico, acima dos 4 GB;
  - com 20 camadas, 3.973 MiB carregada e 3.999 MiB no pico, abaixo dos 4 GB. Ficou essa.
- **RAM:** o modelo reserva cerca de 6,4 GB, e a RAM livre fica em cerca de 0,4 GB com ele carregado.
- **Velocidade:**
  - a leitura vai a 769 tokens/s (27 mil tokens em 35 s);
  - a escrita vai a 14,8 tokens/s com pouco contexto e cai para 8,7 com o contexto quase cheio.
- **As 16 perguntas, sem custo:** o local respondeu 14, contra 6 no lote 39, e 10 citaram o documento esperado,
  contra 3.
  - Nenhuma foi refeita pelo Gemini, contra 3, e nenhuma resposta foi cortada.
  - Só a P1 e a E1 foram ao Gemini, por passarem de 32 mil tokens: 2 chamadas, contra 12.
  - O preço é o tempo: 265 s por pergunta, em média, contra 130 s. As respostas do local levaram de 38 s a 12 min,
    com mediana de 5 min.

Os números estão na [validação do lote 40](../migracao/validacao-lote-40.md).

## Fora deste lote

- **O tempo:** desligar o raciocínio na reescrita da busca e nos trechos.
- **O identificador entre crases:** não apareceu nesta rodada.
- **O roteador na E3.**
