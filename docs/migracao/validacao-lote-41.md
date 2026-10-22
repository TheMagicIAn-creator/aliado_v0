# Validação do lote 41 — o local mais rápido; OCR por página conferido

Data: 18/10/2026. Escopo na [spec 0041](../specs/0041-local-mais-rapido.md); requisitos vivos PRV-07 em
[capacidades/provedores.md](../specs/capacidades/provedores.md) e BIB-04 em
[capacidades/biblioteca.md](../specs/capacidades/biblioteca.md). Nenhuma chamada paga e nenhum download.

## Bateria

| Conferência | Resultado |
|---|---|
| `pytest`, arquivo por arquivo | 808 testes passaram nos 45 arquivos, nenhum falhou, em 270 s (os 806 do lote 39 e 2 novos) |
| `ruff check .` e `git diff --check` | sem apontamentos |
| Testes novos ou revistos | `test_only_the_light_route_goes_without_reasoning`, a reescrita com raciocínio baixo em `test_query_rewrite.py` e `test_ocr_runs_only_on_pages_without_a_text_layer` (PDF todo digital e todo escaneado) |
| Requisitos vivos citados por testes | todos, incluindo PRV-07 e BIB-04 |

## OCR por página: calibração na biblioteca real (só leitura, 99 s)

| Caracteres úteis na camada de texto | Origem gravada |
|---|---|
| 0 | 368 por OCR e 2 páginas em branco |
| 1 a 49 | nenhuma página |
| 50 a 99 | 2 nativas (páginas de abertura de livro e de trabalho, com 61 e 74 caracteres) |
| 100 a 199 | 58 nativas |
| 200 ou mais | 1.814 nativas e 1 por OCR, por caracteres corrompidos |

O limite de 20 fica: qualquer valor entre 1 e 50 decidiria igual. A regra existe desde a 0.1.0 (`eac1a36`) e não foi
reimplementada. Sem mudança na ingestão, não há tempo de antes e depois.

## As 16 perguntas reais, três rodadas

Todas com 32 mil de contexto, o Gemini falso e uma cópia nova da biblioteca. As três cópias são idênticas: 31
documentos, 20.191 trechos e 1.276 descrições.

| | Lote 40 | Lote 41, 1ª rodada | Lote 41, final |
|---|---|---|---|
| O que mudava | (base) | reescrita e trechos sem raciocínio | só a reescrita sem raciocínio |
| Reescritas registradas | 0 de 7 | 7 de 7 | 7 de 7 |
| Respondidas pelo local, no fim | 14 | 9 | 9 |
| Citaram o documento esperado | 10 | 5 | 7 |
| Refeitas pelo Gemini | 0 | 6 | 5 |
| Chamadas ao Gemini | 2 | 8 | 7 |
| Tempo médio por pergunta | 265 s | 236 s | 158 s |

- **A reescrita falhava em silêncio.** Nos lotes 39 e 40, com raciocínio, o local gastava os 2.048 tokens de saída
  pensando, cerca de 2 minutos a 15 tokens/s. A reescrita não se completava, e a busca seguia com a pergunta original:
  o registro de uso do lote 40 não tem nenhuma chamada de reescrita.
  - Agora, as 7 reescritas saem em segundos, com consultas como "Colli FMEA Brookhaven photovoltaic array ranking
    scales".
  - A E1 caiu de 145 para 12 s; a E6, de 730 para 200 s; a E7, de 301 para 131 s.
- **Os trechos sem raciocínio:** na 1ª rodada, a P5 e a P6 deixaram de citar, e a trava combinada desfez essa parte.
  Na rodada final, já com raciocínio, a P5 falhou de novo. A prova contra é fraca, e manter o raciocínio é a escolha
  conservadora.
- **O sorteio:** das 9 perguntas cujo caminho o lote não muda, 4 trocaram de desfecho entre as rodadas (P2, P5, P7
  e P8). O modelo usa temperatura 1. Com uma rodada por configuração, a queda de 14 para 9 não pode ser atribuída ao
  lote.
- **A conferência funcionou:** as 5 refeitas da rodada final foram pegas por ela. Quatro não citavam os trechos
  enviados, e uma (a P7) trazia números que não conferiam com os resultados. Ela pega citação ausente ou inventada e
  número que não confere; um texto errado que cite certo passaria.

## O que não foi conferido

- **Mais de uma rodada por configuração,** para separar o efeito do sorteio.
- **A qualidade das consultas reescritas em si:** foi conferido só que elas saem e servem à busca.
