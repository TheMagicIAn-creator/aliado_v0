# Lote 10 — interface local no navegador

Lote do [roteiro da v0](../roteiro-v0.md), autorizado em 26/09/2026. O pesquisador
pediu uma interface nova, com a antiga como base, porque a anterior pareceu seca,
e aprovou a direção visual do esboço e a instalação de cinco pacotes.

## Decisões

- Direção visual: respostas em serifa, citações numeradas com painel de fontes,
  skill ativa como etiqueta, envio de PDF no próprio campo de mensagem, tokens por
  resposta e trilho lateral (Conversas, Biblioteca; Ciência e Memória reservadas).
- Pacotes do extra `web`, nas mesmas versões da interface antiga: `starlette` 1.0.0,
  `uvicorn` 0.47.0, `python-multipart` 0.0.28, `markdown-it-py` 4.2.0 e `mdurl` 0.1.2.
  KaTeX 0.17.0 copiado da origem, com a licença MIT.

## Escopo

- **Servidor** (`aliado.interfaces.web.app`), iniciado por `aliado web`: só em
  127.0.0.1, com recusa de host externo (DNS rebinding), cabeçalho `x-aliado` e
  checagem de origem nas mutações (CSRF), CSP e `nosniff`. Importado apenas pelo
  comando; `aliado.cli` e `aliado.interfaces.web` não carregam Starlette.
- **Conversas** em `data/conversas/*.json`, com gravação atômica e título pela
  primeira pergunta. O histórico recente segue ao modelo. Respostas locais (sem
  evidência ou citação inválida) não voltam ao modelo.
- **Núcleo:** `prepare_request(history=...)` aceita as últimas 12 mensagens, com
  teto de 24 mil caracteres. `Agent.answer(append_sources=False)` devolve as fontes
  citadas em `LLMResult.sources`, na ordem de aparição, sem colar o texto. O
  terminal mantém o comportamento anterior.
- **Renderização** segura: Markdown sem HTML bruto, fórmulas preservadas para o KaTeX
  (`R$ 5,00` não vira fórmula) e `[Kid]` citado convertido em número clicável.
- **Biblioteca:** envio de até 100 MB, indexação em fila de um único trabalhador,
  cópia temporária removida ao final, reenvio de documento que falhou reprocessa,
  visualização do Markdown extraído e abertura do original na página citada
  (`document_files`, `document_id` nos resultados da busca).
- **Correção encontrada no teste real:** o OCR falhava no Windows porque o
  Tesseract era chamado por caminho relativo. Agora o caminho é resolvido para
  absoluto; isso também corrige `biblioteca adicionar` no terminal.

## Critérios de aceitação

- Testes sem rede para rotas, proteção, conversas, histórico, citações, escape de
  HTML, erros sem vazamento, envio em segundo plano e documentos.
- Uma chamada real barata ao Flash-Lite pela interface, sem a pergunta automática
  de próximo passo. Envio real de um PDF sintético com OCR pela interface.
- Suite completa e Ruff passam.

## Correções após a revisão

A pedido do pesquisador, também entram neste lote:
- resposta em fluxo contínuo, com botão para parar;
- exclusão de conversas para uma lixeira local;
- progresso da extração por página;
- fontes e conversas em painéis sobrepostos em telas estreitas.

Regra para o lote 11: **apagar uma conversa não apaga a memória gerada a partir dela.**

## Fora do escopo

Memória (lote 11), busca na web (12), experimentos (13–15), esvaziamento da lixeira
e acesso por outros computadores.
