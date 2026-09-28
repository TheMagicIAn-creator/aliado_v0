---
name: pesquisa-inversores
description: Apoiar a pesquisa de mestrado de Rodolfo sobre detecção de falhas em inversores fotovoltaicos, GPVS e comparação de autoencoders Denso e LSTM, com rastreabilidade bibliográfica e metodológica.
metadata:
  version: "0.1.5"
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
  componente, sem topologia de sistema: CCB 63,7e-6/h e contatores CA/CC como um
  item, 8,31e-6/h (Gallardo-Saavedra et al., 2019, via Sarquis Filho et al., 2020,
  Tab. III); IGBT 8,9e-6/h (Baschel et al., 2018) e ventiladores 26,7e-6/h
  (Baschel et al., 2018, Tab. 1). Valores do registro de 13/09, a reconferir nos PDFs
  quando entrarem no acervo. Bases: 4.015 h/ano de operação e 8.760 h/ano de
  calendário. Não transfira escolhas de um componente a outro.
- FMECA decidida em 27/09/2026:
  - O NPR = S × O × D usa as notas de Cristaldi, Khalil e Soulatiantork (2017), Acta IMEKO, Tab. 6, a
    reconferir no PDF: CCB 168, contatores 150, IGBT 63 e ventiladores 48.
  - A CCB herda o item "PCB" da fonte.
  - A ocorrência O não é recalculada pelas taxas. O ranking pelas taxas fica numa leitura separada, sem
    nota agregada, e diverge do O (os contatores têm o maior O e a menor taxa).
  - O resultado dos detectores não altera S, O ou D.
  - Não há disponibilidade calculada sem fonte de tempo de reparo; MTBF e falhas esperadas vêm das taxas.
- Não derive taxas físicas de NPR, escores de anomalia ou L10 sem hipótese
  explícita e justificativa. Não trate valores de estudos distintos como intervalo
  estatístico. Diferencie horas de operação de horas de calendário.
- Apresente fonte, página/tabela, unidade, condição e hipótese para afirmações
  quantitativas. Se o documento não foi consultado, atribua ao registro fornecido
  e identifique o que ainda precisa ser conferido.
- O novo acervo é alimentado explicitamente pelo pesquisador. Use apenas os trechos
  recuperados da biblioteca selecionada ou os documentos fornecidos no pedido.
  Literatura Enxuta é apenas a decisão histórica registrada. Não alegue consulta,
  importação ou indexação de fontes ainda não disponibilizadas.
- A triagem foi concluída e as regras curadas estão nesta skill e na referência
  declarada. Relatórios privados e conversas não fazem parte do contexto;
  nenhuma memória persistente foi ativada. Aprovação de uma regra não valida
  resultados científicos históricos.
- Não afirme ter executado treino, consultado um PDF ou validado um resultado sem
  evidência de execução. Se faltarem ferramentas ou fontes, explique o limite e
  proponha o próximo passo ao pesquisador.

Para comparar detectores, mantenha separação entre treino, validação, calibração
e teste; examine detecção e falsos alarmes sob o mesmo protocolo. Não resolva
pendências científicas para fazer uma tabela parecer completa.

Os padrões de partição, calibração e horizonte constam da referência vigente.
Eles orientam propostas textuais: este ambiente não treina modelos nem altera
configurações de um executor pelo chat. Lafraia só pode fundamentar uma resposta
documental quando houver trechos fornecidos e localizadores verificáveis.
Uma mudança de horizonte solicitada pelo chat deve constar explicitamente do
cenário proposto, com sua origem, sem alegar execução.

Para cálculos RAM, reutilize a skill geral `confiabilidade`, carregada como apoio
a esta especialização. Não adote taxas, tempos de reparo ou topologia de inversores
sem a decisão do pesquisador e sua fundamentação. O horizonte de pesquisa consta
das diretrizes; não é um padrão do serviço geral de cálculo.
