# Validação do lote 10

Verificação local em **26/09/2026**, Windows/Python 3.12. Nenhum commit, push ou PR;
os commits ficam para a v0 concluída.

## Resultado

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **247 testes passaram** (227 anteriores + 20 novos). |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| `pip check` após instalar o extra `web` | Sem conflitos. |
| Importação sem servidor | `aliado.cli` e `aliado.interfaces.web` não carregam Starlette nem Uvicorn. |

O único aviso da suíte vem do próprio `starlette.testclient` (alias antigo do
`anyio`) e não afeta o comportamento.

## Teste real no navegador

Servidor iniciado com dados e biblioteca temporários em `tmp/lote-10/`, fora do Git.

- **Layout** conferido em 1400×860 (claro) e 800 px (escuro, modo compacto).
- **Chamada real** ao `gemini-3.5-flash-lite`, sem especialização: "Em uma frase: o que
  é MTBF?". A resposta correta saiu em serifa, **sem** a pergunta automática de
  próximo passo, com 453 tokens. O título da conversa e o contador do topo foram
  atualizados.
- **Envio real** do PDF sintético `ocr-sintetico.pdf`. A primeira tentativa falhou
  no OCR: o Tesseract era chamado por caminho relativo, defeito existente desde o
  lote 04. Com a correção, o reenvio reprocessou o documento, que ficou "pronto",
  com 1 trecho lido por OCR e confiança média de 96%.
- **Biblioteca:** lista, estado, Markdown extraído e original abrindo como `application/pdf`.
- **Citações:** exibição conferida com uma resposta simulada no navegador, sem nova
  chamada paga: número clicável, fórmula no KaTeX, cartão destacado com página, aviso
  de OCR e links para a página e o Markdown.
- **Proteção:** host externo e POST sem o cabeçalho próprio foram recusados (403).
  Console do navegador sem erros.

## Correções após a revisão do pesquisador

Pedido do pesquisador: corrigir as limitações listadas, mesmo que o design mude. Todas
foram corrigidas e conferidas no navegador:

| Limitação | Correção | Evidência |
|---|---|---|
| Resposta chegava inteira | Fluxo contínuo em linhas JSON (`Agent.stream_answer`, Gemini com tokens no fim). A checagem de citações segue sobre o texto completo, e o botão de enviar vira "parar". Interromper não grava nada. | Chamada real ao Flash-Lite com a biblioteca ligada: o texto chegou em 6 pedaços, de 8 a 285 caracteres, entre 2,5 e 2,8 s. |
| Sem exclusão de conversas | Lixeira em cada conversa, com confirmação. O arquivo vai para `data/conversas/lixeira/`, recuperável. Apagar uma conversa não apaga a memória gerada (regra para o lote 11). | Conversa apagada pela interface; o arquivo apareceu na lixeira e sumiu da lista. |
| OCR sem contagem de páginas | `progress(etapa, atual, total)` na extração e na biblioteca. O cartão mostra "Lendo página x de y", "OCR na página x de y" e "Indexando n trechos", com barra proporcional. | PDF de 10 páginas: estados 4/10, 6/10, 9/10 e 39 trechos indexados. |
| Fontes ocultas em telas estreitas | Painel de fontes e gaveta de conversas abrem sobrepostos, com botão de fechar e fundo escurecido. A resposta ganha o link "n fonte(s)". | Conferido a 399 px: citação, painel, gaveta e exclusão. |

A validação das **citações com resposta real do Gemini**, que estava pendente, foi
feita: a resposta citou o trecho do PDF sintético, a checagem aprovou e a citação
virou o número 1. Foram 822 tokens.

**Também corrigido:** rolagem horizontal em telas estreitas, causada pelo topo largo
demais. A largura do conteúdo agora é igual à da janela, mesmo a 319 px.

Resultado: **252 testes passaram** (247 anteriores + 5 novos, com os testes da
interface reescritos para o fluxo contínuo) e Ruff sem problemas.

## Limites

Durante o fluxo, as marcações `[K…]` aparecem como "[fonte]" e só viram números após
a checagem final. A exclusão move a conversa para a lixeira; não há esvaziamento pela
interface.
