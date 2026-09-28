# Validação do lote 12

Verificação local em **27/09/2026**, Windows/Python 3.12. Nenhum commit, push ou PR;
os commits ficam para a v0 concluída.

## Resultado

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **280 testes passaram** (265 anteriores + 15 novos). |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| Sintaxe do front-end | `node --check` sem erros. |

## Validação real

Servidor com dados temporários em `tmp/lote-12/`, fora do Git, `gemini-3.5-flash-lite`.

1. **Resposta com busca:** "Qual norma IEC trata da segurança de inversores
   fotovoltaicos?". Resposta correta (IEC 62109, partes 1 e 2), 1 busca, 2 fontes,
   marcas `[Wn]` nos trechos e painel "Na web" com a consulta feita (682 tokens).
   **Problema achado:** o texto trazia uma lista de fontes ("International
   Electrotechnical Commission…") diferente das fontes reais, que eram uma loja.
2. **Correção:** a instrução da web passou a proibir listas de fontes no texto e a
   pedir fontes primárias. Na repetição, cada afirmação trouxe a marca da fonte real
   e não houve lista inventada, com 2 buscas (754 tokens). As fontes continuaram
   comerciais: isso vem dos resultados da busca, não da instrução.
3. **Conferência:** uma anotação *sua* com erro proposital ("a IEC 61215 trata da
   segurança de inversores") foi conferida. O veredito foi "contradiz", com a correção
   "IEC 61215 trata da qualificação de projeto e aprovação de tipo de módulos
   fotovoltaicos terrestres", fonte **iec.ch** (273 tokens, 1 busca). Por ser anotação
   sua, virou **conflito**; a sua seguiu valendo. Ao "Aceitar a nova", a correção ficou
   ativa, a original ficou superada e o selo de conflitos sumiu.

Gasto total: **2.856 tokens e 4 buscas**, em 5 chamadas (2 respostas, 2 revisões e
1 conferência). A cobrança das buscas segue a tabela do Google, depois da cota gratuita.

## Observações

- A qualidade das fontes depende da busca do Google. Nas respostas apareceram lojas;
  na conferência, a fonte foi primária. Uma lista de domínios excluídos, deixada para
  depois, reduziria as fontes comerciais.
- O título que o Gemini devolve costuma ser o domínio; o link passa pelo redirecionador
  do Google.
- O 404 no console veio de uma conversa guardada de outra pasta de teste, como no lote 11.
