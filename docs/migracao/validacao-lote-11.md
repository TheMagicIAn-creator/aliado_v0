# Validação do lote 11

Verificação local em **26/09/2026**, Windows/Python 3.12. Nenhum commit, push ou PR;
os commits ficam para a v0 concluída.

## Resultado

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **265 testes passaram** (252 anteriores + 13 novos; os testes da interface foram ajustados ao evento de memória). |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| Sintaxe do front-end | `node --check` sem erros. |

Um defeito foi encontrado pelos próprios testes durante a implementação: a conexão
SQLite da memória fechava sem confirmar a gravação. Foi corrigido antes da validação real.

## Validação real no navegador

Servidor com dados temporários em `tmp/lote-11/`, fora do Git, usando o `gemini-3.5-flash-lite`.

1. **Conversa A:** "Prefiro respostas com no máximo duas frases. O que é MTTR?". A
   resposta veio em duas frases (474 tokens). O revisor criou a anotação *preferência ·
   sua*, válida em todas as skills, com a conversa e o trecho de origem (426 tokens).
2. **Conversa B (nova):** "O que é disponibilidade inerente?". A resposta veio em duas
   frases e mostrou "usou 1 memória", e o painel exibiu a preferência usada (645
   tokens). O revisor não duplicou a anotação (423 tokens).
3. **PDF sintético** enviado com a skill de pesquisa. Etapas: OCR, depois ficha. A
   ficha gerou o resumo e o fato "O reparo do equipamento levou duas horas" na página
   1, ambos inferidos e com a etiqueta da pesquisa (356 tokens).
4. **Aba Memória:** filtros e contagens corretos. Editar o fato criou uma versão com
   origem *sua*; a anterior ficou *superada* e aparece no histórico.

Gasto total da validação: **2.324 tokens** no Flash-Lite, em 5 chamadas (3 respostas ou
fichas e 2 revisões).

## Observações

- Sem especialização, o modelo tratou MTTR como métrica de TI ("tempo de recuperação").
  Com a skill de confiabilidade, a leitura esperada é "tempo médio de reparo".
- O navegador embutido registrou `ERR_ABORTED` nas respostas em fluxo, com status 200.
  Um teste com Uvicorn real e cliente HTTP mostrou o encerramento correto, com os
  quatro eventos entregues: é um artefato do registrador de rede.
- O 404 no console veio da tentativa de reabrir uma conversa de outra pasta de teste;
  a interface voltou à tela inicial, como esperado.
- O botão "Nova anotação" quebrava a linha em larguras médias; foi corrigido.

## Limites

Decisões marcadas "diverge da skill" valem pela memória, mas a skill só muda num lote
de desenvolvimento. A importação das memórias antigas fica para a v1.
