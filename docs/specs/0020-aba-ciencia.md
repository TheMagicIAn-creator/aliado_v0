# Lote 20 — aba Ciência: resultados, exploradores e cálculos

Lote autorizado em 28/09/2026. Cumpre a decisão de que a aba Ciência faz tudo pela interface
(28/09) e foi separado do GPVS pela interface, que fica para o lote 21. A versão 0.2.0 sai no
fim do lote 21.

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Alcance da aba | Tudo pela interface, com gráficos, tabelas e exploradores com dados reais, no estilo do explicador de k e limiar. |
| Divisão | **Dois lotes.** Lote 20: resultados, exploradores, confiabilidade e FMECA. Lote 21: GPVS pela interface (preparar, treinar e avaliar). |
| Explorador de alarme e detecção | Pode usar o teste e os ensaios com falha, com a faixa "exploração pós-teste, não canônica (M14)". |
| Nova avaliação do GPVS (lote 21) | **Permitida com registro:** aviso, confirmação explícita e registro da consulta; a avaliação oficial continua a de 27/09. |
| Confiabilidade | **Explorar livre, salvar com fonte:** os controles recalculam sem gravar; salvar como cenário exige fonte e hipóteses. |

## Escopo implementado

- **Exploradores** (`science/explorer.py`):
  - carregam a rodada canônica pela própria avaliação (`gpvs-avaliacao-001` → `gpvs-modelos-002`), com os hashes de configuração, pesos e dados conferidos;
  - reaproveitam `segment_errors`, `top_k_scores`, `calibrate_threshold` e `run_metrics`, sem reimplementar contas;
  - calculam o erro por variável de cada janela uma vez, para os 10 modelos, e o guardam em `data/ciencia/erros-<hash do treino>.npz`, com os hashes do treino e dos dados;
  - não alteram nada em `data/resultados`.
- **Refatoração mínima:** `evaluation.segment_errors` separa o cálculo do erro de `score_segment`, que continua dando os mesmos escores.
- **Explorador do limiar:**
  - só usa a calibração;
  - controles: modelo, semente, k de 1 a 24 e percentil de 90 a 99,9;
  - mostra os escores reais ordenados, o limiar, a posição, o percentil efetivo, as janelas acima e o falso alarme esperado;
  - avisa quando o percentil cai no maior escore;
  - mostra também o erro das 24 variáveis de uma janela escolhida, com as k maiores em destaque.
- **Explorador de alarme e detecção:**
  - controles: modelo, semente, k, percentil e m de 1 a 10;
  - mostra detecções, atraso mediano e falsos alarmes no teste saudável (com o limite superior) e no pré-falha;
  - a tabela dos 14 ensaios traz a coluna canônica;
  - a linha do tempo de um ensaio tem as fases, o limiar, os alarmes e o início nominal. A escala vai até 4 vezes o limiar, e os escores maiores aparecem no topo;
  - a faixa do M14 é fixa, e o botão "Voltar aos canônicos" restaura k = 5, p99 e m = 3.
- **Confiabilidade:**
  - controles de λ (1/h), horas por ano, base e horizonte, que chamam `evaluate_scenario` sem gravar;
  - os 8 cenários dos inversores servem de ponto de partida;
  - uma caixa aceita qualquer cenário em JSON;
  - salvar exige fonte e hipóteses (a fonte "exploração" é recusada) e grava numa pasta nova.
- **FMECA:**
  - a tabela, com S, O, D, NPR, λ, MTBF e F(1) e F(20) em operação;
  - as duas ordens em gráficos separados, os pares discordantes, as ressalvas e os limites;
  - o relatório numa pasta nova.
- **Resultados:**
  - lista `data/resultados`, com um nível de agrupamento, como em `lote-07/igbt-operacao`;
  - mostra o relatório em Markdown (com fórmulas) e, conforme o tipo, as curvas, os escores de calibração, a tabela por ensaio ou a medição da busca;
  - o caminho mostrado é o real.
- **Interface:**
  - `static/ciencia.js` desenha os gráficos em SVG próprio, sem biblioteca nova nem CDN;
  - o botão Ciência deixou de estar "em breve";
  - `aliado web` ganhou `--resultados` e `--gpvs`;
  - o explorador só é criado no primeiro uso da aba, e numpy e PyTorch não pesam na abertura do servidor.

## Critérios de aceitação

- **Testes:**
  - com os dados reais, os exploradores reproduzem exatamente a avaliação de 27/09 nos 10 modelos e sementes: limiar, detecções, atrasos, falsos alarmes e sensibilidade;
  - o mesmo vale para as grades de sensibilidade de m e k da semente de referência;
  - a confiabilidade repete o cenário do IGBT;
  - as rotas de resultados, cenários e FMECA gravam só em pasta nova e exigem fonte para salvar;
  - o acesso a pastas fora dos resultados é recusado.
- **Aceite no navegador:** as cinco seções, sem chamadas pagas, gravando só numa cópia dos resultados.
- A suíte completa e o Ruff passam.

## Fora do escopo

- Preparar, treinar e avaliar o GPVS pela interface, com progresso e o registro de nova consulta ao teste: lote 21.
- O chat chamar os cálculos: o serviço continua sendo acionado pelo usuário.
