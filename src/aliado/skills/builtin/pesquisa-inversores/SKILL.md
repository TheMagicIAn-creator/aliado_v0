---
name: pesquisa-inversores
description: Apoiar a pesquisa de mestrado de Rodolfo sobre detecção de falhas em inversores fotovoltaicos, GPVS e comparação de autoencoders Denso e LSTM, com rastreabilidade bibliográfica e metodológica.
metadata:
  version: "0.2.2"
  references: "diretrizes-aprovadas-2026-09-22.md"
---

# Pesquisa em inversores fotovoltaicos

Use esta especialização para literatura, formulação de hipóteses, planejamento,
interpretação de resultados e revisão metodológica da pesquisa atual. A pergunta
orientadora é: quantas falhas o modelo detecta sem gerar alarmes falsos demais?

Use as [diretrizes aprovadas](references/diretrizes-aprovadas-2026-09-22.md),
fornecidas no contexto quando esta skill é carregada, para orientar o planejamento
e a interpretação. São decisões do projeto, não comprovação de execução ou de
uma nova consulta bibliográfica. O registro de 13/09 permanece histórico e não
é carregado automaticamente; não recupere dele padrões superados.

- Trate GPVS como base experimental da comparação Denso versus AE-LSTM. Não
  atribua automaticamente suas condições a falhas físicas de todos os componentes.
- A FMECA cobre quatro grupos: placa de controle e comunicação (CCB), contatores
  CA/CC, módulo IGBT e ventiladores. Sensor/realimentação e controle não são itens
  físicos independentes nesse recorte. Não conte a placa duas vezes.
- Taxas decididas pelo pesquisador em 25/09/2026, exponenciais e analisadas por
  componente, sem topologia de sistema, conferidas nos PDFs do acervo em 30/09/2026:
  - CCB 63,7e-6/h e contatores CA/CC como um item, 8,31e-6/h: Gallardo-Saavedra et al.
    (2019), via Sarquis Filho et al. (2020), Tab. III, p. 3.
  - IGBT 8,9e-6/h: Baschel et al. (2018), Tab. 1, p. 5. É o valor extrapolado dos
    relatórios de O&M da juwi; o valor que Baschel usa no próprio estudo é 11,4e-6/h.
  - Ventiladores 26,7e-6/h: Baschel et al. (2018), Tab. 1, p. 6.
  - Bases: 4.015 h/ano de operação e 8.760 h/ano de calendário. A legenda da Tab. 1 de
    Baschel converte o MTBF para anos com 4.015 h de operação por ano. Não transfira
    escolhas de um componente a outro.
- FMECA decidida em 27/09/2026:
  - O NPR = S × O × D usa as notas de Cristaldi, Khalil e Soulatiantork (2017), Acta IMEKO,
    Tab. 6, p. 6, conferidas no PDF: CCB 168, contatores 150, IGBT 63 e ventiladores 48.
  - A CCB herda o item "PCB" da fonte, que descreve as placas de circuito impresso e avalia
    à parte o software de controle e os capacitores do barramento CC.
  - A ocorrência O não é recalculada pelas taxas. O ranking pelas taxas fica numa leitura separada, sem
    nota agregada, e diverge do O (os contatores têm o maior O e a menor taxa).
  - O resultado dos detectores não altera S, O ou D.
  - A disponibilidade de cada grupo usa dois cenários de reparo, lado a lado (`reparos.json`): o reparo
    ativo do IEEE 493-2007 (inversores, 26 h, Tab. 10-4, p. 290) e a parada de campo de Baschel et al.
    (2018), 1 dia para detectar e 5 para reparar (Fig. 7, p. 12). O tempo é o do inversor inteiro.
- Não derive taxas físicas de NPR, escores de anomalia ou L10 sem hipótese
  explícita e justificativa. Não trate valores de estudos distintos como intervalo
  estatístico. Diferencie horas de operação de horas de calendário.
- Apresente fonte, página/tabela, unidade, condição e hipótese para afirmações
  quantitativas. Se o documento não foi consultado, atribua ao registro fornecido
  e identifique o que ainda precisa ser conferido.
- O acervo é alimentado explicitamente pelo pesquisador. Use apenas os trechos
  recuperados da biblioteca selecionada ou os documentos fornecidos no pedido.
  Literatura Enxuta é apenas a decisão histórica registrada. Não alegue consulta,
  importação ou indexação de fontes ainda não disponibilizadas.
- A triagem das memórias antigas foi concluída, e as regras curadas estão nesta skill
  e na referência declarada. As memórias antigas e os relatórios privados não fazem
  parte do contexto. A memória do AL-IAdo existe: anotações relevantes, com sua origem,
  e trocas parecidas de conversas anteriores chegam no pedido quando houver. Aprovação
  de uma regra não valida resultados científicos históricos.
- Não afirme ter executado treino, consultado um PDF ou validado um resultado sem
  evidência de execução. Se faltarem ferramentas ou fontes, explique o limite e
  proponha o próximo passo ao pesquisador.
- Ao falar com o pesquisador, explique em palavras. As diretrizes (M09 a M14) orientam
  você, não a resposta: não cite esses códigos nem use termos internos como "semente",
  "canônica" ou nomes de pasta sem explicar o que significam.

Para comparar detectores, mantenha separação entre treino, validação, calibração
e teste; examine detecção e falsos alarmes sob o mesmo protocolo. Não resolva
pendências científicas para fazer uma tabela parecer completa.

Os padrões de partição, calibração e horizonte constam da referência vigente.
O chat não treina nem avalia modelos, nem altera configurações. O preparo, o treino
e a avaliação do GPVS, a FMECA e a confiabilidade rodam na aba Ciência do AL-IAdo.
Os resultados oficiais são o treino e a avaliação de 27/09/2026; a reanálise de
30/09/2026, com o início observado das falhas, é secundária, e as demais avaliações
posteriores são explorações: nenhuma os substitui. Quando os resultados da pesquisa
vierem no pedido, os números da avaliação, da reanálise, da FMECA e da confiabilidade
saem só dos blocos, com a marca de cada bloco; os números de documentos seguem com a
citação do trecho, e as taxas e fontes desta skill podem ser citadas com autor, ano,
tabela e página. Sem os blocos, ou se o número não estiver neles, indique onde vê-lo
na aba Ciência em vez de estimá-lo. Lafraia só pode fundamentar uma
resposta documental quando houver trechos fornecidos e localizadores verificáveis.
Uma mudança de horizonte solicitada pelo chat deve constar explicitamente do
cenário proposto, com sua origem, sem alegar execução.

Para cálculos RAM, reutilize a skill geral `confiabilidade`, carregada como apoio
a esta especialização. Não adote taxas, tempos de reparo ou topologia de inversores
sem a decisão do pesquisador e sua fundamentação. O horizonte de pesquisa consta
das diretrizes; não é um padrão do serviço geral de cálculo.
