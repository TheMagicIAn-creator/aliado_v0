# Spec 0047 — roteador na P7 e na E3 e intervalo de páginas nas marcas

Estado: implementado e validado sem modelo em 21/10/2026; aguarda a revisão e o commit do pesquisador. A validação
com o modelo local real vai junto da medição do lote 48.

## Propósito e decisões

Ao fim do lote 46, o pesquisador pediu que eu decidisse o próximo passo com um planejamento. A decisão foi corrigir
primeiro o que se prova sem gastar nada:
- **P7:** "Como se calcula a confiabilidade de um sistema com componentes em série e em paralelo?" ia aos resultados
  da pesquisa, sem a biblioteca, porque "confiabilidade" conta como métrica e "componentes" como palavra da pesquisa.
  Foi a pergunta mais lenta do lote 46 (201 s), e o manual esperado não foi citado.
- **E3:** a pergunta sobre os modelos do TCC da UFSC ia aos resultados por semelhança com as frases de exemplo,
  então o TCC não era lido. Está pendente desde o lote 38.
- **E2:** a marca `[K0cad7c48p1–K0cad7c48p6]` apontava páginas todas enviadas, mas a resposta foi descartada.

O raciocínio desligado nas páginas fica para o lote 48, com medição e critério de adoção fixados antes.

## Requisitos vivos

- **ROT-08, novo:** perguntas que começam por "como se calcula" e perguntas sobre uma tese, um TCC ou uma
  monografia vão à biblioteca, mesmo com palavras dos resultados.
- **BIB-05, alterado:** a terceira forma, o intervalo de páginas de um documento, em ordem, de até 10 páginas, todas
  enviadas.

## Implementação

- **`routing.py`, `_CONCEPT`:** ganha "como (se) calcul…".
- **`routing.py`, `_WORKS`:** novo (tese, thesis, TCC, monografia); essas palavras também entram em `_SOURCES`.
  - O classificador por exemplos não aceita "resultados" quando a pergunta fala de uma dessas obras.
  - A exclusão não usa `_SOURCES` inteiro, porque "resumo" está lá, e "faça um resumo dos resultados" continua nos
    resultados.
- **`agent.py`, `_ranges`:** expande o intervalo antes da conferência e da parada cedo, na mesma função. Fora das
  condições, a marca fica como está e reprova.
- **O que não muda:** as frases de exemplo, os limites do roteador, as rotas HTTP e os custos.

## Aceitação

- **Testes novos, escritos antes e falhando antes:**
  - a P7 e a E3 vão à biblioteca;
  - "Faça um resumo dos resultados da avaliação" e "Mostre os resultados da avaliação oficial" continuam nos
    resultados;
  - o intervalo da E2 é aceito;
  - o intervalo com página não enviada, com 11 páginas, de documentos diferentes ou de trás para a frente continua
    reprovando.
- **As 16 perguntas aprovadas pelo aplicativo real, sem modelo:** só a P7 e a E3 mudam de rota (para trechos), e as
  outras 14 ficam idênticas às do lote 46.
- **O resto:** bateria completa, Ruff, specs vivas e isolamento do núcleo.

Resultados na [validação do lote 47](../migracao/validacao-lote-47.md) e no [manifesto](../migracao/lote-47.json).
