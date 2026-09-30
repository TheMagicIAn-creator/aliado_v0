# Lote 24 — início observado das falhas, alarmes falsos e incerteza do limiar

Lote autorizado em 30/09/2026, depois do lote 23 (`745880a`). Na análise crítica dos resultados de 27/09,
três pontos ficaram fora do esperado, e o pesquisador pediu para resolver o que tivesse solução, "com
engenharia se for preciso":

1. **O início da falha é o meio do registro.** Os CSVs do GPVS não têm canal de disparo, e o conjunto diz
   só que as falhas foram introduzidas "manualmente, na metade do experimento". Isso infla o atraso e
   rebaixa a sensibilidade.
2. **A evidência de alarmes falsos é fraca.** O teste saudável tem 5,3 s, e o limite superior fica em 2.050/h.
3. **O limiar p99 vem de 192 janelas de calibração** e cai no 2º maior valor.

## Decisões do pesquisador (30/09)

| Tema | Decisão |
|---|---|
| Ordem dos lotes | Este vira o **24**, com o tema do antigo 25. A confiabilidade por componente, a FMECA e a disponibilidade passam a ser o **25**. |
| Trecho entre o meio e a mudança | **Fica de fora** das métricas por janela. Um alarme nele conta como detecção, com atraso negativo em relação à mudança. |
| Ensaios sem mudança clara (F4, F6 e F7) | **Continuam no início nominal**, marcados. As médias saem para os 14 ensaios e também para os 8 de mudança clara. |
| Tela | **Seção nova "Início das falhas"**. O Resumo continua com os números oficiais, e os escores ganham a linha da mudança. |
| Lote 23 | Commit antes de começar, feito pelo assistente com a autorização do pesquisador (`745880a`). |

## Princípios

- A avaliação de 27/09 fica intacta e continua sendo a oficial.
- A reanálise reaproveita os escores gravados em `gpvs-avaliacao-001/escores.npz` e não roda os modelos. Ela entra no registro de consultas ao teste como consulta nº 2, do tipo "reanalise".
- O método do início foi fixado antes de recalcular qualquer métrica. Ele usa só os sinais e os ensaios saudáveis, e a configuração fica congelada com hash.

## Escopo implementado

- **Início observado** (`science/detection/onset.py`, só numpy):
  - **Entrada:** as 24 variáveis por janela, padronizadas pelo comissionamento de cada ensaio (mediana e IQR, com limite de ±10). Nos saudáveis, o primeiro quarto do registro faz esse papel.
  - **Método:** PELT (Killick, Fearnhead e Eckley, 2012), com custo quadrático, segmento mínimo de 5 janelas e penalidade c · 24 · ln n.
  - **Escolha de c:** o menor da grade (1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30) sem mudança nos dois saudáveis. Com os dados atuais, **c = 4**; no c = 3, o F0M ainda mostra uma mudança.
  - **Início observado:** a primeira mudança depois do comissionamento.
  - **Classes:** "clara", se a mesma mudança fica até o c = 30; "fraca", se some; "nenhuma", se não há mudança.
  - A configuração é `OnsetConfig`, com `digest()`.
- **Reanálise** (`science/detection/reanalysis.py`):
  - os escores são remontados de `escores.npz`, e os limiares vêm de `evaluation.load_thresholds`, conferidos pelo hash e sem os pesos;
  - uma cópia de `PreparedGPVS` é rotulada de novo, e `evaluation.run_metrics` e `summarize` rodam sem mudança;
  - nos ensaios de mudança clara:
    - o trecho entre os dois inícios vai para a transição, que fica fora das métricas;
    - as positivas começam na mudança;
    - a fronteira passa a ser a mudança, de onde sai o atraso.
- **Saídas da reanálise:**
  - o resumo para os 14 ensaios, para os 8 de mudança clara com a mudança e para os mesmos 8 com o meio, que separa o efeito do início do efeito de escolher os 8;
  - a grade do limiar em p95, p97,5 e p99, só relatada;
  - uma pasta nova com `configuracao.json`, `inicio.json`, `relatorio.json`, `metricas_por_ensaio.csv` e `relatorio.md`.
- **Alarmes falsos estimados** (`metrics.markov_alarm_rate`):
  - uma cadeia de Markov de dois estados nas janelas saudáveis (teste saudável e pré-teste dos 14 ensaios, 52 s), com π₀ · p₀₁ · p₁₁^(m−1) por janela;
  - o intervalo de 95% sorteia os 16 trechos;
  - o previsto e o observado nas sequências de 2 janelas e nos alarmes ficam lado a lado (Brook e Evans, 1972).
- **Incerteza do limiar** (`threshold.false_alarm_interval`): Beta(n + 1 − r, r) para a chance de alarme por janela (Vovk, 2012), com os quantis pela identidade binomial, sem scipy.
- **Comando e registro:**
  - `aliado ciencia reanalisar-gpvs --saida <pasta nova>`, com a avaliação `gpvs-avaliacao-001` e o treino `gpvs-modelos-002` por padrão;
  - `registry.record_reanalysis` acrescenta a consulta.
- **Tela:**
  - **seção nova "Início das falhas"** (`GET /api/ciencia/inicio`):
    - o gráfico do início por ensaio, com o registro, o meio e a mudança;
    - os indicadores de cada modelo com os dois inícios, nos 14 e nos 8;
    - a sensibilidade por ensaio, o atraso por ensaio e a comparação por objetivo;
    - um parágrafo sobre o que a reanálise não resolve;
  - **escores:** uma linha pontilhada na mudança clara, e o rodapé com o atraso desde o meio e desde a mudança;
  - **Resumo:**
    - os alarmes falsos por hora passam a usar os 52 s saudáveis;
    - cartões novos com a estimativa pela cadeia e com as janelas saudáveis acima do limiar, ao lado da faixa esperada pelo limiar;
  - "Rodar e arquivos" reconhece a reanálise, e o histórico a mostra como "reanálise com o início observado (mesmos escores)";
  - o glossário ganhou as notas dos termos novos;
  - em tela estreita, os gráficos da seção usam só o nome do ensaio, e a legenda quebra em linhas.

## Critérios de aceitação

- **Testes sem rede:**
  - o PELT acha mudanças conhecidas, nada em ruído, e respeita o segmento mínimo;
  - a escolha da penalidade e as classes;
  - no GPVS sintético, a mudança é no meio;
  - a rotulagem deixa o trecho de fora, e o atraso sai negativo quando o alarme vem antes;
  - a cadeia de Markov recupera uma cadeia conhecida;
  - a Beta confere com a forma fechada e com uma simulação;
  - o comando, a pasta nova, o registro nº 2, a recusa de pasta existente, as visões da aba e as rotas.
- **Com os dados reais:**
  - com o início nominal, a reanálise repete o `relatorio.json` oficial bit a bit;
  - os inícios são os da tabela de 30/09, com c = 4;
  - a detecção não muda, e o atraso desde o meio é o oficial;
  - a sensibilidade só muda nos ensaios de mudança clara.
- **No navegador:** a seção nova, a linha nos escores e os cartões do Resumo, nos dois temas, em 360 px sem rolagem lateral, com a exportação SVG e PNG.

## Fora do escopo

- Mudar o protocolo (percentil, divisão ou calibração maior): exigiria uma avaliação nova. A grade de percentil fica só relatada.
- Dados saudáveis novos: o GPVS não tem mais que os 52 s usados.
- A skill do mestrado e os resultados no chat, que ficam para o lote 26.
