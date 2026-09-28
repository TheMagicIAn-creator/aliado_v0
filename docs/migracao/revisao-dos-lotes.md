# Revisão separada dos lotes

Os lotes estão no ambiente local, ainda sem primeiro commit. Esta separação
permite revisar o resultado antes de decidir sobre versionamento, push ou PR.
O início do lote 02 foi registrado por cópias locais e hashes dos 40 arquivos
versionáveis já presentes, em `tmp/lote-02/baseline/` e `baseline.json`.
Esse snapshot auxiliar não é um commit nem faz parte do pacote.

## Lote 01 — fundação funcional

Revisar os [requisitos](../specs/0001-fundacao.md), o [mapa](README.md#lote-01--núcleo-e-especializações)
e os [resultados de validação](validacao-lote-01.md).

O recorte reúne configuração do projeto, regras de colaboração, três skills de
desenvolvimento, contratos/provedores LLM, núcleo/CLI, duas skills do AL-IAdo e
seus testes. O manifesto `lote-01.json` preserva a origem dos nove arquivos
reaproveitados e do documento do pesquisador. A fundação e os adaptadores de
execução permanecem como estavam ao iniciar o lote 02.

## Lote 02 — alterações sobre essa fundação

| Arquivos adaptados | Propósito |
|---|---|
| `AGENTS.md` | Registrar o lote autorizado e a separação entre triagem privada e memória ativa. |
| `README.md`, `docs/migracao/README.md` | Descrever o estado atual e orientar a revisão. |
| `src/aliado/skills/builtin/pesquisa-inversores/SKILL.md` | Declarar novo acervo vazio e memórias pendentes, mantendo intacto o registro de 13/09. |
| `tests/test_migration.py` | Ampliar o teste de importação para os quatro módulos e dependências web, verificando ausência de estado. |

Arquivos novos:

- `src/aliado/knowledge/__init__.py`, `src/aliado/memory/__init__.py`,
  `src/aliado/science/__init__.py`, `src/aliado/interfaces/__init__.py` e
  `src/aliado/interfaces/web/__init__.py`: somente responsabilidades documentadas.
- `docs/specs/0002-preparacao-triagem.md` e `docs/arquitetura/modulos.md`:
  requisitos e fronteiras para implantação posterior.
- `docs/ciencia/procedimentos.md` e `docs/migracao/ferramentas-lote-02.md`:
  procedimentos editáveis e destino proposto das 13 ferramentas.
- `docs/migracao/lote-02.json`, `docs/migracao/validacao-lote-02.md` e este
  documento: proveniência, verificação e separação dos lotes.

Não houve exclusão de arquivos. `pyproject.toml`, dependências, implementação da
CLI, núcleo, gateway e adaptadores não foram alterados neste lote. A reserva web
acompanha o pacote, mas seu servidor e extra de instalação serão definidos depois.

## Revisão privada das memórias

Em `data/memory-review/`, abra `README.md` para o inventário dos 30 arquivos,
`lote-02.json` para as evidências e `grupo-01.md` a `grupo-04.md` para revisar
quatro propostas por vez. Os caminhos são locais; esse conteúdo não acompanha
Git, wheel ou pedidos do agente.

Cada proposta admite preservação, reescrita, não transferência ou manutenção da
pendência. Aprovar uma proposta não implementa o armazenamento nem a ativa
automaticamente. A origem continua preservada, inclusive os arquivos sem conteúdo
útil e os resultados antigos.

## Lote 03 — diretrizes aprovadas

A triagem privada está concluída: M01–M16 aprovadas, nenhuma pendente e nenhuma
memória persistente ativa. O lote 03 incorpora princípios gerais ao núcleo e
M09–M14 ao contexto da skill de pesquisa. Os relatórios privados não são lidos
pelo agente nem distribuídos; somente os textos curados entram no contexto.

A referência de 13/09 permanece byte a byte no pacote, mas deixa de ser carregada
automaticamente. M15 é registrada na arquitetura. Os procedimentos científicos,
testes de contexto e documentação foram alinhados sem introduzir executores.

Consultar a [spec](../specs/0003-diretrizes-aprovadas.md), o
[manifesto de arquivos e decisões](lote-03.json) e a
[validação](validacao-lote-03.md). O baseline anterior ao lote 03 está em
`tmp/lote-03/baseline.json`, fora do Git; permite conferir mudanças mesmo antes
do primeiro commit e não substitui o versionamento do projeto.

## Lotes 04–06 — serviços e revisão semântica

O plano posterior foi autorizado pelo pesquisador. O lote 04 implementa biblioteca
documental, OCR local, busca híbrida e integração supervisionada ao agente. Também
separa `.env` privado de `.env.example` e corrige validação nos provedores.

O lote 05 gera revisão privada em Markdown/JSON dos 30 arquivos, com três
refinamentos propostos. As 16 decisões anteriores permanecem aprovadas e nenhuma
memória fica ativa. O lote 06 entrega cálculos gerais RAM, exportação e skill
reutilizada pela especialização. Não importa parâmetros físicos da origem.

Consultar [validação e arquivos dos lotes 04–06](validacao-lotes-04-06.md).
Os manifestos 01–03 registram os bytes nas respectivas entregas; mudanças
posteriores não reescrevem esses registros históricos.

## Lote 07 — decisões registradas e cenários por componente

As três propostas privadas foram decididas: A01 aprovada como correção do serviço;
A02 e A03 não transferidas. Nenhuma memória persistente foi ativada. As taxas e as
duas bases temporais foram escolhidas; os oito cenários analisam componentes
isolados. A execução exploratória foi registrada na
[validação do lote 07](validacao-lote-07.md); as taxas ainda não foram reconferidas
nos PDFs. A instalação em `.claude/skills/` orienta o desenvolvimento no Claude
Code e não acrescenta skills ao runtime do AL-IAdo.

## Lote 08 — correções da revisão

O hook passa a analisar o campo de comando do JSON, reconhece opções globais do
Git e não reproduz conteúdo potencialmente sensível nas mensagens. O texto do
serviço e do guia distingue tempos em anos, h(t) em 1/ano e probabilidades sem
unidade. Os cálculos e as decisões científicas do lote 07 permanecem preservados.
O pacote é reconstruído com o runtime atual. Consulte a
[spec](../specs/0008-correcoes-revisao.md) e a
[validação](validacao-lote-08.md).

## Ponto de participação

Escolher identificadores de modelos para a API, fornecer as novas referências
para a biblioteca e reconferir as taxas; depois, definir tempos de reparo e
revisão do NPR por perguntas e respostas. Web/upload pelo chat e MCP v1 ficam
para lotes posteriores. O pesquisador fará os commits; não houve commit, push
ou PR automático.
