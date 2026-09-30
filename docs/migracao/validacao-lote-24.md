# Validação do lote 24 — início observado das falhas

Verificação local em **30/09/2026**, sobre o commit `745880a` (lote 23). **Nenhuma chamada paga.** O
assistente não fez push nem tag.

## Método fixado antes das métricas

O detector de mudança foi calibrado só nos sinais e nos ensaios saudáveis, sem os escores dos modelos,
antes de qualquer métrica ser recalculada. A configuração (`OnsetConfig`) tem o sha256 `1510880c…`,
gravado na pasta da reanálise e no registro.

| Penalidade c | 1 | 2 | 3 | 4 | 5 a 30 |
|---|---:|---:|---:|---:|---:|
| Mudanças em F0L | 2 | 0 | 0 | 0 | 0 |
| Mudanças em F0M | 52 | 21 | 1 | 0 | 0 |

**c = 4** é o menor sem mudança nos dois saudáveis.

| Ensaios | Meio (s) | Mudança (s) | Classe |
|---|---|---|---|
| F1L / F1M | 6,45 / 6,95 | 8,66 / 8,46 | clara |
| F2L / F2M | 7,11 / 7,20 | 8,88 / 8,70 | clara |
| F3L / F3M | 5,17 / 3,50 | 8,92 / 6,74 | clara |
| F5L / F5M | 7,15 / 7,20 | 7,14 / 7,38 | clara |
| F6L / F6M | 7,20 | 5,60 / 11,60 | fraca: some a partir de c = 8 e c = 5 |
| F7L / F7M | 7,20 | 9,32 / 11,16 | fraca: some a partir de c = 8 |
| F4L / F4M | 7,20 | — | nenhuma |

As mudanças claras são as mesmas de c = 1 ou 2 até c = 30. A resolução é de uma janela (20 ms).

## Reanálise

`aliado ciencia reanalisar-gpvs --saida data/resultados/gpvs-reanalise-001` levou cerca de 10 s e entrou no
registro como **consulta nº 2**, do tipo "reanalise", com a nº 1 semeada da avaliação de 27/09. A mesma rodada
numa cópia (`tmp/lote-24`) deu o mesmo `relatorio.json`.

- **Regressão:** com o início nominal, `summarize` sobre os escores gravados repete o `relatorio.json` de 27/09 **bit a bit**.
- **Detecção igual à oficial:** Denso com 10 de 14 e AE-LSTM com 8 de 14. O atraso desde o meio de cada ensaio é o oficial.

| Treino de referência | 14 ensaios, meio | 14 ensaios, mudança | 8 de mudança clara, meio | 8 de mudança clara, mudança |
|---|---:|---:|---:|---:|
| Denso: atraso mediano | 2,04 s | 60 ms | 1,70 s | 60 ms |
| Denso: sensibilidade | 0,402 | 0,590 | 0,671 | 1,000 |
| Denso: F1 | 0,458 | 0,596 | 0,744 | 0,985 |
| Denso: AUC-ROC | 0,775 | 0,862 | 0,847 | 1,000 |
| AE-LSTM: atraso mediano | 1,70 s | 60 ms | 1,70 s | 60 ms |
| AE-LSTM: sensibilidade | 0,386 | 0,576 | 0,668 | 1,000 |
| AE-LSTM: F1 | 0,434 | 0,575 | 0,746 | 0,994 |

- **Atrasos desde a mudança:** de 40 a 60 ms, isto é, 2 ou 3 janelas, o mínimo da regra de 3 janelas seguidas.
- **Comparação por objetivo:** continua "sem diferença clara" em todos os objetivos, nos 14 e nos 8 ensaios.
- **Circularidade:** a mudança e os modelos olham as mesmas 24 variáveis. Por isso, a sensibilidade de 1 nos 8 ensaios mostra que os modelos veem logo o que aparece nas variáveis; ela não mede falhas que não aparecem. Isso está escrito no relatório e na tela.
- **Alarmes falsos, nos 52 s saudáveis:**

  | Modelo | Janelas acima | Observados | Estimados por hora (IC 95%) | Sequências de 2 (previstas / vistas) | Alarmes (previstos / vistos) |
  |---|---:|---:|---|---|---|
  | Denso | 57 de 2.611 | 0 (limite 207/h) | 19,4 (0 a 53,4) | 3,9 / 4 | 0,28 / 0 |
  | AE-LSTM | 40 de 2.611 | 1 (limite 327/h) | 55,8 (0 a 263) | 5,3 / 5 | 0,81 / 1 |

- **Faixa do limiar:** com a posição 191 de 192, a faixa esperada vai de 0,13% a 2,87% por janela. O observado cabe nela: Denso com 0,76% no teste e 2,34% antes da falha; AE-LSTM com 0,38% e 1,66%.
- **Grade de percentil, só relatada:** com p95 e p97,5, o Denso detectaria 13 de 14, mas teria 39 e 15 alarmes antes da falha.

## Testes

- `tests/test_onset.py`, com 7 testes:
  - o PELT com mudanças conhecidas, em ruído e com o segmento mínimo;
  - as classes, a escolha da penalidade e a configuração;
  - o GPVS sintético, com a mudança no meio;
  - os inícios reais.
- `tests/test_reanalysis.py`, com 6 testes:
  - os limiares sem os pesos e os escores gravados iguais aos pontuados;
  - a rotulagem, com o trecho de fora e o atraso negativo;
  - o comando, com a pasta nova, o registro nº 2, a recusa de pasta existente, as visões da aba e o tipo na lista de resultados;
  - com os dados reais, a regressão bit a bit e a reanálise.
- `tests/test_detection_metrics.py` e `tests/test_detection_threshold.py`, com 3 testes novos: a cadeia de Markov e a Beta.
- `tests/test_science_views.py`, com 1 teste novo e a rota do início. O relatório sintético ganhou os campos que o real já tem: a parte combinada e as frações.

**409 testes passaram** (392 do lote 23 e 17 novos). O Ruff não apontou problemas, e `ciencia.js` e `graficos.js` passaram na checagem de sintaxe.

## Aceite no navegador

A interface de teste rodou em `127.0.0.1:8773`, com a cópia `tmp/lote-24`. Os prints foram feitos por Chrome headless.

| Item | Resultado |
|---|---|
| Início das falhas | O gráfico por ensaio mostra o registro, o meio e a mudança (clara, fraca ou nenhuma). Vêm em seguida os indicadores dos dois modelos com os 4 cortes, a sensibilidade e o atraso por ensaio, a comparação e o parágrafo sobre o que a reanálise não resolve. |
| Escores | A linha pontilhada da mudança cai no salto dos escores em todos os 8 ensaios. O rodapé mostra, por exemplo, "detectou 2,25 s depois do meio e 40 ms depois da mudança". |
| Resumo | Os alarmes falsos por hora usam os 52 s: Denso com 0 e limite de 207, AE-LSTM com 68,9 e limite de 327. Entram os cartões da estimativa e das janelas acima do limiar, com a faixa esperada. |
| Rodar e arquivos | A reanálise aparece como "GPVS: reanálise com o início observado", com o aviso de que a oficial continua a de 27/09. O histórico mostra a consulta nº 2 como "reanálise com o início observado (mesmos escores)". |
| Exportação | O SVG do gráfico novo sai em fundo branco, sem variáveis de CSS e com a cor da mudança. O PNG tem 3.125 px de largura. |
| Tema escuro | Os gráficos se redesenham com as cores do tema. |
| Tela estreita (360 px) | Sem rolagem lateral no Resumo, nos Escores e no Início. |
| Console e servidor | Sem erros do aplicativo. |

## Defeitos encontrados e corrigidos no aceite

1. **Em 360 px, os rótulos e a legenda do gráfico de início ficavam cortados.** Em tela estreita, os rótulos passaram a ser só o ensaio (F1L), com o nome na dica, e a legenda quebra em linhas.
2. **O rodapé dos escores não dizia de onde contava o atraso.** Ele passou a dizer "depois do meio" e "depois da mudança".

## Estado final

- `data/resultados/gpvs-reanalise-001` e `data/resultados/registro-consultas-teste.jsonl` ficam fora do Git, como os demais resultados.
- `.claude/launch.json` ganhou a entrada `aliado-web-lote-24`.
- Depois da revisão, a pedido do pesquisador, a pasta `tmp/` foi limpa: 2,3 GB de cópias de teste dos lotes 02 a 24, páginas de PDF renderizadas e um backup antigo do `.env`, anterior ao lote 09. O `.env` atual ficou intacto. As entradas antigas de `.claude/launch.json` apontam para essas cópias; cada lote novo cria a sua.
- O commit do lote 24 foi feito pelo assistente, com a autorização do pesquisador (30/09), sem push.
