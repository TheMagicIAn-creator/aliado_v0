# Spec 0003 — transferência das diretrizes aprovadas

Data: 22/09/2026. **Implementação local concluída e validada; resultado para revisão.**
O usuário aprovou o recorte apresentado nesta especificação. A preparação anterior
criou somente esta spec; o lote autorizado agora incorpora as diretrizes ao agente.

## Problema e resultado esperado

A triagem privada terminou com M01–M16 aprovadas e nenhuma memória ativa.
Antes deste lote, o agente carregava o registro histórico de 13/09 e orientações
anteriores à conclusão da triagem. As decisões aprovadas passam a orientar o
contexto enviado ao modelo, conforme a validação do lote.

O lote proposto transfere essas decisões como instruções curadas e referências
editáveis, aproveitando o carregador de skills existente. Ao preparar uma
pergunta de pesquisa, o AL-IAdo receberá o protocolo aprovado, com seus limites.
Uma pergunta geral continuará sem conteúdo do mestrado.

O benefício deste lote é atualizar o contexto efetivamente enviado ao modelo.
Ele não entrega cálculos, busca, indexação, treinamento ou memória persistente.

## Módulos e decisões transferidas

| Destino | Decisões | Tratamento proposto |
|---|---|---|
| Núcleo (`aliado.agent`) | M01–M08 e M16 | Incorporar os princípios gerais às instruções existentes: modularidade, evidência, cálculo verificável, proveniência, participação, preservação das entradas e comunicação das capacidades. Sem termos ou parâmetros do mestrado. |
| Skill `pesquisa-inversores` | M09–M14 | Transferir as regras científicas aprovadas para uma referência Markdown, declarada pela skill; atualizar suas instruções e eliminar orientações operacionais superadas. |
| Documentação de arquitetura | M15 | Registrar MCP reservado para v1, com serviços independentes da integração. Não transformar decisão arquitetural em conteúdo repetido em todas as perguntas. |
| Documentação científica e de migração | M01–M16 | Alinhar procedimentos e registrar a correspondência entre decisões e destinos, sem copiar conversas ou evidências privadas. |

As decisões gerais entram na instrução já existente do núcleo. Não criar um
novo carregador, banco de regras ou dependência apenas para este lote.
As skills de desenvolvimento continuam em `.agents/skills/`; o AL-IAdo recebe
somente orientações compatíveis com suas capacidades textuais atuais.

## Conteúdo científico a incorporar

- **M09:** detecção, criticidade FMECA e confiabilidade física são resultados
  distintos; não inferir redução de falhas ou aumento de vida útil do detector.
- **M10–M11:** seleção pela cobertura GPVS, comparação Denso versus AE-LSTM sob
  protocolo comum e FMECA independente, com os quatro grupos aprovados.
- **M12:** confiabilidade fundamentada na literatura, com apoio de Lafraia;
  horizonte de 20 anos onde aplicável, substituível pelo solicitado pelo usuário.
  Sem dados próprios de vida útil, não apresentar ajuste empírico de Weibull/RUL
  a partir de instantes de injeção ou severidade. A regra orienta planejamento
  textual; a alteração de parâmetros de um executor pelo chat continua futura.
- **M13:** métricas principais comuns e conclusões por objetivo, sem obrigação
  de vencedor único, pontuação agregada ou escolha retrospectiva favorável.
- **M14:** 50/15/15/20 antes dos intervalos de separação e p99 na calibração
  saudável de cada modelo como referência inicial configurável; escolhas
  congeladas antes do teste final. Teste saudável mede falsos alarmes, e ensaios
  com falhas avaliam detecção. Sequências e intervalos exigem verificação na
  futura implementação. Não prometer 1% de falsos alarmes em novos dados.

Preservar os limites e qualificações dos textos aprovados. Este lote não
escolhe taxas, NPR, orçamento de treino, novas métricas ou novos parâmetros.
Citar Lafraia como fundamento aprovado não significa que o agente tenha acesso
ao PDF: o acervo continua vazio até sua ingestão em etapa própria.

## Arquivos previstos na implementação

Os caminhos desta tabela são relativos à raiz do projeto. A lista delimita o
lote proposto; apenas esta especificação foi criada durante o planejamento.

| Arquivo | Alteração prevista |
|---|---|
| `src/aliado/agent.py` | Ajustar somente as instruções gerais, preservando APIs e montagem dos pedidos. |
| `src/aliado/skills/builtin/pesquisa-inversores/SKILL.md` | Atualizar versão, instruções e referência declarada para as decisões vigentes. |
| `src/aliado/skills/builtin/pesquisa-inversores/references/diretrizes-aprovadas-2026-09-22.md` | Criar referência curada M09–M14, sem transcrições privadas, caminhos pessoais ou resultados históricos. |
| `docs/ciencia/procedimentos.md` | Alinhar procedimentos ao texto aprovado e apontar para a referência vigente, evitando outra cópia integral do protocolo. |
| `docs/arquitetura/modulos.md` | Distinguir instruções curadas de memória persistente e registrar MCP na v1. |
| `docs/migracao/README.md` e `docs/migracao/revisao-dos-lotes.md` | Atualizar o estado da triagem e descrever o recorte do lote 03. |
| `docs/migracao/lote-03.json` | Criar manifesto com IDs das decisões, destinos, tipo de adaptação e hashes dos artefatos entregues; sem extratos privados. |
| `docs/migracao/validacao-lote-03.md` | Registrar verificações executadas e limites observados. |
| `docs/specs/0003-diretrizes-aprovadas.md` | Atualizar o estado após aprovação e após implementação verificada. |
| `tests/test_skills_agent.py` e `tests/test_migration.py` | Ajustar expectativas de contexto e verificar isolamento, preservação histórica e ausência de carregamento privado. |
| `AGENTS.md` | Registrar o lote 03 somente depois da autorização do usuário. |

O arquivo `references/decisoes-2026-09-13.md` permanece byte a byte como
histórico, mas deixa de ser declarado para carregamento automático pela skill.
Continuará no repositório e no pacote conforme a regra de empacotamento atual.
A referência vigente será carregada em seu lugar, evitando instruções conflitantes.

Os módulos `memory`, `knowledge`, `science` e `interfaces.web` permanecem com as
fronteiras já reservadas. Não há importação automática da triagem privada.
As regras curadas passarão a orientar os pedidos; isso deve ser comunicado como
alteração do contexto ativo, sem afirmar ativação de memória persistente.

## Proveniência e limites da transferência

A base desta curadoria são as 16 decisões aprovadas pelo pesquisador, com
evidências guardadas na revisão privada. O manifesto público identifica IDs e
destinos; não publica conversas, PDFs, dados pessoais ou o relatório privado.

Os manifestos dos lotes 01 e 02 conservam o commit-fonte
`55c44df6bda807b73c4ac3762f0a89734633d384`. A consulta recente do código para M14
foi feita em `2743c7318edfb44447446606ca47aa5d5e9ed372`, sem substituir aquela
proveniência. O commit histórico não estava resolvendo no clone local durante
a revisão; qualquer futura cópia de código exige conferir uma fonte imutável
acessível e registrar seu hash. Este lote não copia código científico da origem.

## Critérios de aceitação

| ID | Resultado verificável |
|---|---|
| D01 | Cada decisão M01–M16 possui destino explícito no manifesto, sem promoção de evidências históricas a novas conclusões. |
| D02 | Pedidos sem skill e com `engenharia` não recebem GPVS, FMECA, p99 ou horizonte de 20 anos como instruções de domínio. |
| D03 | A skill de pesquisa carrega a referência aprovada; o registro histórico não entra automaticamente nos pedidos e seu hash permanece igual ao manifesto do lote 01. |
| D04 | Nenhum conteúdo de `data/memory-review/` ou `tmp/` é lido para preparar pedidos ou incluído no wheel. |
| D05 | CLI, contratos e gateway preservados; nenhuma ferramenta é anunciada e nenhum serviço é inicializado pela importação. |
| D06 | O wheel contém a nova referência e permite preparar pedidos fora da pasta do projeto, sem rede ou credenciais. |
| D07 | Documentação distingue instruções atuais, capacidades implementadas e requisitos futuros; nenhuma execução científica ou consulta bibliográfica é alegada. |

Na implementação, executar `.venv/Scripts/python.exe -m pytest` e
`.venv/Scripts/python.exe -m ruff check .`; construir e inspecionar o wheel,
com preparação offline de pedidos em diretório separado. Revisar a coerência
dos textos com as decisões aprovadas. Testes de contexto verificam o material
enviado ao modelo, não garantem a qualidade de suas respostas científicas.

Na preparação desta spec, conferir somente escopo, caminhos e preservação dos
arquivos existentes. Não apresentar resultados antigos de testes como novos.

## Participação e entrega

O usuário autorizou este recorte de implementação em 22/09/2026.
Arquivos e verificações estão no [manifesto](../migracao/lote-03.json) e no
[relatório de validação](../migracao/validacao-lote-03.md), para revisão.
Commit, push e PR permanecem decisões posteriores
sobre o resultado concreto. Não instalar dependências, importar acervo, excluir
arquivos ou executar ciência como efeito desta aprovação.
