# Lote 06 — serviço científico geral

Plano autorizado na conversa; implementação local para revisão em 25/09/2026.

## Escopo implementado

O módulo `aliado.science` recebe um cenário JSON explícito. Oferece confiabilidade
exponencial e Weibull de dois parâmetros (R, F, h e MTTF), série e paralelo ativo
independentes, mantenabilidade exponencial e disponibilidade inerente estacionária.
Parâmetros, fontes, hipóteses e unidade temporal são obrigatórios. Não ajusta dados.

O serviço é geral; não contém taxas de inversores, topologia predefinida ou horizonte
padrão. A skill `confiabilidade` orienta o planejamento e interpretação; a
especialização `pesquisa-inversores` a reutiliza. O horizonte de 20 anos e sua
substituição por solicitação do pesquisador continuam na especialização.

O CLI `ciencia calcular` executa apenas o cenário fornecido e exporta JSON, CSV e
Markdown, com PNG opcional, em diretório novo explícito. Não há execução científica
autônoma pelo chat, treinamento de detectores ou ferramenta MCP neste lote.

## Critérios e limites

Verificar exemplos analíticos, probabilidades, extremos numéricos, unidades,
proveniência, distinção MTTF/MTBF, restrições dos modelos e recusa de sobrescrita.
Validação somente com cenários sintéticos; não representa resultados do mestrado.

As escolhas físicas — taxas, reparos e representação dos componentes — serão
feitas com Rodolfo em perguntas e respostas apoiadas na literatura selecionada.
Não há escolha automática ou herança do catálogo antigo.

Contrato, fórmulas e exemplos: [guia científico](../ciencia/confiabilidade.md).
