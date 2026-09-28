# Lote 08 — correções da revisão do lote 07

Autorização: em 26/09/2026, o pesquisador pediu a correção dos pontos da revisão
e a avaliação da utilidade das skills de `.claude/` para o próprio AL-IAdo.

## Escopo

- Corrigir o hook ativo do Claude Code: analisar o JSON e o comando, cobrir
  variantes comuns com opções globais/flags e evitar exposição do payload.
- Corrigir a descrição das unidades: tempos e MTTF em anos da base escolhida;
  h(t) em 1/ano; R(t) e F(t) adimensionais. Preservar fórmulas e parâmetros.
- Atualizar documentação corrente com as decisões do lote 07, sem reabrir
  A01–A03, taxas ou topologia por componente.
- Reconstruir e verificar o wheel em `dist/lote-08/`, preservando o pacote anterior.
- Explicar a separação entre skills de desenvolvimento e de runtime. A avaliação
  não identificou necessidade de nova skill: o núcleo e `engenharia` já cobrem
  as orientações úteis, e `grilling`/Git Guardrails dependem de outro fluxo/ambiente.

## Arquivos e limites

Hook: `.claude/hooks/block-dangerous-git.sh`, `check_git_command.py` e
`tests/test_git_hook.py`. Runtime: apenas a descrição em `src/aliado/science/ram.py`.
Documentação: `AGENTS.md`, README, guia científico e registros de migração.

O hook inspeciona comandos Git literais; não é um interpretador completo nem
uma sandbox. Aliases, scripts e construção dinâmica de comandos continuam
dependendo da revisão do assistente. Checkout e sintaxe não analisável são
bloqueados conservadoramente. Bash e Python precisam estar disponíveis.

Não editar os manifestos 01–07, as cópias originais das skills, as memórias
privadas, os resultados anteriores ou o repositório de origem. Não executar
cenários reais, fazer chamadas pagas, instalar skills, excluir arquivos ou
realizar commit, push ou PR. O pesquisador fará os commits.

## Critérios de aceitação

- Testes enviam comandos como texto ao hook, sem executá-los. Cobrem bloqueios,
  consultas permitidas, texto citado, entradas inválidas e não exposição de segredo.
- Suite completa e Ruff passam; unidades numéricas e decisões científicas permanecem.
- Wheel contém o runtime atual, com importação/preparo isolados e sem conteúdo privado
  ou skills dos assistentes de desenvolvimento.
- Novo manifesto registra mudanças e hashes; verificações confirmam preservação
  dos manifestos anteriores e do estado Git da origem.
- Pendências reais ficam explícitas: modelos de API, acervo/reconferência das taxas,
  reparos/NPR e interfaces futuras. Nenhuma memória é ativada neste lote.
