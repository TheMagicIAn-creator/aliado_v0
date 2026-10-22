# Validação do lote 46 — correções do relatório de eficiência

Datas: 20 e 21/10/2026. Escopo na [spec 0046](../specs/0046-correcoes-do-relatorio.md). O relatório em PDF, conferido
afirmação por afirmação, está em
[docs/revisao/2026-10-20-relatorio-eficiencia-conferido.md](../revisao/2026-10-20-relatorio-eficiencia-conferido.md).
Validado localmente; aguarda a revisão e o commit do pesquisador.

## Testes sem modelo

**Antes das correções:** os testes novos falharam pelos motivos esperados.
- **8 falharam:** as marcas da P8 e da E8 e o `[K...]` literal; a parada no fluxo; as notas do local; o fechamento
  do fluxo HTTP; a reescrita, com o mesmo `TypeError` do aplicativo; e o cache da Ciência.
- **4 já passavam:** são os casos que devem continuar reprovando (página errada, P5, E7 e a marca ambígua).
- **O caso novo da escalada:** também já passava, porque só acrescenta cobertura ao que o aplicativo já fazia.

**Depois das correções:**

| Conferência | Resultado |
|---|---|
| Pytest, 46 arquivos, um processo por arquivo | **827 passaram, 0 falharam, 0 ignorados**, em 235,9 s (os 814 do lote 44 e 13 novos) |
| Ruff, sem reescrita | sem apontamentos |
| `git diff --check` | sem apontamentos |
| Specs vivas e isolamento do núcleo | aprovados: BIB-05, novo, e PRV-02, PRV-06 e PRV-07, alterados, citados por testes |

Execução e registros em `tmp/lote-46/pytest.json`, `ruff.log` e `diff_check.log`, fora do Git.

## Medição com o modelo local real

Autorizada pelo pesquisador em 20/10/2026: as 16 perguntas aprovadas, só no modelo local, com o Gemini simulado.
Nenhum token pago e no máximo 30 chamadas locais.

**Método:** o mesmo do lote 45.
- O servidor HTTP real do aplicativo, com a pergunta escrita como o pesquisador escreve.
- Uma cópia da biblioteca (31 documentos) e dos resultados, e memória nova por pergunta.
- O modelo `aliado-local`, com contexto de 32.768 tokens e 32 camadas na placa.
- O `.env` não foi lido: o script definiu só o modelo local e nomes falsos para o Gemini, sem chave nenhuma.

**Consumo:**
- 24 chamadas locais: 22 na rodada e 2 ao repetir a P6.
- 5 chamadas ao Gemini simulado, sem rede.
- 0 token pago.

**Placa:**
- 6.002 MiB livres antes, sem o Firefox e o VS Code abertos.
- Com o modelo carregado (13,3 s para carregar), 5.633 MiB ocupados e 370 MiB livres.

| Pergunta | Lote 45: quem respondeu (s) | Lote 46: quem respondeu (s) | O que houve no lote 46 |
|---|---|---|---|
| P1 | Gemini (22,8) | Gemini simulado (8,2) | fora do alcance do local (mais de 32 mil tokens), como antes |
| P2 | local (90,4) | local (112,8) | 16 citações, todas exatas |
| P3 | local (188,7) | local (144,4) | 16 exatas |
| P4 | local (38,8) | local (27,6) | 2 exatas; rota leve, sem raciocínio |
| P5 | Gemini (77,1), marca alterada | **local (96,3)** | 10 exatas |
| P6 | local (111,0) | local (97,1) | 1ª tentativa: erro 500 do Ollama, passageiro; repetida: 10 exatas |
| P7 | local (181,5) | local (201,3) | sem a biblioteca: o roteador mandou aos resultados da pesquisa |
| P8 | Gemini (71,6), marca alterada | Gemini simulado (59,4) | marca com 1 caractere a menos; **parou 5 s depois do primeiro texto** |
| E1 | Gemini (29,2) | Gemini simulado (5,1) | fora do alcance do local, como antes |
| E2 | local (141,9) | Gemini simulado (66,3) | marca com um intervalo de páginas; **parou 3 s depois do primeiro texto** |
| E3 | local (55,5) | local (40,0) | sem a biblioteca, como antes (roteador) |
| E4 | local (40,6) | local (182,4) | sem citação nas duas tentativas (ver os limites) |
| E5 | local (231,6) | local (110,9) | 3 exatas |
| E6 | local (224,8) | local (125,3) | 21 exatas |
| E7 | Gemini (72,4), marca alterada | **local (46,9)** | 2 exatas |
| E8 | Gemini (209,2), marca alterada | **local (87,7)** | 6 exatas |

Nota: o tempo vai do envio da pergunta ao fim da resposta. No lote 46, quem respondeu "Gemini simulado" respondeu na
hora, sem custo e sem citar: o tempo dessas linhas não se compara ao do lote 45.

| Medida | Lote 45 | Lote 46 |
|---|---|---|
| Respostas finais do modelo local | 10 de 16 | **12 de 16** |
| Respostas locais reprovadas por marca fora do que foi enviado | 4 (P5, P8, E7 e E8) | **2** (P8 e E2), as duas paradas cedo |
| Marcas normalizadas pelo BIB-05 | não existia | 0: as formas do lote 45 não apareceram |
| Resposta local reprovada por não citar nada | 0 | 1 (E4) |
| Erro 500 do Ollama | 2, na P2, com programas abertos | 1, na P6, sem programas abertos; a repetição respondeu |
| Documento esperado citado nas respostas finais do local | 8 | 8 |
| Tempo médio das 9 perguntas respondidas pelo local nos dois lotes | 129,2 s | 115,7 s |
| Mediana dessas 9 | 111,0 s | 112,8 s |

Notas:
- "Marca fora do que foi enviado" é a citação cujo identificador não corresponde a nenhum trecho ou página enviados.
  A conferência reprova a resposta, e o Gemini Flash a refaz.
- "Documento esperado" é o que as notas de avaliação de 28/09/2026 indicam para cada pergunta. O indicador mede só a
  presença dele, não a correção científica.
- O tempo do local não mudou de forma significativa: o lote não mexeu no modelo nem no raciocínio. As diferenças
  acompanham o tamanho do raciocínio de cada resposta.

## Para onde vai o tempo do local

Nas 11 respostas locais com raciocínio, medido no fluxo do Ollama:

| Parte | Média | Parte do tempo |
|---|---:|---:|
| Leitura do pedido, até o primeiro token | 14,1 s | 14% |
| Raciocínio oculto, do primeiro token ao primeiro texto visível | 56,3 s | 54% |
| Texto visível, até o fim | 33,2 s | 32% |

Notas:
- O raciocínio oculto chega no campo `reasoning` do fluxo e não aparece na tela. Teve 5.687 caracteres em média,
  contra 2.860 do texto visível; na P7, foram 14.071 caracteres de raciocínio.
- Isso confirma, medido, o que o relatório corrigido mostra pelo lote 45: a leitura do pedido não é o gargalo.

## As marcas novas

- **P8:** `[Kfef6efcbcb34f98]` é o trecho `K2fef6efcbcb34f98` sem o primeiro caractere. É uma alteração diferente
  da do lote 45, que tinha a página colada. Sem comparação aproximada (BIB-05), ela reprova, e o local parou na hora.
- **E2:** `[K0cad7c48p1–K0cad7c48p6]` é um intervalo de páginas do documento lido inteiro, numa marca só. Não é uma
  das duas formas aprovadas; o local parou na hora.
  - Aceitar um intervalo quando todas as páginas dele foram enviadas seria uma extensão do BIB-05 e pede a decisão
    do pesquisador.
- **O que não reapareceu:** nenhum `[K12ab…]`, nenhum "p5" e nenhum `[K...]`.

## Limites

- **Uma rodada por configuração:** com temperatura 0,6, há variação de uma rodada para outra. No lote 43, 3 das 16
  perguntas trocaram de desfecho entre duas rodadas iguais. A E2 e a E4 mudaram sem mudança que as explique.
- **E4:** na rota leve, sem raciocínio, o local respondeu de conhecimento geral, sem citar, e a conferência pegou.
  - Como o Gemini simulado não cita, a pergunta subiu para as páginas inteiras e voltou ao local, que também não
    citou.
  - Numa conversa real, o Gemini Flash teria refeito a resposta. A volta ao local depois da escalada, na subida para
    as páginas, é o desenho atual da escada e fica registrada para um próximo lote.
- **O erro 500 da P6:** o servidor do Ollama não está gravando log, então a causa não foi identificada. A folga da
  placa com o modelo carregado é de cerca de 370 MiB. A repetição da mesma pergunta respondeu normalmente.
- **A parada cedo:** a economia é estimada pelo tamanho das mesmas respostas no lote 45 (cerca de 15 a 20 s em cada
  uma), não medida. As tentativas interrompidas ficam sem a contagem de tokens.
- **O que não se mede:** a qualidade das respostas do Gemini e a correção científica das respostas.

## Evidências e commit

**Evidências**, fora do Git:
- a medição em `tmp/lote-46/medicao/` e `tmp/lote-46/medicao-p6/`;
- os scripts `medir.py` e `repetir_p6.py`;
- os hashes no [manifesto](lote-46.json).

**Commit:** 13 arquivos já rastreados que o lote 46 alterou também estão na lista de commit da 0.8.0, preparada no
lote 44: o código, os testes, as specs vivas, o roteiro e o CHANGELOG.
- **O patch:** `tmp/lote-46/lote-46-codigo.patch` separa só as mudanças do lote 46 nesses 13 arquivos.
- **Conferência:** o patch foi conferido na ida e na volta, e o estado anterior a ele passa no teste das specs.
- **Uso:** com ele, é possível commitar a 0.8.0 como foi validada e o lote 46 depois.

Não houve commit, push nem publicação.
