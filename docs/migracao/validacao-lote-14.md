# Validação do lote 14

Verificação local em **27/09/2026**, Windows/Python 3.12, numpy 2.5.3, torch 2.12.0+cpu
(10 threads). Nenhum commit, push ou PR; nenhuma chamada paga.

## Resultado

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **309 testes passaram** (295 anteriores + 14 novos, um deles com os dados reais). O único aviso vem do `starlette.testclient` e não é deste lote. |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| PyTorch | `torch-2.12.0-cp312-cp312-win_amd64.whl` (123 MB, PyPI), SHA-256 `8b958caf…afb549` conferido antes da instalação; dependências novas: sympy, networkx, mpmath, Jinja2, MarkupSafe e setuptools 81. |
| Origem | `mestrado-utfpr` sem alterações; os modelos congelados foram só lidos. |

## Reprodução da origem (separação 2, semente 42)

| Grandeza | Denso: origem | Denso: AL-IAdo | AE-LSTM: origem | AE-LSTM: AL-IAdo |
|---|---|---|---|---|
| Parâmetros | 1.088 | 1.088 | 17.216 | 17.216 |
| Melhor época / épocas | 111 / 131 | 111 / 131 | 141 / 150 | 141 / 150 |
| Perda de validação | 0,2557632625 | 0,2557632625 | 0,6537104845 | 0,6537104845 |
| Limiar p99 (posição 208/210) | 3,461894989 | 3,461894989 | 17,381608963 | 17,381608963 |
| Maior diferença nos pesos | — | **0** | — | **0** |

O histórico de perdas é idêntico em todas as épocas. Os valores e o hash dos pesos da
origem estão em `tests/data/gpvs_modelos_referencia.json`, e o teste com dados reais
refaz a conferência (cerca de 25 s).

## Rodada canônica

`data/resultados/gpvs-modelos-001` (fora do Git, 535 kB), configuração `09b7ed243bf2…`.
- **Divisão:** 711 janelas de treino, 191 de validação, 192 de calibração e 263 de teste.
- **Verificação do M14:** a distância entre blocos é 12 e o lag necessário é 12, então é **suficiente**.
- **Calibração:** 3,84 s de operação.
- **Tempo:** 75 s para as 5 sementes.
- **Reprodutibilidade:** uma segunda execução gerou pesos idênticos.

| Modelo | Limiar p99, semente 42 | Limiares nas 5 sementes | Melhor época | Épocas | Falso alarme esperado |
|---|---:|---|---|---|---|
| Denso | 3,702 | 3,145 – 3,793 (mediana 3,510) | 115 – 144 | 135 – 150 | 2/193 ≈ 1,04% por janela, cerca de 1.865 por hora |
| AE-LSTM | 17,382 | 17,382 – 22,677 (mediana 20,188) | 132 – 149 | 150 em todas | idem |

**Sensibilidade na semente 42 (p99):**
- Denso: 3,702, 2,021 e 1,074 para k = 5, 10 e 20;
- AE-LSTM: 17,382, 8,795 e 4,401.

**Autocorrelação dos escores de calibração, lag 1 (F0L; F0M), com n efetivo de 192:**
- Denso: de 0,18 a 0,46, n efetivo entre 95 e 111;
- AE-LSTM: de −0,04 a 0,13, n efetivo entre 161 e 179.

## Observações

- **Os escores são bem menos autocorrelacionados que as variáveis.** A estimativa feita
  na conversa (cerca de 10 observações independentes) usava a ACF das variáveis. Medida
  nos próprios escores, a calibração vale cerca de metade (Denso) a quase todas
  (AE-LSTM) as 192 janelas.
- **O limite de 150 épocas pesou em 8 dos 10 treinos:** a validação ainda melhorava nas
  últimas 20 épocas (todo o AE-LSTM e o Denso nas sementes 13, 29 e 42). A origem tinha
  o mesmo comportamento. Mudar o orçamento é escolha do pesquisador e, pelo M14, precisa
  ser feita pela validação e antes do lote 15.
- **Limiar igual do AE-LSTM (17,3816) com separação 2 e 11:** coincidência verificada.
  - O treino é o mesmo, e a melhor época (141) não mudou.
  - O maior escore da calibração antiga (19,88) era a 2ª janela do bloco de F0M, removida pela separação de 11.
  - Assim, o 2º maior de 192 é o antigo 3º maior de 210.
- **O falso alarme esperado é o de janelas isoladas.** Em campo, 1,04% por janela dá
  cerca de 1.865 alarmes por hora. A regra de alarme e as métricas físicas (falsos
  alarmes por hora, atraso em ms, faixa de incerteza) ficam para a decisão do lote 15.

## Revisão: parada pela validação (decisão de 27/09/2026)

Configuração `be9e54fa5d21…`; nova rodada canônica em `data/resultados/gpvs-modelos-002`
(104 s). A 001 continua preservada.

- **Parada:** todos os 10 treinos pararam pela validação, entre as épocas 135 e 311.
- **Mesmo resultado da exploração:** uma rodada prévia, com a mesma configuração, gerou pesos idênticos.
- **Denso:** 3 sementes não mudaram. As outras 2 melhoraram a perda de validação em 3,6% e 4,2%. Os limiares ficaram entre 3,145 e 3,793, com mediana de 3,510.
- **AE-LSTM:** a perda de validação melhorou de 0,9% a 5,2%. Os limiares ficaram **mais próximos entre as sementes**: de 19,38 a 21,78, contra 17,38 a 22,68 com o teto.
- **Semente 42:** limiar de 3,7338 no Denso (época 189) e de 19,3805 no AE-LSTM (época 210).
