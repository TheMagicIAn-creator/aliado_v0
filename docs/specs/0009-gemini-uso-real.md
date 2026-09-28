# Lote 09 — Gemini em uso real

Primeiro lote do [roteiro da v0](../roteiro-v0.md), autorizado pelo pesquisador
em 26/09/2026, incluindo duas chamadas reais pagas.

## Decisões

- Só o Gemini será usado, por ser a API com orçamento disponível. OpenAI continua configurável.
- Modelos escolhidos entre os 44 listados para a chave: `flash` → `gemini-3.8-flash`
  e `flash_lite` → `gemini-3.5-flash-lite`. Versões fixas, porque os aliases
  `*-latest` mudam de modelo sem aviso.

## Escopo

- `.env`: somente as duas linhas de modelo foram preenchidas. A chave não foi exibida.
- `LLMUsage.reasoning_tokens`: o adapter Gemini passa a ler `thoughts_token_count`,
  que é cobrado e não entra em `candidates_token_count`.
- `aliado.llm.usage_log`: resumo dos tokens e registro JSONL por chamada, com data,
  provedor, modelo, tarefa e tokens, sem pergunta nem resposta. O CLI `perguntar`
  imprime o resumo e grava em `data/uso/chamadas.jsonl`, ou no caminho de
  `--registro-uso`. Se o registro falhar, a resposta já entregue é mantida.
- Preços não ficam no código, porque mudam; o custo é calculado a partir dos tokens.

## Critérios de aceitação

- Testes sem rede: captura dos tokens de raciocínio, registro sem conteúdo da
  conversa e resposta preservada quando o registro falha.
- Duas chamadas reais: Flash-Lite sem skill e Flash com `pesquisa-inversores`.
  A segunda deve reproduzir as taxas e bases decididas no lote 07.
- Suite completa e Ruff passam.

## Fora do escopo

Interface web, memória, busca na web, streaming no CLI, OpenAI e cálculo de preço.
