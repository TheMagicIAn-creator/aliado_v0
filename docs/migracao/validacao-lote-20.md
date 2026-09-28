# Validação do lote 20 — aba Ciência

Verificação local em **28/09/2026**, sobre o commit `fb366c4` (lote 19). Nenhum commit, push ou
tag. **Nenhuma chamada paga.**

## Testes

`tests/test_science_tab.py` traz 8 testes novos, sem rede:

| Teste | O que prova |
|---|---|
| Reprodução canônica (com os dados reais; pulado sem eles) | Com k = 5, p99 e m = 3, os 10 modelos e sementes repetem **exatamente** a avaliação de 27/09: limiar, detectados, atraso mediano, sensibilidade, falsos alarmes no teste e no pré-falha, e o resultado de cada um dos 14 ensaios. Repetem também as grades de sensibilidade relatadas (m ∈ {1, 2, 3, 5} e k ∈ {5, 10, 20}, semente 42). |
| Cache | Uma segunda carga reaproveita o mesmo arquivo; outro k muda o limiar e deixa de ser "canônico". |
| Confiabilidade | O explorador repete, valor a valor, o cenário do IGBT em operação. |
| Rotas | Resultados listados com agrupamento, caminho fora dos resultados recusado, explorador exigindo o preparo, cenário salvo só com fonte e hipóteses e sempre em pasta nova, FMECA gravada em pasta nova. |
| Página | O botão Ciência deixou de estar "em breve" e carrega `ciencia.js`. |

**362 testes passaram** (354 do lote 19 e 8 novos), o Ruff não apontou problemas e `app.js` e
`ciencia.js` passaram na checagem de sintaxe, no Python 3.12.14. O preparo dos exploradores
(modelos, dados e erro por variável dos 10 modelos) levou cerca de 2,6 s.

## Aceite no navegador

Interface de teste em `127.0.0.1:8769`:
- dados em `tmp/lote-20/dados`;
- os resultados numa **cópia** de `data/resultados`, em `tmp/lote-20/resultados`;
- os dados reais do GPVS, só para leitura.

| Seção | Resultado |
|---|---|
| Resultados | 15 resultados listados. Os modelos mostram 2 gráficos de calibração e o relatório. A avaliação mostra as 28 linhas da semente 42 (2 modelos × 14 ensaios). A medição da busca mostra 13 de 16 e MRR 0,781. |
| Limiar | Denso, semente 42: limiar de 3,7338, igual ao canônico, na 191ª posição de 192, com falso alarme esperado de 1,04% por janela (o valor do lote 14). Com k = 10, o limiar foi a 1,98. Com p99,9, caiu no máximo (192ª de 192), com o aviso de que seriam precisas 1.001 janelas. |
| Alarme e detecção | Faixa do M14 fixa. Com os parâmetros canônicos, apareceram 10 de 14 detectados, atraso mediano de 2,04 s, 0 falsos alarmes (limite superior de 2.050 por hora) e 0 no pré-falha, com a nota "reproduzem a avaliação de 27/09". Com m = 1, apareceram 13 de 14, 0,839 s, 2 falsos alarmes no teste e 51 no pré-falha, os mesmos números da grade relatada. "Voltar aos canônicos" restaurou m = 3. |
| Confiabilidade | IGBT em operação: F(1) = 3,51% e F(20) = 51,1%. CCB em calendário, pelo ponto de partida: F(1) = 42,8%. Os dois conferem com o lote 07. O cenário foi salvo com as fontes do ponto de partida e recusado sem fonte. |
| FMECA | Mesma ordem da `fmeca-001`: pelo NPR, CCB, contatores, IGBT e ventiladores; pela taxa, CCB, ventiladores, IGBT e contatores. O relatório foi gravado numa pasta nova. |
| Tela estreita | Com 319 px, a página não rola para os lados, e a tabela dos ensaios rola dentro da própria caixa. |
| Console | Um 400, que é a recusa proposital do cenário sem fonte, e um 404 que não veio de nenhuma rota da API (todas responderam 200, 201 ou 202). O servidor não registrou erros. |

**Os resultados reais não mudaram.** Comparada com `data/resultados`, a cópia tem só as duas
pastas gravadas no aceite (um cenário e uma FMECA). O cache do erro por variável ficou em
`tmp/lote-20/dados/ciencia` (8,5 MB). No uso normal, ele fica em `data/ciencia/`, fora do Git.

## Defeitos encontrados e corrigidos no aceite

1. **Legenda sobre a curva** nos gráficos de R(t) e F(t). Ela passou para uma faixa acima da área do gráfico.
2. **Caminho fixo nas mensagens.** "Salvo em data/resultados/…" aparecia mesmo com `--resultados` apontando para outra pasta. Agora o servidor devolve o caminho real.
3. **Nome da pasta cortado no meio de uma palavra** ("…-ccb-8-76"). Agora ele é cortado numa fronteira.
4. **Arredondamento enganoso:** 99,6% aparecia como "100%". As porcentagens passaram a 3 algarismos.
5. **Linha do tempo ilegível.** Os escores do pós-falha, dezenas de vezes o limiar, achatavam o resto. A escala agora vai até 4 vezes o limiar, com aviso do valor máximo.
6. **Rótulos fracionados** ("48,8") no eixo das janelas. São inteiros quando o eixo é de contagem.

## Estado final

- `data/resultados` intacto; nada foi gravado em `data/ciencia` durante o aceite.
- `.claude/launch.json` ganhou a entrada `aliado-web-lote-20` para o servidor de teste.
- `tmp/lote-20` guarda a cópia dos resultados, os dados do aceite e o cache, e pode ser apagada depois da revisão.
