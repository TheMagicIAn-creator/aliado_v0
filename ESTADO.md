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
- **Comandos de commit:** `tmp/lote-72/comandos-commit.txt` (dois commits: orientação; produto dos lotes 67 a 70, 72 e
  o registro do 73).
- **Decisões do pesquisador:**
  - 27/10: o nome é perguntado uma única vez pelo app; a orientação foi refeita do zero; arquivos primeiro, código
    depois;
  - 28/10: rodada com teto de 45 chamadas; o cumprimento corrigido primeiro; "Boa noite" de madrugada.

## Sem commit desde 2f3bdaa (24/10)

- Lotes 67 a 70 (specs 0067 a 0070), com o código, as specs vivas e os testes deles.
- Lote 71: `CLAUDE.md`, `WORKFLOW.md`, `ESTADO.md`, `workflows/`, `.claude/agents/revisor.md` e os ajustes no
  `AGENTS.md`, no roteiro e em `docs/migracao/skills-desenvolvimento.md`.
- Lote 72: o código, a spec 0071, as specs vivas, os testes, o README, o CHANGELOG e a revisão de 27/10.
- Lote 73: o registro da rodada na spec 0071 e no roteiro (nenhum código).
- Lote 74: `src/aliado/agent.py`, o teste em `tests/test_skills_agent.py`, a spec 0072, o NUC-05, o roteiro e o
  CHANGELOG.

## Próxima ação

Pedir a autorização da comparação com a mensagem antiga (20 chamadas). Depois dela, decidir com o pesquisador se a
mensagem fica, muda ou volta, e então se vem o nome dito como apelido ("prefere ser chamado de") ou os outros passos
da revisão de 27/10.
