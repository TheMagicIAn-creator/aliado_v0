# Spec 0049 — os laços dos testes dos autoencoders

Estado: feito em 21/10/2026, com commits locais autorizados pelo pesquisador no plano de 21/10; push e tag ficam com
ele.

## Propósito e decisões

O pesquisador apontou "o laço dos testes" dos autoencoders. A conferência de 21/10 achou:
- **Treinos:** 28 treinos de rede por bateria. O treino com os dados reais rodava duas vezes, e os mesmos 4 modelos
  sintéticos, três vezes.
- **Dados:** o GPVS sintético era gerado 5 vezes, e os CSVs reais eram lidos em processos diferentes.
- **Organização:**
  - testes importavam outros testes (`write_synthetic`, `synthetic`);
  - havia 6 condições diferentes para os dados reais;
  - testes com os dados reais podiam gravar em `data/gpvs` se o cache faltasse.

**Decisões do plano aprovado em 21/10:**
- só testes, ferramentas e documentos; o produto não muda;
- os testes da ciência e do mestrado em pastas que espelham as pastas finais;
- nenhum teste importa outro;
- o protocolo fixo vira requisito, pela regra 1 do relatório em LaTeX de 21/10.

## Requisitos vivos

- **EXP-12, novo:** protocolo fixo. São:
  - os 24 atributos;
  - a janela de um ciclo;
  - a normalização robusta;
  - a divisão;
  - o escore dos 5 maiores;
  - o p99;
  - as 3 janelas;
  - a sequência de 8.

  Mudar um deles é mudar o método e pede spec própria.

## Implementação

**`tests/apoio/`:**
- os caminhos do repositório;
- as duas condições dos dados reais: "base presente" e "resultados oficiais presentes";
- o GPVS sintético;
- a avaliação sintética e a rodada oficial em miniatura.

**`tests/science/` e `tests/mestrado/`:** pacotes com um arquivo por pasta da ciência e do mestrado.
- **Ciência:** partição, normalização, redes, treino, pesos, inferência, escore, limiar, alarmes, métricas,
  confiabilidade, FMECA, componentes e resumo citável.
- **Mestrado:** base, atributos, preparo, treino, avaliação, comandos, início das falhas, reanálise, resultados, tela,
  exploradores, resumo para o chat e protocolo fixo.
- **Ficam onde estavam:** os testes do chat e `test_experiments.py`.
- **Commits:** a mudança de lugar dos arquivos inteiros (`git mv`) foi um commit; a divisão por pasta, outro.

**Fixtures de sessão** (`tests/conftest.py` e `tests/mestrado/conftest.py`):
- `gpvs_sintetico` e `preparado_sintetico`: o GPVS sintético, gerado e preparado uma vez;
- `rodada_sintetica`: os 4 detectores sintéticos treinados, exportados e avaliados uma vez. Ela é só de leitura, e
  `rodada_sintetica_copia` dá uma cópia a quem grava;
- `base_real`: a base real numa pasta temporária, com os CSVs ligados sem cópia e o cache dos atributos montado uma
  vez pelo código de hoje. Nada é gravado em `data/`;
- `official_results`: a cópia da avaliação de 27/09, do treino dela e da reanálise de 30/09;
- `origin_gpvs_runs`: o treino da origem, uma vez.

**Marcações:**
- `treina` e `dados_reais`, registradas no `pyproject.toml`;
- vêm do uso das fixtures, e os testes que chamam o treino direto são marcados à mão.

**`tests/test_specs.py`:** lê os testes de todas as subpastas.

**Ferramentas versionadas:**
- `ferramentas/bateria.py`: cada subpasta de testes roda num processo, e cada arquivo de fora, em outro. Ela registra
  o tempo, os treinos de rede (pelo plugin `ferramentas/medicao.py`) e o pico de memória de cada processo.
  - `--rapida` deixa de fora `treina` e `dados_reais`.
- `ferramentas/equivalencia.py`: roda `aliado experimento rodar` num GPVS sintético de 72 mil linhas e compara a
  rodada com uma referência. As datas, a duração e a versão ficam fora da comparação.
  - Arquivos e chaves novos aparecem à parte das diferenças.
  - O `autoteste` prova os dois lados: duas execuções iguais não mostram diferença, e uma alterada mostra.

## Aceitação

- **Os nomes dos testes:** os mesmos 834, mais os 2 do EXP-12, com 0 ignorados.
- **Os treinos por bateria:** de 28 para 18, com o treino real uma vez.
- **O tempo e o pico de memória:** medidos antes e depois, na
  [validação do lote 49](../migracao/validacao-lote-49.md).
- **A equivalência:** o `autoteste` sem diferença entre execuções iguais e com diferença na alterada. A referência
  fica gravada para os lotes 50 a 55.
- **O resto:** Ruff e as specs.
