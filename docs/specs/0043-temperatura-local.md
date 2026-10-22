# Spec 0043 — temperatura 0,6 no modelo local

Estado: aplicado e medido localmente em 19/10/2026; aguarda a revisão e o commit do pesquisador. Não muda código nem
requisitos vivos.

## Propósito

Nos lotes 41 e 42, a mesma pergunta mudava de desfecho de uma rodada para outra. Com temperatura 1, o padrão do
`qwen3.5`, só 7 das 16 perguntas reais tinham o mesmo desfecho em duas rodadas seguidas. O pesquisador pediu para
baixar a temperatura e medir em duas rodadas, para a citação variar menos.

## O que muda

- **`aliado-local`** (`tmp/lote-38/Modelfile`): `PARAMETER temperature 0.6`. O resto segue igual: `num_ctx 32768`,
  `num_gpu 32` e `use_mmap true`.
- **Vale só para as respostas do local.** A conversa não define temperatura, então vale a do modelo. A reescrita, as
  fichas e as figuras já usam 0, e o revisor de memória 0,2. O Gemini não muda.
- **A trava combinada:** a temperatura fica se mais perguntas repetirem o desfecho nas duas rodadas, sem piorar as
  respondidas pelo local nem as citações certas. Senão, volta a 1.

## Resultado

| | Temperatura 1, lote 41 | Temperatura 1, lote 42 | 0,6, rodada 1 | 0,6, rodada 2 |
|---|---|---|---|---|
| Respondidas pelo local | 9 | 10 | 13 | 11 |
| Citaram o documento esperado | 7 | 7 | 8 | 8 |
| Refeitas pelo Gemini | 5 | 6 | 2 | 3 |
| Chamadas ao Gemini | 7 | 8 | 4 | 5 |
| Tempo médio por pergunta | 158 s | 102 s | 90 s | 96 s |
| Mediana das respostas do local | 131 s | 136 s | 98 s | 78 s |

- **Mesmo desfecho nas duas rodadas:** 13 de 16 com 0,6, contra 7 de 16 com 1. Trocaram só a P2, a E2 e a E8.
- **A trava aprovou:** a variação caiu, e as respostas, as citações e o tempo melhoraram. A temperatura 0,6 fica.
- O lote 41 rodou com 20 camadas na placa; o tempo comparável é o do lote 42, que já tinha 32.

Os números estão na [validação do lote 43](../migracao/validacao-lote-43.md).

## Fora deste lote

- **A penalidade de repetição** (`presence_penalty 1.5`, o padrão do `qwen3.5`), que pode desestimular a repetição
  do formato `[K…]`;
- respostas mais curtas;
- o raciocínio nas páginas inteiras.
