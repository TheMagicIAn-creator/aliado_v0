# Migração dirigida do AL-IAdo

Origem: [mestrado-utfpr no commit 55c44df6](https://github.com/TheMagicIAn-creator/mestrado-utfpr/tree/55c44df6bda807b73c4ac3762f0a89734633d384).
Destino: `TheMagicIAn-creator/aliado_v0`. A origem e seu histórico permanecem intactos.

## Lote 01 — núcleo e especializações

| Parte | Tratamento |
|---|---|
| Contratos LLM | `contratos_llm.py` → `src/aliado/llm/contracts.py`: conteúdo textual preservado integralmente. |
| Base e registro | `provedores/base.py` e `registry.py` → `src/aliado/llm/providers/`: somente imports realocados. |
| Gateway | Imports realocados; Gemini exige identificador explícito de modelo, fica desabilitado sem configuração e anuncia texto/JSON. Streaming verifica configuração antes de chamar o adapter. |
| Adapter OpenAI | Imports realocados e adição de `store=False`. Responses API já era utilizada na origem. |
| Adapter Gemini | `GeminiProvider` extraído do módulo legado; integração reescrita para encaminhar contexto, instruções, papéis da conversa, schema JSON e metadados de uso diretamente ao SDK. |
| Testes da origem | Três arquivos de contratos, gateway e adapters preservados com mudança dos imports; clientes de API são simulados. Testes adicionais do destino ficam em `test_migration.py` e `test_skills_agent.py`. |
| Skill de pesquisa | Criada para o próprio AL-IAdo; carrega o registro fornecido pelo pesquisador, preservado integralmente. |
| Skill de engenharia | Criada para análise de requisitos e propostas verificáveis de software/projetos técnicos. |
| Núcleo e CLI | Nova composição pequena, sem regras do mestrado embutidas no núcleo. |

Não foram transportados menus antigos de provedores, papéis fixos do Gemini,
carregamento automático de `.env` ou identificadores de modelos presumidos.
Os aliases lógicos existentes foram mantidos como configuração de transição.
Multimodalidade e execução de ferramentas não são anunciadas pelo novo gateway.

O [manifesto](lote-01.json) registra SHA-256 dos arquivos-fonte e do registro do
usuário. Mudanças posteriores no destino serão registradas por Git após revisão.
Os hashes de origem permanecem fixos e não representam hashes do código adaptado.

### Revisão da transferência em 14/09/2026

Os nove arquivos do manifesto foram comparados com o snapshot do commit-fonte;
os nove hashes conferem. A tabela acima distingue preservação, adaptação e
composição nova. A integração Gemini é a maior adaptação deste lote: o módulo
de origem tinha 595 linhas e reunia fachada, configuração e papéis legados;
o adapter de destino tem 120 linhas. Essa diferença não mede qualidade nem
significa equivalência de todas as funcionalidades antigas.

A revisão não alterou código ou testes. A aceitação indevida de JSON `null`
pelos adapters e de resposta estruturada vazia pelo OpenAI permanece como
melhoria posterior. O caso OpenAI já existe no arquivo-fonte comparado; não
foi demonstrado que a correção seja requisito para esta transferência.

Ponto para decisão do usuário: revisar este recorte e suas adaptações antes
do primeiro commit. Os demais subsistemas abaixo continuam fora do lote 01.

## Lote 02 — preparação e triagem

Plano implementado localmente em 15/09/2026, aguardando revisão do resultado:

- Quatro módulos reservados: `knowledge`, `memory`, `science` e `interfaces.web`.
  São pacotes importáveis, com [responsabilidades documentadas](../arquitetura/modulos.md),
  sem serviços novos ou inicialização de dependências.
- Inventário dos 30 arquivos de memória do commit-fonte. Os relatórios privados
  ficam em `data/memory-review/`, fora do Git, da distribuição e do contexto do agente.
  Há 9 candidatos à preservação e 7 decisões a rever; nenhuma memória foi ativada.
  Dois arquivos contêm apenas erro de consolidação. A triagem não revalida os
  números nem a bibliografia dos resultados antigos.
- [Catálogo das 13 ferramentas](ferramentas-lote-02.md): 4 serviços gerais,
  2 orientações em Markdown, 5 interfaces científicas futuras e 2 ferramentas adiadas.
- [Procedimentos científicos editáveis](../ciencia/procedimentos.md), sem executores
  neste lote. O novo acervo segue vazio; os documentos serão fornecidos pelo usuário.
  Referências provenientes de repositórios abrangem documentação, sem indexar código.

O [manifesto](lote-02.json) identifica os arquivos inspecionados e seus hashes.
Código científico e mecanismos de memória, indexação e web não foram copiados.
Os testes e limites estão na [validação](validacao-lote-02.md), e a
[revisão dos lotes](revisao-dos-lotes.md) separa os arquivos anteriores das alterações
desta etapa. Nenhum commit, push ou PR foi criado.

## Lote 03 — diretrizes aprovadas

Implementação autorizada em 22/09/2026. A triagem privada concluiu M01–M16,
com 16 decisões aprovadas e nenhuma memória persistente ativa.

- M01–M08 e M16 incorporadas às instruções gerais existentes do núcleo.
- M09–M14 transferidas para uma referência Markdown curada da skill de pesquisa.
  O registro de 13/09 permanece intacto no pacote, sem carregamento automático.
- M15 registrada na arquitetura: MCP reservado para v1.
- Procedimentos alinhados, sem cópia de código científico, dados ou resultados.

A [spec 0003](../specs/0003-diretrizes-aprovadas.md) define o recorte; o
[manifesto](lote-03.json) mapeia decisões e arquivos, e a
[validação](validacao-lote-03.md) registra as verificações. O contexto textual
foi atualizado; a aplicação continua sem executores, RAG ou memória persistente.
Os estados descritos nos lotes anteriores são históricos de suas entregas.

## Lotes 04–06 — biblioteca, aprendizados e ciência geral

Implementação autorizada pelo pesquisador e preparada em 25/09/2026.

- Biblioteca local com PDF/MD/JSON, OCR português/inglês, versões, busca híbrida e
  citações supervisionadas. O catálogo SQLite do destino é novo e independente.
- Revisão privada dos 30 arquivos: três refinamentos semânticos aguardam decisão,
  mantendo M01–M16 aprovadas e nenhuma memória persistente ativa.
- Serviço científico RAM geral, parametrizado e testado; skill `confiabilidade`
  composta com a especialização, sem taxas físicas antigas.
- `.env` privado preparado a partir dos valores locais fornecidos pelo usuário,
  exemplo público sanitizado e correções das respostas estruturadas dos provedores.

O encoder ONNX reaproveita o modelo e a abordagem inspecionados na origem, com
implementação separada das dependências antigas. Fórmulas científicas foram
implementadas a partir dos contratos aprovados e referências de método, sem
copiar parâmetros, modelos treinados ou resultados do mestrado.
Consulte o [manifesto](lotes-04-06.json) e a [validação](validacao-lotes-04-06.md).
Os relatos dos lotes 01–03 acima descrevem o estado de cada entrega histórica.

## Lote 07 — decisões pendentes, cenários físicos e skills do Claude Code

Implementação autorizada pelo pesquisador em 25/09/2026, conforme a
[spec 0007](../specs/0007-decisoes-cenarios-skills.md).

- A01 virou a conversão `time_base` no serviço científico; A02 e A03 não foram transferidas.
- λ do IGBT (8,9×10⁻⁶/h) e contatores como um item (8,31×10⁻⁶/h), com duas bases
  temporais e análise por componente, registrados nas skills existentes e em oito cenários.
- Skills do catálogo instaladas para o Claude Code em `.claude/skills/`, com hook
  auxiliar para comandos Git; as falhas encontradas foram corrigidas no lote 08.

Nenhum código, dado ou resultado novo da origem foi importado. As taxas vêm do
registro de 13/09 e ainda precisam ser reconferidas nos PDFs quando entrarem no acervo.
Consulte o [manifesto](lote-07.json) e a [validação](validacao-lote-07.md).

## Lote 08 — correções da revisão

Correções autorizadas em 26/09/2026, conforme a
[spec 0008](../specs/0008-correcoes-revisao.md): hook com leitura do comando JSON,
opções globais/flags do Git e mensagens sem payload; descrição correta das unidades
no serviço RAM; documentação corrente alinhada ao lote 07; wheel reconstruído.
As skills do Claude permanecem restritas ao desenvolvimento; não foi identificada
necessidade de duplicar suas orientações no runtime. Manifestos, decisões e
resultados anteriores foram preservados. Consulte o [manifesto](lote-08.json)
e a [validação](validacao-lote-08.md).

## Lote 09 — Gemini em uso real

Primeiro lote do [roteiro da v0](../roteiro-v0.md), sem migração de código da origem.
Modelos configurados, tokens de raciocínio registrados e duas chamadas reais
conferidas. Consulte a [spec 0009](../specs/0009-gemini-uso-real.md), o
[manifesto](lote-09.json) e a [validação](validacao-lote-09.md).

## Lote 10 — interface local

Interface nova, com a antiga (`src/webapp` da origem) como referência de padrões:
Starlette, acesso local, limites de envio e KaTeX, este copiado da origem com a licença
MIT. Layout, estilo e lógica da tela foram escritos do zero. Consulte a
[spec 0010](../specs/0010-interface-local.md), o [manifesto](lote-10.json) e a
[validação](validacao-lote-10.md).

## Lote 11 — memória persistente

Memória nova, em `aliado.memory`, sem código nem dados da memória antiga da origem.
As memórias antigas triadas nos lotes 02–05 continuam privadas e fora do agente; a
importação fica para a v1. Consulte a [spec 0011](../specs/0011-memoria-persistente.md),
o [manifesto](lote-11.json) e a [validação](validacao-lote-11.md).

## Lote 12 — busca na web

Busca integrada do Gemini, sem código da origem. Consulte a [spec 0012](../specs/0012-busca-web.md),
o [manifesto](lote-12.json) e a [validação](validacao-lote-12.md).

## Lote 13 — dados GPVS e protocolo M14

Reimplementação do contrato de dados da origem (`src/ml/dados_gpvs.py`, commit `21f6ddf`),
sem copiar código: os mesmos números foram reproduzidos e conferidos. Os 16 CSVs foram
copiados de `dados/brutos/gpvs` com os hashes do manifesto da origem, e o arquivo de
estatísticas de referência foi copiado para os testes. O mapeamento antigo das falhas
para a FMECA não foi transferido (M11). Consulte a [spec 0013](../specs/0013-gpvs-protocolo-m14.md),
o [manifesto](lote-13.json) e a [validação](validacao-lote-13.md).

## Lote 14 — autoencoders e limiar

Reimplementação dos modelos e do limiar da origem (`src/ml/modelos_autoencoder.py` e
`src/ml/treino_comparacao.py`, commit `21f6ddf`), sem copiar código: com separação 2 e
semente 42, os pesos e o histórico são idênticos bit a bit aos modelos congelados da
origem, que foram só lidos. Os valores de referência e o hash dos pesos foram copiados
para `tests/data/gpvs_modelos_referencia.json`. O AE-LSTM com atenção, exploratório na
origem, não foi transferido. Consulte a [spec 0014](../specs/0014-autoencoders-limiar.md),
o [manifesto](lote-14.json) e a [validação](validacao-lote-14.md).

## Lote 15 — avaliação M13

Reimplementação das métricas por janela e da pontuação da E3 da origem
(`src/ml/avaliacao_comparativa.py` e `src/ml/estatistica_comparacao.py`, commit `21f6ddf`),
sem copiar código e sem scikit-learn. Com os modelos equivalentes aos da origem, os escores
das 14.064 janelas e as métricas dos 28 pares de modelo e ensaio coincidem. Os resultados
da E3 foram só lidos, e os valores de referência foram copiados para
`tests/data/gpvs_avaliacao_referencia.json`. Não foram transferidos a ablação temporal nem a
varredura de detectabilidade (injeção de severidade e Weibull de `a_det`). Consulte a
[spec 0015](../specs/0015-avaliacao-m13.md), o [manifesto](lote-15.json) e a
[validação](validacao-lote-15.md).

## Lote 16 — FMECA

As notas S, O e D dos quatro grupos vêm do documento da origem (`docs/fmeca.md`, commit
`21f6ddf`), que as atribui a Cristaldi, Khalil e Soulatiantork (2017), Tabela 6. Não houve
cópia de código: o NPR é recalculado. Os itens de sensor/realimentação e de controle da
origem ficaram fora, pelo recorte de quatro grupos, assim como o mapeamento para o GPVS (M11)
e o NPR definido pelo pesquisador para sensor/realimentação. Consulte a
[spec 0016](../specs/0016-fmeca.md), o [manifesto](lote-16.json) e a [validação](validacao-lote-16.md).

## Lote 17 — lançamento v0.1.0

Instalação do zero no Python 3.14, aceite com chamadas reais, README reescrito como guia de uso,
`CHANGELOG.md` e o pacote v0.1.0. Foram corrigidos dois defeitos encontrados no aceite:

- a regra `data/` do `.gitignore` excluía `tests/data/`;
- o identificador interno das anotações de memória chegava à resposta.

A auditoria antes do commit não encontrou segredos. Consulte a
[spec 0017](../specs/0017-lancamento.md), o [manifesto](lote-17.json) e a [validação](validacao-lote-17.md).

## Lote 18 — biblioteca, memória, anexos e fontes

Primeiro lote depois da v0.1.0, sem migração de código da origem. Parte dos apontamentos do
pesquisador no uso real: catálogo e resposta sem citação exibida com aviso no modo biblioteca,
perfil e memória de conversas, fila de anexos e fontes numa janela sobre a resposta. O aceite
encontrou e corrigiu anotações longas sem vetor, um defeito que vinha do lote 11. As memórias
antigas continuam fora do agente. Consulte a [spec 0018](../specs/0018-biblioteca-memoria-anexos.md),
o [manifesto](lote-18.json) e a [validação](validacao-lote-18.md).

## Lote 19 — qualidade da busca da biblioteca

Não houve migração de código da origem. O lote trouxe:
- palavras vazias ignoradas na busca por palavras e mais peso ao significado;
- limite de trechos por documento;
- a ficha de cada documento (título, autores, ano e DOI), conferida no próprio texto.

A medição usa 16 perguntas de referência, que ficam fora do Git: os acertos passaram de 12
para 13, com o ganho vindo das perguntas que citam o autor. As 27 fichas da biblioteca real
foram preenchidas depois de uma cópia de segurança do catálogo, que só ganhou uma tabela.
Consulte a [spec 0019](../specs/0019-qualidade-da-busca.md), o [manifesto](lote-19.json) e a
[validação](validacao-lote-19.md).

## Lote 20 — aba Ciência

Não houve migração de código da origem. A aba mostra os resultados e traz exploradores com os
modelos congelados do lote 14. Eles reaproveitam as funções da avaliação canônica e repetem
exatamente a avaliação de 27/09 com os parâmetros oficiais. A aba também roda confiabilidade e
FMECA pela interface. `data/resultados` não é alterado: o que a aba grava vai sempre para uma
pasta nova, e o erro por variável fica em `data/ciencia/`. O GPVS pela interface fica para o
lote 21. Consulte a [spec 0020](../specs/0020-aba-ciencia.md), o [manifesto](lote-20.json) e a
[validação](validacao-lote-20.md).

## Lote 21 — GPVS pela interface e 0.2.0

Não houve migração de código da origem. As três etapas do GPVS rodam pela aba Ciência, em
subprocessos dos próprios comandos do terminal. Uma nova avaliação exige a frase de confirmação e
entra no registro de consultas ao teste (M14) como não canônica. No aceite, feito numa cópia dos
resultados, o treino e a avaliação pela interface reproduziram bit a bit a rodada de 27/09. O lote
fecha a versão 0.2.0, com o pacote em `dist/v0.2.0`. Consulte a
[spec 0021](../specs/0021-gpvs-interface.md), o [manifesto](lote-21.json) e a
[validação](validacao-lote-21.md).

## Lote 22 — correções de confiança

Não houve migração de código da origem; o repositório `mestrado-utfpr` só foi lido, para ver as
visões de resultados que ele tinha e servir de referência aos lotes 23 e 24.
- A skill do mestrado descreve a situação atual, e o texto das regras M09 a M14 ficou idêntico.
- As taxas e as notas da FMECA foram conferidas nas páginas dos PDFs, e os valores não mudaram.
- A biblioteca ganhou o recurso de apagar documentos. Os dois recortes do Lafraia saíram da biblioteca do pesquisador, e as 16 deduções tiradas deles foram revogadas.
- A busca do chat passou a usar uma consulta reescrita pela conversa, em português e inglês, com até 10 trechos por resposta. As perguntas de referência foram de 13 para 16 de 16.
- A interface ganhou o seletor de fonte do texto.

Consulte a [spec 0022](../specs/0022-correcoes-confianca.md), o [manifesto](lote-22.json) e a
[validação](validacao-lote-22.md).

## Lote 23 — aba Ciência nova, parte 1

Do `mestrado-utfpr` vieram, só lidos e copiados:
- o **D3 v7.9.0**, de `src/webapp/static/vendor/d3/`, com a licença ISC e o sha no manifesto;
- as referências de estilo: as cores e o formato das figuras de `src/ml/estilo_graficos.py` e `src/ml/graficos_comparacao.py`, e os padrões de `src/webapp/static/results-charts.js`.

Nenhum código de cálculo veio da origem. As visões leem a avaliação oficial de 27/09 com
`science/detection/summary.py`. Consulte a [spec 0023](../specs/0023-aba-ciencia-nova.md), o
[manifesto](lote-23.json) e a [validação](validacao-lote-23.md).

## Lote 24 — início observado das falhas

Não houve migração de código da origem. O `mestrado-utfpr` só foi consultado para confirmar que o início da falha era o meio nominal do registro (`fault_boundary`, "nominal_mid_record", em `src/ml/dados_gpvs.py`). A descrição do GPVS no Mendeley Data diz só que as falhas foram introduzidas manualmente, na metade dos experimentos. O detector de mudança (PELT), a reanálise, a cadeia de Markov e a faixa do limiar foram escritos aqui, só com numpy. Consulte a [spec 0024](../specs/0024-inicio-das-falhas.md), o [manifesto](lote-24.json) e a [validação](validacao-lote-24.md).

## Implementações posteriores a discutir

| Subsistema encontrado | Direção de reaproveitamento |
|---|---|
| Router e observabilidade | Avaliar a política de modelos, retries, fallback e auditoria antes de migrar, preservando controle de custos. |
| RAG híbrido e evidências | Avaliar qualidade no acervo escolhido e ampliar a recuperação conforme evidências de uso. |
| Memória e Obsidian | Reaproveitar mecanismos; revisar dados e regras antes de qualquer importação. |
| Ferramentas científicas e ML | Definir parâmetros físicos por perguntas e respostas; treino/avaliação de detectores será lote separado. |
| Webapp | Reaproveitar componentes úteis; criar autenticação por convite e isolamento antes de acesso compartilhado. |

A base antiga pode restaurar automaticamente o índice da literatura a partir de
snapshots. A troca de corpus precisará abranger catálogo, documentos, índice
vetorial, índice lexical, snapshots e memórias derivadas selecionadas. Nenhuma
limpeza foi executada na origem; o destino começa sem esse estado.

O registro anterior aponta Literatura Enxuta como corpus escolhido, mas o usuário
informou que a literatura mudará. A composição final será confirmada antes da
ingestão. As cópias temporárias usadas na triagem são apenas material de inspeção
em `tmp/lote-02/`, ignorado pelo Git; não compõem a memória nem o acervo do agente.
Não foram importados PDFs, resultados, modelos treinados da pesquisa ou dados GPVS.
O encoder documental foi preparado de fonte pública com revisão fixa; chaves locais
foram mantidas somente no `.env` privado.

## Skills e referências utilizadas

- **Skills instaladas para o assistente de desenvolvimento:** `karpathy-guidelines`,
  `verification-before-completion` e `doc-coauthoring`, em `.agents/skills/`.
  Foram lidas e aplicadas à revisão do mapa, com versões fixadas. O
  [registro de seleção e uso](skills-desenvolvimento.md) explica compatibilidade,
  equivalentes já disponíveis e limites; o [manifesto](skills-desenvolvimento.json)
  registra fontes, commits e hashes.
- **Skill Creator do Codex:** organização e validação das três skills próprias
  do AL-IAdo; continua disponível como ferramenta nativa de desenvolvimento.
- [Agent Skills](https://agentskills.io/specification): formato `SKILL.md`,
  instruções e referências. O runtime deste lote implementa um subconjunto
  explícito, sem scripts ou instalação dinâmica.
- [OpenSpec](https://github.com/Fission-AI/OpenSpec): referência para spec,
  requisitos verificáveis e evolução por mudanças revisáveis. CLI não instalado.
- [Superpowers](https://github.com/obra/superpowers): consultado como referência
  e utilizado pela skill independente `verification-before-completion`.
  O framework completo e seus hooks não foram instalados.
- [Skills da Anthropic](https://github.com/anthropics/skills): consultadas como
  referência de organização e utilizadas por `doc-coauthoring` no desenvolvimento.
  As capacidades documentais já disponíveis no Codex atendem PDF, Word,
  apresentações e planilhas.

As skills de pesquisa e engenharia são próprias deste projeto. A instalação de
skills para o Codex não as adiciona ao runtime do AL-IAdo. Para este último,
a seleção depende do domínio, das ferramentas implementadas e da revisão do usuário.

## Validação dos lotes

Os resultados dos 49 testes, lint, validação das skills e empacotamento estão
em [validação do lote 01](validacao-lote-01.md). A preparação e a triagem têm
[validação própria do lote 02](validacao-lote-02.md). A inferência real e a qualidade científica das respostas
permanecem por avaliar com o usuário e com fontes efetivamente disponíveis.
