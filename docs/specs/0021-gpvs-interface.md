# Lote 21 — GPVS pela interface e lançamento da 0.2.0

Lote autorizado em 28/09/2026, depois do lote 20 (`4d38e19`). Completa a aba Ciência com as três
etapas do GPVS, que só rodavam pelo terminal, e fecha a versão 0.2.0.

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Treino | **Os ajustes do comando:** separação, sementes e teto de épocas, preenchidos com a configuração canônica. Uma mudança marca a rodada como exploratória. |
| Nova avaliação (M14) | **Permitida com registro** (decisão de 28/09): confirmação por **frase digitada** ("consultar o teste"), registro da consulta e marca de não canônica. A oficial continua a de 27/09. |
| Aceite | Uma avaliação igual à de 27/09 pela interface, **numa cópia** dos resultados; o registro fica na cópia. |
| Exploradores | Continuam só na rodada canônica (`gpvs-modelos-002` e `gpvs-avaliacao-001`). |

## Escopo implementado

- **Execução** (`interfaces/web/gpvs_runs.py`):
  - cada etapa roda num subprocesso `python -m aliado ciencia preparar-gpvs | treinar-gpvs | avaliar-gpvs`, com os argumentos do terminal. É o mesmo caminho de código, e um erro não derruba o servidor;
  - só uma etapa por vez, num executor separado do envio de documentos;
  - o progresso vem das linhas que o treino imprime, uma por modelo e semente;
  - **Cancelar** encerra o processo;
  - cada etapa grava numa pasta nova com o próximo número (`gpvs-preparo-NNN`, `gpvs-modelos-NNN`, `gpvs-avaliacao-NNN`) e, ao fim, grava `execucao.json` (origem, comando, horários, estado e se a configuração é a canônica);
  - o executor é injetável (`WebSettings.gpvs_command`), para os testes.
- **Registro das consultas ao teste** (`science/detection/registry.py`):
  - `registro-consultas-teste.jsonl`, na pasta de resultados, só acrescentado;
  - na primeira gravação, começa pela consulta canônica de 27/09, lida da própria avaliação. Ler o registro não grava nada;
  - uma nova avaliação exige a frase exata (conferida no servidor), recebe o próximo número e gera os eventos "iniciada" e "concluída", "falhou" ou "cancelada";
  - a pasta da avaliação ganha `consulta.json`, com `canonica: false`.
- **Interface:**
  - a seção **Rodar GPVS** tem os cartões Preparar, Treinar (com o selo "configuração canônica" ou "exploratória") e Avaliar;
  - a janela do M14 só libera o botão com a frase completa;
  - o progresso mostra as linhas, o tempo e o Cancelar, e há o link para o resultado;
  - a tabela das consultas ao teste fica visível.
- **Resultados:**
  - reconhecem o preparo (`gpvs-preparo`);
  - marcam a avaliação como canônica ou não canônica, com o número da consulta, e o treino como canônico ou exploratório;
  - mostram quando a rodada foi feita pela interface.
- **Correção do lote 20:** em telas estreitas, as grades da aba Ciência (a seção Rodar e os gráficos lado a lado da FMECA) causavam rolagem lateral. As colunas passaram a caber no espaço.
- **Lançamento 0.2.0:**
  - versão no `pyproject.toml`, CHANGELOG, README e roteiro;
  - pacote `dist/v0.2.0/aliado-0.2.0-py3-none-any.whl`.
  - **A tag e o push ficam com o pesquisador.**

## Critérios de aceitação

- **Testes sem rede:**
  - frase exigida no servidor e registro semeado, numerado e só acrescentado;
  - pastas novas e numeradas;
  - uma etapa por vez e o cancelamento;
  - treino marcado como canônico ou exploratório;
  - faixas nos Resultados.
- **Com os dados reais:** o preparo pela interface gera o mesmo relatório que o comando.
- **Aceite no navegador, numa cópia dos resultados e sem chamadas pagas:**
  - o treino canônico pela interface reproduz bit a bit os 10 modelos de `gpvs-modelos-002`;
  - a avaliação dele reproduz a `gpvs-avaliacao-001`;
  - o registro da cópia mostra as consultas 1 (canônica) e 2 (não canônica);
  - o cancelamento não deixa processo nem pasta;
  - a tela estreita não rola para os lados.
- **Pacote:** o wheel instalado fora do projeto roda os comandos e serve a aba Ciência.
- A suíte completa e o Ruff passam.

## Fora do escopo

- Exploradores sobre rodadas não canônicas.
- A tag `v0.2.0` e o push, que ficam com o pesquisador.
