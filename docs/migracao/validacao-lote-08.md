# Validação do lote 08

Verificado em 26/09/2026, no ambiente local Windows/Python 3.12. As correções
seguem a [spec 0008](../specs/0008-correcoes-revisao.md) e o pedido do pesquisador.

## Resultado

| Verificação | Evidência |
|---|---|
| Regressões do hook antes da correção | 23 falhas e 20 passes nos 43 casos iniciais; comandos enviados como texto, nunca executados. |
| Suite completa após a correção | `python -m pytest -q`: **220 passaram**, incluindo 46 casos do hook e os 174 testes anteriores. |
| Análise estática | `python -m ruff check .` e `python -m ruff check .claude/hooks/check_git_command.py`: ambos sem apontamentos. |
| Pacote | Build concluído em `dist/lote-08/aliado-0.1.0-py3-none-any.whl`; 28 arquivos de runtime conferidos byte a byte com `src/aliado/`. |
| Uso isolado do wheel | Importação e preparo em diretório vazio, com bloqueio de rede, subprocessos, escrita e leitura de `.env`/estado privado; passou sem criar arquivos. |
| Conteúdo distribuído | Nenhum `.env`, `data/`, `tmp/`, `.agents/` ou `.claude/` no wheel. |
| Preservação | Manifestos 01–07 e manifesto de skills inalterados; 30 arquivos de skills/cenários conferem com o baseline. Wheel anterior preservado. |
| Origem | HEAD `21f6ddffb71d6082fd7e6a729c50636d6d85d4cb` e estado Git conferem com o início deste lote. |
| Credenciais | Busca pelos valores sensíveis configurados localmente não encontrou correspondência nos arquivos públicos; nenhum valor foi exibido. |

Os comandos Python acima usam `.venv/Scripts/python.exe`. O hash do wheel e os
hashes dos arquivos alterados ficam no [manifesto do lote 08](lote-08.json).
Evidências auxiliares: `tmp/lote-08/baseline.json`, `wheel-verification.json`
e `integrity.json`, todos ignorados pelo Git.

## Correções entregues

O hook ativo extrai `tool_input.command` do JSON e identifica variantes comuns
com opções globais do Git, flags combinadas, encadeamento e shells literais.
Consultas e texto citado são permitidos; entradas inválidas são bloqueadas.
Mensagens de bloqueio não reproduzem comandos ou credenciais. As cópias originais
das skills permanecem intactas.

No serviço científico, somente a explicação textual mudou: tempos e MTTF em
anos, h(t) em 1/ano e R(t)/F(t) adimensionais. Fórmulas, taxas, cenários e contexto
científico permanecem preservados. Os resultados exploratórios anteriores não
foram regenerados; conservam a redação histórica daquela execução.

README, mapa e revisão dos lotes distinguem decisões concluídas de pendências.
Nenhuma skill de `.claude/` foi integrada ao runtime: as orientações úteis já
estão no núcleo e em `engenharia`. A
[avaliação das skills](skills-desenvolvimento.md#revisão-de-utilidade-e-hook--lote-08-26092026)
explica a finalidade dessas pastas e os limites do hook.

## Limites e pendências

O hook é uma proteção auxiliar para o assistente Claude Code, não uma sandbox.
Não resolve aliases, scripts externos nem comandos construídos dinamicamente;
checkout inteiro e sintaxe não analisável podem ser bloqueados conservadoramente.
O teste exercitou o launcher configurado e seu verificador local; não iniciou
uma sessão real do Claude Code. As regras de colaboração continuam obrigatórias.

Permanecem a escolha dos identificadores de modelos de API, o fornecimento do
novo acervo e a reconferência bibliográfica das taxas, além das decisões sobre
reparos/NPR. Web/upload e MCP v1 seguem para etapas futuras. O lote não alterou
memórias privadas nem ativou memória persistente; não executou cenários reais ou
chamadas pagas. Não houve commit, push, PR ou exclusão de arquivos do projeto.
O pesquisador fará os commits.
