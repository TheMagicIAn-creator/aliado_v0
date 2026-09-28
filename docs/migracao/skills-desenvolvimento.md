# Skills para conduzir a migração

Seleção e aplicação em 14/09/2026. O usuário esclareceu que o catálogo fornecido
se destina principalmente ao assistente que desenvolve o AL-IAdo. O propósito
imediato é revisar e versionar a transferência, com participação do usuário.

## Instalação realizada

As três skills abaixo foram lidas na íntegra e instaladas pelo `skill-installer`
do Codex, a partir de commits imutáveis, em `.agents/skills/` deste repositório.
Seus arquivos `SKILL.md` são cópias integrais das versões consultadas. A licença
MIT fornecida pelo Superpowers acompanha sua skill. As fontes, declarações de
licença disponíveis e hashes constam em [skills-desenvolvimento.json](skills-desenvolvimento.json).

| Skill | Motivo da seleção | Aplicação nesta revisão |
|---|---|---|
| [karpathy-guidelines](../../.agents/skills/karpathy-guidelines/SKILL.md) | Alterações restritas ao pedido e simplicidade. | Comparação entre origem e destino, identificação precisa das adaptações e manutenção da correção de JSON fora do lote de transferência. |
| [verification-before-completion](../../.agents/skills/verification-before-completion/SKILL.md) | Evidências antes de afirmar conclusão. | Conferência dos nove hashes da origem, dos arquivos instalados, dos documentos de decisão e do estado Git. Resultados antigos de testes continuam identificados como validação anterior. |
| [doc-coauthoring](../../.agents/skills/doc-coauthoring/SKILL.md) | Coautoria de documentação e decisões. | Uso do contexto já fornecido, revisão localizada do mapa e apresentação do recorte para avaliação do usuário. O fluxo permanece na revisão colaborativa; não houve teste com leitor independente. |

Na próxima interação, as skills instaladas ficam disponíveis à descoberta do
Codex. Nesta interação, foram usadas por leitura explícita dos arquivos conferidos.

## Compatibilidade e forma de uso

`SKILL.md` é Markdown com metadados YAML. Esse formato pode ser compartilhado,
mas instruções que dependem de ferramentas, scripts, hooks ou caminhos de uma
plataforma precisam de suporte no ambiente de destino. A especificação prevê
metadados de compatibilidade e suporte variável a `allowed-tools`.

As três selecionadas descrevem procedimentos. Não foi necessário instalar
executáveis ou credenciais para utilizá-las. Em `doc-coauthoring`, referências
a Claude e às operações `create_file`/`str_replace` são atendidas aqui pela
conversa e pelas ferramentas locais de edição do Codex. O conteúdo original
permanece preservado; essa equivalência operacional é registrada neste documento.

O ritmo combinado com o usuário prevalece: perguntas breves, aproveitamento do
contexto já conhecido e revisão por lotes. Não se reinicia uma entrevista extensa
para decisões já tomadas. Uma skill não autoriza commit, push, exclusão, chamada
paga ou ampliação de escopo.

## Demais opções do catálogo

| Grupo ou opção | Encaminhamento |
|---|---|
| Skill Creator; PDF, DOCX, PPTX, XLSX; Data Analysis | Equivalentes já disponíveis no ambiente: `skill-creator`, `pdf`, `documents`, `presentations`, `spreadsheets` e `data-analytics`. Usar quando a tarefa correspondente ocorrer. |
| OpenSpec | Continua como referência do formato de spec. CLI e scaffolding não instalados; sua adoção será uma decisão explícita do projeto. |
| Superpowers — Writing Plans | Conteúdo lido. Útil para um próximo lote de implementação; não instalado agora porque esta etapa revisa uma transferência já preparada. |
| GSD, Planning With Files, Spec-Driven Development, Allium, PAUL, BMAD | Alternativas de planejamento identificadas no catálogo. Não introduzidas em conjunto com o processo e os documentos já existentes. |
| Find Skills | Opção para descoberta futura. Nesta seleção, o PDF já forneceu as fontes e o `skill-installer` atende à instalação. |
| Grill Me, Caveman, Git Guardrails | Entrevista e concisão já orientadas pelo usuário; revisar compatibilidade dos hooks de Git Guardrails antes de qualquer adoção. As regras Git atuais estão em `AGENTS.md`. |
| Kits de programação e Improve Codebase Architecture | Avaliar diante de um problema concreto do próximo lote; não ampliar a transferência para uma refatoração geral. |
| Frontend, design e testes web | Reavaliar no lote da interface web, conforme a stack reaproveitada. |
| Segurança, MCP Builder, Claude API, Axiom | Selecionar apenas para auditoria, integração ou plataforma correspondente. Não são necessários para esta revisão. |
| Firecrawl, Last30Days e outras automações de pesquisa | Reavaliar quando definirmos busca e ingestão do novo acervo; podem exigir serviços e credenciais. |
| Marketing, música, vídeo, arte e identidade visual | Sem aplicação demonstrada ao lote atual. |

O catálogo foi relido integralmente. Os arquivos completos das skills selecionadas
e de Writing Plans foram consultados; as demais entradas não receberam auditoria
individual de seus repositórios nesta etapa.

## Skills do próprio AL-IAdo

Na entrega de 14/09, o runtime carregava somente `pesquisa-inversores` e `engenharia`, em
`src/aliado/skills/builtin/`. Ele recebe instruções e referências em texto;
ainda não executa scripts de skills nem ferramentas de pesquisa ou escrita.

Para o próximo desenho, `karpathy-guidelines` é candidata a orientar revisões de
engenharia; `doc-coauthoring`, a escrita de specs e documentos de pesquisa;
`verification-before-completion`, a conferência de evidências quando houver
ferramentas para obtê-las. A escolha e a adaptação serão discutidas com o usuário.
Nenhuma dessas três foi adicionada ao runtime nesta instalação de desenvolvimento.

## Fontes

- Catálogo do usuário: `document.pdf`, Asimov Academy, páginas 1–10.
- [Documentação oficial de skills do Codex](https://learn.chatgpt.com/docs/build-skills).
- [Especificação Agent Skills](https://agentskills.io/specification).
- Repositórios e commits de cada skill: [manifesto](skills-desenvolvimento.json).

## Instalação para o Claude Code — lote 07, 25/09/2026

O pesquisador indicou que o catálogo também se destina ao Claude Code, que lê
`.claude/skills/`, e não `.agents/skills/`. O registro de 14/09 acima permanece
como estava. Origem, commits e hashes desta instalação ficam no
[manifesto do lote 07](lote-07.json).

| Skill | Origem | Motivo |
|---|---|---|
| karpathy-guidelines, verification-before-completion, doc-coauthoring | Cópias idênticas de `.agents/skills/` | Mesmo uso do Codex, agora também no Claude Code. |
| grill-me e grilling | `mattpocock/skills`, commit `c55ee46` | Formaliza as perguntas e respostas: a decisão é do pesquisador; os fatos, o assistente busca. |
| git-guardrails-claude-code | `mattpocock/skills`, commit `c55ee46` | Os commits são do pesquisador; o hook impede o assistente de enviar ou descartar alterações Git. |

Os arquivos das skills foram lidos na íntegra e não foram alterados. `grill-me`
apenas chama `grilling`, por isso as duas foram instaladas. `grilling` recomenda
delegar a busca de fatos a subagentes; aqui o assistente faz essas consultas
diretamente, salvo pedido do pesquisador.

O script de `git-guardrails` usa `jq`, ausente nesta máquina. Sem ele, o comando
lido ficaria vazio e nada seria bloqueado. A cópia ativa em
`.claude/hooks/block-dangerous-git.sh`, na entrega do lote 07, trocava essa linha
pela busca de padrões no JSON bruto. O hook cobre as ferramentas Bash e
PowerShell e restringe só o assistente, não os comandos digitados pelo pesquisador.
Essa implementação produzia falsos bloqueios em textos e deixava passar variantes
com opções globais do Git. Foi substituída no lote 08, como descrito abaixo.

Não foram instaladas as skills de documentos (PDF, DOCX, XLSX, PPTX), Skill Creator,
MCP Builder nem Claude API, que o Claude Code já oferece nativamente. As demais
opções do catálogo seguem o encaminhamento da tabela acima, conforme a necessidade.

## Revisão de utilidade e hook — lote 08, 26/09/2026

O AL-IAdo carrega `engenharia`, `confiabilidade` e `pesquisa-inversores` a partir
de `src/aliado/skills/builtin/`. Não lê `.agents/skills/` nem `.claude/skills/`.
Essas duas pastas configuram os assistentes que desenvolvem o projeto e não
acompanham o wheel. A instalação para Claude permite que outro assistente de
desenvolvimento consulte as mesmas orientações locais.

Após a avaliação solicitada pelo pesquisador, nenhuma skill de desenvolvimento
foi copiada para o runtime: alterações pequenas, evidências, perguntas relevantes
e revisão conjunta já estão no núcleo e em `engenharia`. O fluxo extenso de
`grilling` não deve substituir a conversa concisa combinada; o hook Git depende
do ambiente Claude Code e não tem utilidade como instrução do agente de pesquisa.
As cópias instaladas foram preservadas, inclusive a versão original do script
dentro de `.claude/skills/git-guardrails-claude-code/`.

Somente o hook ativo foi adaptado: o launcher Bash chama
`.claude/hooks/check_git_command.py` com o Python da `.venv` ou um Python do PATH.
O verificador usa apenas a biblioteca padrão, lê `tool_input.command` do JSON e
bloqueia entradas inválidas sem imprimir seu conteúdo. Reconhece opções globais
do Git, flags combinadas, comandos separados e invocações literais por shells.
Bloqueia push, reset --hard, clean sem simulação, restore, checkout e exclusão
de branches. Consultas e menções como `echo "git push"` passam.

O comportamento é conservador: checkout inteiro e sintaxe com aspas atravessando
linhas podem ser bloqueados mesmo sem descarte. O hook é uma proteção auxiliar,
não uma sandbox: não resolve aliases, scripts externos ou execução dinâmica.
As regras de `AGENTS.md` continuam obrigatórias, inclusive commits pelo usuário.
O hook não se aplica ao Codex, ao runtime do AL-IAdo nem ao terminal do pesquisador.
