# Validação do lote 39 — o modelo local lê as páginas pelo texto guardado

Data: 18/10/2026. Escopo na [spec 0039](../specs/0039-local-le-texto.md); requisitos vivos em
[capacidades/provedores.md](../specs/capacidades/provedores.md) (PRV-01 e PRV-03 alterados; PRV-06, novo).

Nenhuma chamada paga e nenhum download. A medição usou o Ollama e o `aliado-local` instalados no lote 38. O Gemini foi
trocado por um falso, que só conta as chamadas. A biblioteca usada foi uma cópia, em `tmp/lote-39/medicao`. O modelo
local está ligado no `.env` do pesquisador desde antes deste lote, por decisão dele.

## Bateria

| Conferência | Resultado |
|---|---|
| `pytest`, arquivo por arquivo | 806 testes passaram nos 45 arquivos, nenhum falhou, em 239 s |
| `ruff check .` | sem apontamentos |
| `git diff --check` | sem apontamentos |
| Testes novos | `test_pdf_parts_with_their_text_go_as_text_with_the_reading_note_and_the_citation_rule` e `test_described_pages_reach_the_local_model_as_text` |
| Teste revisto | `test_the_model_gets_whole_documents_with_one_mark_per_page`: a parte em PDF leva a chave `text`, com o texto das 12 páginas |
| Requisitos vivos citados por testes | PRV-01 a PRV-06: todos |

## A biblioteca, antes de mudar (só leitura, 31 documentos e 2.245 páginas)

- **Texto por página:** mediana de 1.831 letras, média de 2.116 e 90% abaixo de 3.733.
- **Descrições:** 1.276 páginas descritas, com mediana de 1.132 letras.
- **Documentos inteiros:** 13 dos 31 caberiam em 16 mil tokens e 22 em 32 mil, contando só o texto.

## Medição: as 16 perguntas reais, sem custo

São as mesmas perguntas do lote 38 (`data/avaliacao-busca/perguntas.json`), feitas pela conversa do AL-IAdo, com o
mesmo script. A conta é pelo primeiro desfecho de cada pergunta:

| Desfecho | Lote 38 | Lote 39 |
|---|---|---|
| Respondidas pelo local | 3 (P6, P7 e P8) | 6 (P5, P6, P7, P8, E3 e E7) |
| Citaram o documento esperado | 1 (P6) | 3 (P5, P6 e E7) |
| Direto ao Gemini | 8, por ter mais de 4 páginas de PDF | 7, pelo contexto: P1, P2, P3, E1, E2, E5 e E8 |
| Refeitas pelo Gemini, sem as marcas | 3 (P4, P5 e E4) | 3 (P4, E4 e E6) |
| Pedido de ajuda no meio do texto | 1 (E3) | 0 |
| Sem resposta | 1 (E7, Ollama fechado) | 0 |
| Chamadas ao Gemini | 13 | 12 |
| Tempo médio por pergunta | 105 s | 130 s |

### O que mudou

- **O limite das 4 páginas sumiu.** Na E6, as páginas inteiras foram ao local, com 11,4 mil tokens reais. No lote 38,
  ela ia direto ao Gemini.
- **A regra de citação resolveu a P5,** que no lote 38 foi refeita pelo Gemini. Ainda falharam três:
  - a P4 escreveu o identificador entre crases (`K42a22a79e0224720`), e não entre colchetes;
  - a E4 e a E6 citaram o documento pelo nome.
- **A E7 citou o documento esperado.** No lote 38, ficou sem resposta.
- **A E3 saiu sem o "[ESCALAR]".** O local disse que o material enviado não fala da tese da UFSC. O roteador não
  mandou essa pergunta à biblioteca, e isso segue como ponto aberto.

### O que agora segura as perguntas: o contexto

| Pedido | Tokens reais que o Ollama contou |
|---|---|
| Sem biblioteca (P7, E3), só a base de regras e skill | 6.647 a 6.929 |
| Trechos (P4, P5, P6, P8, E4, E7) | 6.914 a 9.713 |
| Páginas inteiras que couberam (E6) | 11.392 |

- **As 7 que foram ao Gemini:** estimavam de 19.068 a 56.616 tokens (a conta do AL-IAdo é de 3 letras por token). Pela
  conta medida no lote 38, de 3,8 letras por token, são cerca de 15 a 45 mil reais.
- **Com 32 mil tokens,** 6 das 7 caberiam. Só a E1 ficaria de fora, com cerca de 45 mil.

### Tempo

- **Respostas do local:** de 95 a 275 s, com raciocínio, e de 6,6 a 11,4 mil tokens de entrada.
- **As que foram direto ao Gemini sem reescrita da busca:** de 0,3 a 7 s (P1, P2, P3 e E8).
- **A E1, a E2 e a E5:** de 130 a 140 s. A busca delas foi reescrita (rota "simples"), e a reescrita, feita pelo
  local com raciocínio, levou cerca de 2 minutos antes de a pergunta seguir ao Gemini. Desligar o raciocínio nessa
  etapa é outra alavanca de tempo.

## O que não foi conferido

- **O contexto de 32 mil tokens:** a placa e a RAM com ele, e as perguntas que ele traria ao local. É a próxima decisão.
- **A qualidade das respostas em si:** foi conferida só a citação do documento esperado.
- **A tela:** não muda neste lote; o que muda é o que vai ao modelo local.
