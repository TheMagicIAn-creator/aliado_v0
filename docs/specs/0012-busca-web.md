# Lote 12 — busca na web

Lote do [roteiro da v0](../roteiro-v0.md), autorizado em 26/09/2026 depois de perguntas
e respostas. As decisões são do pesquisador.

## Decisões

| Tema | Decisão |
|---|---|
| Quando buscar | Interruptor "Buscar na web" por pergunta. Ligado, o Gemini decide se precisa buscar. |
| Autocorreção | Botão "Conferir na web" em cada anotação, e revisor que anota fatos da web nas respostas com busca. |
| Biblioteca e web | Podem ficar ligadas juntas. Cada afirmação precisa de fonte (PDF ou web); citação de PDF inventada bloqueia a resposta. |
| Domínios | Nenhuma exclusão por ora. O painel mostra o domínio de cada fonte. |

## Escopo implementado

- **Busca integrada do Gemini** (grounding): ligada só quando `LLMRequest.web_search`
  é verdadeiro. O adaptador lê fontes (uri, título, domínio), consultas e trechos
  sustentados, também no modo fluxo. Não combina com saída JSON estruturada. A
  capacidade `web_search` só existe nos modelos Gemini; outros provedores recusam.
- **Agente:** instrução própria para a web, que pede fontes primárias, proíbe listas
  de fontes no texto e manda apontar divergências sem alterar decisões. Marcas `[Wn]`
  ao fim de cada trecho sustentado. Com biblioteca e web juntas, uma resposta sem
  `[K…]` vale se a busca trouxe fontes (`web_grounded`), e uma biblioteca sem trechos
  não bloqueia a resposta.
- **Conferência de anotação** (`check_memory`): formato de texto fixo (veredito,
  correção, explicação), porque o Gemini não combina busca e JSON. Sem fonte da web, o
  veredito é sempre "inconclusivo". Uma correção entra como dedução pelas regras do
  lote 11: supera outra dedução, mas contra uma anotação do usuário vira conflito.
- **Interface:** interruptor ao lado de "Usar biblioteca", números da web em outra cor,
  painel com "Seus documentos" e "Na web" (com as buscas feitas), "N buscas na web" na
  resposta, e botão "Conferir na web" com veredito, explicação e fontes no cartão.
- **Uso:** o registro conta as buscas (`web_queries`) sem guardar o texto delas; o
  terminal mostra a contagem.

## Critérios de aceitação

- Testes sem rede: adaptador, fluxo, capacidade, marcas, validação combinada, uso,
  revisor com fonte da web, conferência e rotas.
- Validação real: uma resposta com busca e fontes, e uma conferência de anotação
  aplicando a regra de conflito.
- Suite completa e Ruff passam.

## Fora do escopo

Lista de domínios excluídos (pode ser ligada depois), busca por outros provedores e
conferência automática periódica da memória.
