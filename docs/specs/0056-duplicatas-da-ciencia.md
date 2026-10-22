# Spec 0056 — as duplicatas da ciência

Estado: feito em 22/10/2026, sem commit; o commit fica com o pesquisador.

## Propósito e decisões

É o primeiro lote da 0.9.0 e vem da lista "Depois" do plano de 21/10. Duas contas estavam escritas em dois lugares,
e uma constante da rede de 50 Hz estava na ciência geral. Cada conta passa a existir num lugar só, e nenhum número
muda.

**Decisões do pesquisador em 22/10/2026:**
- **A 0.9.0** reúne os lotes 46 a 55 e os itens "Depois", em lotes pequenos combinados com ele.
- **O relatório em LaTeX, colado de novo:** é o de 21/10, já conferido em
  [relatório em LaTeX, conferido](../revisao/2026-10-21-relatorio-latex-conferido.md). Os lotes 49 e 50 dele são os
  nossos 54 e 55.
- **O Fourier** fica como está desde o lote 55: na arquitetura e sem tela. Nas palavras dele, "Ele não precisa
  aparecer". A subaba "Harmônicos" sai da lista.
- **Seguem abertas:** o Ollama, a leitura de páginas inteiras, a lista da limpeza, os nomes em inglês e quem faz os
  commits.

| Conta | Antes | Agora |
|---|---|---|
| Métricas de contagem: sensibilidade, especificidade, precisão, F1, acurácia balanceada e MCC | escritas duas vezes: em `window_metrics`, na ciência geral, e em `paineis.from_counts`, no mestrado | `from_counts` fica em `science/deteccao/metricas/por_janela.py`; `window_metrics` a usa, e o painel a importa |
| Comissionamento: a 1ª metade do pré-falha, com no mínimo 30 janelas | escrito duas vezes: em `preparo/preparacao.prepare` e em `inicio_das_falhas/estimativa.commissioning_windows` | `preparo/preparacao.commissioning_windows`, usada pelos dois |
| Janelas por hora | `WINDOWS_PER_HOUR = 3600 × 50` na ciência geral, que assim supunha a rede de 50 Hz | um argumento obrigatório de `markov_alarm_rate`; o mestrado passa `base/ensaios.WINDOWS_PER_HOUR` = 3.600 · 10.000 / 200 = 180.000 |

**Decisões tomadas na implementação:**
- **A ordem das chaves fica:** `window_metrics` devolve as AUCs antes das contagens, como sempre foi gravado.
- **A trava "pré-falha insuficiente" fica em `prepare`.** O início das falhas não tinha essa trava e continua sem ela.
- **As janelas por hora não têm valor padrão.** Sem o argumento, a chamada falha com `TypeError`: a ciência geral não
  supõe uma rede.
  - O produto dá os mesmos bits com 180.000 inteiro e com 180.000,0.
  - Isso foi conferido em 10 mil valores e, de novo, na equivalência.
- **`paineis.from_counts` continua existindo, como importação.** O apoio sintético dos testes e as asserções de
  `test_resultados.py` seguem chamando por ele, e um teste exige que seja a mesma função da ciência geral.

## Requisitos vivos

- **Nenhum requisito novo ou alterado.**
- **NUC-01, conferido de novo:** o núcleo não cita o domínio. A ciência geral deixa de fixar os 50 Hz da rede.

## Implementação

| Arquivo | O que muda |
|---|---|
| `science/deteccao/metricas/por_janela.py` | `from_counts`, nova; `window_metrics` passa a usá-la |
| `science/deteccao/alarmes/taxa.py` | sem `WINDOWS_PER_HOUR`; `markov_alarm_rate(..., windows_per_hour)` |
| `specializations/mestrado/resultados/paineis.py` | importa `from_counts`; sai a cópia e o `import math` |
| `specializations/mestrado/preparo/preparacao.py` | `commissioning_windows`, que `prepare` usa |
| `specializations/mestrado/inicio_das_falhas/estimativa.py` | chama `preparacao.commissioning_windows`; sai a cópia |
| `specializations/mestrado/base/ensaios.py` | `WINDOWS_PER_HOUR = 3600 * SAMPLING_HZ / WINDOW` |
| `specializations/mestrado/reanalise/reanalise.py` | passa `windows_per_hour=ensaios.WINDOWS_PER_HOUR` |

**Testes:**
- **`tests/science/test_metricas.py`:** `window_metrics` dá o `from_counts` das próprias contagens, mais as AUCs, nos
  mesmos bits e na mesma ordem das chaves.
- **`tests/science/test_alarmes.py`:** as chamadas passam as janelas por hora; sem elas, sai `TypeError`.
- **`tests/mestrado/test_preparo.py`:** a regra do comissionamento, com o mínimo de 30 janelas. O início das falhas
  não tem mais a cópia.
- **`tests/mestrado/test_resultados.py`:** `paineis.from_counts` é a função da ciência geral.

**Documentos:** `docs/ciencia/mapa-das-pastas.md` (etapas 3, 9 e 10).

## Aceitação

- **Equivalência:** uma rodada no GPVS sintético, comparada com a referência, sem nenhuma diferença. Ela passa pelo
  preparo, pelas métricas, pela reanálise e pela taxa de alarmes. Os arquivos novos dos lotes 54 e 55 seguem
  listados à parte.
- **Testes:**
  - os dos arquivos afetados, sem os dados reais;
  - a seleção rápida do pedido de 22/10;
  - a bateria rápida;
  - os testes que treinam só com dados sintéticos.
- **Ruff.**
- **Fica fora a bateria completa, com os dados reais:** ela treina com a base real e só roda com o OK do pesquisador.
