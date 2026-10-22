# Spec 0041 — o local mais rápido: sem raciocínio na reescrita da busca; OCR por página conferido

Estado: implementado e medido localmente em 18/10/2026; aguarda a revisão e o commit do pesquisador. Spec de mudança:
os requisitos vivos estão em [capacidades/provedores.md](capacidades/provedores.md) (PRV-07, novo) e em
[capacidades/biblioteca.md](capacidades/biblioteca.md) (BIB-04, novo, para o que já existia).

## Propósito

No lote 40, o local passou a responder 14 das 16 perguntas reais, mas com 5 minutos de mediana por resposta. O
pesquisador pediu para desligar o raciocínio do local na reescrita da busca e nos trechos, "com a segurança de
resposta". Mandou também o documento "Por que o Aliado local está lento", com uma tarefa: o OCR decidido página por
página na ingestão. Se já existisse, era para relatar e não reimplementar.

## O que muda

- **`knowledge/rewrite.py`:** o pedido da reescrita vai com `reasoning_level="low"`. O local desliga o raciocínio, e o
  Gemini, quando é ele quem reescreve, pensa pouco: a tarefa é mecânica, com temperatura 0.
- **Os trechos sem raciocínio, no local: experimentados e desfeitos.** Na primeira rodada, a P5 e a P6 deixaram de
  citar. A trava combinada era desfazer essa parte se caíssem as respostas ou as citações certas. Os trechos seguem
  com o raciocínio que o roteador decidir. A rodada final mostrou que a P5 falha também com raciocínio, então a prova
  contra os trechos sem raciocínio é fraca. Manter o raciocínio é a escolha conservadora.
- **A segurança da resposta:** a conferência continua igual. A resposta sem citação, com números que não conferem ou
  com o pedido de ajuda é refeita pelo Gemini (PRV-02). Na rodada final, ela refez 5 respostas, uma delas (a P7)
  pelos números que não conferiam com os resultados.

## O OCR por página (o documento do pesquisador)

- **Já existe** (`knowledge/extraction.py`, desde a 0.1.0, commit `eac1a36` de 27/09/2026):
  - a camada de texto de cada página sai pelo `pypdf`;
  - só a página com menos de 20 caracteres úteis, ou com caracteres corrompidos, passa pelo Tesseract (por+eng);
  - o texto fica gravado com o número da página e a origem (`native` ou `ocr`, com a confiança).
- **Não foi reimplementado.** Ganhou o requisito vivo BIB-04 e os testes que faltavam (PDF todo digital e todo
  escaneado; o misto já tinha).
- **Calibração na biblioteca real (2.245 páginas, só leitura):**
  - 368 páginas sem nenhuma camada de texto foram por OCR, e 2 estão em branco;
  - nenhuma página tem entre 1 e 49 caracteres úteis;
  - 60 páginas têm entre 50 e 199, todas nativas; as duas mais curtas, de 61 e 74, são páginas de abertura;
  - 1.814 têm 200 ou mais e são nativas; 1 passou por OCR por ter caracteres corrompidos.
  - Qualquer limite entre 1 e 50 decidiria igual: o 20 fica. Sem mudança na ingestão, não há tempo de antes e depois.

## Testes

- **`test_local_provider.py`:** só o pedido de raciocínio baixo vai sem raciocínio; os trechos e as páginas, com ele.
- **`test_query_rewrite.py`:** a reescrita sai com raciocínio baixo.
- **`test_knowledge.py`:** o OCR no PDF todo digital (nenhuma página) e no todo escaneado (todas).

## Resultado

São as mesmas 16 perguntas, com 32 mil de contexto, o Gemini falso, sem custo e numa cópia nova da biblioteca a cada
rodada. As três cópias são idênticas.

| | Lote 40 | Lote 41, 1ª rodada (reescrita e trechos sem raciocínio) | Lote 41, final (só a reescrita) |
|---|---|---|---|
| Reescritas da busca que funcionaram | 0 de 7 | 7 de 7 | 7 de 7 |
| Respondidas pelo local, no fim | 14 | 9 | 9 |
| Citaram o documento esperado | 10 | 5 | 7 |
| Refeitas pelo Gemini | 0 | 6 | 5 |
| Chamadas ao Gemini | 2 | 8 | 7 |
| Tempo médio por pergunta | 265 s | 236 s | 158 s |
| Mediana das respostas do local | 301 s | — | 131 s |

- **O que é firme: a reescrita.** Nos lotes 39 e 40, com raciocínio, o local gastava os 2.048 tokens da reescrita
  pensando, cerca de 2 minutos, e não entregava nada. A busca seguia com a pergunta original, sem aviso. Agora as 7
  reescritas saem em segundos. O tempo médio caiu de 265 para 158 s, e a mediana do local, de 301 para 131 s.
- **O que é ruído: a queda nas respostas.** Das 9 perguntas cujo caminho este lote não muda, 4 trocaram de desfecho
  entre as rodadas: P2, P5, P7 e P8. O modelo usa temperatura 1, o padrão do `qwen3.5`, e com uma rodada só não dá
  para separar efeito de sorteio. A rodada do lote 40 (14 de 16) pode ter sido de sorte. A medida firme exige repetir
  as rodadas ou baixar a temperatura.
- **Os testes:** a bateria inteira está na [validação do lote 41](../migracao/validacao-lote-41.md).

## Fora deste lote

- **A temperatura do local:** a próxima alavanca, para a citação variar menos entre as rodadas. O `qwen3.5` vem com
  temperatura 1; um valor menor no Modelfile tende a variar menos, mas isso é a medir, com duas rodadas.
- **O raciocínio nas páginas inteiras e no documento,** que são as respostas mais longas.
- **O roteador na E3.**
