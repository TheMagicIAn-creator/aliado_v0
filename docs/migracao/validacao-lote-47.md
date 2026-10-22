# Validação do lote 47 — roteador na P7 e na E3 e intervalo de páginas

Data: 21/10/2026. Escopo na [spec 0047](../specs/0047-roteador-e-intervalos.md). Validado sem modelo e conferido
com o modelo local real na medição do lote 48. Aguarda a revisão e o commit do pesquisador.

## Testes sem modelo

**Antes das correções:** falharam 3 testes novos: a P7 e a E3 no roteador, e os dois intervalos válidos. Os 4
intervalos inválidos já reprovavam e precisam continuar assim.

**Depois das correções:**

| Conferência | Resultado |
|---|---|
| Pytest, 46 arquivos, um processo por arquivo | **834 passaram, 0 falharam, 0 ignorados**, em 237,9 s (os 827 do lote 46 e 7 novos) |
| Ruff e `git diff --check` | sem apontamentos |
| Specs vivas e isolamento do núcleo | aprovados: ROT-08, novo, e BIB-05, alterado, citados por testes |

## As 16 perguntas aprovadas, sem modelo

O aplicativo real, com a biblioteca e os resultados copiados no lote 46, levou cada pergunta até a rota. A resposta
e a reescrita foram trocadas por versões falsas: nenhuma chamada a modelo.

| Pergunta | Rota no lote 46 | Rota agora |
|---|---|---|
| P7 | resultados da pesquisa, sem a biblioteca | **síntese, com trechos** |
| E3 | resultados da pesquisa, sem a biblioteca | **síntese, com trechos** |
| As outras 14 | — | idênticas: mesmo motivo do roteador e mesma leitura inicial |

Nota: no lote 46, a E4 subiu de trechos para as páginas depois de uma resposta sem citação. A comparação usa a
leitura de antes da subida, que é a do roteador.

## Com o modelo local real

As duas rodaram na medição autorizada do lote 48, com o Gemini simulado e o raciocínio como o roteador decide:

| Pergunta | Lote 46 | Lote 48, com o roteador do lote 47 |
|---|---|---|
| P7 | 201,3 s, sem a biblioteca; não citou o manual esperado | **74,3 s**, trechos; 8 citações exatas; citou o manual esperado |
| E3 | 40,0 s, sem a biblioteca; não citou o TCC | **47,0 s**, trechos; 5 citações exatas; citou o TCC esperado |

O intervalo de páginas não reapareceu na medição; ele está coberto pelos testes com a marca real da E2 do lote 46.

## Evidências e commit

**Evidências**, fora do Git:
- a conferência das rotas, em `tmp/lote-47/rotas.py` e `rotas.json`;
- a bateria, em `tmp/lote-47/pytest.json`;
- os hashes no [manifesto](lote-47.json).

**O patch:** `tmp/lote-47/lote-47.patch` separa as mudanças do lote 47 nos 8 arquivos já rastreados, conferido na
ida e na volta.

Não houve commit, push nem publicação.
