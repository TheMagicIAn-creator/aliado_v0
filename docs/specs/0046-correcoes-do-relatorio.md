# Spec 0046 — correções do relatório de eficiência, conferidas com as medições

Estado: implementado e validado em 20/10/2026; aguarda a revisão e o commit do pesquisador.

## Propósito e decisões

O pesquisador pediu as correções e os testes do "Relatório de Melhoria e Eficiência do Modelo Local", seguindo os
lotes 44 e 45. Conferi cada afirmação do relatório com os registros do lote 45, com o Ollama instalado e com o
código. O relatório corrigido está em
[docs/revisao/2026-10-20-relatorio-eficiencia-conferido.md](../revisao/2026-10-20-relatorio-eficiencia-conferido.md).
- **O que não conferiu:** a falta de memória de vídeo e o prefill não são a causa da lentidão. O cache do local já
  usa q8_0, e o modelo é híbrido.
- **O tempo:** vai quase todo para o raciocínio oculto do modelo.
- **As 4 respostas locais descartadas:** tinham identificadores de citação alterados. O modelo copiou os exemplos
  das instruções e colou a página no identificador do trecho.

**Decisões do pesquisador, em 20/10/2026:**
- as quatro correções do chat;
- a chave do cache da Ciência;
- a medição das 16 perguntas só no modelo local, com o Gemini simulado;
- a configuração do Ollama mantida como está: 32 camadas na placa, contexto de 32 mil e cache q8_0.

## Requisitos vivos

- **BIB-05, novo:** a marca que aponta um único trecho enviado vale como ele; o `[K...]` literal sai do texto.
- **PRV-02, alterado:** na primeira marca que não confere, o local para e o Flash refaz sem esperar o fim.
- **PRV-06, alterado:** a nota e a regra de citação do local não mostram identificador de exemplo.
- **PRV-07, alterado:** a reescrita simples pede só a consulta; o plano, só com partes.

## Implementação e compatibilidade

- **`local.py`:**
  - `TEXT_NOTE` e `CITE_RULE` sem `[K12ab34p5]` e sem `[K...]`;
  - o fluxo do SDK é fechado no `finally`, também quando quem lê para antes do fim.
- **`agent.py`:**
  - `_canonical` aceita só as duas formas exatas de BIB-05, e `_stray` reaproveita a mesma conferência para a
    parada no fluxo;
  - as regras comuns (`[K...]` e `[K1][K2]`) não mudam, porque o Gemini não errou com elas;
  - a resposta paga não para no meio.
- **`app.py`:** o `query_rewriter` de `default_settings` deixa o `plan` com quem chama, como o contrato já testado
  em `tests/test_coverage.py`. Defeito desde a 0.6.0 (`30f1681`).
- **Ciência, `explorer.py`:** a chave do cache dos erros por variável ganha os hashes dos pesos, já conferidos por
  `load_training`, e a ordem das 24 variáveis.
  - `CACHE_VERSION` passa a 2, e o nome do arquivo vem da chave inteira.
  - Nenhum cálculo muda: o cache é refeito uma vez ao abrir os exploradores, sem tokens.
  - O arquivo antigo `data/ciencia/erros-<12>.npz` deixa de ser lido e fica para o pesquisador apagar, se quiser.
- **O que não muda:** rotas HTTP, formatos, limites de custo, o modelo local e o cálculo da detecção.

## Fora deste lote

- Configuração do Ollama: q4_0, 31 camadas, contexto de 8 mil e orçamento de 3 mil tokens.
- Raciocínio desligado nas páginas e no documento, que pede uma medição própria.
- PLD, decodificação por gramática, modelo de 3B, torch.compile e HDF5.
- O arquivo oficial dos erros da rodada, que depende do formato e do instante da janela.
- O roteador na E3 e na P7 e a expansão errada de ECP na P3.

## Aceitação

- Testes novos, escritos antes das mudanças e falhando antes delas:
  - as marcas reais do lote 45;
  - a parada no fluxo e o fechamento do fluxo HTTP;
  - a escalada por `invalid_citations`;
  - a reescrita com e sem plano pelo `default_settings`;
  - o cache ligado aos pesos.
- Bateria completa, arquivo por arquivo, Ruff, specs vivas e isolamento do núcleo.
- Medição das 16 perguntas com o modelo local real e o Gemini simulado: nenhum token pago, no máximo 30 chamadas
  locais.

Resultados na [validação do lote 46](../migracao/validacao-lote-46.md) e no
[manifesto](../migracao/lote-46.json). Sem commit e sem publicação.
