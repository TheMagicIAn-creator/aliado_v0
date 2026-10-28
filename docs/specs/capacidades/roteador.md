# Capacidade: roteador do chat

Spec viva: diz o que vale **hoje** para as escolhas de cada mensagem do chat. Um lote que mudar esta
capacidade atualiza este arquivo e cita na própria spec de mudança os requisitos que acrescenta, altera ou
retira. Cada requisito é citado por pelo menos um teste (`tests/test_specs.py`).

Criada no lote 35 (18/10/2026), pela [spec 0035](../0035-chat-tela-minima.md). O roteador nasceu no lote 31
([spec 0031](../0031-roteador-e-escada.md)), e o aprendizado com o uso, no lote 33
([spec 0033](../0033-reescrita-aprendizado-resultados.md)). O lote 47, pela [spec 0047](../0047-roteador-e-intervalos.md),
acrescentou o ROT-08; o lote 70, pela [spec 0070](../0070-revisor-roteador-harness.md), o ROT-09.

## O que é

Para cada mensagem, o roteador local escolhe, sem tokens, a skill, o modelo, a leitura da biblioteca (sem
biblioteca, trechos, páginas inteiras, o documento citado ou a leitura ampla), a web e os resultados da pesquisa.
A tela não tem seletores: quem quer escolher escreve o pedido na própria mensagem.

## Requisitos

**ROT-01. Pedido escrito.** Uma frase de pedido no começo ou no fim de uma oração vira escolha e sai do texto que
vai ao roteador, à busca e ao modelo; a conversa guarda o texto como foi escrito. As frases: "use o modelo
maior/menor", "sem biblioteca", "só trechos", "use as páginas inteiras", "leia o documento inteiro", "leitura
ampla" ou "leia todos os documentos inteiros", "busque na web", "sem web", "com/sem os resultados", "use a skill
X" (só uma skill que existe) e "com o apoio da skill X". O pedido do documento inteiro fica no texto, porque diz
qual é o documento. No meio da frase, ou seguido de "de/do/da", não é pedido.
*Cenário:* dada "Use o modelo maior. O que é MCC?", então o modelo maior responde a "O que é MCC?"; dada "O modelo
maior detectou mais falhas?", então nada muda.

**ROT-02. Tela mínima.** A tela do chat não tem seletores de skill, modelo, leitura e teto, nem as chaves de
biblioteca, web, resultados e apoio. Sem os campos, a skill, o modelo e a leitura ficam com o roteador; a
biblioteca e os resultados ficam disponíveis, e o roteador decide se os consulta; a web só entra por pedido.
*Cenário:* dada a mensagem "Obrigado, era isso." sem pedido, então o modelo menor responde sem a biblioteca e sem
a web, e a linha da rota diz "escolha do AL-IAdo".

**ROT-03. Quem vence.** O campo de um botão da tela ("Ler mais fundo", "Completar pesquisa", "Responder só com os
trechos") vale sobre o pedido escrito; o pedido escrito vale sobre a escolha aprendida; a escolha aprendida, sobre
o roteador. A linha da rota diz "pedido por você" e o que foi pedido.
*Cenário:* dada "Use o modelo maior. ..." enviada com o campo do modelo menor, então responde o modelo menor.

**ROT-04. Leitura ampla.** Só por pedido escrito. Ela pede confirmação todas as vezes, mesmo abaixo de 30 mil
tokens, e a confirmação não vale para a mensagem seguinte. "Ler mais fundo" para no documento inteiro. Os limites
não mudam: acima de 30 mil tokens, a confirmação; depois de 300 mil tokens no dia, toda leitura acima dos trechos
pergunta.
*Cenário:* dada "Faça a leitura ampla. ..." com uma estimativa de 9 mil tokens, então a tela pergunta antes; sem o
pedido, a mesma pergunta nunca chega à leitura ampla.

**ROT-05. Mensagem só com o pedido.** Uma mensagem que é só um pedido ("busque na web") refaz a pergunta anterior
com ele e com os pedidos dela. Sem pergunta anterior, o servidor pede a pergunta junto do pedido.
*Cenário:* dada a pergunta sobre autoencoders e, depois, "Busque na web, por favor", então a pergunta sobre
autoencoders é refeita com a busca na web.

**ROT-06. Aprendizado.** Um pedido escrito de modelo, skill ou leitura, diferente da escolha automática, fica
guardado para as mensagens muito parecidas, como um botão. A leitura ampla e a web nunca ficam guardadas. Uma
lição que falha não leva as outras.
*Cenário:* dada "Use o modelo maior. Oi, tudo bem?", então um "Oi, tudo bem?" seguinte usa o modelo maior e a rota
diz "repetiu uma escolha sua".

**ROT-07. Teto e aviso diário.** Acima de 30 mil tokens estimados, o servidor não chama o modelo sem a
confirmação; depois de 300 mil tokens no dia, toda leitura acima dos trechos pede confirmação, e a confirmação
não é reaproveitada.
*Cenário:* dada uma leitura do documento de 46 mil tokens, então a tela pergunta, e nada é gravado antes da
resposta.

**ROT-08. Conceito e obras de outros vão à biblioteca.** Pergunta que começa por "como se calcula" ou "como
calcular" é de conceito, e a que fala de uma tese, um TCC ou uma monografia pede o que essa obra diz. As duas vão à
biblioteca, com trechos, mesmo que tenham palavras dos resultados da pesquisa ("confiabilidade", "componentes",
"modelos") ou que pareçam com as frases de exemplo dos resultados. Os resultados continuam valendo para as perguntas
sobre eles, inclusive "faça um resumo dos resultados".
*Cenário:* dadas a P7 ("Como se calcula a confiabilidade de um sistema com componentes em série e em paralelo?") e a
E3 (os modelos usados no TCC da UFSC) das perguntas aprovadas, então as duas vão à biblioteca, com trechos; "Mostre
os resultados da avaliação oficial" continua nos resultados.

**ROT-09. Tradução, explicação curta e lista vão direto ao modelo.** Uma mensagem que pede tradução ("traduza",
"translate"), explicação para leigo ou curta ("para um leigo", "em uma frase", "em até 3 frases", "em poucas
palavras") ou começa por "liste" vai ao modelo sem a biblioteca, como tarefa. Não vale quando a mensagem também pede
fonte (literatura, citação, documentos, referências…) nem quando cita um documento, e não muda as regras de antes
dela, inclusive a continuação depois de uma resposta com a biblioteca. Pedido de definição ("O que é MTTF?") continua
indo à biblioteca (lote 70).
*Cenário:* dadas "Traduza para o inglês: o inversor falhou por sobreaquecimento." e "Explique o que é FMECA para um
leigo, em até 3 frases.", então as duas vão sem a biblioteca; "Liste as fontes que tratam de MPPT." e as perguntas
aprovadas que não citam documento continuam na biblioteca.
