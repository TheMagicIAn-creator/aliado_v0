# Spec 0061 — o intervalo de páginas abreviado nas citações

Estado: feito em 23/10/2026, sem commit.

## Propósito e decisões

**A origem:** na medição das 16 perguntas de 22/10, com o cache q8_0 (registrada na
[validação do lote 58](../migracao/validacao-lote-58.md)), o modelo local escreveu `[Kf74ae8ecp1–8]` na P2.
- **O que era:** um intervalo de páginas abreviado, em que o fim vem só com o número da página.
- **O que aconteceu:** a conferência das citações só aceitava o intervalo com o identificador inteiro dos dois lados
  (`[Kf74ae8ecp1–Kf74ae8ecp8]`, lote 47). Ela reprovou a resposta, e o local parou cedo.

**A decisão (pesquisador, 23/10/2026):** "Faça o ajuste do formato".

**O que muda:** o fim do intervalo pode vir só com o número da página. As condições são as mesmas da forma inteira:
- do mesmo documento;
- em ordem;
- de 2 a 10 páginas;
- todas enviadas.

Fora disso, a marca continua reprovando.
- **A parada cedo do local (PRV-02):** usa a mesma conta (`_stray`), então aceita a mesma forma.
- **O custo:** nenhum token a mais.

## Requisitos vivos

- **BIB-05 (alterado), em `biblioteca.md`:** o intervalo de páginas aceita o fim abreviado.

## Implementação

- **`src/aliado/agent.py`:**
  - `_RANGE` deixa opcional o identificador do segundo lado.
  - `_ranges` toma o documento do primeiro lado quando o segundo não traz o dele.
- **`tests/test_knowledge.py`:** o teste do BIB-05 ganha 5 casos da forma abreviada.
  - **Os que valem:** de 1 a 6 com travessão e de 2 a 3 com hífen.
  - **Os que reprovam:** largo demais, páginas não enviadas e de trás para a frente.
  - Os 2 que valem falharam antes da mudança, e os 3 que reprovam já passavam.

## Aceitação

- **O teste do BIB-05:** passando, com a forma inteira e a abreviada.
- **Os testes do chat, a bateria rápida e o Ruff.**
- **O modelo real:** sem medição. A forma apareceu numa resposta só, e a conta é a mesma da forma inteira.
