---
name: confiabilidade
description: Formular cenários e interpretar cálculos de confiabilidade, mantenabilidade e disponibilidade inerente, com parâmetros fornecidos e hipóteses explícitas.
metadata:
  version: "0.1.1"
---

# Confiabilidade, mantenabilidade e disponibilidade

Use esta skill para organizar entradas e interpretar resultados do serviço
`aliado.science`. Ela não fornece taxas físicas nem ajusta distribuições a dados.
O chat prepara o cenário; a execução exige o comando explícito `aliado ciencia calcular`.
Nunca apresente um cenário proposto como cálculo já executado.

- Defina a pergunta, o tipo de sistema e a unidade temporal antes de escolher o
  modelo. Peça parâmetros ausentes; registre fonte, página/tabela e condições de uso.
  Diferencie tempo de calendário, tempo de operação e tempo ativo de reparo.
- Para vida exponencial, a entrada `rate` é uma taxa por unidade de tempo, positiva
  e constante. Para Weibull de dois parâmetros, `shape` é adimensional e `scale`
  tem a unidade do tempo. A escolha exige justificativa física ou bibliográfica.
  Taxa não é probabilidade: nunca a apresente como porcentagem nem a converta de
  cabeça. Para taxa em 1/h e horizonte em anos, use `time_base` e cite o F(t)
  calculado pelo serviço, com horizonte e horas por ano.
- O serviço calcula R(t), F(t), h(t) e MTTF para esses modelos. MTTF é tempo médio
  até falha; não substitua automaticamente o MTBF de um sistema reparável.
- Série e paralelo ativo exigem componentes independentes e topologia explícita.
  Série falha com o primeiro componente; paralelo funciona enquanto pelo menos um
  componente funciona. Causas comuns, standby e compartilhamento de carga ficam
  fora dessas fórmulas. Não deduza a topologia só pelo nome do equipamento.
- Mantenabilidade exponencial usa `mttr > 0` e representa a probabilidade de
  concluir o reparo até t, sob taxa constante. Não confunda com confiabilidade.
- Disponibilidade inerente estacionária usa MTBF/(MTBF+MTTR), considerando apenas
  operação e manutenção corretiva ativa. Exclui preventiva, espera logística e
  atrasos administrativos; não é disponibilidade operacional. MTTR zero é um limite ideal.
- Exija `sources` e `assumptions` junto dos parâmetros. Todos os tempos devem usar
  a mesma unidade (`s`, `min`, `h`, `day` ou `year`); fora de `time_base`, o serviço
  não converte unidades.
  Não preencha um horizonte ausente por conta própria.
- Resultados são condicionais ao cenário. Fontes registradas não equivalem a
  fontes verificadas. Não transforme uma projeção em comprovação empírica.

Use JSON para entradas estruturadas e JSON/CSV/Markdown para saídas revisáveis.
O serviço pode produzir PNG; não sobrescreve um diretório de resultados existente.
Preserve o registro da execução e suas limitações ao explicar as curvas.
