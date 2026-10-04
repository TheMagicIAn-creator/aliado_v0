# Validação do lote 31 — roteador local e escada de leitura

Verificação local em **04/10/2026**, sobre o commit `85dce50` e o lote 30, ainda sem commit. O assistente não
fez commit, push nem tag.

- A biblioteca real, `data/bibliotecas/principal`, foi usada só para leitura. As conversas e a memória do
  pesquisador foram lidas em cópias temporárias, apagadas no fim. O registro de uso do aplicativo
  (`data/uso/`) não recebeu as chamadas da medição.
- As medições e os roteiros ficaram em `tmp/lote-31/`, fora do Git.

## Testes

684 testes passam, e o Ruff não aponta nada. São 20 testes novos:

- **`tests/test_routing.py` (13):**
  - as regras: conversa e memória sem biblioteca, no modelo menor e com pouco raciocínio; pergunta sobre o
    acervo com a lista completa; figura e tabela nas páginas inteiras; resultados da pesquisa sem biblioteca,
    e com trechos quando a pergunta também pede a literatura; tarefa de código no modelo maior; biblioteca
    desligada sem leitura nenhuma;
  - documento citado pelo autor ou pela sigla; a mensagem curta que continua a leitura ou os resultados da
    resposta anterior; o pedido de leitura mais funda;
  - sem o modelo local, valem as regras, e a dúvida vai por trechos; um modelo local que falha não derruba
    a rota;
  - as frases de exemplo pelo modelo local; a skill da conversa fica numa mensagem curta e sai na conversa;
  - os termos do assunto de uma pergunta, sem as palavras do pedido;
  - a contagem exata: documentos e páginas por termo, a palavra e as que começam por ela, a expressão, o
    termo ausente;
  - o degrau das páginas: páginas soltas da busca, as de uma resposta anterior na frente, só elas quando não
    há busca (o índice não é varrido), as páginas do documento citado antes das dos outros, e o lugar
    reservado para páginas de respostas parecidas;
  - o degrau do documento sem nenhum citado: o mais bem colocado da busca; o citado vale sobre ele;
  - a parte fixa enxuta: sem a lista completa e sem o material de referência, com os nomes dos documentos, e a
    ordem estável do pedido;
  - a troca anterior chega ao modelo sem as marcas de citação antigas, e a contagem de termos, como dados;
  - acima do teto, o agente devolve a estimativa e a chave em vez de chamar o provedor; com a chave, segue;
    depois do aviso diário, a chave muda;
  - as trilhas: as páginas citadas sem repetição, a pergunta parecida, outro assunto sem trilha, a troca
    esquecida, a chave pela consulta de busca e a semelhança da frase; a memória de conversas do lote 18
    continua igual;
  - o reforço (a página citada de novo sobe) e um banco anterior ao lote, que ganha as colunas sem perder as
    trocas.
- **`tests/test_web.py` (7):**
  - o roteador escolhe modelo, skill e leitura, e a resposta guarda a rota e de quem foi cada escolha; um
    nome nos seletores fixa a escolha;
  - acima do teto, um único aviso de confirmação e nada gravado; com a chave, a resposta sai; por trechos não
    há teto a conferir; depois de 300 mil tokens no dia, toda leitura acima dos trechos pergunta;
  - a resposta sem citação sobe um degrau, as duas chamadas ficam no registro de uso, e a rota guarda a
    primeira tentativa; com o degrau fixado, não sobe; se a subida passa do teto, vale a primeira resposta;
  - a pergunta respondida deixa trilha; a mesma pergunta em outra conversa vai sem busca, com a troca e as
    páginas; refeita em seguida, sobe para as páginas; outro assunto não pega trilha; documento apagado sai;
  - o documento citado que é grande vai pelas páginas dele, sem pedir confirmação; o que cabe vai inteiro;
  - a resposta oferece o degrau seguinte com o custo;
  - as travas da tela: as opções automáticas, a linha da rota, a confirmação e "Ler mais fundo".
- **Testes anteriores ajustados (5):** o padrão da leitura passou a ser o automático, e os resultados da
  pesquisa só seguem em perguntas sobre eles. Os testes da leitura ampla pedem "integral" na chamada.

## O roteador nas mensagens rotuladas (sem custo)

80 mensagens com os degraus aceitos escritos à mão: 48 mensagens reais das conversas do pesquisador e as 32
perguntas de referência.

| Grupo | No degrau aceito |
|---|---:|
| Mensagens reais | 47 de 48 |
| Perguntas de referência | 16 de 16 |
| Perguntas sobre figuras e tabelas | 16 de 16 |

- O erro: "Saberia me dizer por qual motivo a sua indexação está ruim?" foi por trechos, sem precisar.
- **As regras foram ajustadas nestas mesmas mensagens.** O número mede o ajuste, e não o acerto em mensagens
  novas, que será menor.
- Modelo escolhido: o menor em 26 das 80, e o maior em 54.

## Tokens por pergunta, antes e depois (sem custo)

As 80 mensagens passaram pelo servidor de verdade (roteador, escada e parte fixa), com a biblioteca real e um
modelo simulado que devolve a estimativa do pedido. "Antes" é o pedido por trechos de antes do lote, com a
parte fixa inteira e os resultados da pesquisa. Sem memória nos dois lados.

| Grupo | Antes, por pergunta | Depois, por pergunta | Soma |
|---|---:|---:|---:|
| 48 mensagens reais | 18,1 mil | 5,4 mil (mediana 0,7 mil) | de 867 mil para 258 mil: 70% a menos |
| 16 perguntas de referência | 18,4 mil | 11,4 mil | de 295 mil para 183 mil: 38% a menos |
| 16 perguntas sobre figuras e tabelas | 18,6 mil | 12,0 mil | de 297 mil para 193 mil: 35% a menos |

- **Contra a leitura ampla do lote 30,** as 32 perguntas de referência custariam 12,5 milhões de tokens
  (374 e 410 mil por pergunta); pela escada, 375 mil.
- **Por degrau, nas mensagens reais:** sem a biblioteca, 28 mensagens, 1,4 mil em média (0,7 mil na
  conversa; 10,8 mil quando vão os resultados da pesquisa); trechos, 16 mensagens, 10,5 mil; páginas, 3
  mensagens, 11,0 mil; documento, 1 mensagem, 17,0 mil.
- **A estimativa contra o uso real,** nas 12 perguntas da medição paga: de 10% abaixo a 6% acima.

## As perguntas de 04/10

| Mensagem | Lote 30 | Lote 31 |
|---|---|---|
| "Quais foram nossas últimas conversas?" | 386 mil tokens, com a biblioteca | 459 tokens, sem a biblioteca, no modelo menor (medido) |
| "Com citação direta, me diga, com base na literatura, o que são autoencoders." | — | trechos, 8,0 mil (estimado) |
| "Há alguma literatura que explica explicitamente sobre autoencoder?" | — | trechos, a lista completa e a contagem exata, no modelo menor, 11,9 mil (estimado) |
| "E o pertile?" | a busca não trouxe o documento | 10 páginas de Pertile (2023): 3, 8, 18, 19, 21, 24, 27, 36, 46 e 73, cerca de 8 mil (estimado). O documento tem 77 páginas e não vai inteiro sem confirmação |

- **Uma correção saiu desta conferência.** Na primeira versão, o documento citado que é grande ia pelas 10
  páginas mais próximas de toda a biblioteca: em "E o pertile?", 4 eram de Pertile e 6 de outros seis
  documentos. Agora as páginas do documento citado vêm antes.
- **A contagem exata** diz que "autoencoder" aparece em 5 dos 26 documentos (Francisti et al., Ibrahim et
  al., Ahirwar e Nandanwar, Sharma et al. e Kull et al.) e em nenhuma página de Pertile (2023). O sexto
  documento da contagem de 04/10 (Marangis et al., 2025) tem a palavra "encoder", e não "autoencoder".

## Trilhas nas conversas já gravadas (sem custo)

Numa cópia das conversas e da memória: 52 trocas guardadas, e 14 ganharam trilha (resposta com citações
conferidas). A consulta de busca das perguntas novas foi escrita à mão, no estilo do reescritor.

| Pergunta nova | Trilha | Assunto | Frase |
|---|---|---:|---:|
| "Como Lafraia define disponibilidade?" | forte: 9 páginas | 0,89 | 0,89 |
| "O que é um autoencoder, segundo a literatura?" | fraca | 0,76 | 0,83 |
| "Defina manutenção centrada na confiabilidade com base em duas fontes." | fraca | 0,91 | 0,25 |
| O resumo do artigo de Ghoneim, com outras palavras | fraca | 0,95 | 0,67 |
| "De acordo com Lafraia, o que é a mantenabilidade?" (outro pedido) | fraca | 0,70 | 0,73 |
| "Quais são os princípios da MCC segundo a NASA?" (outro pedido) | fraca | 0,94 | 0,29 |
| "Como um autoencoder LSTM detecta anomalias?" (outro pedido) | nenhuma | — | — |
| Três perguntas de outros assuntos | nenhuma | — | — |

- **Nenhuma pergunta de outro pedido ou de outro assunto foi tratada como já respondida.**
- **Só 1 das 4 perguntas refeitas com outras palavras foi reconhecida.** A regra pede o assunto (0,86) e a
  frase (0,75) parecidos: ela prefere buscar de novo a responder pelas páginas erradas. Só com o assunto,
  "os princípios da MCC" seria respondida pelas páginas da definição (0,94).
- Trilha fraca não dispensa a busca: reserva 3 das 10 páginas numa leitura por páginas.

## Medição paga

As 12 perguntas do piloto do lote 30, cada uma numa conversa nova, pela escolha automática, pelo servidor
de verdade e pela via com fluxo, que é a da tela. Sem a reescrita da consulta, como no piloto do lote 30.

| Forma | Tokens de entrada nas 12 | Tempo por pergunta | Documento esperado | Página esperada |
|---|---:|---:|---:|---:|
| Só trechos (lote 30) | 137.832 | 7 a 13 s, 120 s no total | 12 de 12 | 5 de 6 |
| Leitura ampla (lote 30) | 3.207.059 | 31 s a 12,5 min, 2.092 s no total | 12 de 12 | 6 de 6 |
| Escolha automática (lote 31), primeira rodada | 146.672 | 10 a 55 s, 295 s no total | 12 de 12 | 5 de 6 |
| Escolha automática (lote 31), código final | 143.639 | 10 a 35 s, 266 s no total | 12 de 12 | 6 de 6 |

- **A primeira rodada achou um defeito.** Em 3 das 12 perguntas (E5, F11 e T3), a mensagem cita um livro ou
  uma norma, e iam as 10 páginas mais próximas de toda a biblioteca. Em T3 (disjuntores na IEEE 493, de 426
  páginas), a página 202, da tabela, ficou de fora, e a resposta saiu parcial. Com as páginas do documento
  citado na frente, as três foram refeitas: a tabela entrou, e a resposta citou as páginas 57, 58, 202, 329
  e 330. A linha "código final" troca essas três pelas refeitas.
- **Por degrau, no código final:** trechos, 2 perguntas, 5,3 e 7,7 mil tokens, 10 e 18 s; páginas inteiras, 5
  perguntas, 10,5 a 11,3 mil, 24 a 31 s; documento citado inteiro, 5 perguntas, 10,6 a 16,8 mil, 14 a 35 s.
- **Modelo:** o maior em 11, e o menor em 1 (um fato pontual).
- **As três respostas que só a leitura ampla completava saíram completas:**
  - **E2** (escalas de Colli, 2015): as três escalas de 1 a 5, por 10,6 mil tokens;
  - **T1** (transformador em Baschel et al., 2018): as duas linhas da tabela (17,8 e 27,4 falhas por milhão
    de horas, 14 e 9,1 anos), por 16,6 mil tokens;
  - **T3** (disjuntores na IEEE 493): a tabela (9, 42, 32, 7% e os demais), por 10,5 mil tokens.
- **Nenhuma das 12 respostas saiu sem citação,** então a subida de degrau não aconteceu nesta rodada. Ela
  foi conferida depois (veja "As três funções com o modelo real").
- **Conversa:** "Quais foram nossas últimas conversas?" custou 459 tokens e levou 4 s, no modelo menor, com
  pouco raciocínio (o serviço aceitou o pedido de pouco raciocínio).
- **Trilha:** a pergunta P4, refeita em outra conversa, foi de 7.749 tokens e 10 s (trechos) para 4.649
  tokens e 8 s (a troca anterior e a página citada, sem busca), com a mesma resposta em outras palavras e a
  mesma página citada.
- **A trilha repete o alcance da resposta anterior.** Nas duas primeiras tentativas de refazer E5, F11 e T3,
  as perguntas partiram das trilhas das respostas da primeira rodada (5,8 a 7,1 mil tokens, 11 a 14 s), e a
  de T3 saiu parcial de novo, com as mesmas duas páginas. A memória nova tinha ganhado as trilhas das
  conversas já gravadas, como o servidor faz ao abrir. Só com dados limpos a leitura foi refeita.
- **Reaproveitamento pelo Gemini:** a pergunta P1 refeita teve 13.553 dos 16.538 tokens de entrada
  reaproveitados.

| O que | Chamadas | Tokens de entrada |
|---|---:|---:|
| Uma mensagem de conversa | 1 | 459 |
| 12 perguntas pela escolha automática, primeira rodada | 12 | 146.672 |
| 2 perguntas refeitas em outra conversa (P1 e P4) | 2 | 21.187 |
| E5, F11 e T3 refeitas, que saíram pelas trilhas (5 chamadas) e pela leitura nova de E5 (1) | 6 | 43.515 |
| F11 e T3 refeitas com dados limpos | 2 | 21.748 |
| As três funções com o modelo real: trilha (4), subida de degrau (2) e confirmação (1) | 7 | 47.110 |
| **Total** | **30** | **280.691** |

- **Autorizado:** até 30 chamadas e 500 mil tokens de entrada. O roteiro conta cada chamada antes de ela
  sair e para antes do limite.
- **O limite de chamadas foi usado inteiro.** As 7 últimas foram autorizadas pelo pesquisador na conversa
  de 04/10, depois da primeira entrega do lote.
- **Saída:** 18.798 tokens, e mais 42.047 de raciocínio. **Reaproveitados pelo serviço:** 17.599 da entrada.
- **Modelos:** `gemini-3.8-flash` e `gemini-3.5-flash-lite`.
- O registro das chamadas está em `tmp/lote-31/piloto/`, nas pastas `dados`, `dados-limpos` e
  `dados-verificacao`, em `uso/chamadas.jsonl`.
- A medição enviou 107 arquivos ao serviço de arquivos do Google; todos foram apagados de lá no fim.

## As três funções com o modelo real

Na primeira entrega do lote, três funções só tinham sido conferidas com modelo simulado. O pesquisador
autorizou as 7 chamadas que restavam, e as três foram conferidas com o Gemini, numa pasta de dados limpa
(`tmp/lote-31/verificar.py`).

- **Pergunta já respondida, com a consulta reescrita pelo modelo menor** (4 chamadas):
  - "Como se calcula a confiabilidade de um sistema com componentes em série e em paralelo?" foi respondida
    por trechos; em outra conversa, "Qual é o cálculo da confiabilidade de um sistema quando os componentes
    estão em série e em paralelo?" foi reconhecida (assunto 0,98 e frase 0,96) e partiu das 5 páginas que a
    primeira citou, sem busca. As duas respostas citaram as mesmas 5 páginas.
  - **A trilha não poupou tokens:** 5.962 de entrada na resposta pela trilha, contra 4.086 na resposta por
    trechos; e 19 s contra 21 s. As 5 páginas inteiras e a troca anterior pesam mais que os 10 trechos. O
    que a trilha dá é a leitura das páginas inteiras e a dispensa da busca.
  - A reescrita custou 242 e 245 tokens no modelo menor.
- **Subida de degrau** (2 chamadas): "Com base na literatura, o que é o algoritmo de consenso Raft em
  sistemas distribuídos?", um assunto que a biblioteca não tem.
  - A resposta por trechos saiu sem citação, a tela recebeu o aviso, e a pergunta foi refeita com 10 páginas
    inteiras de 6 documentos. A segunda resposta também saiu sem citação, dizendo que nada do que foi lido
    trata do assunto. A rota guardou a primeira tentativa.
  - **Custo de subir num assunto ausente:** 19.908 tokens de entrada (8.909 e 10.999) e 29 s, para dizer que
    não há.
- **Confirmação acima do teto** (1 chamada), com o teto desta etapa em 10 mil tokens, para um artigo de 16
  páginas passar dele sem gastar os 50 mil de um documento maior:
  - o servidor não chamou o modelo e devolveu o aviso: 17.984 tokens estimados, "Baschel et al., 2018: 16
    páginas"; nada foi gravado na conversa;
  - com a confirmação, a resposta saiu pelo documento inteiro, com 16.667 tokens de entrada (a estimativa
    ficou 8% acima) e as páginas 5, 6 e 10 citadas.

## No navegador

Servidor de teste (`tmp/lote-31/servidor_teste.py`, porta 8780): a interface, as rotas, o roteador e o agente
reais, com modelo simulado e uma biblioteca de teste. Sem erros no console.

- Os três seletores abrem em "automático", e **Usar biblioteca** começa ligado.
- "Obrigado, era isso.": a linha mostra "modelo-simulado-flash_lite · Sem especialização · sem a biblioteca",
  com o motivo e de quem foi cada escolha na dica; 728 tokens.
- Pergunta de texto: "trechos", com "Ler mais fundo (cerca de 11 mil tokens)".
- Pergunta sobre uma figura: "páginas inteiras", "leu 10 páginas inteiras de 2 documentos".
- Resposta sem citação: o aviso "Os trechos não bastaram: lendo as páginas inteiras…" aparece, e a rota
  guarda a primeira tentativa, com os tokens dela.
- "Documento inteiro" num livro de 45 páginas: a tela mostra "Esta leitura envia cerca de 32 mil tokens ao
  modelo (Souza, 2001: 45 páginas)", com "Ler assim", "Responder só com os trechos" e "Cancelar". Depois de
  "Ler assim", a resposta sai com "leu 1 documento (1 inteiro) · 45 páginas".
- A mesma pergunta em outra conversa: "páginas de uma resposta anterior" e "partiu de uma resposta anterior",
  com a data e a pergunta na dica.
- "Ler mais fundo" refaz a pergunta no degrau seguinte, e a rota diz "leitura: fixado por você".
- A captura de tela não saiu: a janela estava minimizada. A conferência foi pelo conteúdo da página.

## Pacote 0.5.0

- **Arquivo:** `dist/v0.5.0/aliado-0.5.0-py3-none-any.whl`, 99 arquivos, 786 kB, SHA-256
  `24f6cd2ec32fe53b7067c0de8ec837664264b1ed9b645e66a4a79e00981bd027`.
- **Conteúdo, conferido arquivo por arquivo contra `src`:** os 94 arquivos do pacote têm o mesmo hash dos de
  `src`, nenhum ficou de fora, e `aliado/routing.py` e `aliado/routing_examples.py` estão nele.
- **Teste fora do projeto:** instalado com `--target` em `tmp/lote-31/pkg` e carregado de outra pasta. O
  código veio do pacote, a versão lida foi 0.5.0, e o roteador respondeu.
- O pacote 0.4.1, do lote 30, continua em `dist/v0.4.1/`. Ele não foi lançado.

## O que não foi verificado

- **A confirmação com o teto de 30 mil:** o aviso foi conferido com o Gemini com o teto em 10 mil; o número
  muda, e o caminho é o mesmo.
- **A trilha em perguntas refeitas com palavras bem diferentes,** com a consulta reescrita pelo modelo: só um
  par foi medido.
- **O acerto do roteador em mensagens novas.**
- **O aviso diário** com o uso real de um dia: só nos testes.

## Pendências

- **A pergunta já respondida repete o alcance da resposta anterior:** se aquela ficou incompleta, a nova
  também fica. Os remédios hoje são refazer a pergunta em seguida, na mesma conversa, e "Ler mais fundo".
- **A trilha não poupa tokens quando a primeira resposta veio de trechos:** as páginas inteiras custam mais
  que os trechos (5.962 contra 4.086 na medição).
- **Subir um degrau num assunto que a biblioteca não tem custa duas chamadas** (cerca de 20 mil tokens)
  para dizer que não há. A contagem exata de termos poderia evitar a subida.
- **Um teste de 04/10, sem custo, com 10 perguntas sobre os resultados escritas de outro jeito:** o roteador
  reconheceu 7. Ficaram sem os resultados "Quantas falhas o LSTM detectou?", "Qual a sensibilidade do
  autoencoder denso?" e "O que eu consegui até agora no mestrado?".
- **A leitura por páginas lê 10 páginas.** Quando a mensagem não cita o documento, elas vêm de toda a
  biblioteca, e uma tabela de um documento grande pode ficar de fora.
- **O tempo:** 10 a 35 s por pergunta, contra 7 a 13 s dos trechos. A busca leva cerca de 4 s deles.
- **A trilha reconhece poucas perguntas refeitas com outras palavras** (1 de 4 na conferência).
- **Uma pergunta sobre os resultados da pesquisa sem as palavras que o roteador conhece** vai sem eles.
- **Fica para o lote 32:** busca em memória, reordenação local das páginas e o revisor de memória só quando há
  o que guardar.
- **Com o pesquisador:** reiniciar o AL-IAdo para o lote valer (a tela avisa enquanto o programa em execução
  for o anterior); o teste no uso real; o commit dos lotes 30 e 31, a tag `v0.5.0` e o push; o aceite do
  lote 28 no Obsidian; e o que fazer com `tmp/lote-29/`, `tmp/lote-30/`, `tmp/lote-31/` e `dist/v0.4.1/`.
