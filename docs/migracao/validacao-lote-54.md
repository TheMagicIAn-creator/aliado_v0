# Validação do lote 54 — a identidade e o contrato da rodada

Data: 22/10/2026. Escopo na [spec 0054](../specs/0054-identidade-e-contrato-da-rodada.md). Commit local autorizado pelo
pesquisador no plano de 21/10; o push e a tag ficam com ele.

## Bateria

| Medida | Lote 53 | Lote 54 |
|---|---|---|
| Testes | 838 passando | 849 passando (4 da identidade e 7 da matriz de erros), nenhum ignorado |
| Treinos de rede por bateria | 18 | 18 |
| Tempo da bateria inteira | 196,0 s | 212,5 s |
| Pico de memória | 559 MiB, na busca (medido no lote 49) | 559,6 MiB, na busca; a ciência e o mestrado no máximo 495 MiB |

**Os 16 s a mais:** a avaliação passa a recalcular a matriz de erros à parte para conferir os escores, e os testes novos
preparam dados e conferem matrizes. Nenhum treino a mais.

## Conferências

| Conferência | Resultado |
|---|---|
| Equivalência contra a referência do lote 49 | 28 de 28 arquivos iguais; nenhuma diferença, nenhum faltando |
| Arquivos e chaves novos, listados à parte | `avaliacao/erros.npz`; em `resultado.json`, a chave `identidade` e as 17 de dentro dela |
| Autoteste da equivalência (duas rodadas novas) | 29 de 29 arquivos iguais, `erros.npz` e a identidade inclusive; a rodada alterada mostrou a diferença |
| Os três hashes de configuração depois da troca pela função única | os mesmos de antes: be9e54fa…, ce8b06e4… e 1510880c… |
| A matriz reproduz os escores (GPVS sintético) | bit a bit, em todo modelo, repetição e k, na calibração, no teste saudável e nos 14 ensaios |
| A avaliação de 27/09 e a rodada-002 (dados reais) | "anteriores ao contrato"; comparadas, todos os indicadores iguais; viram PDF |
| A rodada real de ponta a ponta (5 épocas) | grava a identidade, com a versão do programa no estado "registrado" |
| Toda importação de `aliado…` resolve | sim |
| Pastas vazias ou só com `__pycache__` | nenhuma |
| As cópias antigas dos hashes fora dos registros | nenhuma |
| Os comandos e o PDF do experimento, numa cópia dos resultados | saída 0; o PDF da rodada atual com 238.737 bytes (era 235.111), pelas três linhas e notas novas |
| O wheel de uma cópia limpa | 148 arquivos `.py` presentes (4 novos); 146 módulos importados do próprio wheel, sem erro |
| NUC-01, NUC-02, NUC-04 e Ruff | passando |

## O que a conferência pegou no caminho

- **O código da matriz:** o hash do arquivo `erros.npz` mudaria a cada gravação, porque o arquivo compactado guarda a
  hora. A identidade grava o código do conteúdo, e o autoteste mostra que duas rodadas iguais dão o mesmo.
- **Os testes do cache do explorador:** o laço dos erros saiu do explorador para `avaliacao/pontuacao.errors_all`.
  Os quatro monkeypatches do teste do cache passaram a apontar para o módulo de onde a função os lê.
- **Fim de linha:** quatro arquivos reescritos por script tinham ficado com CRLF na cópia de trabalho. Voltaram ao LF
  antes do commit; o Git guarda LF de qualquer jeito.
- **A busca pelas cópias antigas** achou só o nome de um teste novo terminado em `_sha256(`, que foi renomeado.

## Os cinco pontos que tratam `ValueError` de forma ampla

O erro de contrato é um `ValueError`. Os cinco pontos foram conferidos:
- **O "Preparar" do explorador:** é o único que pode recebê-lo, e já mostra a mensagem.
- **O PDF, na interface e no terminal:** também mostra a mensagem.
- **A rodada oficial, os painéis, o resumo do chat e a comparação de parâmetros:** não leem nenhum arquivo do
  contrato. Nada foi acrescentado neles.
