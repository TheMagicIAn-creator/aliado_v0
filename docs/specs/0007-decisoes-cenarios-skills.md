# Lote 07 — decisões pendentes, cenários físicos e skills do Claude Code

Plano autorizado na conversa em 25/09/2026; implementação local para revisão.
As decisões abaixo foram tomadas pelo pesquisador em perguntas e respostas.

## Decisões

| Pendência | Decisão |
|---|---|
| A01 — taxa, probabilidade e porcentagem | Aprovada como **correção no serviço**: a conversão de taxa em 1/h para o horizonte em anos é feita pelo código. |
| A02, A03 | Não transferidas, para manter o AL-IAdo enxuto. Ficam só no registro privado. |
| λ do IGBT | 8,9×10⁻⁶/h (Baschel et al., 2018). |
| Contatores CA/CC | Um item, 8,31×10⁻⁶/h. |
| Base temporal | Dois cenários: 4.015 h/ano de operação e 8.760 h/ano de calendário. |
| Topologia | Só por componente, sem série ou paralelo. |
| Orientação do AL-IAdo | Nenhum Markdown novo; só editar as skills que já existem. |
| Skills do catálogo Asimov | Instaladas para o Claude Code, no projeto; runtime do AL-IAdo inalterado. |

Já decididos antes: CCB 63,7×10⁻⁶/h e ventiladores 26,7×10⁻⁶/h (registro de
13/09) e horizonte de 20 anos (M12).

## Escopo implementado

**Serviço científico.** O campo opcional `time_base` aceita apenas `exponential`
com `time_unit: "year"`. `rate` continua em 1/h; o serviço multiplica pela quantidade
de horas por ano (maior que 0 e no máximo 8.784), registra `summary.rate` em 1/ano e
descreve a conversão nas limitações. Nenhuma coluna de porcentagem foi criada:
F(t) continua entre 0 e 1. Cenários sem `time_base` mantêm a saída anterior.

**Skills do AL-IAdo, só com edições.** `confiabilidade` (0.1.1) passa a proibir a
conversão de cabeça e a apresentação de taxa como porcentagem. `pesquisa-inversores`
(0.1.4) traz os quatro λ decididos, com fonte, bases temporais e recorte por
componente, e mantém a exigência de revisão do NPR. As referências declaradas não mudam.

**Cenários.** Oito JSON em `docs/pesquisa-inversores/cenarios/`: quatro grupos em
duas bases, tempos de 0 a 20 anos, com fontes e hipóteses. Os resultados são gerados
em `data/`, fora do Git.

**Registro privado.** `data/memory-review/lote-05/` recebeu as decisões A01–A03.
A cópia anterior foi preservada em `tmp/lote-07/`.

**Assistente de desenvolvimento.** Em `.claude/skills/`, copiadas sem alteração:
karpathy-guidelines, verification-before-completion e doc-coauthoring. Baixadas
de `mattpocock/skills` no commit `c55ee46`: grill-me, grilling e
git-guardrails-claude-code. O hook `PreToolUse` para `Bash|PowerShell` em
`.claude/settings.json` usa uma cópia adaptada do script, que dispensa o `jq`,
ausente nesta máquina.

## Critérios de aceitação

- Para cada base, F(t) igual a 1−exp(−λ·h·t); recusa de `time_base` inválido ou fora de
  `exponential`/`year`; entrada não alterada.
- As taxas aparecem só no contexto da especialização, nunca no núcleo, em
  `engenharia` ou em `confiabilidade`.
- Oito cenários executados; dois valores conferidos à mão.
- Comandos Git perigosos do assistente bloqueados; comandos comuns liberados.
- `pytest` e `ruff` sem falhas; manifestos anteriores e origem intactos.

## Fora do escopo

Tempos de reparo, disponibilidade, revisão do NPR, topologia de sistema,
reconferência das taxas nos PDFs, treino de detectores e interface web.
