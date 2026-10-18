# Spec 0036 — o mestrado fora do núcleo, com zero menções

Estado: implementado e validado localmente em 18/10/2026; aguarda a revisão e o commit do pesquisador.
Spec de mudança: os requisitos vivos estão em [capacidades/nucleo.md](capacidades/nucleo.md) (NUC-01 completado,
sem a lista de transição; NUC-02 e NUC-03, novos).

## Propósito

O núcleo do AL-IAdo é a base do projeto pessoal seguinte do pesquisador; código e textos marcados com o domínio do
mestrado atrapalham essa separação. Regra dele: as menções ao domínio no núcleo não podem ser maiores que zero. É o
terceiro lote da [revisão da modularização e das specs](../revisao/2026-10-modularizacao-e-specs.md) e fecha a 0.7.0.

## Decisões do pesquisador (17/10/2026)

- O código do mestrado vai para `src/aliado/specializations/mestrado/`, dentro do AL-IAdo.
- Zero menções a `gpvs|inversor|mestrado|fotovolt` em qualquer arquivo do núcleo.
- Sem mecanismo de descoberta por YAML; não dividir `app.py` nem inverter a dependência `knowledge → routing`.
- Lançamento da 0.7.0, com os lotes 34 a 36; o commit, a tag, o push e o release são dele.

## O que muda

- **Mudam de lugar** (`git mv`), para `specializations/mestrado/`: `gpvs.py`, `training.py`, `evaluation.py`,
  `onset.py`, `reanalysis.py` e `summary.py`, que estavam em `science/detection/`; `explorer.py`, que estava em
  `science/`; e a skill `pesquisa-inversores`, que estava em `skills/builtin/` e agora fica em `skills/` da
  especialização.
- **Ficam no núcleo:** `protocol`, `metrics`, `threshold`, `models` e `registry` (detecção por reconstrução, para
  qualquer base), `ram`, `fmeca` e `components`.
- **Dividido:** `science/digest.py` fica com a formatação dos números e o texto dos blocos para o modelo; os blocos
  [R1]…[R8] do mestrado vão para `specializations/mestrado/digest.py`.
- **Novos na especialização:**
  - `__init__.py` expõe os atributos de NUC-02;
  - `routing.py`: as frases de exemplo que nomeiam o domínio, a skill da pesquisa e "gpvs" como termo de resultados;
  - `notes.py`: o glossário da aba Ciência (63 notas), que saiu de `graficos.js`; o resumo do chat usa as mesmas;
  - `commands.py`: `aliado ciencia preparar-gpvs`, `treinar-gpvs`, `avaliar-gpvs` e `reanalisar-gpvs`, com os
    mesmos argumentos;
  - `web.py`: as rotas da aba com a rodada atual (resumo, métricas, escores e início das falhas) e os exploradores.
- **No núcleo:**
  - `specializations.first()`, ao lado de `installed()` e `gather()`;
  - o roteador junta as frases, os termos e a skill padrão das especializações na primeira mensagem
    (`_specialized`), nunca ao importar;
  - o terminal recebe os comandos das especializações (`add_commands`, com `handler`) e tira delas a skill padrão,
    a pasta das referências e os resultados de `--resultados`;
  - a interface tira delas a pasta das referências, os resultados do chat e o assunto da reescrita da busca;
  - `/api/ciencia` junta o estado de cada especialização e o glossário; `ciencia.js` o passa a `graficos.js`;
  - a curva de confiabilidade da exploração (`reliability`) e a fonte da exploração vão para `science/ram.py`;
  - o agente usa o apoio declarado na skill (`metadata.apoio` no SKILL.md), no lugar do nome fixo;
  - o carregador de skills procura também em `specializations/<nome>/skills/`;
  - a reescrita da busca recebe o assunto da biblioteca de quem a chama;
  - textos sem o domínio: o docstring de `science/detection`, um limite em `components.py` e a origem do D3 em
    `graficos.js`.
- **Pacote:** versão 0.7.0; as skills da especialização entram no `package-data`.
- **Testes:**
  - os imports seguem os módulos;
  - o do manifesto do lote 1 segue a skill pelo novo caminho, sem editar o manifesto;
  - o do carregador aceita as pastas das especializações;
  - o do glossário confere a fonte única;
  - `test_isolation.py` exige zero menções e confere NUC-02.

## Fora deste lote

- Nomes dos modelos e o padrão dos ensaios no roteador (`RESULT_MODELS`, `_TRIAL`): não são menções e servem só
  quando o resumo dos resultados não está montado.
- Os textos da aba Ciência em `ciencia.js` e `graficos.js` que falam dos ensaios sem citar o domínio pelo nome.
- Registros antigos (manifestos, specs 0001 a 0035, mapas de arquitetura de 05/10) citam os caminhos de antes: são
  registros e não mudam.

## Aceitação

- `pytest` e `ruff`; `tests/test_isolation.py` com zero menções no núcleo.
- `aliado skills` lista a skill da pesquisa; o pacote 0.7.0 leva a skill e as referências; o servidor sobe com a
  aba Ciência e o chat.
- Nenhuma chamada paga. Os resultados e os dados do pesquisador não são tocados.
