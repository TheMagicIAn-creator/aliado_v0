# Diretrizes aprovadas — pesquisa em inversores

Revisão de 22/09/2026. Regras de transferência aprovadas pelo pesquisador,
curadas para orientar esta especialização. Não são resultados experimentais,
fontes bibliográficas consultadas pelo agente ou autorização para executar
ferramentas. A execução atual oferece somente inferência textual.

## M09 — Detecção e risco físico são conceitos distintos

Manter desempenho de detecção, criticidade FMECA e confiabilidade física como resultados distintos. Nem um detector de DL/ML nem o índice de detecção da FMECA comprovam, por si só, redução de falhas ou aumento de vida útil. Métricas do detector não alteram automaticamente S/O/D, NPR ou taxas de falha; uma revisão física exige evidência e decisão próprias.

## M10 — Prioridade do contator CA por NPR

Selecionar os ensaios pela cobertura do GPVS, usando o mesmo protocolo para os dois autoencoders. A prioridade automática do contator por NPR deixa de orientar os experimentos.

## M11 — Recorte de componentes e experimentos

Manter FMECA e avaliação com GPVS como análises independentes, sem comparação entre elas nem correspondência física presumida. A FMECA conserva os quatro grupos do registro de setembro: placa de controle e comunicação (CCB), contatores CA/CC, módulo IGBT e ventiladores. A avaliação com GPVS mantém a comparação Denso versus AE-LSTM, com protocolo próprio.

## M12 — RUL, Weibull e eixo de tempo

Fundamentar a confiabilidade física na literatura, com apoio metodológico de Lafraia; não há registros próprios de vida útil, horas até falha ou acompanhamento sem falha disponíveis neste estudo. Usar horizonte padrão de 20 anos nas análises em que se aplica, substituível pelo prazo explicitamente solicitado pelo pesquisador via chat. Registrar o horizonte efetivo, a base temporal, o modelo, os parâmetros, as fontes e as hipóteses em cada resultado. Taxa constante exige justificativa; projeções bibliográficas são condicionais às suas hipóteses. GPVS permanece fonte experimental para detecção; seus instantes de injeção, severidades e atrasos não são dados físicos de vida útil nem base para ajustar Weibull ou RUL dos componentes.

## M13 — Objetivo e métricas de avaliação

Aplicar o mesmo conjunto principal de métricas a Denso e AE-LSTM, sob protocolo comparável, apresentando as vantagens e limitações de cada modelo. As perguntas de pesquisa e os objetivos explícitos orientam qual modelo é mais apropriado; podem existir conclusões diferentes por objetivo ou ausência de vencedor único. Não criar pontuação agregada nem escolher critérios retrospectivamente para favorecer um modelo. Não herdar prioridade universal de AUC, metas de 95% ou rankings antigos.

## M14 — Partições, calibração e limiar

Preservar, como referência inicial reproduzível da especialização GPVS, a divisão temporal atual de 50% treino, 15% validação, 15% calibração e 20% teste saudável, antes dos intervalos de separação. Treino ajusta o modelo e o normalizador compartilhado; validação orienta a escolha da época de treinamento; calibração saudável separada define o limiar p99 de cada modelo; teste saudável mede falsos alarmes, e ensaios com falhas avaliam a detecção. Manter as mesmas regras de partição e avaliação para Denso e AE-LSTM. Documentar e preservar inicialmente a construção de sequências dentro de cada bloco e os intervalos existentes; sua adequação à dependência temporal deverá ser verificada na implementação. Percentuais, sequência e percentil são parâmetros explícitos e revisáveis, não regras universais nem garantias de desempenho. Congelar as escolhas antes da avaliação final; não ajustar parâmetros pelos resultados do teste. Registrar e versionar mudanças de protocolo, preservando configurações e resultados anteriores e prevendo avaliação independente se um teste já consultado orientar mudanças. A aprovação desta regra encerra a triagem de M14, sem exigir novo experimento neste lote; migração executável e verificação do protocolo pertencem a lote posterior combinado.

## Aplicação e limites atuais

Situação atualizada em 30/09/2026. As regras acima orientam o planejamento e a
interpretação; a execução fica fora do chat. O preparo, o treino e a avaliação do
GPVS, a FMECA e a confiabilidade rodam na aba Ciência do AL-IAdo, com protocolo
registrado; o treino e a avaliação oficiais são de 27/09/2026. P99 na calibração
não garante 1% de falsos alarmes em dados novos.

O acervo é alimentado pelo pesquisador e inclui o manual de Lafraia, que só
fundamenta uma resposta com trechos recuperados e localizadores verificáveis. As
taxas e as notas da FMECA foram conferidas nos PDFs do acervo em 30/09/2026. Um
pedido para usar outro horizonte deve ser refletido no plano, sem alegar alteração
de arquivos ou cálculos executados. Valores físicos, condições de aplicação,
unidades e fontes precisam ser conferidos antes de produzir cenários numéricos. Não
reutilizar taxas, NPR, métricas, pesos ou resultados antigos por omissão.
