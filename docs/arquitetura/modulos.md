# Fronteiras dos módulos

Estado após os lotes 04–06: conhecimento e ciência têm serviços locais;
memória persistente e web permanecem reservados. Importar módulos não inicia
SDKs, downloads, OCR, modelos ou gravação de estado.

| Módulo | Responsabilidade | Dependência permitida por desenho |
|---|---|---|
| `aliado.knowledge` | Catálogo SQLite, extração/OCR, versões e busca híbrida local | Extra `knowledge`, Tesseract e encoder local; sem interface ou regras do mestrado. |
| `aliado.memory` | Memórias aprovadas, origem e revisão | Armazenamento explícito por usuário/projeto; sem indexar automaticamente relatórios de triagem. |
| `aliado.science` | Cálculos RAM explícitos e exportação JSON/CSV/MD/PNG | Biblioteca padrão para cálculo, matplotlib opcional para PNG; sem LLM ou ML. |
| `aliado.interfaces.web` | Conversa, biblioteca e gestão de conta | Consome o agente e os serviços; não define fórmulas científicas ou fontes bibliográficas. |

O pacote `aliado.interfaces` apenas organiza interfaces futuras. A CLI permanece
em `aliado.cli`; novos comandos consomem os serviços. `Agent.answer` aceita uma
biblioteca opcional e composição de skills, preservando chamadas sem biblioteca.
`SKILL.md` orienta o modelo, mas não instala bibliotecas, concede permissões ou
implementa ferramentas. Instruções do desenvolvimento em `.agents/skills` são
distintas das especializações em `aliado.skills.builtin`.

## Fluxo documental implementado

1. O usuário seleciona um PDF, Markdown ou JSON e um diretório de biblioteca.
2. Preservar o original por hash e registrar versão, processamento e localizadores.
3. Extrair texto, aplicar OCR quando necessário e registrar falhas. Gerar Markdown
   e JSON para revisão, sem reescrita de conteúdo por LLM.
4. Indexar trechos com encoder local fixo e FTS5. Nova versão ou reprocessamento
   muda o índice ativo, preservando originais, registros e artefatos anteriores.
5. Recuperar trechos da biblioteca escolhida, inserir como dados no pedido e
   conferir os identificadores citados na resposta. Acervo vazio evita consulta paga.

Não existe scanner de pastas, upload pelo chat ou restauração automática de snapshots.
O registro histórico do pesquisador permanece arquivado no pacote, sem compor
o contexto automático da skill ou um corpus bibliográfico indexado. Documentação
de repositório pode ser fornecida como Markdown/JSON com commit e origem declarados
pelo usuário; não há clonagem, rastreamento automático ou ingestão de código.

## Memória, ciência e web

Relatórios privados de triagem são material para decisão humana. A futura memória
ativa precisará de aprovação, proveniência e isolamento; o marcador `ativo` de um
JSON antigo e a confiança atribuída por outro agente não dispensam essa revisão.
Sincronização com Obsidian, consolidação por LLM e persistência no GitHub são
integrações posteriores, não efeitos colaterais da leitura ou importação.

No lote 03, os princípios gerais aprovados orientam as instruções do núcleo e
as regras científicas curadas entram somente pela skill de pesquisa. Isso altera
o contexto enviado ao modelo, sem criar memória persistente ou ler relatórios
privados. O histórico de 13/09 permanece no pacote, sem carregamento automático.

Conforme M15, a integração MCP fica reservada para a v1. Serviços científicos e
documentais devem permanecer independentes desse mecanismo. Nenhuma conexão ou
servidor foi instalado; integrações futuras serão avaliadas por utilidade,
compatibilidade, manutenção e permissões da etapa.

Métodos e limites científicos ficam em [procedimentos](../ciencia/procedimentos.md).
O serviço Python recebe parâmetros, fontes, hipóteses e unidade explicitamente,
valida seu contrato e produz artefatos com proveniência em diretório novo. A skill
geral `confiabilidade` é composta com a de pesquisa. Markdown orienta interpretação;
o comando científico executa o cenário. O chat não dispara cálculos sozinho.
Resultados antigos não são resultados do destino, e o serviço geral não fixa
parâmetros de inversores ou horizonte de 20 anos.

A reserva web já acompanha o pacote Python, mas não há servidor nem dependência
web instalada por este lote. Um lote posterior definirá o extra de instalação e
a implementação. Convites, autenticação e isolamento de dados serão necessários
antes de disponibilizar a aplicação a outros usuários.
