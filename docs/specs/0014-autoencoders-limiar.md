# Lote 14 — autoencoders Denso e AE-LSTM e limiar p99

Segundo lote do experimento de detecção no [roteiro da v0](../roteiro-v0.md), autorizado
em 27/09/2026. Treina os dois modelos só com janelas saudáveis e fixa o limiar de cada um
na calibração. O teste saudável e os ensaios com falha **não são pontuados**: ficam
fechados até a avaliação do lote 15, com a configuração já congelada (M14).

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Separação entre blocos | **11 janelas** (distância 12), que cumpre o critério de autocorrelação do lote 13. Uma rodada com 2 janelas serve só para conferir a reprodução da origem. |
| Escore e limiar | Principal **k = 5** e **p99**, como na origem. Sensibilidade de k ∈ {5, 10, 20} com p99, fixada agora e só relatada. Percentis acima de 99 ficam fora: com cerca de 200 janelas, caem no maior valor da calibração ou perto dele. |
| Modelos e sementes | Como na origem: Denso 24-16-8-16-24 e AE-LSTM sem atenção; até 150 épocas, paciência 20, lote 32, taxa 0,001, dropout 0,2; sementes 13, 29, 42, 71 e 101, com a 42 como referência. |
| PyTorch | **2.12.0**, a versão da origem, só CPU, instalado do PyPI com o SHA-256 conferido. |

## Escopo implementado

- `aliado.science.detection.threshold`, só com numpy:
  - `calibrate_threshold`: escore de índice ceil((n − 1)·p/100) na fila crescente, recusando percentis que caiam no máximo;
  - `minimum_n_for_percentile`: n ≥ (q − 2)/(q − 1);
  - falso alarme esperado (n + 1 − posição)/(n + 1), válido para janelas permutáveis com as da calibração;
  - `effective_sample_size`: Σ n·(1 − ρ)/(1 + ρ) por bloco, aproximação AR(1) com ρ de lag 1.
- `aliado.science.detection.models`, com o extra `ml`:
  - arquiteturas, ordem de criação das camadas e sequência de sementes iguais às da origem;
  - treino com Adam e MSE, parada pela validação, restaurando a melhor época;
  - erro por variável (no AE-LSTM, só o do último passo) e escore top-k;
  - pesos salvos só com tensores e tipos simples, abertos com `weights_only=True`, sem pickle.
- `aliado.science.detection.training`:
  - `ExperimentConfig` congelada com SHA-256;
  - `train_detectors`, que recebe só os blocos de treino, validação e calibração e recusa antes de treinar uma calibração pequena demais para o percentil;
  - `export_training` numa pasta nova, com `configuracao.json`, `relatorio.json`, `relatorio.md`, `modelos/*.pt`, `historicos/*.csv`, `escores_calibracao.npz` e `normalizacao.npz`.
- O relatório traz, por modelo e semente:
  - melhor época e perda de validação;
  - limiar, posição, percentil efetivo e falso alarme esperado por janela e por hora (50 janelas por segundo);
  - limiares da sensibilidade;
  - autocorrelação dos escores de calibração e n efetivo;
  - hashes dos arquivos.
- `gpvs.PURGE = 11` passa a ser a separação canônica. `PreparedGPVS` guarda frações e separação, e o relatório as lê de lá.
- Comandos:
  - `aliado ciencia treinar-gpvs --saida <pasta nova> [--separacao N] [--sementes a,b,...]`;
  - `preparar-gpvs` ganha `--separacao`.

## Critérios de aceitação

- Com separação 2 e semente 42, os dois modelos reproduzem a origem **bit a bit**: pesos, histórico por época, melhor época, perda de validação e limiar.
- A configuração canônica gera 711/191/192/263 janelas e cumpre a verificação do M14.
- Nenhuma janela de teste ou de ensaio com falha é pontuada.
- Os testes cobrem:
  - top-k, o erro no último passo e a contagem de parâmetros;
  - determinismo, a restauração da melhor época e a paciência;
  - carregamento sem pickle;
  - a configuração e seu hash;
  - a vedação do teste, a exportação e o comando;
  - a reprodução com os dados reais, pulada se `data/gpvs/` ou o torch faltarem.
- A suíte completa e o Ruff passam.

## Revisão de 27/09/2026: parada pela validação

Na preparação do lote 15, o pesquisador decidiu que **a validação decide a parada**. O
teto de 150 épocas da origem encerrava 8 dos 10 treinos ainda melhorando.

- Paciência de 20 épocas mantida.
- Teto de 2.000 épocas, só de segurança.
- O relatório indica, por treino, se quem parou foi a validação ou o teto.
- A opção `--teto-epocas 150` reproduz a origem, e a conferência bit a bit continua com esse valor.
- A rodada canônica passa a ser `data/resultados/gpvs-modelos-002`; a 001 fica preservada.
