# AL-IAdo — diagnóstico de arquitetura complementado

Data: 20/10/2026. Documento para revisão do pesquisador e eventual encaminhamento ao Gemini.

## 1. Escopo e base examinada

Esta versão complementa o arquivo `Diagnostico_Arquitetura_Aliado_para_Gemini_2026-10-20.txt`, preservado no anexo original. Acrescenta a estrutura completa do produto, as mudanças locais posteriores ao diagnóstico, os contratos pendentes e uma sequência de trabalho revisável. Não constitui autorização para implementar a proposta.

O diagnóstico original examinou o commit `77fb76d7414316a3aa04e8e62c0dc571cbe01172`. O diretório local continua com esse HEAD, mas contém alterações e arquivos novos dos lotes posteriores. Portanto, o commit sozinho não identifica o código local aqui examinado. As conclusões desta versão resultam da leitura dos arquivos presentes em 20/10/2026; não são uma inspeção do processo servidor em execução.

Convenções:

- **Observado:** encontrado nos arquivos locais.
- **Verificado nesta revisão:** conferido por comando executado nesta sessão.
- **Registro anterior:** informação das specs ou validações históricas, não medida novamente.
- **Proposta:** mudança ainda não implementada por este trabalho.
- **Pendente:** falta decisão, especificação ou evidência adicional.

Não foram lidos segredos do `.env`, memórias pessoais ou conteúdos dos resultados privados. Não houve chamada a modelo real, experimento, reindexação, instalação, commit ou publicação.

## 2. Conclusão arquitetural

O AL-IAdo já possui dois fluxos distintos: a assistência por linguagem, com biblioteca e memória, e os cálculos científicos executados em Python. O LLM interpreta evidências e resultados; a decisão numérica de detecção é calculada pelo pipeline experimental.

O trabalho prioritário é explicitar os contratos entre etapas e melhorar a rastreabilidade dos artefatos. Depois disso, a divisão dos módulos pode ocorrer em pequenos lotes, preservando os cálculos e as decisões metodológicas.

A organização aprovada usa `science/` para métodos gerais e `specializations/mestrado/` para a pesquisa. A árvore com `core/` e `agent/` apresentada no anexo é uma alternativa de organização, ainda não implementada nem aprovada como nova arquitetura. Trocar nomes de diretórios não é pré-requisito para separar responsabilidades.

## 3. Estrutura atual do projeto

Árvore resumida dos caminhos existentes, omitindo arquivos auxiliares:

```text
aliado_v0/
  AGENTS.md                         regras de colaboração e autorização
  pyproject.toml                    pacote, versão e dependências
  requirements-dev.lock             ambiente de validação registrado
  docs/
    specs/0001-*.md ... 0043-*.md    histórico dos lotes
    specs/capacidades/               requisitos vivos
    migracao/                       proveniência e validações
    revisao/                        diagnósticos e propostas
    roteiro-v0.md                   decisões e sequência dos lotes
  src/aliado/
    cli.py                          comandos de terminal
    agent.py                        contexto, execução e conferência
    routing.py                      escolhas locais para cada pergunta
    routing_examples.py             exemplos gerais de roteamento
    numbers.py                      apoio à conferência de números
    llm/
      contracts.py                  pedidos, respostas e uso
      usage_log.py                  registro de chamadas
      providers/
        registry.py                 modelos e capacidades
        gateway.py                  escolha e encaminhamento
        gemini.py / openai.py        provedores remotos
        local.py                    adaptador do Ollama
    skills/
      library.py                    descoberta e leitura das instruções
      builtin/engenharia/
      builtin/confiabilidade/
    knowledge/
      library.py                    catálogo, indexação e busca
      extraction.py / chunking.py    extração por página e trechos
      figures.py / metadata.py       descrições e fichas
      embeddings.py / reranking.py   busca vetorial e reordenação
      rewrite.py / reading.py        consulta e seleção da leitura
      coverage.py                   cobertura das partes do pedido
    memory/
      store.py / reviewer.py         memória e revisão das anotações
    experiments/
      __init__.py                   rodadas, resultados e comparação
      pdf.py                        exportação por pedido
    science/
      ram.py / fmeca.py              confiabilidade e análise de risco
      components.py / digest.py      componentes e evidências citáveis
      detection/
        models.py                    redes, treino, inferência e pesos
        protocol.py                  operações temporais e normalização
        threshold.py / metrics.py    limiar e métricas
        registry.py                  consultas aos dados de teste
    specializations/
      __init__.py                   descoberta dos pacotes
      mestrado/
        __init__.py / commands.py    integração e comandos da pesquisa
        routing.py / notes.py        escolhas de domínio e glossário
        gpvs.py                     leitura e atributos da base GPVS
        training.py / evaluation.py treino, calibração e avaliação
        onset.py / reanalysis.py     início observado e reanálise
        autoencoders.py              execução completa do experimento
        summary.py / digest.py       resultados para tela e chat
        explorer.py / web.py         exploradores e rotas da pesquisa
        skills/pesquisa-inversores/
    interfaces/web/
      app.py                        servidor e fluxo da conversa
      conversations.py              histórico das conversas
      science.py / experiments.py   telas e execução dos experimentos
      obsidian.py                   espelho de saída
      rendering.py / static/        apresentação no navegador
  tests/                            contratos e verificações
  data/                             dados privados locais, fora do Git
```

`data/memoria/`, `data/memory-review/` e `data/obsidian/` têm funções diferentes: memória ativa, triagem de material antigo e espelho de saída, respectivamente. Candidatos em triagem não são memórias aprovadas; notas do Obsidian não são fonte de instruções. Não se deve importar acervo ou memória antigos automaticamente.

## 4. Fronteiras e fluxos principais

### 4.1. Pergunta e resposta

```text
Mensagem escrita
  -> roteador local: skill, modelo e leitura
  -> biblioteca, memória e/ou resultados, conforme o pedido
  -> agente: instruções + evidências + pergunta
  -> gateway: modelo local ou provedor remoto
  -> conferência das citações e dos números
  -> resposta, histórico e memória elegível
```

O roteamento inicial não consome tokens. A reescrita da consulta pode chamar um modelo quando há dependência da conversa ou siglas; não se confunde com o roteador local. O plano por partes é usado quando o pedido contém partes.

A biblioteca extrai o texto por página e aplica OCR nas páginas que precisam dele. A descrição de figuras e tabelas é uma operação distinta, somente por pedido. As páginas enviadas ao local usam o texto guardado e as descrições já disponíveis; isso não equivale a executar uma nova leitura visual do PDF.

O chat usa referências documentais e blocos de resultados citáveis. Conferir marcas e números reduz erros, mas não comprova a correção de uma interpretação causal nem a qualidade científica integral da resposta.

### 4.2. Experimento numérico

```text
GPVS -> atributos -> partições e normalização
  -> treino -> calibração do limiar
  -> abertura da consulta ao teste -> avaliação
  -> início observado e reanálise -> consolidação
  -> resultado.json e resultado.md
  -> tela, resumo citável e PDF por pedido
```

O executor usa uma pasta nova por rodada. O resultado consolidado é gravado por último; a interface considera a rodada completa mais recente, com a avaliação histórica como alternativa quando não existe uma nova completa. A comparação com resultado salvo e o PDF com JSON anexo já pertencem à capacidade de experimentos.

O botão que impede repetir os mesmos parâmetros é uma regra operacional. Parâmetros iguais não comprovam identidade de código, dados e ambiente, nem garantem equivalência entre computadores.

### 4.3. Núcleo e especialização

O núcleo descobre os pacotes percorrendo `specializations/`, sem mencionar a pesquisa pelo nome. A especialização fornece experimentos, comandos, regras de roteamento, glossário, referências e resultados para o chat. Skills são instruções carregadas; não executam automaticamente treinamento ou outras ações.

A descoberta de especializações não é uma sandbox para código desconhecido: são pacotes Python do próprio projeto. A ampliação para extensões externas exigiria um contrato e uma política próprios.

## 5. Complementos ao diagnóstico do pipeline neural

Os principais fatos do anexo permanecem como descrição do pipeline: PyTorch; 24 atributos por janela de 200 amostras; MLP por janela; LSTM com oito janelas; separação entre treino, validação, calibração e teste; escore pela média dos maiores erros por atributo; limiar no percentil 99 e alarme principal após três janelas consecutivas acima dele.

O escore principal usa os cinco maiores erros. As comparações de sensibilidade com outros valores de k não devem ser apresentadas como uma seleção posterior do melhor resultado. O limiar usa comparação estrita `escore > limiar`.

O LSTM aprende a reconstruir a sequência inteira, mas a pontuação usa o último passo. A descrição metodológica e os testes de equivalência devem preservar essa diferença. O comissionamento dos ensaios com falha pressupõe um trecho saudável inicial; essa disponibilidade deve ser declarada como hipótese operacional.

**Correção sobre os erros por atributo:** os exportadores de treino e avaliação preservam escores, sem transformar a matriz completa de erros em artefato oficial da rodada. Entretanto, `specializations/mestrado/explorer.py`, em `_errors()`, já calcula e grava matrizes completas num cache NPZ. O explorador de limiar também entrega a linha de erros da janela e os nomes dos atributos.

Portanto, existe persistência dos erros para exploração. A pendência é um artefato estável da rodada, com alinhamento temporal e contrato verificável. O cache usa como metadados a versão do cache, o hash da configuração de treino e os hashes dos dados; não explicita nesse conjunto o hash dos pesos, a revisão do código ou a ordem dos atributos. O cache não deve ser promovido a evidência imutável sem definir essas garantias.

O checkpoint `.pt` contém pesos e metadados para reconstruir a rede, mas não inclui todo o estado necessário para retomar exatamente um treinamento interrompido. Não há necessidade de implementar retomada se esse comportamento não for requisito da pesquisa.

## 6. Mudanças locais que faltavam no anexo

Os lotes 37–43 acrescentam tratamento de páginas e o uso do Ollama como provedor principal. A versão declarada em `pyproject.toml` é `0.8.0`; a versão instalada informada pelos metadados do ambiente consultado ainda é `0.7.0`. Essa diferença pede alinhar a identificação da instalação; sozinha, não demonstra qual código um servidor já aberto carregou.

Com o modelo local configurado:

- O local responde primeiro aos pedidos que comporta.
- Limite de raciocínio, resposta vazia ou saída estruturada inválida podem levar ao Gemini Flash. No chat, a falha de citação ou de conferência numérica também pode provocar uma nova resposta.
- Busca na web ou contexto que excede a capacidade local seguem diretamente ao modelo remoto escolhido.
- Falha técnica do Ollama produz erro claro, sem transferir automaticamente o pedido ao Gemini.
- Chamadas locais são registradas, mas ficam fora da contagem de uso pago.

O código usa contexto padrão de 16.384 tokens. As specs dos lotes 40–43 registram uma configuração local de 32.768 tokens; o lote 43 registra temperatura 0,6. São registros de configuração e medição anteriores: esta revisão não consultou o `.env`, não interrogou o Ollama e não repetiu os ensaios de desempenho.

O contexto do modelo local, o teto de confirmação por pergunta e o aviso diário são controles diferentes. A política conserva a confirmação acima de 30 mil tokens e, depois de 300 mil tokens no dia, para leituras acima dos trechos. As specs de provedores tratam separadamente a contagem dos tokens locais. Leitura ampla continua somente por pedido escrito e sempre confirmada; nenhuma alteração desses controles está proposta aqui.

## 7. Contratos que precisam ficar explícitos

Os itens abaixo são propostas para uma futura spec de mudança. Não descrevem novos schemas já implementados.

| Fronteira | Contrato a formalizar | Verificação necessária |
|---|---|---|
| Dados → atributos | Identidade dos dados, canais, unidades, frequência, tamanho e passo da janela, ordem dos atributos e valores inválidos | Dimensão, ordem, unidades e correspondência temporal |
| Atributos → partições | Índices por ensaio, intervalos descartados, normalização e comissionamento | Nenhuma sequência atravessa os papéis experimentais; ajuste respeita os dados permitidos |
| Treino → inferência | Arquitetura, inicialização, hiperparâmetros, versão e hash do checkpoint | Incompatibilidade de atributos ou pesos impede a leitura |
| Inferência → pontuação | Matriz de erro quadrático, formato, passo do LSTM, tipo numérico e atributos | O escore é recalculável a partir da matriz preservada |
| Pontuação → decisão | k, agregação, limiar, calibração, comparação estrita e confirmação temporal | Pontos de fronteira e eventos reproduzem a regra existente |
| Rodada → comparação | Identidade de protocolo, dados, código e ambiente | Comparações indicam diferenças e incompatibilidades metodológicas |
| Resultado → chat | Evidências, indicadores, unidades, limitações, origem e identificadores de citação | Números e fontes usados no texto pertencem ao material enviado |

O manifesto de uma rodada deve reunir os vínculos já distribuídos entre configurações e relatórios, acrescentando versão do schema, revisão do código e hashes dos artefatos. Para código com mudanças sem commit, registrar apenas o HEAD é insuficiente: é preciso identificar também a revisão local utilizada, sem incluir segredos ou dados privados.

O artefato de erros proposto deve vincular ensaio, índice da janela, convenção do tempo, modelo, inicialização, atributos, erros, escore, decisão por janela e eventos de alarme. É preciso decidir se o tempo representa começo, centro ou fim da janela e qual é sua origem. Não preencher essa convenção por suposição.

Campos ausentes, formatos incompatíveis e arquivos corrompidos devem ter resposta definida. Um leitor não deve preencher informação metodológica ausente com valores padrão silenciosos. Reconstruções completas e resíduos com sinal só precisam ser preservados se houver uso científico definido.

## 8. Pendências e decisões

| Pendência | O que já se sabe | Próxima evidência ou decisão |
|---|---|---|
| Identidade da revisão local | Há mudanças além do commit do diagnóstico | Fixar a revisão usada numa futura implementação e validação |
| Identificação da instalação | Fonte declara 0.8.0; metadados instalados indicam 0.7.0 | Conferir empacotamento e processo em execução, sem presumir atualização |
| Erros por atributo | Existem no cache dos exploradores | Decidir seu contrato e incorporação à rodada |
| Manifesto unificado | Configurações e hashes já existem em partes do fluxo | Definir schema, compatibilidade e leitura das rodadas históricas |
| Habilidades operacionais menores | Há leitura, comparação e resumos implementados em módulos | Definir o que falta antes de propor novas skills ou ferramentas |
| Separação de módulos | `models.py`, `training.py` e `evaluation.py` concentram responsabilidades | Escolher um primeiro lote que preserve a API e os cálculos |
| Specs vivas | Há núcleo, roteador, experimentos, biblioteca e provedores | Completar as capacidades ainda distribuídas nas specs históricas; biblioteca cobre apenas parte do conjunto |
| Validade científica | Código e registros descrevem o protocolo | Reprodução integral e análise dos resultados exigem trabalho específico autorizado |
| Qualidade do chat | Existem conferência e testes simulados | Avaliação semântica com perguntas reais exige escopo e chamadas combinados |
| Documentação histórica | Há mapas de 05/10 e revisão de 17/10 | Usar suas datas e contextos; não apresentá-los como retrato integral de 20/10 |

As propostas `read_run`, `compare_runs`, `interpret_detection` e `write_report`, do anexo, podem organizar responsabilidades, mas parte do comportamento já existe. Antes de criar novas interfaces, é necessário mapear as funções existentes e definir entradas, saídas, erros e permissões. Acrescentar arquivos `SKILL.md` não cria contratos executáveis.

As decisões metodológicas antigas não devem ser reabertas ou preenchidas com valores herdados sem verificar as diretrizes aprovadas. Uma mudança de arquitetura não autoriza alterar limiar, atributos, normalização, protocolo ou associação entre falhas e componentes.

## 9. Sequência proposta para pequenos lotes

1. **Contratos e evidência:** escolher a primeira fronteira, escrever a spec de mudança, registrar o comportamento e definir a identidade dos artefatos.
2. **Separação interna:** extrair uma responsabilidade de `models.py`, preservando importações públicas e formatos existentes. Manter `science/detection/` como ponto de partida.
3. **Auditoria dos erros:** transformar a necessidade científica em artefato da rodada, aproveitando o cálculo do explorador sem confundir cache com evidência final.
4. **Leitura e comparação:** validar compatibilidade de resultados antigos e novos antes de montar tabelas ou fornecer evidências ao chat.
5. **Interpretação e relatório:** reduzir o contexto e explicitar limitações, sem transferir classificação ou cálculo de métricas ao LLM.

Cada lote deve definir arquivos, requisitos, critérios de equivalência e validação antes das mudanças. Resultados e manifestos anteriores permanecem como registros. Qualquer migração ou conversão deve produzir saída nova, sem sobrescrever a entrega original.

Não se recomenda incluir automaticamente a divisão de `interfaces/web/app.py` ou a inversão da dependência `knowledge/rewrite.py → routing`: ambas ficaram fora do roteiro por decisão expressa do pesquisador na revisão de 17/10. Podem ser discutidas em outro lote.

## 10. Verificações desta revisão e limites

Foi executado:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_specs.py tests/test_isolation.py tests/test_contracts.py tests/test_gateway.py tests/test_local_provider.py -q
```

Resultado: **40 testes passaram**, em 2,09 s. Houve um aviso de permissão ao gravar o cache do pytest; os testes terminaram com código de saída zero. A seleção verifica ligação dos requisitos às specs, isolamento do núcleo, contratos e comportamento do gateway/provedor local com clientes simulados.

O ambiente consultado informa Python 3.12.14, PyTorch 2.12.0 e NumPy 2.5.3. Assim, as ausências de pytest e PyTorch relatadas no diagnóstico original dizem respeito à cópia usada naquela inspeção, não a este ambiente local.

A suíte completa não foi executada. A fixture `origin_gpvs_runs`, em `tests/conftest.py`, pode preparar dados reais e treinar modelos quando eles estão presentes; portanto, executar toda a suíte não seria apenas uma conferência documental. Não se declara aqui equivalência numérica dos modelos, reprodução experimental, integridade das saídas privadas ou desempenho do LLM real.

Esta entrega altera somente documentação. As próximas alterações de código, execuções científicas e chamadas reais precisam de seus escopos próprios, conforme as regras do projeto.

## 11. Fontes locais para conferência

- [Fundação](../specs/0001-fundacao.md), [revisão de 17/10](2026-10-modularizacao-e-specs.md) e [roteiro](../roteiro-v0.md).
- [Núcleo](../specs/capacidades/nucleo.md), [roteador](../specs/capacidades/roteador.md), [experimentos](../specs/capacidades/experimentos.md), [biblioteca](../specs/capacidades/biblioteca.md) e [provedores](../specs/capacidades/provedores.md).
- [Provedor local](../../src/aliado/llm/providers/local.py), [gateway](../../src/aliado/llm/providers/gateway.py), [agente](../../src/aliado/agent.py) e [leitura documental](../../src/aliado/knowledge/reading.py).
- [Redes e treinamento](../../src/aliado/science/detection/models.py), [preparo GPVS](../../src/aliado/specializations/mestrado/gpvs.py), [treino](../../src/aliado/specializations/mestrado/training.py) e [avaliação](../../src/aliado/specializations/mestrado/evaluation.py).
- [Cache e exploradores](../../src/aliado/specializations/mestrado/explorer.py), [executor do experimento](../../src/aliado/specializations/mestrado/autoencoders.py) e [gestão das rodadas](../../src/aliado/experiments/__init__.py).
- [Dependências](../../pyproject.toml), [testes das specs](../../tests/test_specs.py), [isolamento](../../tests/test_isolation.py) e [fixtures de validação](../../tests/conftest.py).
- [Spec 0039](../specs/0039-local-le-texto.md), [spec 0041](../specs/0041-local-mais-rapido.md), [spec 0042](../specs/0042-local-na-vram.md) e [validação histórica do lote 43](../migracao/validacao-lote-43.md).

Para avaliar este documento em outra ferramenta, distinguir os fatos locais das propostas, conferir os arquivos citados e evitar tratar uma validação histórica como medição realizada nesta revisão.
