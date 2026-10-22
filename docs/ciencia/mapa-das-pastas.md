# Mapa das pastas da ciência

Criado no lote 50 (22/10/2026). Liga cada etapa do método à equação, à pasta, aos arquivos e funções e ao teste que a
confere. As funções e classes têm os nomes de antes; só o lugar mudou. A tabela do fim, do nome antigo para o novo,
serve à tradução para o inglês, quando tudo estiver operando.

## Ciência geral: `src/aliado/science/`

Vale para qualquer base de dados. Nenhum arquivo cita o domínio de uma especialização (NUC-01), e o `__init__.py` de
cada pasta só explica o que ela tem (NUC-04).

### A detecção, na ordem do método (`science/deteccao/`)

**1. Partição** (`particao/`, teste `tests/science/test_particao.py`)
- `blocos.py`: `temporal_split`, `ROLES` e `DEFAULT_FRACTIONS`.
  - Blocos contíguos de treino, validação, calibração e teste. As fronteiras ficam em int(n × fração acumulada), e
    `purge` janelas são descartadas depois de cada fronteira.
- `sequencias.py`: `sequences_from_flow` e `sequences_for_blocks`.
  - Uma sequência de 8 janelas por janela, sem atravessar blocos; a 1ª janela se repete só no início do bloco.
- `autocorrelacao.py`: `autocorrelation` e `decorrelation_report`.
  - Em que lag |ACF| fica abaixo de 0,2 em 90% das variáveis, para conferir a separação.

**2. Normalização** (`normalizacao/escala_robusta.py`, teste `test_normalizacao.py`)
- `robust_center_scale` e `RobustScaler`.
- z = (x − mediana) / escala. A escala é o IQR do bloco de treino; com piso, a escala é o maior entre o IQR e o
  piso, e sem piso o IQR nulo vira 1.

**3. Redes** (`redes/autoencoders.py`, teste `test_redes.py`)
- `Hyperparameters`, `DenseAutoencoder`, `LSTMAutoencoder`, `build` e `parameter_count`.
- **Denso:** 24 → 16 → 8 → 16 → 24, com ReLU, dropout de 0,2 antes do gargalo e antes da saída, e saída linear.
  Tem 1.088 parâmetros.
- **AE-LSTM:**
  - o encoder é uma LSTM de 24 para 32 e uma camada linear de 32 para 8;
  - o decoder volta de 8 para 32, repete o vetor nos 8 passos e passa por uma LSTM de 32 para 32 e por uma camada
    linear de 32 para 24, com dropout nas duas travessias do gargalo;
  - tem 17.216 parâmetros.

**4. Treino** (`treino/laco.py`, teste `test_treino.py`)
- `set_seed`, `fit` e `TrainingHistory`.
- Adam, com taxa de 10⁻³ e perda quadrática média, em lotes de 32 embaralhados por gerador semeado.
- Até 2.000 épocas, com paciência de 20 na validação; fica guardada a época de menor perda de validação.

**5. Pesos** (`pesos/arquivos.py`, teste `test_pesos.py`)
- `save_model` e `load_model`.
- Só tensores e tipos simples, lidos com `weights_only=True`, sem pickle.

**6. Inferência** (`inferencia/erros.py`, teste `test_inferencia.py`)
- `feature_errors`.
- e_{j,t} = (x_{j,t} − x̂_{j,t})², para j = 1 … 24. No AE-LSTM, só o último passo da sequência.

**7. Escore** (`escore/top_k.py`, teste `test_escore.py`)
- `top_k_scores`.
- s_t = (1/k) · Σ dos k maiores e_{j,t}, com k = 5.

**8. Limiar** (`limiar/calibracao.py`, teste `test_limiar.py`)
- `calibrate_threshold`, `false_alarm_interval` e `effective_sample_size`.
- τ é o escore de calibração na posição ceil((n − 1) · p / 100) + 1 da fila crescente, sem interpolação, com
  p = 99. Com n = 192, é o 2º maior.
- O alarme falso esperado por janela é (n + 1 − posição) / (n + 1).

**9. Alarmes** (`alarmes/`, teste `test_alarmes.py`)
- `confirmacao.py` (`alarm_starts` e `first_alarm`):
  - o alarme é a m-ésima janela seguida com s_t > τ, com m = 3;
  - uma sequência longa conta como um alarme só;
  - na avaliação, o alarme é datado pelo fim da janela que o confirma.
- `taxa.py` (`markov_alarm_rate` e `WINDOWS_PER_HOUR`): a chance de alarme por janela é π₀ · p₀₁ · p₁₁^(m−1), numa
  cadeia de Markov de dois estados (Brook e Evans, 1972).

**10. Métricas** (`metricas/`, teste `test_metricas.py`)
- `por_janela.py` (`window_metrics`, `auc_roc` e `auc_pr`):
  - sensibilidade = VP/(VP + FN), especificidade = VN/(VN + FP), precisão, F1, MCC e acurácia balanceada;
  - AUC-ROC por Mann-Whitney e AUC-PR por trapézios.
- `incerteza.py` (`proportion_interval`, `poisson_upper`, `paired_interval` e `verdict`):
  - bootstrap em blocos móveis de 12 janelas, com 20.000 reamostragens;
  - limite exato de Poisson (Garwood, 1936);
  - diferenças pareadas Denso − AE-LSTM.

**11. Registro** (`registro/consultas.py`, teste em `tests/test_experiments.py`)
- `start`, `finish`, `consultations` e `close_open`.
- Cada consulta aos dados de teste vira uma linha de `registro-consultas-teste.jsonl`, que só cresce.

Notas:
- VP, FN, FP e VN são as janelas com falha detectadas, com falha não detectadas, sadias acima do limiar e sadias
  abaixo dele.
- O MCC vai de −1 a 1 e mede a concordância entre o alarme e a falha, mesmo com classes de tamanhos diferentes.

### As outras pastas

| Pasta | Arquivos e funções | Teste |
|---|---|---|
| `confiabilidade/` | `cenarios.py`: `evaluate_scenario` e `reliability` (R(t), F(t), h(t), MTTF, série, paralelo e disponibilidade inerente); `artefatos.py`: `export_result` | `tests/science/test_confiabilidade.py` |
| `fmeca/` | `tabela.py`: `load_table`; `calculo.py`: `evaluate_fmeca` (NPR = S × O × D e a leitura pelas taxas, sem fundir); `relatorio.py`: o Markdown; `artefatos.py`: `export_fmeca` | `tests/science/test_fmeca.py` |
| `componentes/` | `reparos.py`: `load_repairs` e `validate_repairs`; `disponibilidade.py`: `component_view` | `tests/science/test_componentes.py` |
| `resumo_citavel/` | `formato.py`: `num`, `pct`, `seconds`, `dec`, `prompt_text`, `notes_text` e `SECTIONS` | `tests/science/test_resumo_citavel.py` |

## Mestrado: `src/aliado/specializations/mestrado/`

A pesquisa de detecção de falhas na base GPVS-Faults, na ordem do método. Os testes de cada pasta ficam em
`tests/mestrado/test_<pasta>.py`.

| Etapa | Pasta e arquivos | O que tem | Teste |
|---|---|---|---|
| 1. Base | `base/ensaios.py`, `base/leitura.py` | os 16 ensaios (F0L e F0M sadios; F1L a F7M com falha), as 14 colunas, as 7 falhas, a amostragem de 10 kHz, a janela de 200 amostras (um ciclo de 50 Hz), a pasta da base; os arquivos, a proveniência pelos hashes, os CSVs | `test_base.py` |
| 2. Atributos | `atributos/variaveis.py`, `extracao.py`, `cache.py` | as 24 variáveis de cada janela (mediana e IQR de Ipv, Vpv e Vdc; RMS e THD de cada fase; desequilíbrios; potências), a extração por ensaio e o cache | `test_atributos.py` |
| 3. Preparo | `preparo/preparacao.py`, `resumo.py`, `artefatos.py`, `inicio_nominal.py` | a divisão 50/15/15/20 com separação de 11 janelas, a normalização pela linha de base do treino (piso de 10% do IQR), o comissionamento pela 1ª metade do pré-falha, o início nominal (o meio do registro) | `test_preparo.py` |
| 4. Treino | `treino/configuracao.py`, `detectores.py`, `resumo.py`, `relatorio.py`, `artefatos.py` | a configuração congelada com hash, as entradas de cada modelo, o treino em cada repetição e o limiar p99 na calibração | `test_treino.py` |

As pastas seguintes entram nos lotes 52 e 53: `avaliacao/`, `inicio_das_falhas/`, `reanalise/`, `comandos/`,
`rodada/`, `resultados/`, `resumo_para_o_chat/`, `exploradores/`, `tela/`, `roteamento/` e `glossario/`.

## Do nome antigo para o novo

| Antes | Agora | Em inglês (proposta, para depois) |
|---|---|---|
| `science/detection/models.py` | `deteccao/redes/autoencoders.py`, `deteccao/treino/laco.py`, `deteccao/pesos/arquivos.py`, `deteccao/inferencia/erros.py` e `deteccao/escore/top_k.py` | `detection/networks`, `training`, `weights`, `inference` e `score` |
| `science/detection/protocol.py` | `deteccao/particao/blocos.py`, `sequencias.py` e `autocorrelacao.py`; `deteccao/normalizacao/escala_robusta.py` | `partition` e `normalization` |
| `science/detection/threshold.py` | `deteccao/limiar/calibracao.py` | `threshold` |
| `science/detection/metrics.py` | `deteccao/alarmes/confirmacao.py` e `taxa.py`; `deteccao/metricas/por_janela.py` e `incerteza.py` | `alarms` e `metrics` |
| `science/detection/registry.py` | `deteccao/registro/consultas.py` | `registry` |
| `science/ram.py` | `confiabilidade/cenarios.py` e `artefatos.py` | `reliability` |
| `science/fmeca.py` | `fmeca/tabela.py`, `calculo.py`, `relatorio.py` e `artefatos.py` | `fmeca` |
| `science/components.py` | `componentes/reparos.py` e `disponibilidade.py` | `components` |
| `science/digest.py` | `resumo_citavel/formato.py` | `citable_digest` |
| `mestrado/gpvs.py` | `base/ensaios.py` e `leitura.py`; `atributos/variaveis.py`, `extracao.py` e `cache.py`; `preparo/preparacao.py`, `resumo.py` e `artefatos.py` (lote 51) | `dataset`, `features` e `preparation` |
| `mestrado/training.py` | `treino/configuracao.py`, `detectores.py`, `resumo.py`, `relatorio.py` e `artefatos.py` (lote 51) | `training` |
| `evaluation._onset`, `reanalysis._nominal` e `summary.onset` | `preparo/inicio_nominal.nominal_onset` (lote 51) | `nominal_onset` |

Os mapas datados de `docs/arquitetura/2026-10-05/` são registros daquele dia e mantêm os caminhos antigos.
