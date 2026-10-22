# AL-IAdo — relatório em LaTeX de 21/10/2026, conferido

Data: 21/10/2026. Confere a versão em LaTeX do "Relatório de Melhoria e Eficiência do Modelo Local", que acrescenta
ao PDF de 20/10 a série de Fourier e uma especificação de lotes (46 a 50) para o Claude Code.
- **O que se repete do PDF de 20/10:** já foi conferido em
  [relatório de eficiência, conferido](2026-10-20-relatorio-eficiencia-conferido.md).
- **Aqui:** só o que é novo e o que o pesquisador decidiu em 21/10.

Não foi lido o `.env`. Nenhum modelo foi chamado para esta conferência.

## 1. Conclusão

| Seção do relatório | Confere? | Decisão de 21/10 |
|---|---|---|
| 1 a 4: memória, latência e as 5 propostas | Não. As contas de memória são as mesmas do PDF de 20/10 | Vale a decisão de 20/10: o Ollama fica como está |
| 5.1: formalização do método | Sim, com uma correção (seção 3) | Entra no mapa das pastas, com uma equação por etapa |
| 5.2: contrato da matriz de erros | O pedido vale | Entra no lote 54, em NPZ |
| 5.2: `torch.compile` | Não se aplica | Não entra |
| 6: série de Fourier | As fórmulas conferem; 4 pontos não (seção 4) | Entra no lote 55, como evidência descritiva |
| 7: regras e lotes | As regras valem, e a 4 foi adotada | Ver a seção 5 |
| 8: projeções | Não se sustentam | — |

## 2. Memória e latência (seções 1 a 4)

As contas são as do PDF de 20/10. A tabela resume a conferência daquele dia.

| Item | O relatório | O que vale |
|---|---|---|
| Camadas e cabeças K/V | 36 camadas × 8 cabeças × 128 | 32 blocos, só 8 com atenção completa, 4 cabeças × 256 |
| Cache K/V a 32.768 tokens | 2,25 a 4,5 GiB em FP16 | 544 MiB em q8_0, com flash attention |
| Total | 7,515 GiB, acima da placa | Pico medido de 5.641 de 6.143 MiB, com as 32 camadas na placa |
| Falhas da P2 (lote 45) | Estouro inevitável da placa | Aconteceram com o Firefox e o VS Code abertos e sumiram depois de fechá-los |
| Primeiro texto em 83,7 s | Prefill | Leitura do pedido (14%) e raciocínio oculto (54%), que vem antes do texto |
| Propostas 1 a 5 | 8 mil de contexto, 3 mil de orçamento, PLD, gramática, modelo de 3B | Não se aplicam; os motivos estão na seção 5 da conferência de 20/10 |

A parada cedo da resposta reprovada, pedida na especificação do lote 48 do relatório, já foi feita no lote 46.

## 3. O método (seção 5)

**As fórmulas conferem com o código:**
- o erro quadrático por atributo;
- o escore pela média dos 5 maiores;
- no AE-LSTM, só o último passo de cada sequência de 8 janelas;
- o limiar no percentil 99 da calibração;
- o alarme com 3 janelas seguidas acima do limiar.

**A correção:** o autoencoder denso não tem uma camada oculta só, como na equação do relatório. Ele é 24-16-8-16-24,
com ReLU, dropout antes do gargalo e antes da saída, e saída linear (`science/detection/models.py:40-51`).

**O contrato da matriz de erros:**
- **A convenção de tempo já está no código.** Cada janela é datada pela 1ª amostra (`gpvs.py:161`), e o alarme,
  pelo fim da janela que completa a confirmação (`evaluation.py:191-192`).
- **O que já existe:** o cache do explorador guarda os hashes dos pesos e a ordem das 24 variáveis desde o lote 46.
- **O lote 54 faz:**
  - a matriz passa a ser um arquivo da própria rodada, conferido contra os escores;
  - a falta de um campo dá um erro de contrato, sem valor suposto.
- **Por que NPZ e não HDF5:** o NPZ é o formato de todos os outros arquivos da ciência. O HDF5 pediria baixar uma
  biblioteca nova, sem garantia a mais: a integridade vem do hash e dos metadados.

## 4. A série de Fourier (seção 6)

**O que confere:**
- **As fórmulas** de a0, a_k, b_k e C_k e a identidade de Parseval.
- **A janela:** as 200 amostras são exatamente um ciclo de 50 Hz a 10 kHz (`gpvs.py:53-55`), então o bin k é o
  k-ésimo harmônico.
- **A fase:** a amplitude de cada harmônico não depende da fase em que a janela começa.

**O que não confere, e como o lote 55 faz:**

1. **A janela de Hann.** Ela serve quando a janela não cobre um número inteiro de ciclos. Aqui cobre, e Hann cria
   o que não existe.
   - Num seno puro x = cos θ, o sinal com Hann fica 0,5 cos θ − 0,25 − 0,25 cos 2θ.
   - Isso dá nível DC/fundamental = 0,5 e 2º harmônico/fundamental = 0,5. É a assinatura da falha de IGBT, em toda
     janela sadia.
   - O lote 55 usa a janela retangular, e um teste documenta a diferença.
2. **A THD já é atributo:** 6 dos 24 atributos (`ia_thd`…`vc_thd`) são a THD de cada fase. A conta usa a FFT da
   janela sem a média, janela retangular, e harmônicos de 2 a 40 sobre a fundamental (`gpvs.py:129-133`).
   - A evidência nova usa a mesma conta, e um teste exige o mesmo valor.
   - O que é novo:
     - o nível DC sobre a fundamental;
     - a fundamental sobre a referência sadia;
     - o 2º, o 3º e o 5º harmônicos sobre a fundamental.
3. **A tabela assinatura → modo de falha → FMECA.**
   - **Contraria as diretrizes aprovadas em 22/09:** detecção, criticidade da FMECA e confiabilidade são resultados
     distintos (M09), e a FMECA é independente do GPVS (M11).
   - **Contraria o NUC-01:** levaria o domínio para a ciência geral.
   - **Tem modos que não estão no GPVS:** a degradação do filtro LCL não é uma das 7 falhas. A falha 2 é um erro de
     20% no sensor ou na realimentação, não uma deriva aditiva.
   - **No lugar dela:** uma tabela descritiva, por ensaio e por fase, que mostra quais indicadores mudam de fato
     entre o comissionamento e o trecho depois da falha.
4. **O canal de maior erro.**
   - Os canais de corrente contínua (Ipv, Vpv e Vdc) não têm fundamental de 50 Hz, e as razões sobre C1 não fazem
     sentido neles.
   - A evidência fica nas 6 fases de corrente e tensão. Escolhe-se a fase cujos atributos próprios (RMS e THD) têm o
     maior erro, e o texto diz também qual atributo teve o maior erro geral.

**O vazamento espectral:**
- **Por que existe:** a amostragem real é de 10.000,3 Hz, e a rede pode se afastar um pouco de 50 Hz.
- **Quanto pesa:** um desvio de 0,2% na frequência põe cerca de 0,1% a 0,2% da fundamental no nível DC e no 2º
  harmônico, muito abaixo da assinatura de uma chave aberta.
- **Passos irregulares:** as janelas com passo de tempo irregular (F5M e F7M) ficam marcadas.

**O custo no chat:** o relatório estima menos de 45 tokens por evento, mas são 28 eventos (14 ensaios × 2 modelos).
Por isso, os blocos novos só vão quando a pergunta fala do assunto.

## 5. As regras e os lotes (seção 7)

| O relatório | O que vale |
|---|---|
| Regra 1, protocolo fixo | Vira o requisito EXP-12, com teste (lote 49) |
| Regra 2, sem valor padrão silencioso | Vira o requisito EXP-13, com `ContractViolationError` (lote 54) |
| Regra 3, segredos e memórias | Já vale (AGENTS.md) |
| Regra 4, manter `science/` e `specializations/mestrado/` | Adotada em 21/10: as pastas técnicas de dentro ficam em português (lotes 50 a 53) |
| Lotes 46 a 48 (Ollama) | Não entram (seção 2); a parada cedo já existe desde o lote 46 |
| Lote 49 (matriz de erros e manifesto) | Lote 54 |
| Lote 50 (Fourier) | Lote 55 |
| Suíte rápida | `ferramentas/bateria.py --rapida`, que deixa de fora os testes que treinam ou leem os dados reais |
| `test_error_artifact.py` e `test_fourier_digest.py` | `tests/mestrado/test_artefato_de_erros.py`, `tests/science/test_espectro.py` e `tests/mestrado/test_evidencia_espectral.py` |

Os números dos lotes do relatório colidem com os lotes 46 a 48 já feitos. Por isso, o plano de 21/10 os renumerou.

## 6. Projeções (seção 8)

As projeções partem do diagnóstico de memória e de prefill, que não confere:
- 18 a 24 s por resposta;
- o primeiro texto abaixo de 6 s;
- nenhuma falha de memória;
- autonomia total.

Elas não se sustentam com as medições dos lotes 42 a 48. A projeção física da seção 8 (diagnóstico com invariantes
harmônicos) vale como descrição; o lote 55 não a usa para classificar falhas.
