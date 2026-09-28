# Lote 11 — memória persistente

Lote do [roteiro da v0](../roteiro-v0.md), autorizado em 26/09/2026 depois de três
rodadas de perguntas e respostas. As decisões são do pesquisador.

## Decisões

| Tema | Decisão |
|---|---|
| O que anotar | Revisor automático (Flash-Lite) depois de cada resposta, mais o pedido explícito ("lembre que…") e o botão "Lembrar". |
| Tipos | Preferência, correção, fato com fonte e decisão. |
| Origem | O que o usuário disse (feedback ou comando) vale na hora. As deduções do agente valem marcadas como "inferida" e revogáveis. |
| Conflito | Feedback vence dedução. Dedução contra feedback vira **conflito**; a anotação do usuário continua valendo até a decisão dele. Dedução vence dedução. |
| Chat × skill | Uma decisão explícita do usuário no chat vale na hora e fica marcada "diverge da skill", para ser incorporada à skill num lote. Deduções nunca contrariam skills. |
| Recuperação | Preferências sempre (até 10). As demais por semelhança com a pergunta, até 8, na skill ativa ou globais. |
| Escopo | Etiqueta por skill; preferências valem em todas. |
| Transparência | Aba Memória, e aviso na resposta: "usou N memórias · N anotações novas". |
| Ficha de leitura | Ao indexar um PDF, o Flash-Lite cria um resumo e até 8 fatos com página, como anotações inferidas. |
| Conversas apagadas | Não apagam a memória: a anotação guarda o próprio texto, o trecho e o título da conversa. |

## Escopo implementado

- `aliado.memory.store.MemoryStore`: SQLite em `data/memoria/`, fora do Git, com uma
  transação por operação. Anotações nunca são apagadas: edição e correção criam versão
  nova (a anterior fica "superada"), revogar muda o estado, e o histórico mostra a
  cadeia. A busca usa o mesmo modelo local da biblioteca; sem ele, cai na ordem recente.
- `aliado.memory.reviewer`: revisor da troca e ficha de leitura com saída JSON
  estruturada. O modelo só propõe. O código valida tipo, origem (fato nunca é
  feedback), citação existente, página existente, substituição de uma anotação
  recuperada e divergência apenas em decisão do usuário.
- `agent.py`: as anotações entram como regras (developer) e dados (user), antes do
  histórico. A instrução geral deixou de afirmar que não há memória.
- Interface: evento `memoria` depois do `fim`, sem atrasar a resposta; aba Memória com
  filtros, contagens, origem, histórico, editar, revogar e resolver conflitos; selo de
  conflitos no trilho; painel "Memória nesta resposta"; janela "Lembrar". O envio de
  PDF leva a skill ativa para a ficha.
- O revisor e a ficha entram no registro de uso (`memoria-revisor`, `memoria-ficha`).

## Critérios de aceitação

- Testes sem rede das regras de origem, conflito, versões, busca, validação do revisor
  e da ficha, contexto do agente, rotas e independência em relação às conversas.
- Validação real: uma preferência dada numa conversa aparece e é usada numa conversa
  nova, e o envio de um PDF gera a ficha com página.
- Suite completa e Ruff passam.

## Fora do escopo

Importação das memórias antigas (v1), busca na web (lote 12) e incorporação automática
de decisões divergentes às skills, que é feita num lote de desenvolvimento.
