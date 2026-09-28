# Validação do lote 02

Data: 15/09/2026. Implementação local concluída para revisão do pesquisador.
Nenhum commit, push ou PR criado. Este registro complementa a
[validação do lote 01](validacao-lote-01.md); não substitui seu histórico.

## Resultados observados

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest` | 49 testes passaram, incluindo a importação ampliada aos quatro módulos reservados. |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| Skill Creator `quick_validate.py`, com Python em UTF-8 | Skill `pesquisa-inversores` válida após a atualização. |
| `.venv/Scripts/python.exe -m pip check` | Nenhuma incompatibilidade entre as dependências instaladas. |
| `.venv/Scripts/python.exe -m build --wheel --outdir tmp/lote-02/dist` | Wheel gerado com build isolado e setuptools 84.0.0. |
| Inspeção do wheel | 27 entradas: código do pacote, duas skills, registro histórico e metadados. Nenhum relatório privado, memória legada ou documento de inspeção. Bytes do pacote conferidos contra os arquivos atuais. |
| Importação e CLI diretamente do wheel, em pasta temporária externa | Módulos importados sem SDKs LLM, ML, banco ou servidor web. Listagem das duas skills e preparação offline passaram; nenhum arquivo criado. |
| Bloqueio de efeitos no processo externo | Importação, leitura das skills e preparação executadas com bloqueio de rede, subprocessos, escrita, leitura de `.env` e dos relatórios privados. |
| Inventário de memória | Cobertura exata dos 30 arquivos em `notas/memorias/` na árvore completa do commit-fonte. |
| Proveniência da inspeção | SHA-256 e Git blob conferidos para 30 memórias, 9 arquivos de código e 1 sessão usada como evidência. Nenhum código legado executado para a inspeção. |
| Propostas privadas | 16 propostas com trechos, linhas e hashes conferidos: 9 candidatas à preservação e 7 decisões a rever, todas pendentes e inativas. |
| Ferramentas | 13 nomes extraídos da declaração da origem via AST, sem importá-la; cobertura do manifesto e catálogo conferida: 4 gerais, 2 orientações, 5 científicas futuras, 2 adiadas. |
| Relatórios privados | Seis arquivos em `data/memory-review/` existem e são ignorados por `git check-ignore`; não estão no índice Git nem no wheel. |
| Separação dos lotes | Baseline de 40 arquivos conferido: 12 arquivos novos, 5 adaptados e nenhuma exclusão no lote 02; 32 links locais válidos nos documentos conferidos. |
| Registro de 13/09 | SHA-256 original preservado no checkout e no wheel. |
| Origem | `git status --porcelain=v1` sem alterações; não houve escrita deliberada no repositório de origem. |

Wheel: `tmp/lote-02/dist/aliado-0.1.0-py3-none-any.whl`.
SHA-256: `30774ed96568fa4a7ebf0a0748c5629c81133458d21c39218becde32feff65f1`.
Ambiente: Windows, Python 3.12.14, pytest 9.1.1, setuptools 84.0.0 no build
isolado. Dependências da aplicação preservadas em `requirements-dev.lock`.

A tentativa inicial com `--no-isolation` falhou porque a `.venv` não contém
setuptools. O comando padrão acima criou o ambiente de build e passou; não foi
necessário alterar as dependências do projeto.

## Conferência do escopo

- **P01–P02:** pacotes reservados importáveis, sem novos serviços, comandos ou
  ferramentas do LLM; CLI, contratos, gateway e adaptadores preservados.
- **P03:** skill distingue corpus vazio, histórico e triagem; referência original
  preservada byte a byte.
- **P04–P05:** cobertura das memórias e evidências verificada; triagem privada,
  nenhuma aprovação presumida ou ativação de memória.
- **P06–P07:** catálogo completo e procedimentos com entradas, hipóteses, passos,
  limites e verificação. Divergência FMECA de seis versus quatro grupos registrada.
- **P08:** fonte fixa e árvore de trabalho da origem limpa; nenhuma importação de
  dados no agente, indexação, treino, servidor ou inferência paga nesta validação.

Um leitor independente respondeu às cinco perguntas de aceitação documental:
capacidades atuais, conteúdo legado, destino das ferramentas, participação do
usuário e separação dos lotes. A revisão identificou a falta de um link direto
dos procedimentos ao registro histórico; o link e sua função foram explicitados
e a correção foi confirmada pelo leitor.

## Limites e revisão do resultado

As fronteiras são reservas documentadas; ainda não há upload, indexação, memória
persistente, execução científica ou web funcional. Não foi avaliada a qualidade
das respostas de um provedor real, nem revalidada toda a bibliografia ou os
resultados numéricos das memórias. A cobertura de 30 arquivos é triagem estrutural
e temática, não uma auditoria científica integral de seu conteúdo.

As cópias e verificações auxiliares ficam em `tmp/lote-02/`, ignorado pelo Git.
`verify_preparation.py` reproduz as conferências de inventário, evidências e wheel
usando o snapshot local; `verification.json` registra o resultado. O manifesto
público permite conferir as fontes sem publicar o conteúdo privado da triagem.

Os arquivos para revisão estão separados em [revisão dos lotes](revisao-dos-lotes.md).
O próximo lote e quaisquer operações de versionamento serão combinados com o
pesquisador sobre este resultado concreto.
