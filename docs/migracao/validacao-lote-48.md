# Validação do lote 48 — sem raciocínio na leitura de páginas e do documento

Data: 21/10/2026. Escopo na [spec 0048](../specs/0048-raciocinio-nas-paginas.md). Medido e adotado; aguarda a
revisão e o commit do pesquisador.

## A medição

Autorizada com a aprovação do plano em 21/10/2026: o modelo local real, o Gemini simulado, nenhum token pago e no
máximo 30 chamadas locais.

**Consumo:** 21 chamadas locais e 1 ao Gemini simulado, sem rede.

**Placa:** 6.002 MiB livres antes, sem o Firefox e o VS Code abertos. Não houve erro do Ollama.

**Método:** o do lote 46, sobre as mesmas cópias da biblioteca e dos resultados, com memória nova por pergunta. O
raciocínio foi desligado pelo script de medição, só no pedido com leitura de páginas ou do documento.

**Ordem:**
1. a P7 e a E3, com o roteador do lote 47 (resultado na [validação do lote 47](validacao-lote-47.md));
2. as 6 perguntas de páginas e de documento, duas vezes.

## O critério, fixado antes da medição

| Critério | Base, com raciocínio | Sem raciocínio | Passou |
|---|---|---|---|
| Mediana da chamada local até 93 s | 133,0 s (11 respostas dos lotes 45 e 46) | **71,3 s** (11 respostas completas) | sim |
| No máximo 2 respostas descartadas em 12 | 2 em 12 | **1 em 12** | sim |
| Documento esperado citado em pelo menos 8 de 12 | 4 de 6 no lote 46 | **10 de 12** | sim |

Os três passaram, e a mudança foi adotada.

Notas:
- A mediana é o valor do meio dos tempos ordenados.
- "Descartada" é a resposta refeita pelo Gemini, por marca fora do que foi enviado ou por não citar.
- O documento esperado é o das notas de avaliação de 28/09/2026; o indicador mede presença, não correção.

## Por pergunta

Tempo da chamada local que escreveu a resposta, em segundos:

| Pergunta | Lote 45, com raciocínio | Lote 46, com raciocínio | Lote 48, 1ª rodada | Lote 48, 2ª rodada |
|---|---:|---:|---:|---:|
| P2 (documento inteiro) | 81,6 | 110,1 | 65,4 | 59,8 |
| P3 (páginas inteiras) | 182,5 | 138,2 | 78,8 | 81,9 |
| E2 (documento inteiro) | 133,0 | parou cedo | 71,3 | 68,0 |
| E5 (páginas inteiras) | 213,8 | 97,8 | 82,0 | 58,5 |
| E6 (páginas inteiras) | 209,5 | 114,6 | parou cedo, `[K1]` | 64,6 |
| E8 (páginas inteiras) | 148,2 | 81,0 | 88,7 | 98,2 |

O que as respostas mostram:
- **Citações:** nas 11 respostas completas, todas as marcas estavam exatas; nenhuma precisou de normalização.
- **Raciocínio:** saiu de fato, com 0 caracteres de raciocínio nas 12 chamadas.
- **Texto:** o visível ficou mais longo, de 3.083 a 7.540 caracteres; o modelo passa a explicar no próprio texto.
- **E8:** não ficou mais rápida. A resposta sem raciocínio foi a mais longa.
- **O descarte:** na E6 da 1ª rodada, o local escreveu `[K1]`, copiado do exemplo `[K1][K2]` das regras comuns. A
  conferência reprovou, e o local parou 14 s depois de começar; na 2ª rodada, a mesma pergunta citou certo.
  - A correção fica proposta para um próximo lote: tratar esses exemplos como o formato das regras, ou tirá-los das
    regras comuns.

## Testes sem modelo

| Conferência | Resultado |
|---|---|
| Teste do PRV-07 | alterado antes da mudança e falhando antes dela; passa depois |
| Pytest, 46 arquivos, um processo por arquivo | **834 passaram, 0 falharam, 0 ignorados**, em 234,8 s |
| Ruff e `git diff --check` | sem apontamentos |

## Limites

- **Rodadas:** duas por configuração, com temperatura 0,6.
- **A base:** vem de dois lotes anteriores, um deles com as instruções antigas de citação (lote 45).
- **O Gemini simulado:** não cita, então a pergunta escalada (E6, 1ª rodada) conta como descartada e sem o documento
  esperado.
- **O que não se mede:** a correção científica das respostas, só a presença de citações exatas e do documento
  esperado.

## Evidências e commit

**Evidências**, fora do Git:
- a medição, em `tmp/lote-48/medicao/` (`resultado.json`, `escalada.json`, `calls.json` e `metadata.json`);
- o script, `tmp/lote-48/medir_raciocinio.py`;
- os hashes no [manifesto](lote-48.json).

**O patch:** `tmp/lote-48/lote-48.patch` separa as mudanças do lote 48 nos arquivos já rastreados.

Não houve commit, push nem publicação.
