# Estado do trabalho

Mantido pelo assistente (Claude Code ou Codex), conforme o [WORKFLOW.md](WORKFLOW.md). É um registro para retomar o
trabalho, não uma autorização: confira com os arquivos, o Git e a conversa atual antes de continuar.

## Agora

- **Data:** 28/10/2026.
- **Pedidos de hoje:**
  - a rodada do lote 72 no modelo local (lote 73), com teto de 45 chamadas: feita, com 38 chamadas locais e nenhum
    token pago, e registrada na [spec 0071](docs/specs/0071-nome-e-provedores.md). Script e resultados em
    `tmp/lote-73/`;
  - o cumprimento certo do período (lote 74, [spec 0072](docs/specs/0072-cumprimento-do-periodo.md)): feito, com 882
    testes e o Ruff passando e a revisão independente corrigida;
  - a rodada curta do cumprimento (30 das 35 chamadas autorizadas), feita e registrada na spec 0072:
    - a despedida foi corrigida, e os cumprimentos acertaram em 15 de 18;
    - 11 de 30 respostas comentam as instruções;
    - falta comparar com a mensagem antiga nas sementes 71 e 72.
- **Achados abertos:**
  - "Pode me chamar de Rô." virou a anotação "O usuário prefere ser chamado de Rô.", mas o local, na conversa nova,
    não a leu como o nome;
  - as respostas que comentam as instruções: para saber se vêm da mensagem nova, falta rodar a mensagem antiga com
    as sementes 71 e 72 (20 chamadas), o que pede autorização nova;
  - o Ollama parou duas vezes (C09 e C19). Ele se atualizou sozinho em 25/10.
- **Decisões do pesquisador:**
  - 27/10: o nome é perguntado uma única vez pelo app; a orientação foi refeita do zero; arquivos primeiro, código
    depois;
  - 28/10: rodada com teto de 45 chamadas; o cumprimento corrigido primeiro; "Boa noite" de madrugada; parar aqui
    e fazer o commit.

## Commits de 28/10 (a pedido do pesquisador)

- `3c772fd`: lote 71, a orientação do assistente (`CLAUDE.md`, `WORKFLOW.md`, `ESTADO.md`, `workflows/`,
  `.claude/agents/revisor.md`, `AGENTS.md`, `docs/migracao/skills-desenvolvimento.md`).
- `0709c73`: lotes 67 a 70 e 72 a 74, com o código, as specs, os testes, o README, o CHANGELOG e a revisão de 27/10.
- Um terceiro commit registra os dois no roteiro e aqui.
- O push fica com o pesquisador. Nenhuma tag nem versão: os lotes 67 a 74 estão em "Não lançado" no CHANGELOG.

## Próxima ação

Na próxima conversa, perguntar ao pesquisador por onde seguir:
- a comparação com a mensagem antiga nas sementes 71 e 72 (20 chamadas, pede autorização). Depois dela, decidir se
  a mensagem da hora fica, muda ou volta;
- o nome dito como apelido ("prefere ser chamado de");
- os outros passos da revisão de 27/10.
