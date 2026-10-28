# Spec 0071 — o nome do usuário e a integração do Gemini com o Ollama

## Propósito e decisões

**O pedido (27/10/2026):** avaliar o que ficou das últimas análises, as inconsistências entre o Gemini e o Ollama e
por que o AL-IAdo não gravou o nome do pesquisador. O diagnóstico completo está na
[revisão de 27/10](../revisao/2026-10-27-pendencias-provedores-nome.md).

**As decisões do pesquisador, na mesma conversa:**
- o nome que faltou é no AL-IAdo, e ele deve **perguntar o nome uma única vez**;
- primeiro os arquivos de orientação do assistente (lote 71, sem spec de produto), depois o código, no mesmo pedido.

**O diagnóstico do nome:** nas 20 conversas guardadas, o nome nunca foi dito; em duas, o pesquisador perguntou qual
era. O NUC-05 (lote 67) proíbe o agente de pedir o nome, e a memória não tinha anotação dele. Além disso, quando o
revisor de memória falhava, a tela não avisava: o evento ia sem o id da mensagem, e a tela ignorava o aviso.

## O que muda

- **O nome (NUC-06, novo; NUC-05, alterado):** sem uma anotação de perfil com o nome, a primeira resposta concluída
  termina com a frase fixa "Ainda não sei seu nome: como prefere ser chamado?". Quem pergunta é o app, sem chamada a
  mais ao modelo; o agente continua sem pedir o nome. Um arquivo `nome-perguntado` na pasta da memória impede que a
  pergunta volte. A resposta aciona o revisor, que a recebe junto da pergunta e anota o perfil.
  - A resposta à pergunta (só o nome, ou uma frase que diz o nome) vai como conversa, sem a biblioteca e com o modelo
    mais barato; uma pergunta, uma reclamação ou um "Continue" seguem o roteador. Sem isso, o roteador a
    tratava como continuação e mandava aos trechos com o Flash, e o Flash podia refazer, pago, um "Prazer, Rodolfo"
    que não citou nada.
  - Se a resposta com o nome não chegar à memória, a pergunta volta uma vez: com o revisor falhando, a tela diz que o
    nome não foi anotado; com a resposta fora do contexto, a pergunta só volta. Uma mensagem que ignorou a pergunta não
    a traz de volta. A memória de conversas e o revisor recebem a resposta sem a pergunta.
  - A anotação de perfil sobre outra pessoa ("A orientadora do usuário se chama Ana.") não conta como o nome.
  - O filtro do revisor também reconhece "anotar/guardar/gravar/salvar meu nome", que antes caía no "pode" de uma
    consulta ("Pode anotar meu nome?").
  - A falha do revisor aparece na tela (PRV-07): o evento leva o id da mensagem, e a tela mostra o aviso.
- **As fichas sem raciocínio (PRV-07, alterado):** a ficha de leitura da memória e a ficha do documento vão com
  raciocínio baixo, como o revisor desde o lote 70; a saída cortada é um erro, em vez de uma ficha vazia.
  - **O uso da saída cortada:** o erro leva o resultado, e o app registra o uso antes de mostrar a falha. Isso vale
    também para o revisor, que, desde o lote 70, deixava a chamada cortada fora do registro.
- **Sem internet (PRV-08, alterado):**
  - apagar os arquivos enviados ao serviço de arquivos do Google é recusado: a rota chamava o Google sem passar pela
    checagem de rede;
  - no modo forçado, a recusa vem antes de conferir a chave e os modelos do Gemini. Desde o lote 68, quem forçava o
    modo sem ter o Flash configurado via "Configure a chave do Gemini", em vez do motivo.
- **A reescrita local fora do teto (PRV-05, alterado):** os tokens da reescrita feita pelo local não descontam mais
  do teto de 30 mil da segunda leitura.
- **Sem requisito novo:**
  - o terminal dá a dica conforme o motivo: tirar `AL_IADO_OFFLINE` só no modo forçado; sem rede, conferir a conexão;
  - o streaming do Gemini com saída estruturada passa o uso e o corte, como o local (nenhum chamador usa esse caminho
    hoje);
  - o `.env.example` documenta `AL_IADO_OFFLINE`, `AL_IADO_FIGURE_MODEL` e `AL_IADO_EMBEDDINGS_DIR`.

## O que fica igual, de propósito

- As checagens `provider == "local"` do app: são dos avisos respondidos sem modelo, não do Ollama (spec 0038).
- A escalada sempre para o Flash, decidida no gateway, no agente e no app; a regra de sem internet escrita no gateway
  e no app; o local depender dos modelos do Gemini na tela; JSON inválido escalar no local e dar erro no Gemini; os
  provedores sem tempo limite próprio. Ficam na revisão de 27/10, para decisão.

## Requisitos vivos

- **NUC-06 (novo), em `nucleo.md`;** NUC-05 alterado para remeter a ele.
- **PRV-05, PRV-07 e PRV-08 (alterados), em `provedores.md`.**

## Aceitação

- **Os testes, sem o modelo:**
  - a pergunta do nome aparece uma vez, não volta em outra conversa, não aparece com o nome no perfil nem na
    mensagem que diz o nome, e a resposta a ela vai sem a biblioteca e chega ao revisor junto da pergunta;
  - a pergunta volta quando o revisor falha, e a chamada cortada entra no registro de uso;
  - o filtro com a resposta à pergunta e com "anotar meu nome";
  - o evento de falha do revisor com o id da mensagem;
  - as fichas com raciocínio baixo e a saída cortada como erro, com o resultado junto;
  - a exclusão dos arquivos do Google recusada sem internet;
  - o modo forçado recusando antes da configuração, e o sem rede ainda avisando que falta configurar;
  - a reescrita local fora do teto; a dica do terminal; o uso no streaming estruturado do Gemini.
- **Revisão independente:** um subagente só de leitura apontou 8 problemas; os 6 de código e os 2 de documentação
  foram corrigidos, com os testes acima. A segunda conferência achou a resposta ao nome reconhecida de jeitos
  diferentes em cada ponto: agora um só critério (`name_reply`) vale para a rota e para a volta da pergunta.
- **A bateria e o Ruff:** 881 testes passando (eram 862 no lote 70) e o Ruff sem apontamentos, em 27/10/2026.
- **No modelo real:** medido na rodada do lote 73, abaixo.

## A rodada no modelo local (lote 73, 28/10/2026)

Autorizada pelo pesquisador com teto de 45 chamadas locais ("Autorizo 45"): só o local, Gemini simulado, nenhum token
pago. Foram 38 chamadas locais e 1 ao Gemini simulado, em 8 minutos; pico da placa de 5.397 MiB. O método é o do lote 70
(um processo e uma memória nova por caso, servidor real, hora fixa, semente 70, temperatura 0,6). O script, os casos e
os resultados ficam em `tmp/lote-73/` (`medicao/resultado.json` e `medicao/comparacao.json`).

**O nome (dois casos novos, com a última mensagem numa conversa nova, para o nome vir da memória):**
- **C22:** "Olá, aliado." às 21h, depois "Rodolfo", depois, noutra conversa, "Como eu me chamo?".
  - A pergunta veio no fim da primeira resposta. "Rodolfo" foi tratado como conversa, sem a biblioteca e sem o Gemini.
  - O revisor anotou "O usuário se chama Rodolfo." O turno levou 36 s, com o revisor.
  - Na conversa nova, a resposta foi "Seu nome é Rodolfo.", em 1 s, e a pergunta não voltou.
  - Falhou o cumprimento: "Bom dia, aliado." às 21h, com "aliado" como se fosse o nome do usuário, e "Bom dia, Rodolfo"
    na resposta seguinte.
- **C23:** "Bom dia!", depois "Pode me chamar de Rô.", depois, noutra conversa, "Qual é o meu nome?".
  - A pergunta, a rota de conversa e a anotação "O usuário prefere ser chamado de Rô." saíram certas.
  - Na conversa nova, o local respondeu que não tinha o nome nas anotações. A anotação estava ativa e foi no pedido: o
    local não leu "prefere ser chamado de" como o nome. **Achado novo**, ainda sem correção.

**As fichas (dois artigos da cópia da biblioteca, pelos construtores do servidor):**

| | Golnas, 2012 (6 páginas) | Formica e outros, 2017 (8 páginas) |
|---|---|---|
| Ficha do documento | no local, 8 s, 76 tokens de saída, sem corte; igual à anterior (só o apóstrofo do título muda) | no local, 9 s, 104 tokens, sem corte; igual à anterior |
| Ficha de leitura | no local, 27 s, 516 tokens, sem corte; resumo e 8 fatos, todos com página | no local, 34 s, 555 tokens, sem corte; resumo e 8 fatos, todos com página |

Com o raciocínio baixo, nenhuma das quatro fichas ficou perto do teto de saída (512 e 2.048 tokens). Gastar o teto
pensando foi o defeito que o lote 70 mediu no revisor e que o lote 72 corrigiu nas fichas, sem medi-lo nelas antes.

**A conversa (os 21 casos do lote 70, com a pergunta do nome já feita):**

| | Lote 70 (24/10) | Lote 73 (28/10) |
|---|---|---|
| Conferências que passaram | 30 de 35 | 32 de 35 |
| Casos sem falha | 16 de 21 | 18 de 21 |
| Cumprimento ou data sem o usuário pedir | 1 (C12) | nenhum |
| Mensagens com erro | 1 (C15, esperado: web sem rede) | 3 (C15, esperado; C09 e C19: o Ollama parou) |
| Tempo mediano por mensagem | 7,0 s | 6,4 s |
| Refeitas pelo Gemini simulado | 2 | 1 |

- **Passaram agora:**
  - C01 e C02, os cumprimentos à noite;
  - C11, a continuação de assunto;
  - C17, a tradução no sentido certo.
- **Falharam agora: C09 ("Que horas são?") e C19 ("Quanto é 17 × 23?").** Não foram respostas erradas: o Ollama
  parou no meio ("model runner has unexpectedly stopped", erro 500). O app mostrou o erro claro, sem chamar o Gemini.
- **C21 continua falhando:** "Tchau, até amanhã!" às 23h recebeu "Bom dia! Boa noite para o próximo dia."
- **Não é efeito do lote 72.** O `agent.py` e o `routing.py` não mudam desde 24/10, antes da rodada do lote 70, e esses
  casos não recebem a pergunta do nome. As diferenças são variação do modelo:
  - mesmo com a semente fixa, "Olá, aliado." deu "boa noite" às 21h05 (C01) e "bom dia" às 21h (C22);
  - o Ollama se atualizou sozinho em 25/10 (agora 0.40.11), depois do lote 70.

  As duas paradas podem vir da atualização. Desde ela, o Ollama não grava mais o registro na pasta de antes, e a causa
  não foi achada.
