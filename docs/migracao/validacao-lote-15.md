# Validação do lote 15

Verificação local em **27/09/2026**, Windows/Python 3.12, numpy 2.5.3, torch 2.12.0+cpu.
Nenhum commit, push ou PR; nenhuma chamada paga.

## Resultado

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **320 testes passaram** (309 anteriores + 11 novos, um deles com os dados reais). O treino equivalente ao da origem é feito uma vez por sessão (fixture em `tests/conftest.py`) e serve às conferências dos lotes 14 e 15. |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| Origem | `mestrado-utfpr` sem alterações; os resultados da E3 foram só lidos. |

## Conferência com a origem (separação 2, 150 épocas, semente 42)

| Grandeza | Resultado |
|---|---|
| Escores das 14.064 janelas de pré-falha e pós-falha (`e3_escores_referencia.csv`) | Iguais até 1,7 × 10⁻⁷ em termos relativos, o último dígito de precisão simples. |
| 8 métricas por janela nos 28 pares de modelo e ensaio (`e3_metricas_por_ensaio.csv`) | Idênticas; a maior diferença é 1,1 × 10⁻¹⁶, na AUC-ROC. |

Os valores de referência foram copiados para `tests/data/gpvs_avaliacao_referencia.json`.

## Avaliação canônica

`data/resultados/gpvs-avaliacao-001`: treino `be9e54fa5d21…`, avaliação `ce8b06e483a0…`,
consulta em 27/09/2026, 5,7 s, 1,2 MB. Alarme com 3 janelas seguidas, semente 42 como
referência (faixa nas 5 sementes entre parênteses).

**Falsos alarmes**

| Modelo | Teste saudável (5,3 s) | Pré-falha (47 s) | Juntos (52 s): limite superior 95% |
|---|---|---|---|
| Denso | 0 alarmes; 2 de 263 janelas acima (0,76%) | 0 alarmes; 55 de 2.348 janelas (2,34%) | 0 alarmes: **até 207 por hora** |
| AE-LSTM | 0 alarmes; 1 de 263 janelas (0,38%) | 1 alarme (F1L); 39 de 2.348 janelas (1,66%) | 1 alarme: 69 por hora, **até 327 por hora** |

Nas 5 sementes, o Denso deu 0 alarmes em todos os trechos. O AE-LSTM deu 0 no teste
saudável e de 1 a 4 no pré-falha.

**Detecção**

| Modelo | Ensaios detectados | Atraso mediano | Sensibilidade média [IC 95%] | Especificidade média |
|---|---|---|---|---|
| Denso | 10 de 14 (9–10) | 2.041 ms | 0,402 [0,203; 0,606] | 0,977 |
| AE-LSTM | 8 de 14 (8–9) | 1.701 ms | 0,386 [0,184; 0,596] | 0,983 |

- **Detectadas pelos dois:** as duas falhas físicas (IGBT, F1, e circuito aberto, F5, nos dois modos), o erro de sensor (F2) e os afundamentos de rede (F3).
- **Nenhum dos dois detecta:** o sombreamento parcial (F4L e F4M), F6M e F7L.
- **Só o Denso detecta:** F6L e F7M, com escores pouco acima do limiar.

**Comparação por objetivo** (Denso − AE-LSTM, pareada): nas 5 métricas, **sem diferença clara**.

| Métrica | Diferença média | IC 95% | Sementes com o mesmo sinal |
|---|---:|---|---|
| Alarmes no pré-falha por ensaio | −0,07 | [−0,21; 0] | 5 de 5 |
| Especificidade | −0,006 | [−0,037; 0,023] | 4 de 5 |
| Ensaio detectado | +0,14 | [0; 0,36] | 5 de 5 |
| Sensibilidade | +0,016 | [−0,001; 0,041] | 5 de 5 |
| Atraso nos 8 ensaios detectados pelos dois | −2,5 ms | [−7,5; 0] | 4 de 5 |

O Denso tende a detectar mais e a alarmar menos, com o mesmo sinal em todas as sementes, mas
14 ensaios não bastam para separar isso do acaso.

**Métricas secundárias** (média nos 14 ensaios, Denso / AE-LSTM): AUC-ROC 0,775 / 0,758;
AUC-PR 0,863 / 0,847; F1 0,458 / 0,434; MCC 0,390 / 0,367; precisão 0,925 / 0,946; acurácia
balanceada 0,689 / 0,685.

**Sensibilidade à confirmação (m):**
- Com m = 1, há muitos alarmes no pré-falha (51 no Denso, 33 no AE-LSTM), e o Denso detecta 13 ensaios.
- Com m = 2, sobram 4 e 5 alarmes.
- Com m = 3 e m = 5, os alarmes quase zeram.

A grade de k não muda os eventos: só as contagens por janela mudam (no pré-falha do Denso, 55, 63 e 64 janelas acima para k = 5, 10 e 20).

## Achados

- **O atraso de segundos não é a velocidade dos detectores.** Em 7 dos 8 ensaios detectados
  pelos dois, os modelos disparam no **mesmo ciclo**; no F1L, com 20 ms de diferença. No ciclo
  do alarme, o escore salta de cerca de 1 para centenas ou até 100 mil. É uma mudança brusca
  no sinal, que aparece de 0,05 a 3,8 s **depois do meio nominal** do registro.
  - O atraso e a sensibilidade por janela medem, em boa parte, onde a falha se manifesta no registro. As janelas pós-falha anteriores a essa mudança contam como falhas não detectadas.
  - A comparação "detecta mais rápido" não é informativa com estes dados.
  - Estimar o início real mudaria o protocolo depois da consulta ao teste e exigiria avaliação independente (M14).
- **O pré-falha passa do limiar mais que a calibração previa:** 2,34% (Denso) e 1,66% (AE-LSTM), contra 1,04% esperado.
  - Esses ensaios são normalizados pelo próprio comissionamento, e não pela linha de base do treino.
  - A confirmação por 3 janelas absorve o efeito: 0 e 1 alarme.
- **Taxas de falso alarme só podem ser limitadas por cima:** com 52 s de operação saudável, até 207 por hora (Denso) e até 327 por hora (AE-LSTM), com 95% de confiança.
- A regra do três vale para o total de 52 s. Separadamente, o teste saudável limita a até 2.050 por hora, e o pré-falha, a até 230 por hora (Denso).
