# Spec 0048 — sem raciocínio na leitura de páginas e do documento

Estado: medido e adotado em 21/10/2026; aguarda a revisão e o commit do pesquisador.

## Propósito e decisões

No lote 46, o raciocínio oculto levou 54% do tempo das respostas locais. Desligá-lo, porém, já tinha tirado
citações: dos trechos, no lote 41, e da E4 do lote 46. Por isso o pesquisador aprovou, no planejamento de 21/10, uma
medição com critério de adoção fixado antes. O produto só mudaria se os três pontos passassem.

**A medição:**
- **Configuração:** o modelo local real e o Gemini simulado, sem token pago. Foram 21 chamadas locais, abaixo do
  teto de 30.
- **O que rodou:** as 6 perguntas de páginas e de documento (P2, P3, E2, E5, E6 e E8), duas vezes, com o raciocínio
  desligado só no pedido com leitura.
- **A base:** as mesmas 6 perguntas com raciocínio nos lotes 45 e 46, num total de 11 respostas completas, com
  mediana de 133,0 s na chamada local.

| Critério, fixado antes | Base | Sem raciocínio | Passou |
|---|---|---|---|
| Mediana da chamada local até 93 s | 133,0 s | **71,3 s** | sim |
| No máximo 2 respostas descartadas em 12 | 2 em 12 | **1 em 12** | sim |
| Documento esperado citado em pelo menos 8 de 12 | 4 de 6 no lote 46 | **10 de 12** | sim |

Notas:
- A mediana é o valor do meio das respostas completas, ordenadas pelo tempo.
- "Descartada" é a resposta refeita pelo Gemini, por marca fora do que foi enviado ou por não citar.
- O documento esperado é o das notas de avaliação de 28/09/2026; o indicador mede só a presença dele, não a
  correção científica.

## Requisitos vivos

- **PRV-07, alterado:** a leitura de páginas inteiras ou do documento vai sem raciocínio no modelo local. Os trechos
  e a conversa seguem com o raciocínio do roteador, e o Gemini segue como antes.

## Implementação

- **`local.py`, `_kwargs`:** `reasoning_effort: "none"` também quando o pedido traz a leitura
  (`request.metadata["reading"]`).
  - A subida da escada para as páginas entra na mesma regra, porque o pedido dela traz a leitura.
- **O que não muda:** a escalada (PRV-02), a conferência das citações, os limites de custo e a configuração do
  Ollama.

## Achado da medição, fora deste lote

Na E6 da 1ª rodada, o local escreveu `[K1]`, copiado do exemplo `[K1][K2]` das regras comuns. A conferência
reprovou, e o local parou cedo; na 2ª rodada, a mesma pergunta citou certo.
- **Proposta para um próximo lote, a decidir pelo pesquisador:** tratar `[K1]`, `[K2]` e afins como o formato das
  regras (BIB-05), ou tirar os exemplos das regras comuns.

## Aceitação

- O teste do PRV-07, alterado antes da mudança e falhando antes dela; a bateria completa, Ruff e as specs.
- A medição, registrada na [validação do lote 48](../migracao/validacao-lote-48.md) e no
  [manifesto](../migracao/lote-48.json). Sem commit e sem publicação.
