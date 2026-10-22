# Spec 0055 — a evidência espectral descritiva

Estado: feito em 22/10/2026, com commit local autorizado pelo pesquisador no plano de 21/10; push e tag ficam com ele.

## Propósito e decisões

É o lote 50 do relatório em LaTeX de 21/10 (Fourier), com as três correções da
[conferência](../revisao/2026-10-21-relatorio-latex-conferido.md). Na janela em que cada modelo confirmou o primeiro
alarme, o AL-IAdo mostra como estão as harmônicas da fase com o maior erro e o que mais muda em cada ensaio. A evidência
descreve o sinal. Ela não classifica a falha, e a FMECA não entra.

**Decisões do plano de 21/10:**
- **A janela é retangular, de um ciclo.** As 200 amostras são exatamente um ciclo de 50 Hz a 10 kHz, e cada bin da
  FFT é uma harmônica. Com Hann, um seno puro mostraria nível DC e 2ª harmônica de metade da fundamental, a assinatura
  de uma falha, em toda janela sadia. Um teste documenta isso.
- **A THD é a mesma das variáveis dos modelos.** `science/espectro/decomposicao.thd` é a conta de antes, e os atributos
  passaram a chamá-la. Os espectros são conferidos contra as 24 variáveis: a THD em float32 é igual em toda janela.
- **Só as 6 fases de corrente e tensão.** Os canais de corrente contínua não têm fundamental de 50 Hz.
- **Sem FMECA.** Detecção e FMECA ficam independentes.
- **Uma tabela descritiva por ensaio**, com os rótulos da avaliação (o início nominal), para não haver raciocínio
  circular.
- **No chat, sob pedido.** R9 e R10 só vão ao modelo quando a pergunta fala de Fourier, harmônicos, nível DC ou THD. O
  limite de 16 mil caracteres dos blocos de sempre fica.

**Decisões tomadas na implementação:**
- **O passo de tempo irregular é marcado por janela.** O plano falava de F5M e F7M, mas na base real todos os 14
  ensaios têm de 3 a 9 janelas com um passo mais de 1% diferente da mediana, cada passo isolado. Quando a janela do
  alarme tem um, o texto avisa.
- **A janela do alarme vem de `paineis.score_panels`.** É a mesma conta da aba Ciência (`alarme_deteccao`), sem cópia
  da regra. A matriz de erros precisa dar, bit a bit, os escores salvos do treino de referência.
- **A medida do que mais muda:** a diferença entre a mediana depois do início nominal e a do comissionamento, em
  amplitudes interquartis do comissionamento. É uma escala robusta, que compara indicadores de grandezas diferentes.
- **A nota das F3 vale para todos.** Cada ensaio com mudança clara diz quantas janelas depois do início nominal vêm
  antes da mudança observada. Nas F3 são 188 e 163 janelas, e a nota explica que a mediana mistura janelas ainda sem
  mudança.
- **O formato:** o nível DC, a THD e as harmônicas aparecem em porcentagem da fundamental, com 2 algarismos.
  - Na base real, o R9 e o R10 somam 6.339 caracteres. No GPVS sintético, a primeira versão, em notação científica,
    somava 8.105.
  - Com eles, o texto dos resultados vai de 15.347 a 24.158 caracteres, só nas perguntas sobre o assunto.
- **A fundamental quase nula:** em F2 e F3, a fundamental da fase cai a menos de 1% do comissionamento na janela do
  alarme. As porcentagens sobre ela explodem (até −68.000%). Nenhum número muda: a nota da fundamental passou a dizer,
  em palavras, que essas porcentagens perdem o sentido físico.
- **O filtro do núcleo é genérico.** `agent.requested_results` lê o campo `sob_pedido` de cada bloco, sem domínio. A
  conferência das marcas usa os mesmos blocos: um R9 citado sem ter ido reprova a resposta, como uma marca inventada.
- **A pasta dos exploradores chega ao resumo pela interface.** `results_digest` recebe `data_dir`. O terminal não o
  passa, então lá só aparece a evidência das rodadas novas.
- **Os alarmes do AE-LSTM:** o plano citava "sem alarme" só em F6L e F7M. Na base real são 6 ensaios (F4L, F4M, F6L,
  F6M, F7L e F7M), coerente com os 8 de 14 que ele detecta na avaliação de 27/09.

## Requisitos vivos

- **EXP-14 (novo), em `experimentos.md`:** a evidência espectral descritiva.
- **EXP-08 e EXP-09 (conferidos de novo):** o resultado de uma rodada nova traz o resumo da evidência, e o PDF dela
  ganha a seção. O PDF de uma rodada anterior não muda.

## Implementação

**Ciência geral, `science/espectro/decomposicao.py`** (numpy, sem domínio):
- `thd`: a conta das variáveis de THD;
- `harmonics`: o nível médio e C_k = 2|X_k|/W, com o bin de Nyquist sem dobrar e a igualdade de Parseval.

**Mestrado, `evidencia_espectral/`:**

| Arquivo | O que tem |
|---|---|
| `espectros.py` | o cache `processado/espectro.npz` ao lado dos CSVs: por ensaio com falha e fase, o nível médio, C1–C5 e a THD de cada janela, o início das janelas e a marca do passo irregular; conferido contra as variáveis e gravado de uma vez |
| `tabela.py` | os 6 indicadores por janela, a tabela comissionamento × depois do início nominal, com a mudança em IQR, e os dois que mais mudam em cada ensaio |
| `evidencia.py` | a evidência: a janela do alarme, a fase do maior dos 12 erros próprios das fases, a posição dela, o maior erro geral, os indicadores e o comissionamento; a conferência dos escores |
| `artefatos.py` | onde fica (a pasta da rodada ou a dos exploradores, nunca `data/resultados` para a avaliação oficial), gravar e ler, só com a biblioteca padrão |
| `relatorio.py` | as linhas das duas tabelas para o chat e o PDF, com os nomes das variáveis em palavras |

**Onde roda:**
- **Rodada nova:** em `run`, depois do início das falhas e dentro da consulta registrada. Grava em
  `<rodada>/evidencia_espectral/evidencia.json`, e `resultado.json` leva o resumo (sem a tabela completa).
- **Rodada anterior:** o "Preparar" do explorador ganhou o 4º passo. Ele grava em
  `data/ciencia/evidencia-espectral-<rodada>-<avaliação>.json`, como exploração pós-teste, e o estado fica em
  `status()["evidencia_espectral"]`. Uma falha fica no estado, com o motivo, e os exploradores seguem.

**No chat:**
- R9 (os harmônicos na janela do primeiro alarme) e R10 (os dois indicadores que mais mudam em cada ensaio) vêm depois
  de R8, na seção Explorar, sempre com o estatuto de exploração.
- A assinatura do resumo inclui os arquivos da evidência.
- O glossário ganhou uma nota para cada indicador novo, e o roteador, uma frase de exemplo.

**Testes:**
- `tests/science/test_espectro.py`: amplitudes exatas, Nyquist, W ímpar, Parseval em 1e-12, a THD e a janela de Hann.
- `tests/mestrado/test_evidencia_espectral.py`:
  - a THD das variáveis igual à dos espectros;
  - o cache;
  - a evidência conferida contra a aba e contra uma janela recalculada do CSV;
  - a matriz alterada recusada;
  - o PDF;
  - o 4º passo do explorador, sem mudar os resultados;
  - R9 e R10 sob pedido, com os números conferidos.
- Com os dados reais, no teste do explorador:
  - a janela do alarme igual à da aba;
  - o Denso sem alarme em F4L e F4M;
  - as F3 com mais de 100 janelas antes da mudança;
  - de 1 a 20 janelas irregulares por ensaio;
  - R9 e R10 dentro de 7.500 caracteres.
- `tests/test_results_chat.py`: o filtro sob pedido, no núcleo. `tests/test_routing.py`: a pergunta sobre os
  harmônicos vai aos resultados.

## Aceitação

- A bateria completa passando, com os testes com os dados reais.
- A equivalência sem diferença nos arquivos de antes, com o arquivo da evidência e as chaves novas listados à parte.
- NUC-01, NUC-02, NUC-04 e Ruff.
- As conferências extras: importações, pastas, cópias antigas, comandos e wheel.
