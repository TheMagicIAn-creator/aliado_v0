# Validação do lote 58 — o cache q4_0 medido no modelo local

Data: 22/10/2026. Escopo na [spec 0058](../specs/0058-cache-q4-medido.md). Sem commit: o commit fica com o
pesquisador. O produto não muda.

## As duas medições

As duas rodadas foram autorizadas pelo pesquisador, em 22/10/2026, com o mesmo método:
- **As perguntas:** as 16 aprovadas, cada uma num servidor HTTP real do aplicativo, com memória nova.
- **O modelo local:** o real (`aliado-local`, com 32 mil tokens de contexto e 32 camadas na placa), no Ollama 0.40.8.
- **O Gemini:** simulado, sem rede e sem chave.
- **A biblioteca e os resultados:** as cópias do lote 46, com o catálogo conferido pelo hash.
- **O `.env`:** não foi lido.

| | q8_0, depois do lote 57 | q4_0, lote 58 |
|---|---|---|
| Início | 22/10, 20:38 | 22/10, 21:38 |
| Chamadas locais (teto de 30) | 24 | 24 |
| Chamadas ao Gemini simulado | 7 | 5 |
| Chamadas pagas | 0 | 0 |
| Processos | um só; ficou sem memória na E8, repetida sozinha | um por pergunta |
| Placa antes de carregar | 6.002 MiB livres | 6.002 MiB livres |
| Firefox e VS Code | fechados | fechados (conferido pelo script) |

## Pergunta por pergunta

O tempo vai do envio da pergunta ao fim da resposta. "Gemini simulado" respondeu na hora, sem citar. "Na 2ª
tentativa" quer dizer que a primeira resposta do local veio sem citar e que, depois do Gemini simulado, a leitura subiu
um degrau e o local respondeu de novo.

| Pergunta | q8_0 (22/10) | q4_0 |
|---|---|---|
| P1 | Gemini simulado, 12 s, fora do alcance do local | Gemini simulado, 9 s, fora do alcance do local |
| P2 | Gemini simulado, 58 s, marca `Kf74ae8ecp1–8` | local (esperado citado), 88 s |
| P3 | local (esperado citado), 84 s | local (esperado citado), 84 s |
| P4 | local (esperado citado), 23 s | local (esperado citado), 72 s, na 2ª tentativa |
| P5 | Gemini simulado, 149 s, o local não citou | local (esperado citado), 61 s |
| P6 | local (esperado citado), 77 s | local (esperado citado), 173 s, na 2ª tentativa |
| P7 | local (esperado citado), 187 s | local (esperado citado), 75 s |
| P8 | local, 64 s | Gemini simulado, 81 s, o local não citou |
| E1 | Gemini simulado, 5 s, fora do alcance do local | Gemini simulado, 10 s, fora do alcance do local |
| E2 | local (esperado citado), 70 s | local (esperado citado), 81 s |
| E3 | local (esperado citado), 102 s | local (esperado citado), 47 s |
| E4 | local, 74 s, na 2ª tentativa | local (esperado citado), 44 s |
| E5 | local (esperado citado), 77 s | local (esperado citado), 73 s |
| E6 | local (esperado citado), 55 s | local (esperado citado), 73 s |
| E7 | local (esperado citado), 130 s, na 2ª tentativa | local (esperado citado), 161 s |
| E8 | Gemini simulado, 31 s, o local pediu ajuda | local, 81 s |

**Nas duas rodadas:**
- **Cópias de identificador de exemplo:** nenhuma, nem com o q8_0 nem com o q4_0. É a conferência posterior do
  lote 57.
- **A marca `Kf74ae8ecp1–8`, da P2 com o q8_0:** é um intervalo de páginas abreviado. Ela aponta sem dúvida as
  páginas 1 a 8 de um documento, mas a conferência só aceita o intervalo com o identificador inteiro dos dois lados
  (BIB-05). Não apareceu de novo com o q4_0.

## O critério

| Medida | q8_0 | O q4_0 precisava de | q4_0 | Passou |
|---|---|---|---|---|
| Memória da placa com o modelo carregado | 5.625 MiB | até 5.425 MiB | 5.377 MiB | sim |
| Respostas finais do local | 11 | ao menos 9 | 13 | sim |
| Documento esperado citado pelo local | 9 | ao menos 7 | 12 | sim |
| Chamada mediana do local nas leituras de páginas e do documento | 62,5 s | até 75 s | 68,4 s | sim |
| Erros do Ollama | 0 | 0 | 0 | sim |

**A memória, em detalhe:**
- **O modelo no Ollama:** com o q8_0, eram 6,38 GiB no total e 5,40 GiB na placa (84,7%). Com o q4_0, foram 6,13 GiB
  no total e 5,15 GiB na placa (84,1%).
- **O pico:** com o q4_0, foi de 5.385 MiB nas 2.451 amostras da placa, de meio em meio segundo. São só 8 MiB acima
  do valor com o modelo carregado.
- **A folga:** no pico, sobram 618 MiB livres; com o q8_0 carregado, sobravam 378.

Notas:
- **A margem de 2 nas medidas de qualidade:** é a variação já vista entre duas rodadas iguais. Por isso, as 2
  respostas e as 3 citações a mais do q4_0 não provam ganho; mostram só que a qualidade não piorou.
- **A mediana:** é o valor do meio da lista ordenada. Aqui, o tempo de uma resposta completa do local nas 6 perguntas
  que leem páginas ou um documento inteiro.

## A troca da variável e o log do Ollama

- **A primeira conferência (21:23):** recusou a medição, sem gastar nenhuma chamada.
  - A variável do usuário ainda estava em q8_0, com a última mudança em 18/10.
  - O Ollama em execução era o das 07:53, aberto pela atualização automática.
- **Uma falha da conferência:** ela olhava só o log mais recente, e o servidor das 07:53 não gravou log. Ela passou a
  conferir também:
  - a variável no registro do Windows, com a hora da última troca;
  - se o log é do servidor em execução;
  - depois de carregar, se o modelo encolheu ao menos 0,2 GiB em relação aos 6,38 GiB do q8_0.
- **A troca:** feita com a autorização do pesquisador.
  - A variável já estava em q4_0 às 21:36: ele a tinha trocado, mas o Ollama não tinha sido reiniciado.
  - O Ollama foi reiniciado às 21:37, com as variáveis do usuário.
  - O log do servidor novo trouxe `OLLAMA_KV_CACHE_TYPE:q4_0`, e o modelo carregou com 6,13 GiB.
- **A volta:** a variável foi para q8_0, e o Ollama reiniciou às 21:59. O log do servidor novo trouxe
  `OLLAMA_KV_CACHE_TYPE:q8_0`.

**O que o log guarda:** ver a [spec 0058](../specs/0058-cache-q4-medido.md). Ele tem a configuração de cada início,
mas não o carregamento do modelo nem os erros 500.

## Registros

Ficam fora do Git:
- **Lote 57, com o q8_0:**
  - `tmp/lote-57/medicao/` e `tmp/lote-57/medicao-e8/`;
  - a comparação, em `tmp/lote-57/comparacao.json`;
  - o modelo carregado, em `tmp/lote-57/ollama-ps-q8.txt`.
- **Lote 58, com o q4_0:** `tmp/lote-58/medicao/`, com:
  - `resultado.json`, `metadata.json` e as 16 perguntas;
  - `placa.csv`, com as amostras da placa;
  - `processos.log`.
- **Os scripts:** `tmp/lote-57/medir_regras.py`, `repetir_e8.py` e `comparar.py`; `tmp/lote-58/medir_q4.py` e
  `comparar.py`.
