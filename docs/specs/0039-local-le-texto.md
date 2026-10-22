# Spec 0039 — o modelo local lê as páginas pelo texto guardado

Estado: implementado e medido localmente em 18/10/2026; aguarda a revisão e o commit do pesquisador. Spec de mudança: os
requisitos vivos estão em [capacidades/provedores.md](capacidades/provedores.md) (PRV-01 e PRV-03 alterados; PRV-06,
novo).

## Propósito

O pesquisador ligou o modelo local no `.env` e pediu o próximo lote. Na medição do lote 38, nas 16 perguntas reais da
biblioteca:
- **8 foram direto ao Gemini.** A leitura das páginas inteiras ou do documento citado vai em PDF, e o local só
  aceitava até 4 páginas como imagem.
- **3 foram refeitas pelo Gemini.** O local citou os documentos por extenso, sem as marcas `[K…]`.

Cada uma é uma chamada paga. O local passa a ler o que a biblioteca já guarda de cada página: o texto extraído (nativo
ou por OCR) e a descrição automática das figuras e tabelas, feita no lote 29. É a direção do pedido dele: "ler
imagem, ler TODO o conteúdo escrito".

## Decisões do pesquisador (18/10/2026)

- O modelo local fica ligado no `.env` (ele mesmo pôs a linha).
- O próximo lote é o local ler as páginas como texto, a alavanca medida que mais tirava perguntas dele.

## O que muda

- **`knowledge/library.py`, `pages()`:** cada página de um PDF ganha `descricao`, com o texto dos itens da descrição
  automática guardada (`_figure_rows`). O `text` da página não muda.
- **`knowledge/reading.py`:**
  - a fonte de cada página leva `descricao`;
  - em `messages()`, cada parte em PDF leva `text`, o texto guardado das suas páginas no formato
    `=== [K…] local (nota) ===`, com a descrição marcada para conferir no original;
  - a formatação fica numa função só, `_page_lines`, que serve também ao ramo sem PDF;
  - o Gemini usa só `type`, `mime_type`, `key` e `data` da parte, então nada muda para ele, nem em tokens.
- **`llm/providers/local.py`:**
  - **Parte em PDF com `text`:** vira texto, sem abrir o PDF e sem o limite de 4 páginas; vale o contexto. A parte
    sem `text` segue como imagem, até 4 páginas.
  - **`TEXT_NOTE`:** quando houve conversão, o `system` ganha a nota de que os PDFs vieram como texto e de que a
    descrição é automática.
  - **`CITE_RULE`:** quando o pedido traz fontes citáveis (`metadata["citations"]`), entra a regra de citar cada
    afirmação com o `[K…]`.

## Testes

- **`test_reading.py`:** a parte em PDF leva o texto das 12 páginas, com os `[K…]`, e a chave `text`.
- **`test_local_provider.py`:** uma parte de 10 páginas com texto vai como texto, sem abrir o PDF, com a nota e a
  regra de citação; sem documento e sem fontes, nenhuma das duas.
- **`test_figures.py`:** a descrição salva de uma página aparece em `pages()` e na parte em PDF, e o texto da página
  segue sem ela.

## Resultado

- **Testes:** 806 passam, arquivo por arquivo (os 804 de antes e 2 novos); o ruff e o `git diff --check` estão
  limpos.
- **Medição:** as mesmas 16 perguntas do lote 38, com o Gemini falso e sem custo. Pelo primeiro desfecho de cada
  uma:

| | Lote 38 | Lote 39 |
|---|---|---|
| Respondidas pelo local | 3 | 6 (P5, P6, P7, P8, E3 e E7) |
| Citaram o documento esperado | 1 | 3 (P5, P6 e E7) |
| Direto ao Gemini | 8, por ter mais de 4 páginas de PDF | 7, todas pelo contexto de 16 mil tokens |
| Refeitas pelo Gemini, sem as marcas | 3 | 3 (P4, E4 e E6) |
| Chamadas ao Gemini | 13 | 12 |

- **O que a leitura como texto resolveu:** o limite das 4 páginas sumiu. Na E6, as páginas inteiras couberam: 11,4
  mil tokens reais.
- **O que agora segura as perguntas:** o contexto.
  - Só a base de regras e skill dá de 6,6 a 6,9 mil tokens reais em toda pergunta.
  - As que ficaram de fora estimavam de 19 a 57 mil tokens, cerca de 15 a 45 mil reais.
  - Com 32 mil, 6 das 7 caberiam.
- **A regra de citação:** resolveu a P5, que no lote 38 foi refeita. Ainda falharam a P4 (o identificador entre
  crases, `K42a22a…`, em vez de colchetes), a E4 e a E6 (o documento citado pelo nome).
- **Tempo:** 130 s por pergunta, em média, contra 105 s no lote 38, porque o local responde mais. As respostas dele
  levam de 1,5 a 4,5 minutos, com raciocínio.

Os números estão na [validação do lote 39](../migracao/validacao-lote-39.md).

## Fora deste lote

- **O contexto de 32 mil tokens:** é a próxima alavanca medida.
  - 6 das 7 perguntas que ficaram de fora caberiam, e 22 dos 31 documentos caberiam inteiros, contra 13 hoje.
  - Com 22 camadas, a placa passaria dos 4 GB; com 20, deve ficar abaixo, a medir.
- **O identificador entre crases:** a conferência das citações não aceita `` `K…` ``.
- **O raciocínio desligado nos trechos.**
- **O roteador na E3.**
- **Desenhar como imagem as páginas sem texto e sem descrição.** São 2 em branco e 28 figuras não descritas.
