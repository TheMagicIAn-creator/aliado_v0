# Validação do lote 55 — a evidência espectral descritiva

Data: 22/10/2026. Escopo na [spec 0055](../specs/0055-evidencia-espectral.md). Commit local autorizado pelo pesquisador
no plano de 21/10; o push e a tag ficam com ele.

## Bateria

| Medida | Lote 54 | Lote 55 |
|---|---|---|
| Testes | 849 passando | 860 passando (5 do espectro, 4 da evidência, 1 do filtro no núcleo e 1 do roteador), nenhum ignorado |
| Treinos de rede por bateria | 18 | 18 |
| Tempo da bateria inteira | 212,5 s | 252,0 s |
| Pico de memória | 559,6 MiB, na busca | 559,6 MiB, na busca; a ciência e o mestrado no máximo 502 MiB |

**O tempo a mais vem da base real:** os espectros dos 14 ensaios com falha são montados uma vez por bateria, a partir
dos CSVs, numa pasta temporária. Nenhum treino a mais.

**A primeira bateria teve uma falha, de um teste do lote 54.** Ele exigia que a pasta do explorador nem existisse,
para provar que o cache dos erros não foi gravado. O 4º passo do "Preparar" passou a gravar ali a evidência, então o
teste agora confere só que não há cache de erros nela. A bateria final já roda com essa correção.

## Conferências

| Conferência | Resultado |
|---|---|
| Equivalência contra a referência do lote 49 | 28 de 28 arquivos iguais; nenhuma diferença, nenhum faltando |
| Arquivos e chaves novos, listados à parte | `avaliacao/erros.npz` e `evidencia_espectral/evidencia.json`; em `resultado.json`, 18 chaves da identidade e 767 do resumo da evidência |
| Autoteste da equivalência (duas rodadas novas) | 30 de 30 arquivos iguais, a evidência inclusive; a rodada alterada mostrou a diferença |
| A THD dos espectros e a das 24 variáveis | iguais em float32 em toda janela dos 14 ensaios, na base sintética e na real (conferido ao montar o cache) |
| A janela do alarme da evidência e a da aba (`alarme_deteccao`) | iguais nos 28 pares de modelo e ensaio, na base real |
| Os ensaios sem alarme, na avaliação de 27/09 | Denso: F4L, F4M, F6M e F7L. AE-LSTM: F4L, F4M, F6L, F6M, F7L e F7M |
| As janelas antes da mudança observada | F3L 188 e F3M 163; nos outros ensaios de mudança clara, de 0 a 111 |
| Janelas com passo de tempo irregular, por ensaio | de 3 a 9 nos 14 ensaios |
| Tamanho do texto dos resultados, na base real | 15.347 caracteres sem R9 e R10, abaixo de 16 mil; 24.158 com eles; R9 3.897 e R10 2.442 |
| A pergunta "o que os harmônicos mostram no primeiro alarme da falha de IGBT?" | vai aos resultados, com R9 e R10; a pergunta sobre a sensibilidade vai sem eles |
| O roteador com o modelo local de busca real, sem rede | a pergunta dos harmônicos e "Qual a THD no alarme do Denso em F1L?" vão aos resultados; "O que a literatura diz sobre harmônicos em inversores?" vai à biblioteca |
| Uma resposta que copia uma linha do R9, com a marca | números conferidos |
| O PDF de uma rodada nova | ganha a seção da evidência; o da rodada atual (anterior a ela) continua igual, com 238.737 bytes |
| Toda importação de `aliado…` resolve | sim |
| Pastas vazias ou só com `__pycache__` | nenhuma |
| A THD antiga (`_thd`) fora dos registros | nenhuma |
| Os comandos e o PDF do experimento, numa cópia dos resultados | saída 0 |
| O wheel de uma cópia limpa | 156 arquivos `.py` presentes (8 novos); 154 módulos importados do próprio wheel, sem erro |
| NUC-01, NUC-02, NUC-04 e Ruff | passando |

Todas as conferências com a base real usaram cópias temporárias. Os caches reais (`data/gpvs/processado/espectro.npz`
e a evidência da avaliação oficial na pasta dos exploradores) só serão criados quando o pesquisador usar o "Preparar"
da aba Ciência.

## O que a evidência mostra na avaliação de 27/09

O conteúdo de R9 e R10, numa cópia, está em `tmp/lote-55/r9-r10-real.md`. Ele não entra no Git.
- **F1L, falha em IGBT com a potência limitada:** a fase do maior erro (ib) tem, no alarme, nível DC de 92 a 95% da
  fundamental e 2ª harmônica de 46 a 51%, contra 7,8% e 8,8% no comissionamento. Em F1M, as fases de maior erro mudam
  pouco no alarme, e o maior erro geral é a mediana de Vpv.
- **F2 e F3:** a fundamental da fase cai a menos de 1% da do comissionamento na janela do alarme (em F5, a 2 a 4%), e
  as porcentagens sobre ela explodem. A nota da fundamental explica isso em palavras.
- **F4, sombreamento:** sem alarme, e os indicadores quase não mudam (menos de 0,5 IQR).

## O que a conferência pegou no caminho

- **O tamanho do R9 e do R10:** a primeira versão, em notação científica, somava 8.105 caracteres no GPVS sintético.
  Com as porcentagens e a fonte mais curta, a base real fica em 6.339.
- **A marca do passo irregular:** o plano falava de F5M e F7M, mas a leitura dos CSVs mostrou passos fora de 1% em
  todos os ensaios, isolados. A marca ficou por janela, e o texto avisa quando a janela do alarme tem um.
- **O 4º passo do explorador:** uma falha nele não pode travar o "Preparar". Qualquer erro fica no estado, com a
  mensagem, e um teste confere que os exploradores seguem funcionando.
