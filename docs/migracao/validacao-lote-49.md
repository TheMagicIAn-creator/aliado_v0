# Validação do lote 49 — os laços dos testes dos autoencoders

Data: 21 e 22/10/2026. Escopo na [spec 0049](../specs/0049-lacos-dos-testes.md). Os commits locais foram autorizados
pelo pesquisador no plano de 21/10; o push e a tag ficam com ele.

## Antes e depois

**Ferramenta:** `ferramentas/bateria.py` mede, em cada processo, o tempo, os treinos de rede e o pico de memória.
- **Antes:** no commit c2768f1 (lote 48), com um processo por arquivo de teste.
- **Depois:** com as pastas `tests/science` e `tests/mestrado` num processo cada, e os outros arquivos um por
  processo.

| Medida | Antes | Depois |
|---|---:|---:|
| Testes que passam | 834 | 836 |
| Testes ignorados ou com falha | 0 | 0 |
| Treinos de rede por bateria | 28 | 18 |
| Bateria inteira | 279,5 s | 217,4 s |
| Testes da ciência e do mestrado¹ | 180,3 s (186 testes) | 124,1 s (188 testes) |
| Maior pico de memória de um processo | 559,3 MiB (`test_reranking`) | 559,4 MiB (`test_reranking`) |
| Maior pico de memória na ciência | 473,5 MiB (`test_experiments`) | 473,7 MiB (`test_experiments`) |

Notas:
- ¹ Com `test_experiments`, `test_science_tab` e `test_specs`, que mudaram neste lote.
- Treino de rede: cada chamada do laço de treino (`fit`), contada pelo plugin `ferramentas/medicao.py`.
- Pico de memória: o maior conjunto de trabalho do processo no Windows, em MiB (1.024² bytes).

**De onde vêm os 18 treinos de depois:**
- 6 dos testes do próprio laço de treino: o determinismo, a paciência e o AE-LSTM com os pesos;
- 2 do teste que prova que o treino não usa o bloco de teste;
- 4 da rodada sintética da sessão (antes, 12, em 3 arquivos);
- 2 do treino da origem com os dados reais (antes, 4, em 2 processos);
- 4 da rodada real de ponta a ponta, em `test_experiments`.

**Os nomes dos testes:** os 834 de antes estão todos presentes, comparados pelo nome e pelos parâmetros, sem o caminho.
Os 2 novos são os do EXP-12.

**O tempo de `test_experiments`:** subiu de 26 para 34 s. A rodada real passou a usar a base da sessão, cujo cache dos
atributos é montado a partir dos CSVs pelo código de hoje, e não lido de `data/gpvs/processado`. É o que garante que
nada é gravado em `data/`.

## A equivalência

`ferramentas/equivalencia.py autoteste` rodou o experimento duas vezes no GPVS sintético (72 mil linhas por ensaio,
separação 2, sementes 42 e 13, teto de 3 épocas).

| Conferência | Resultado |
|---|---|
| Duas execuções iguais | 28 de 28 arquivos iguais, nenhuma diferença |
| Uma execução com um número alterado no `resultado.json` | a diferença aparece, só nesse arquivo |

Notas:
- Os JSON e o Markdown são comparados sem as datas e os horários da própria execução, `duracao_s` e `versao`.
- Os `.npz` e os `.pt` são comparados matriz por matriz; o resto, byte a byte.

**O ajuste achado no autoteste:**
- **O que aconteceu:** na 1ª tentativa, as duas execuções iguais diferiam em 2 arquivos: a configuração e o
  relatório da avaliação gravam o caminho da pasta do treino, e a ferramenta rodava cada execução numa pasta
  temporária nova.
- **A correção:** a ferramenta passou a rodar sempre na mesma pasta (`tmp/equivalencia/trabalho`). Nenhum caminho
  fica escondido da comparação.

**A referência dos lotes 50 a 55:** a rodada "a" do autoteste, copiada para `tmp/equivalencia/referencia` (fora do Git).

## Outras conferências

- **Ruff:** sem erro em todo o repositório.
- **Specs:** o EXP-12 é citado por `tests/mestrado/test_protocolo_fixo.py`, e `tests/test_specs.py` lê as subpastas.
- **`data/` intocado:** o cache real `data/gpvs/processado/variaveis.npz` continua com a data de 27/09/2026.
  - Os testes com os dados reais usam a pasta temporária da sessão, com os CSVs ligados e o cache montado lá.
- **O produto:** nenhum arquivo de `src/` mudou.

## Commits

- **5e1de6f:** a mudança de lugar (`git mv`) dos 12 arquivos de teste da ciência e do mestrado, com `tests/apoio`.
- **O commit seguinte:** a divisão por pasta, as fixtures, as marcações, as ferramentas, o EXP-12 e os registros
  deste lote.
