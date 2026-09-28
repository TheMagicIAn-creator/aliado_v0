# Destino das ferramentas — lote 02

Inventário das 13 entradas de `ESPEC_FERRAMENTAS`, em
`src/conhecimento/ferramentas.py` da origem no commit `55c44df6`.
Os hashes completos estão em [lote-02.json](lote-02.json). A revisão classifica
necessidade e dependências; nenhuma dessas ferramentas foi instalada ou exposta
ao LLM neste lote. A origem e suas funcionalidades permanecem intactas.

| Ferramenta registrada | Destino proposto | Motivo e limite |
|---|---|---|
| `adicionar_anexo_biblioteca` | Serviço geral: `knowledge`, implementação posterior | Reaproveitar inclusão explícita, hash e metadados. A origem aceita PDF e depende do serviço de biblioteca, catálogo e indexador; não copiar restauração de acervo. |
| `listar_base_bibliografica` | Serviço geral: `knowledge`, implementação posterior | Catálogo determinístico útil para qualquer domínio; remover dependência do agente legado e da coleção global. |
| `buscar_web` | Serviço geral: `knowledge`, implementação posterior | Busca externa pode complementar o acervo. Exige adapter e acesso configurados; resultado web não se torna memória ou fonte indexada automaticamente. |
| `registrar_no_cerebro` | Serviço geral: `memory`, implementação posterior | Registro explícito de conteúdo curado é útil. Separar armazenamento aprovado do espelho Obsidian, da geração de nota por LLM e da persistência remota. |
| `consultar_datasets` | Orientação em Markdown; inventário real em Python posteriormente | A explicação do papel do dataset é editável. Contagem, presença, versão e integridade dos arquivos dependem de inspeção executável; não afirmar disponibilidade do GPVS neste destino. |
| `comparar_abordagens_ml` | Orientação em Markdown da especialização | A origem devolve texto fixo sobre modelos, features e métricas. Preservar o método de comparação, sem congelar números, autores ou conclusões do acervo anterior. |
| `executar_comparacao_autoencoders` | Especialização científica: `science`, implementação posterior | Treino e avaliação exigem dados, partições, parâmetros e dependências ML validados. Markdown descreve o protocolo; Python executa e registra resultados. |
| `gerar_confiabilidade` | Especialização científica: `science`, implementação posterior | Fórmulas podem ser documentadas; curvas e tabelas precisam de parâmetros rastreáveis e testes. O cadastro antigo de seis itens da FMECA não deve ser transportado como vigente. |
| `consultar_resultados` | Especialização científica: `science`, implementação posterior | Leitura de artefatos existentes é útil. Separar o leitor do catálogo de arquivos fixos da pesquisa antiga; ausência de resultados deve ser informada. |
| `consultar_comparacao_autoencoders` | Especialização científica: `science`, implementação posterior | Projeção de consulta da comparação, aproveitável sobre o leitor de resultados; não requer segundo motor de cálculo. |
| `consultar_status_pipeline` | Especialização científica: `science`, implementação posterior | Integridade e disponibilidade são úteis, mas o status depende dos experimentos realmente instalados. Não reproduzir a lista legada como capacidade atual. |
| `executar_pipeline_cientifico` | Adiada; fora do núcleo geral | Aciona várias etapas dependentes do estudo original. Reavaliar orquestração após migrar e validar cada executor; não criar comando agregado neste lote. |
| `limpar_resultados_ml` | Adiada; fora do lote | Não há artefatos migrados a limpar. A implementação antiga é específica das publicações e diretórios da origem; não criar exclusões apenas por existir o wrapper. |

Resumo de destinos: 4 serviços gerais, 2 orientações em Markdown, 5 interfaces
científicas dependentes de código e dados, 2 ferramentas adiadas.

## O que pode ser editado em Markdown

Os [procedimentos científicos](../ciencia/procedimentos.md) descrevem finalidade,
entradas, hipóteses, passos, limitações e critérios de verificação. Eles são
documentação do próximo desenho, não funções executáveis ou novas skills ativas.
O catálogo usa nomes legados para rastrear a origem; não promete manter todas
essas funções como APIs públicas do destino.

Descrições de dataset, protocolo de comparação e interpretação dos resultados
podem mudar sem reescrever cálculos. Já leitura de arquivos, hash, estatísticas,
treino e geração de figuras precisam de código verificável. Não executar blocos
Markdown por `eval` ou importar instruções documentais como código.

## Adaptações necessárias antes de migrar código

- A biblioteca da origem mistura catálogo, PDF, ChromaDB, fila e snapshot.
  Aproveitar responsabilidades separadamente quando a ingestão for implementada.
- A memória persistente possui espelhamento Obsidian e persistência remota;
  a consolidação também usa LLM, índice e arquivamento. Essas ações não devem
  ocorrer ao importar ou ler o futuro módulo de memória.
- A origem registra três etapas no pipeline: comparação, detectabilidade e
  confiabilidade. Referências textuais a apenas duas publicações não definem
  o escopo do destino; a detectabilidade E2 também depende de revisão metodológica.
- O módulo de confiabilidade descreve seis itens físicos, incluindo sensor e
  controle separados. O registro de setembro define quatro grupos: CCB,
  contatores CA/CC, módulo IGBT e ventiladores. Não transferir valores S/O/D,
  NPR ou correspondências com GPVS como decisões atuais.

Não foram migrados módulos de treino, datasets, resultados ou tabelas antigas.
Esta seleção será apresentada ao pesquisador antes do lote de implementação
das ferramentas escolhidas.
