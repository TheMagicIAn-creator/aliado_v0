# Spec 0037 — páginas sem pendência falsa

Estado: implementado localmente em 18/10/2026; integrado ao fechamento da 0.8.0, aguardando revisão e commit. Spec de mudança: os requisitos vivos estão na spec
nova [capacidades/biblioteca.md](capacidades/biblioteca.md) (BIB-01 a BIB-03, novos).

## Propósito

O pesquisador anexou documentos e viu avisos de "páginas não lidas". Ele quer que o AL-IAdo conheça todas as páginas.
A medição da biblioteca real mostrou que 2.237 das 2.239 páginas tinham texto e que os avisos restantes eram falsos:
- **páginas em branco** de livros digitalizados;
- **páginas com OCR fraco que o modelo já tinha descrito:** gráficos e tabelas, cujo conteúdo estava na busca.

## Decisões do pesquisador (18/10/2026)

- A versão enxuta: páginas em branco sem erro, páginas descritas sem aviso e as páginas de OCR fraco na lista da
  descrição de figuras.
- A reindexação da biblioteca real é capacidade do próprio AL-IAdo, feita por ele pela tela, e não pelo assistente.

## O que muda

- **`knowledge/extraction.py`:**
  - `blank_page(path, number)` reconhece a página em branco pela imagem: a 100 dpi, menos de 0,1% de pontos visíveis
    no miolo, longe das margens;
  - o limite do OCR fraco virou a constante `LOW_CONFIDENCE = 50`.
- **`knowledge/figures.py`:** a página digitalizada com OCR fraco entra na lista da descrição de figuras e tabelas,
  mesmo sem a legenda lida.
- **`knowledge/library.py`:** `settled(issue, described, original)` tira do documento o aviso da página em branco e o
  da página já descrita pelo modelo; o documento só fica "parcial" pelo que falta de fato.

## Testes

Estão em `tests/test_figures.py`:
- a página em branco e a página descrita deixam de ser pendência (BIB-01 e BIB-02);
- a página de OCR fraco entra na lista da descrição, sem a legenda (BIB-03).

## Fora deste lote

- A reindexação da biblioteca real, para os avisos antigos saírem. É o pesquisador quem faz, pela tela do AL-IAdo,
  quando quiser.
