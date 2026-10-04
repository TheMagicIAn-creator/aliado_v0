# Lote 31 — roteador local e escada de leitura

Lote autorizado em 04/10/2026, sobre o lote 30 (ainda sem commit). O pedido: gastar o mínimo de tokens; o
AL-IAdo escolher sozinho o modelo e a skill, "sendo que essa era a ideia inicial de roteamento de API para
menor custo e mesma entrega ótima"; e ficar menos "quadrado". "Gastamos metade do orçamento total em um dia."

## O que a investigação mostrou

| O quê | Tokens de entrada |
|---|---:|
| Piloto do lote 30 (04/10) | 4,5 milhões |
| Descrição das figuras (03/10, uma vez só) | 2,0 milhões, mais 1,4 milhão de saída |
| "Quais foram nossas últimas conversas?", com a biblioteca ligada | 386 mil |
| Uma pergunta comum por trechos, com os resultados da pesquisa | cerca de 18 mil |

- **A causa no uso diário era a regra do lote 30:** com a biblioteca ligada, toda pergunta lia até 400 mil
  tokens, fosse qual fosse a pergunta.
- **A parte fixa era a maior parte de uma pergunta comum.** Em letras: resultados da pesquisa, 15,3 mil;
  lista dos 26 documentos, 9,1 mil; instruções das duas skills, 8,6 mil; material de referência da skill,
  5,0 mil; regras da biblioteca, 2,1 mil; instruções gerais, 2,0 mil. Os trechos da busca são cerca de 12 mil.
- **Nada decidia antes de gastar.** O AL-IAdo antigo tinha regras rápidas e um roteador de modelos por tipo
  de tarefa; aqui, o modelo, a skill e a leitura eram escolhidos na tela.

## Decisões do pesquisador (04/10)

| Tema | Decisão |
|---|---|
| Leitura padrão | Escada automática: começa barato e só sobe quando preciso. |
| Teto sem confirmação | 30 mil tokens por pergunta; acima, a tela mostra a estimativa e pede um clique. |
| Modelo e skill | O AL-IAdo escolhe e mostra; os seletores ficam para fixar uma escolha. |
| Limite diário | Aviso em 300 mil tokens; depois dele, toda leitura acima do modo barato pede confirmação. |
| Trilhas (perguntas já respondidas) | Entram neste lote, de forma natural: sem botão e sem repetir a resposta antiga. |

## Escopo implementado

### 1. Roteador local, sem tokens (`src/aliado/routing.py`)

Antes de qualquer chamada paga, a mensagem recebe uma rota: o que ela precisa, a skill, o modelo e quanto
raciocínio pedir, com o motivo em palavras.

- **Regras rápidas primeiro:** documento citado pelo autor, pelo título ou pela sigla ("o documento da
  NASA"); palavras de conversa e memória ("nossa conversa", "você lembra"); pergunta sobre o acervo ("há
  alguma literatura sobre"); figura, tabela, gráfico ou fórmula; resultados da pesquisa ("GPVS", "nossos
  resultados"); tarefa de código, escrita ou web.
- **Depois, frases de exemplo:** a mensagem é comparada, pelo modelo local de busca, com frases de cada tipo
  (`src/aliado/routing_examples.py`). Trocar ou acrescentar frases muda a rota sem mexer no código.
- **Na dúvida, o caminho barato:** sem sinal claro, a mensagem só vai à biblioteca se parecer com o título de
  algum documento; e vai por trechos.
- **Mensagem curta continua o assunto:** depois de uma resposta com a biblioteca, "Traga outra fonte." herda
  a leitura dela (até as páginas inteiras); depois de uma resposta com os resultados, "E o LSTM?" continua
  nos resultados.
- **Skill:** a da conversa fica até a mensagem mudar claramente de assunto; conversa solta vai sem skill.
- **Modelo:** o menor (`flash_lite`), com pouco raciocínio, para conversa, pergunta sobre o acervo, fato
  pontual e tarefa sem código; o maior (`flash`) para síntese, figuras, tabelas, documento citado, método e
  resultados.

### 2. Escada de leitura

| Degrau | O que vai ao modelo | Quando |
|---|---|---|
| 0 | Nada da biblioteca | Conversa, memória, tarefa, resultados da pesquisa |
| 1 | Os trechos que a busca achou | Consulta de texto: fato, síntese, método, acervo |
| 2 | As 10 páginas mais próximas da pergunta, inteiras, em PDF | Figura, tabela, gráfico ou fórmula; ou quando o degrau 1 não achou |
| 3 | O documento citado na mensagem ou fixado na conversa, inteiro; os outros, por trechos | A mensagem cita o documento, e ele cabe em 18 mil tokens |
| 4 | A leitura ampla do lote 30 (150 a 400 mil tokens) | Só por escolha sua na tela |

- **Sobe sozinho um degrau** (de trechos para páginas) quando a resposta não cita nenhum documento, se as
  duas chamadas juntas couberem nos 30 mil. A tela avisa "Os trechos não bastaram: lendo as páginas
  inteiras…", e a rota guarda a primeira tentativa.
- **Documento citado que é grande** (um livro, uma norma): na escolha automática vão as 10 páginas dele mais
  próximas da pergunta, e não o documento inteiro; "Ler mais fundo" oferece o documento.
- **Acima de 30 mil tokens estimados,** o servidor não chama o modelo: devolve a estimativa, os documentos e
  as páginas, e a tela pergunta "Ler assim" ou "Responder só com os trechos". Na mesma conversa, a mesma
  leitura não pergunta de novo.
- **Depois de 300 mil tokens no dia,** toda leitura acima dos trechos pergunta, toda vez. O dia é o deste
  computador (antes, o contador de "hoje" virava no horário de Greenwich).
- **"Ler mais fundo (cerca de N mil tokens)"** sob cada resposta com a biblioteca: refaz a pergunta no degrau
  seguinte, com o custo estimado antes do clique.
- **A estimativa** é a do pedido inteiro: o texto, a três letras por token, e 560 tokens por página de PDF.
- Com a busca na web ligada, o pedido segue por trechos, como no lote 30.

### 3. Parte fixa enxuta

- **Lista dos documentos:** a completa (9,1 mil letras) só quando a pergunta é sobre o acervo; nas outras,
  só os nomes (0,6 mil letras).
- **Material de referência da skill** (5,0 mil letras): só em perguntas de método e de resultados, e nas
  continuações.
- **Resultados da pesquisa** (15,3 mil letras): só quando a pergunta é sobre os resultados ou o método. O
  botão "Usar resultados" passa a dizer se eles podem ir, e não que vão sempre.
- **Conversas anteriores lembradas:** uma, em vez de três, quando a pergunta vai à biblioteca.
- **Ordem estável:** regras, nomes dos documentos e documentos no começo; memória, conversa, trechos e a
  pergunta no fim. O que se repete fica onde o Gemini pode reaproveitar.

### 4. Contagem exata de termos (`DocumentLibrary.mentions`)

Em quais documentos e páginas um termo aparece, na biblioteca inteira, pelo índice de palavras, sem custo.
Vai ao modelo nas perguntas sobre o acervo e nas que citam um documento: "autoencoder aparece em 5 dos 26
documentos" deixa de depender do que a busca trouxe. Vale para a palavra escrita e para as que começam por
ela; não acha sinônimos nem traduções, e o modelo é avisado disso.

### 5. Trilhas: o que já foi perguntado e respondido

- **O que é guardado:** a cada resposta com citações conferidas, as páginas citadas (pelo conteúdo do arquivo
  e pelo número da página) e o vetor da consulta de busca da pergunta, na memória de conversas do lote 18.
  As conversas já gravadas ganham as trilhas na primeira abertura.
- **A trilha é achada pelo assunto e pelo pedido.** O assunto é a consulta de busca (sem "traga", "com
  citação direta"); o pedido é a frase da pergunta. Só com os dois parecidos (0,86 e 0,75) a pergunta é tratada
  como já respondida: "os princípios da MCC" e "o conceito de MCC" têm o mesmo assunto e pedidos diferentes.
- **Pergunta já respondida:** o índice não é varrido. O modelo recebe a troca anterior, sem as marcas de
  citação antigas, e até 6 páginas que ela citou, inteiras; e escreve uma resposta nova. Se as páginas não
  bastarem, a resposta sai sem citação e a escada sobe um degrau.
- **Pergunta refeita logo em seguida, na mesma conversa:** é sinal de que a resposta não bastou; a leitura
  sobe para as páginas, com as da resposta anterior na frente.
- **Pergunta do mesmo assunto:** numa leitura por páginas, 3 das 10 ficam reservadas para páginas de
  respostas parecidas, depois das melhores da busca.
- **Reforço:** as páginas das trocas parecidas são somadas, e a mais recente conta em dobro: a página citada
  de novo sobe, e a que deixou de ser citada desce. Documento apagado sai das trilhas.
- **Na tela:** só a linha da rota diz "partiu de uma resposta anterior", com a data e a pergunta na dica.
- Não é uma rede treinada: é uma memória associativa sobre a rede local de busca. Com centenas de perguntas,
  comparar com o que está guardado funciona melhor que treinar.

### 6. Na tela

- Os seletores de skill, modelo e leitura ganham "automático", que é o padrão. A leitura tem cinco opções:
  automática, só trechos, páginas inteiras, documento inteiro e leitura ampla.
- A linha de cada resposta mostra a rota ("gemini-3.5-flash-lite · Sem especialização · sem a biblioteca"),
  com o motivo e de quem foi cada escolha ao passar o mouse.
- O aviso de confirmação, o aviso do limite diário e o botão "Ler mais fundo".
- "Usar biblioteca" continua na tela: ligado, permite a consulta; o roteador decide se a pergunta precisa.

## O que mudou em relação ao plano

| Plano | Feito | Por quê |
|---|---|---|
| A pergunta muito parecida dispensa a busca e a reescrita da consulta | Dispensa a busca; a consulta continua sendo reescrita | A frase sozinha confunde pedidos: "Traga a definição, com citação direta" serve a qualquer assunto. A consulta reescrita diz o assunto |
| A página citada de novo ganha peso, a que deixa de ser citada perde | Soma das trocas parecidas, a mais recente em dobro | Dá o mesmo efeito sem um contador a mais para manter |
| O degrau 2 pode virar o padrão das consultas de texto | O degrau 1 é o padrão; o 2 entra em figuras e tabelas e quando o 1 não acha | Ver a medição em `docs/migracao/validacao-lote-31.md` |
| A contagem de termos ajuda a escolher as páginas do degrau 2 | Vai só ao modelo | A busca já usa o índice de palavras para escolher as páginas |
| Documento citado vai inteiro | Só se couber em 18 mil tokens; senão, as páginas dele mais próximas da pergunta | Um livro citado pelo autor pediria confirmação a cada pergunta |
| (não previsto) | Os resultados da pesquisa só seguem em perguntas de resultados ou de método | Eram a maior parte fixa: 15,3 mil letras em toda pergunta |
| (não previsto) | Uma conversa lembrada, em vez de três, nas perguntas à biblioteca | Até 6 mil letras por pergunta |

## Limites

- **O roteador erra.** Nas 80 mensagens rotuladas, 79 caíram num degrau aceito, e elas serviram para
  ajustar as regras: o número em mensagens novas será menor. Quando ele erra para menos, a resposta sai
  sem o que precisava; os remédios são "Ler mais fundo" e fixar a escolha nos seletores.
- **Resultados que a regra não reconhece:** uma pergunta sobre os resultados sem as palavras que o roteador
  conhece ("GPVS", "nossos resultados", "ensaios") vai sem eles, e a resposta dirá que não os tem.
- **A trilha repete o alcance da resposta anterior:** a pergunta já respondida parte das páginas que aquela
  resposta citou. Se ela ficou incompleta, a nova também fica (aconteceu na medição, com a tabela de uma
  norma). O modelo é instruído a dizer quando as páginas não bastam, e aí a escada sobe; uma resposta parcial
  com citação passa. Refazer a pergunta em seguida, na mesma conversa, ou "Ler mais fundo" fazem uma leitura
  nova.
- **A estimativa de tokens é aproximada:** a três letras por token no texto. O teto é conferido por ela.
- **Fica para o lote 32:** busca em memória (hoje ela leva cerca de 4 s), reordenação local das páginas por
  uma segunda rede, e o revisor de memória só quando há o que guardar.
