# Arquitetura do AL-IAdo — 05/10/2026

Retrato do código local da versão **0.5.0 com as alterações do lote 32**. Os mapas descrevem a implementação encontrada, incluindo as alterações ainda sem commit. Não são uma verificação do processo servidor que estiver em execução: ele precisa carregar esse código para apresentar o mesmo comportamento.

O AL-IAdo é uma aplicação Python local e modular. A interface web, o agente, a biblioteca e a memória são coordenados pelo mesmo servidor. As etapas longas de preparação, treino e avaliação científica têm execução em subprocessos. As chamadas de linguagem do chat web usam o Gemini na nuvem.

## Mapas para visualizar e ampliar

Cada PNG tem 2.700 pixels de largura. O SVG contém texto e formas vetoriais, permitindo ampliar e editar sem perder definição.

| Mapa | O que identifica | Imagem | Vetorial |
|---|---|---|---|
| 01 — Visão geral | Setores, entradas, fronteira local/nuvem e armazenamento | [PNG](01-visao-geral.png) | [SVG](01-visao-geral.svg) |
| 02 — Pergunta | Roteamento, contexto, profundidade de leitura, limites e resposta | [PNG](02-caminho-da-pergunta.png) | [SVG](02-caminho-da-pergunta.svg) |
| 03 — Biblioteca | Ingestão, extração, busca, cache, reordenação e entrega ao modelo | [PNG](03-biblioteca-e-busca.png) | [SVG](03-biblioteca-e-busca.svg) |
| 04 — Memória | Histórico, trilhas, revisão, anotações e recuperação | [PNG](04-memoria-e-dados.png) | [SVG](04-memoria-e-dados.svg) |
| 05 — Ciência | Confiabilidade, autoencoders, avaliação, reanálise e resultados | [PNG](05-ciencia-e-autoencoders.png) | [SVG](05-ciencia-e-autoencoders.svg) |

As setas representam fluxos ou dependências principais, sem enumerar todas as chamadas de função. As cores identificam a função predominante de cada bloco; um setor pode reunir código, armazenamento e modelos. As setas tracejadas indicam alternativas ou ligações explicativas. Os números organizam cada mapa e não são códigos internos do produto.

## Onde cada setor está implementado

Os caminhos abaixo partem da raiz do repositório. Os rodapés dos mapas abreviam esses caminhos para preservar a legibilidade.

| Setor | Responsabilidade | Código principal |
|---|---|---|
| Interface | Chat, fontes, documentos, memória e ciência | [interfaces/web/static/](../../../src/aliado/interfaces/web/static/), [interfaces/web/app.py](../../../src/aliado/interfaces/web/app.py) |
| Terminal | Entrada para os comandos do projeto | [cli.py](../../../src/aliado/cli.py) |
| Coordenação | Montagem de contexto, execução da conversa e conferência | [agent.py](../../../src/aliado/agent.py), [app.py](../../../src/aliado/interfaces/web/app.py) |
| Roteamento | Intenção, skill, modelo e profundidade de leitura | [routing.py](../../../src/aliado/routing.py), [routing_examples.py](../../../src/aliado/routing_examples.py) |
| Skills do produto | Instruções de engenharia, confiabilidade e pesquisa de inversores | [skills/library.py](../../../src/aliado/skills/library.py), [skills/builtin/](../../../src/aliado/skills/builtin/) |
| Provedores | Contratos, capacidades e acesso às APIs | [gateway.py](../../../src/aliado/llm/providers/gateway.py), [registry.py](../../../src/aliado/llm/providers/registry.py), [gemini.py](../../../src/aliado/llm/providers/gemini.py), [openai.py](../../../src/aliado/llm/providers/openai.py) |
| Entrada documental | Originais, extração, figuras, trechos e metadados | [library.py](../../../src/aliado/knowledge/library.py), [extraction.py](../../../src/aliado/knowledge/extraction.py), [figures.py](../../../src/aliado/knowledge/figures.py), [chunking.py](../../../src/aliado/knowledge/chunking.py), [metadata.py](../../../src/aliado/knowledge/metadata.py) |
| Busca e leitura | Consulta reformulada, vetores, candidatos, páginas e citações | [rewrite.py](../../../src/aliado/knowledge/rewrite.py), [embeddings.py](../../../src/aliado/knowledge/embeddings.py), [reranking.py](../../../src/aliado/knowledge/reranking.py), [reading.py](../../../src/aliado/knowledge/reading.py) |
| Memória | Anotações, conversas lembradas, trilhas e revisão | [memory/store.py](../../../src/aliado/memory/store.py), [memory/reviewer.py](../../../src/aliado/memory/reviewer.py), [conversations.py](../../../src/aliado/interfaces/web/conversations.py) |
| Obsidian | Geração de notas e ligações como espelho de saída | [obsidian.py](../../../src/aliado/interfaces/web/obsidian.py) |
| Uso | Registro de chamadas e consumo | [usage_log.py](../../../src/aliado/llm/usage_log.py) |
| Engenharia geral | Modelos analíticos de confiabilidade e risco | [ram.py](../../../src/aliado/science/ram.py), [fmeca.py](../../../src/aliado/science/fmeca.py), [components.py](../../../src/aliado/science/components.py) |
| Pesquisa de inversores | Dados, protocolo, modelos, treino e avaliação | [science/detection/](../../../src/aliado/science/detection/), [gpvs_runs.py](../../../src/aliado/interfaces/web/gpvs_runs.py) |
| Exposição dos resultados | Resumos estruturados para o chat e visualização na Ciência | [digest.py](../../../src/aliado/science/digest.py), [science.py](../../../src/aliado/interfaces/web/science.py) |

## O que mudou com o lote 32

| Bloco novo | Onde atua | Efeito e limite |
|---|---|---|
| Cache de busca | `knowledge/library.py` | Reutiliza textos e vetores em RAM. A versão dos dados do SQLite invalida o cache quando o catálogo muda. Não guarda respostas prontas. |
| Reordenador local | `knowledge/reranking.py` e `agent.py` | Compara a pergunta com até 60 candidatos e muda a ordem das páginas. Aplica-se ao degrau de páginas; preserva a seleção anterior se estiver indisponível. |
| Filtro de revisão | `memory/reviewer.py` e `interfaces/web/app.py` | Evita uma chamada extra ao revisor em mensagens que não precisam virar anotação durável. O histórico e as trocas elegíveis continuam sendo guardados. |

A busca usa MiniLM multilíngue (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`). A reordenação usa `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, em ONNX quantizado. Ambos executam inferência local com pesos preparados previamente. Os autoencoders Denso e AE-LSTM têm outra finalidade: aprendem com sinais saudáveis dos ensaios científicos e produzem erros de reconstrução para detectar anomalias.

## Distinções importantes para interpretar os mapas

- **Coordenação central:** `app.py` concentra a integração web; `agent.py` monta e executa a conversa. A existência de módulos não significa que o sistema já esteja dividido em serviços independentes.
- **Provedores:** existe adaptador OpenAI, mas a configuração padrão do chat web lista modelos Google e chama o agente com esse provedor. O gateway valida capacidades e encaminha a chamada; não implementa uma troca automática entre empresas.
- **Custos:** o roteamento, a busca vetorial, o cache, a reordenação e o filtro de memória são locais. Resposta principal, reformulação da busca e revisões/fichas podem usar chamadas pagas. Descrições de figuras dependem de pedido explícito.
- **Limites:** o código do chat aplica a confirmação de 30 mil tokens às leituras acima de trechos. Após 300 mil tokens no dia, toda leitura acima dos trechos exige confirmação. A reformulação da consulta pode acontecer antes dessa confirmação. Esses valores são estimativas e controles de leitura, não um teto financeiro universal.
- **Leitura ampla:** exige escolha explícita. O modo automático seleciona entre ausência de biblioteca, trechos, páginas e documento referido; considera tamanho e contexto. Ativar busca web limita a leitura documental a trechos.
- **Trilhas:** guardam referências de páginas já citadas. Podem orientar a seleção futura, mas a nova resposta ainda passa pelo modelo.
- **Ciência:** os cálculos vêm de rotinas do projeto. O modelo de linguagem recebe resumos e explica resultados; o chat não executa livremente scripts ou treinos. Dados e configurações de inversores especializam os componentes gerais.
- **Conferência:** valida referências, correspondência de citações e números de resultados. Isso não equivale a uma avaliação automática de toda a correção conceitual ou científica.
- **Skills:** as de `src/aliado/skills/builtin/` pertencem ao produto. As de `.agents/skills/` e `.claude/skills/` orientam os assistentes de desenvolvimento e não são carregadas como skills do chat AL-IAdo.

## Organização dos dados locais

Localizações padrão; a configuração e os argumentos de execução podem substituí-las.

| Local | Conteúdo e papel |
|---|---|
| `data/bibliotecas/principal/` | Catálogo SQLite, originais identificados por hash e extrações documentais. |
| `data/memoria/memoria.sqlite3` | Anotações e trocas indexadas; trilhas de páginas associadas às conversas. |
| `data/conversas/` | Histórico completo em JSON e informações mostradas pela interface. |
| `data/models/minilm/` | Pesos do modelo local de vetores. |
| `data/models/reranker/` | Pesos e tokenizer do reordenador local. |
| `data/gpvs/` | Dados dos ensaios científicos. |
| `data/resultados/` | Preparações, treinos, escores, avaliações, reanálises e registros científicos. |
| `data/uso/chamadas.jsonl` | Registro de consumo das chamadas aos modelos. |
| `data/uso/arquivos-google.json` | Controle local de arquivos enviados ao serviço do Google. |
| `data/obsidian/` | Notas derivadas, geradas em uma direção; não são fonte de dados nem autorização. |

`data/` fica fora do Git. Código, especificações e estes mapas pertencem à documentação versionável. O cache da busca vive na RAM e pode ser reconstruído a partir dos dados persistentes.

## Termos usados

| Termo | Significado neste sistema |
|---|---|
| API | Interface de comunicação com um serviço externo. |
| Gateway | Código local que encaminha solicitações ao provedor selecionado. |
| Skill | Conjunto de instruções e referências adequado à tarefa. |
| OCR | Reconhecimento de texto presente em imagens e páginas digitalizadas. |
| FTS | Índice de busca textual do SQLite. |
| Vetor / embedding | Representação numérica que permite comparar o significado aproximado de textos. |
| Cross-encoder | Modelo que lê pergunta e trecho juntos para atribuir um escore de relevância. O escore ordena candidatos e não representa uma probabilidade. |
| Cache | Cópia temporária de dados já preparados para acelerar consultas. |
| Token | Unidade de texto ou conteúdo contabilizada pelo serviço do modelo. |
| FMECA | Análise dos modos, efeitos e criticidade das falhas. |
| AE-LSTM | Autoencoder com rede recorrente para reconstruir sequências de sinais. |

## Reprodução e verificação

O gerador [gerar_mapas.py](gerar_mapas.py) usa Pillow e as fontes Segoe UI do Windows. A partir da raiz do projeto:

```powershell
.venv/Scripts/python.exe docs/arquitetura/2026-10-05/gerar_mapas.py
.venv/Scripts/python.exe -m ruff check docs/arquitetura/2026-10-05/gerar_mapas.py
```

As cinco imagens foram inspecionadas visualmente; a geração verifica o espaço ocupado pelo texto nos cartões. As referências de arquivos do guia e a estrutura XML dos SVGs foram verificadas localmente. Esta entrega é documental: não altera o funcionamento do AL-IAdo e não executa chamadas reais ao Gemini, treino ou reindexação.
