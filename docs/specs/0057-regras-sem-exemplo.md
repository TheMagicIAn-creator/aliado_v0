# Spec 0057 — as regras de citação sem identificador de exemplo

Estado: feito em 22/10/2026, sem commit; o commit fica com o pesquisador.

## Propósito e decisões

É o segundo lote da 0.9.0 e vem da lista "Depois" do plano de 21/10. Na medição do lote 48, numa das 12 respostas
(a E6 da 1ª rodada), o modelo local escreveu `[K1]`, copiado do exemplo `[K1][K2]` das regras de citação. A
conferência reprovou a marca, e o local parou cedo. A mesma pergunta citou certo na 2ª rodada.

**A decisão (pesquisador, 22/10/2026):** tirar o exemplo das regras. A [spec 0048](0048-raciocinio-nas-paginas.md)
deixou duas saídas:
- tratar `[K1]`, `[K2]` e afins como o formato das regras, na conferência (BIB-05);
- tirar os exemplos das regras comuns.

Ficou a segunda, pelos motivos abaixo.
- **Tira a causa,** como o lote 46 fez com as notas do local: sem um identificador de exemplo, não há o que copiar.
- **A outra saída esconderia um erro.** Tratar `[K1]` como formato poderia tirar do texto uma marca errada que só
  parece exemplo, sem nenhuma conferência.
- **O formato continua dito:** `[K...]` com o identificador fornecido, um identificador por colchete. Se o modelo
  juntar dois num colchete, `split_grouped` já separa as marcas, como antes.

**O que muda:** nas regras da biblioteca (os trechos) e nas da leitura integral (as páginas), sai ", como [K1][K2]".
- **Elas vão ao local e ao Gemini:** as duas regras são as mesmas para os dois modelos.
- **O custo:** cerca de 5 tokens a menos por pergunta com a biblioteca.

**O que fica:** o `[R1]` das regras dos resultados. É o bloco da visão geral, que vai sempre que os resultados vão.
Uma citação errada a ele é pega pela conferência dos números.

## Requisitos vivos

- **PRV-06 (alterado), em `provedores.md`:** as regras de citação da biblioteca e da leitura integral, que o local
  também recebe, só mostram o formato `[K...]`, sem identificador de exemplo.

## Implementação

- **`src/aliado/agent.py`:** `LIBRARY_RULES` e `READING_RULES` sem o exemplo.
- **`tests/test_local_provider.py`:** um teste novo exige que as duas regras não tenham `[K` seguido de letra ou
  número.
  - O placeholder `[K...]` e o `[K]` do catálogo continuam permitidos.
  - O teste reprova o texto de antes nas duas regras.

## Aceitação

- **Os testes dos arquivos do chat:** o provedor local, os trechos, a leitura, as figuras e a biblioteca.
- **A seleção rápida do pedido de 22/10 e a bateria rápida.**
- **Ruff.**
- **A medição com o modelo real:** só com a autorização do pesquisador, com o número de chamadas combinado. Sem
  ela, o lote fica validado sem modelo, como o lote 47.
