# Validação do lote 01

Consolidação: 2026-09-14. Estado: arquivos locais prontos para revisão do usuário;
nenhum commit, push ou PR criado.

## Resultados

| Verificação | Resultado |
|---|---|
| `python -m pytest -q` | 49 testes passaram; clientes de inferência simulados e rede bloqueada na bateria. |
| `python -m ruff check .` | Sem problemas. |
| Skill Creator `quick_validate.py` | Skills `pesquisa-inversores` e `engenharia` válidas. |
| `python -m pip check` | Nenhuma incompatibilidade entre dependências instaladas. |
| `python -m build --wheel` | Pacote `aliado-0.1.0-py3-none-any.whl` gerado. |
| Importação diretamente do wheel em outra pasta | Duas skills disponíveis; referência científica incluída; pedido de pesquisa preparado com quatro mensagens. |
| CLI com saída originalmente configurada como ASCII | Contexto Unicode preparado em UTF-8 sem erro. |
| Proveniência | Nove entradas de código/testes conferidas contra os arquivos do commit-fonte. |
| Registro do usuário | Conteúdo preservado byte a byte, verificado por SHA-256. |
| Repositório de origem | Árvore de trabalho permanece sem alterações. |

Fonte imutável: `55c44df6bda807b73c4ac3762f0a89734633d384`.
SHA-256 do wheel validado:
`74f08221fcb5f7e5a621118bd0530b31b96b523f5b3c708761131d8ea874f875`.

Ambiente: Windows, Python 3.12.14, OpenAI SDK 3.13.0 e Google Gen AI SDK 1.75.0.
As versões instaladas estão em `requirements-dev.lock`; o build utilizou
setuptools 84.0.0 em ambiente isolado. O arquivo de versões descreve este ambiente,
sem promessa de reprodução binária idêntica do wheel em outras plataformas.

## O que foi demonstrado

O núcleo prepara pedidos gerais ou especializados, carrega as referências apenas
da skill selecionada e encaminha instruções/contexto aos adaptadores. Erros de
configuração, caminhos inválidos e saída Unicode foram exercitados. A instalação
inclui as skills e não depende da pasta de origem.

## Limites desta validação

Não houve inferência real, avaliação de respostas científicas, nova conferência dos
artigos, importação de literatura, indexação ou treino. Os testes não demonstram
qualidade de pesquisa sem fontes: essa avaliação depende do próximo lote de RAG
e do corpus selecionado pelo pesquisador.

O CLI é local e não persiste conversas. A web privada, autenticação por convite,
isolamento de usuários, memória e ferramentas científicas ainda não foram migrados.

Próximo ponto de participação: revisar os arquivos do lote com o usuário e decidir
o primeiro commit antes de iniciar o próximo lote.
