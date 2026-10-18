# Validação do lote 36 — o mestrado fora do núcleo, com zero menções

Data: 18/10/2026. Escopo na [spec 0036](../specs/0036-mestrado-fora-do-nucleo.md); requisitos vivos em
[capacidades/nucleo.md](../specs/capacidades/nucleo.md). Nenhuma chamada paga. Os resultados e os dados do
pesquisador não foram tocados: a aba foi conferida sobre a cópia do lote 34, em `tmp/lote-34/resultados`.

## Bateria

| Conferência | Resultado |
|---|---|
| `pytest` | 786 testes passaram (eram 785 no lote 35) |
| `ruff check .` | sem apontamentos |
| Teste novo | `test_isolation.py`: NUC-02, os atributos da especialização e a especialização fora dos imports do núcleo |
| Testes revistos | os imports dos módulos que mudaram de lugar; o manifesto do lote 1, que segue a skill pelo caminho novo; o carregador de skills; o glossário com uma fonte só; o estado da aba com as notas |
| Requisitos vivos citados por testes | NUC-01 a NUC-03: todos |

## Menções ao domínio no núcleo

Medidas com `gpvs|inversor|mestrado|fotovolt` nos arquivos .py, .js, .html, .css, .md e .json de `src/aliado`, fora
de `specializations/<nome>/`.

| Quando | Linhas | Arquivos |
|---|---:|---:|
| 0.6.0 | 294 | 27 |
| Lote 34 | 227 | 22 |
| Lote 35 | 218 | 20 |
| Lote 36 | 0 | 0 |

## Pela tela (servidor de teste `aliado-web-lote-34`, porta 8782)

- **Aba Ciência:** as oito seções abriram com a rodada atual da cópia (rodada-002). As 251 notas "i" das seções
  vieram com texto, todas do glossário servido pela especialização.
- **Rotas:** todas responderam: as da especialização (resumo, métricas, escores, início das falhas, preparar e
  limiar dos exploradores) e as do núcleo (FMECA, componentes, cenários e a curva de confiabilidade).
- **Console:** só o 400 de `/api/memoria`, que o servidor de teste não tem, como no lote 34.

## O pacote 0.7.0

- **Montagem:** `dist/v0.7.0/aliado-0.7.0-py3-none-any.whl`, 111 arquivos, SHA-256
  `b920d7d67a8605063316d6df87b453afec062502aa8c4ca6615f1a77678d9edb`.
- **Por que numa cópia:** foi montado de uma cópia limpa de `src/` em `tmp/v070-build`, sem baixar nada. Montado na
  pasta do projeto, ele levava também os módulos antigos, que estavam no cache `build/` do setuptools.
- **Conferência pelo wheel** (`tmp/v070-check/conferir_pacote.py`), com o AL-IAdo importado do wheel aberto e não da
  pasta `src`:
  - `aliado skills` lista confiabilidade, engenharia e pesquisa-inversores;
  - a skill da pesquisa vem com o apoio de confiabilidade e a referência das diretrizes;
  - `aliado ciencia treinar-gpvs --help` responde;
  - a página abre, e a aba Ciência tem a FMECA, os cenários, a rodada atual e as 63 notas.

## Correções durante a validação

- **Import esquecido:** o resumo do chat ainda importava a rodada atual do lugar antigo; os testes do resumo acusaram,
  e a correção foi feita antes da bateria.
- **Função renomeada:** a rota dos experimentos usava a função de erro da aba pelo nome antigo (`_error`); passou a
  `error`.
- **Pacote com arquivos antigos:** o primeiro wheel saiu com os módulos e a skill nos lugares de antes, vindos do cache
  `build/`. Foi apagado e montado de novo na cópia limpa.

## Fica para depois

- **Roteador:** os nomes dos modelos e o padrão dos ensaios (`RESULT_MODELS`, `_TRIAL`) continuam no núcleo. Não são
  menções e só servem quando o resumo dos resultados não está montado.
- **Textos da aba:** os de `ciencia.js` e `graficos.js` que falam dos ensaios sem citar o domínio pelo nome ficam como
  estão.
- **Cache do setuptools:** `build/`, fora do Git, ainda tem os módulos antigos; apagá-lo não muda nada no projeto.
- **Uso no dia a dia:** para usar a versão nova, é preciso reiniciar o AL-IAdo.
