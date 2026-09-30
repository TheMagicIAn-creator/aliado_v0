# Procedimentos científicos editáveis

Estado: procedimentos do lote 02 alinhados às decisões aprovadas no lote 03.
O lote 06 implementa o [serviço geral de cálculos RAM](confiabilidade.md), com
parâmetros fornecidos e sem ajuste de dados. Treino e experimentos de detecção
continuam fora do escopo executável. Este documento não é carregado automaticamente.
As [diretrizes vigentes M09–M14](../../src/aliado/skills/builtin/pesquisa-inversores/references/diretrizes-aprovadas-2026-09-22.md)
são a referência carregada pela skill de pesquisa. O registro de 13/09 permanece
histórico, sem carregamento automático. As fontes do novo acervo ainda serão
selecionadas; nenhuma regra substitui inspeção bibliográfica ou validação numérica.

## 1. Descrever datasets e comparar abordagens

**Finalidade:** organizar a pergunta científica e explicar o papel das fontes
de dados e dos modelos, separando descrição de disponibilidade comprovada.

**Entradas:** pergunta, documentação do dataset, origem/versão, sinais, unidades,
rótulos, condições de coleta e protocolo proposto. No mestrado, GPVS e comparação
Denso versus AE-LSTM são o contexto atual, sem arquivos importados neste lote.

**Hipóteses:** registrar a relação entre ensaio, sinal e fenômeno observado;
não assumir que uma anomalia experimental representa cada componente físico.

**Procedimento:** identificar o dataset e seu papel; relacionar as variáveis
necessárias; distinguir descrição da fonte e arquivos disponíveis; comparar
métodos sob a mesma pergunta e evidência; listar lacunas sem completar números.

**Limites:** Markdown não verifica a existência de CSVs, extrai features ou
comprova desempenho. Não reproduzir a quantidade de features, modelos vencedores
ou métricas de textos antigos como estado atual.

**Verificação:** cada afirmação sobre dados tem fonte/versionamento; disponibilidade
tem inspeção de arquivos; comparação não mistura protocolos incompatíveis.

## 2. Executar e avaliar comparação de detectores

**Finalidade:** medir detecção e falsos alarmes com resultados reproduzíveis.

**Entradas:** dados autorizados, protocolo revisado, partições, transformações,
configurações dos modelos, sementes, critério de calibração e orçamento de treino.

**Hipóteses:** explicitar a unidade experimental e a dependência temporal;
distinguir generalização demonstrada e hipótese. O conjunto de teste não define
o limiar do detector nem os parâmetros escolhidos para favorecer o resultado.

**Procedimento:** seguir M10, M13 e M14 da referência vigente: documentar dados,
partições e dependência temporal; ajustar modelo e normalizador compartilhado
no treino, usar validação para escolha da época e calibração separada para o
limiar de cada detector. Congelar as escolhas antes do teste final. Apresentar
métricas comuns, conclusões por objetivo, proveniência e limitações, sem obrigação
de vencedor único. Mudanças motivadas por um teste consultado exigem avaliação
independente. Os parâmetros iniciais configuráveis constam de M14.

**Limites:** nenhuma execução neste lote. Não reutilizar métricas, pesos ou
limiares da origem como resultado do destino. Identificar resultados sintéticos,
de bancada e de campo. Conforme M09 e M11, detecção e FMECA permanecem análises
independentes; nem o detector nem o índice de detecção da FMECA comprovam, por si
sós, redução de falhas ou aumento de vida útil.

**Verificação:** testes numéricos e de separação das partições; rastreamento de
entradas e configurações; métricas reobtidas dos artefatos; resultados negativos
e falsos alarmes reportados. A implementação futura permanece em Python.

## 3. Construir cenários de confiabilidade

**Finalidade:** produzir cenários físicos fundamentados em fontes e condições
explícitas, respeitando o recorte de componentes aprovado.

**Entradas:** componente, taxa/parametrização, fonte, página/tabela, unidade,
condições de aplicação, base de tempo e hipótese de modelo. A referência atual
de escopo contém quatro grupos. As taxas e a FMECA foram decididas nos lotes 07 e 16; no lote 22,
as taxas e as notas foram conferidas nos PDFs, com tabela e página registradas nos cenários e na FMECA.

**Hipóteses:** se uma taxa constante for justificada, o cenário exponencial pode
ser documentado por `R(t)=exp(-lambda*t)`, `F(t)=1-R(t)`,
`f(t)=lambda*R(t)` e `h(t)=lambda`, com unidades de tempo compatíveis.
Essa descrição não escolhe valores nem valida a hipótese para um componente.

**Procedimento:** aplicar M12 da referência vigente, com horizonte padrão e
precedência do prazo solicitado pelo pesquisador. Registrar prazo, unidade, origem
da escolha, parâmetros bibliográficos e hipóteses. Conferir a evidência e eventuais
conversões antes de calcular com uma implementação testada; vincular curvas e
tabelas às mesmas entradas. O apoio metodológico de Lafraia não implica acesso
ao livro pelo agente. Não há dados próprios de vida útil: cenários bibliográficos
são condicionais, não ajustes empíricos ao GPVS. Sem evidência suficiente,
registrar a pendência e não gerar resultado físico substituto.

**Limites:** não derivar taxa física de NPR, escore de anomalia ou magnitude
de detecção. Não tratar uma faixa entre estudos como intervalo estatístico.
Não ajustar Weibull físico ou reportar RUL a partir de um eixo sem tempo de vida.
O cadastro antigo de seis itens não é a FMECA vigente do destino.

**Verificação:** unidades coerentes, domínio dos parâmetros e limites matemáticos
testados; por exemplo, para taxa positiva e tempo não negativo, `R(0)=1` e
`R(t)` não cresce. Rastrear a mesma fonte até cada figura e tabela. Esses são
critérios cobertos por testes analíticos do serviço geral no lote 06; não são
validação física dos parâmetros dos inversores ou resultados do mestrado.

## 4. Consultar resultados e verificar disponibilidade

**Finalidade:** responder com artefatos verificáveis sem disparar recálculo.

**Entradas:** pergunta, identificador do experimento, manifesto, versões de
entradas/código/configuração e arquivos de saída disponíveis.

**Hipóteses:** uma saída existente não é automaticamente atual ou aplicável ao
novo estudo. Distinguir inexistente, histórico, desatualizado e verificável.

**Procedimento:** localizar os artefatos no contexto correto; conferir manifesto
e integridade; selecionar resultados pertinentes; responder com localização e
limites; propor recálculo separadamente quando necessário.

**Limites:** consulta não treina, calibra, gera figuras, limpa arquivos ou substitui
resultados ausentes por números de uma memória antiga. Não há artefatos científicos
importados neste lote.

**Verificação:** a resposta corresponde ao artefato identificado; ausência e
desatualização são visíveis; o leitor não tem efeitos de escrita ou execução.
