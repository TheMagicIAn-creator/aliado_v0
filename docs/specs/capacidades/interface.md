# Capacidade: interface

Spec viva criada no lote 44 (20/10/2026), pela [spec 0044](../0044-revisao-fechamento.md). Começa pelo vínculo dos
anexos à conversa; os demais comportamentos continuam descritos nas specs de lote anteriores. O lote 63, pela
[spec 0063](../0063-sem-internet.md), acrescenta o INT-02; o lote 68, pela [spec 0068](../0068-internet-automatica.md),
altera o INT-02.
Cada requisito é citado por pelo menos um teste (`tests/test_specs.py`).

## Requisitos

**INT-01. O anexo fica na conversa do envio.** Ao anexar na apresentação, a interface cria uma conversa e compartilha
essa criação com a primeira pergunta. Ambas usam o identificador retornado pelo servidor. O servidor fixa o documento
nessa conversa quando a leitura termina, mesmo após troca de conversa ou recarregamento. Uma criação pendente,
resposta de fixação ou mensagem atrasada não substitui a conversa escolhida depois. Navegar interrompe uma pergunta
que ainda espera a criação; o anexo continua destinado à conversa original. Uma falha permite nova tentativa.
Se a conversa foi apagada, o documento permanece apenas na biblioteca; envios pelo painel não fixam documentos.
*Cenário:* dada a apresentação sem conversa, quando o pesquisador anexa um documento e envia uma pergunta antes de
a criação terminar, então é criada uma única conversa, usada pelo envio e pela pergunta; ao terminar a leitura,
o documento fica fixado nela. Se ele abrir outra conversa durante a espera, o anexo mantém o destino original e
a resposta atrasada não muda a conversa aberta.

**INT-02. Sem internet: selo e recusa com o motivo.** No modo sem internet (PRV-08, PRV-09), um selo "Sem internet" fica no
topo da tela, com a nota de que só o modelo local responde. A busca na web, a leitura ampla e a conferência de uma
anotação na web são recusadas antes de qualquer chamada. Quando o gateway recusa, a tela diz o motivo e o que fazer
(pedir só os trechos e, no modo forçado, tirar `AL_IADO_OFFLINE` do .env e reiniciar; sem rede, esperar a internet
voltar), e a pergunta não fica na conversa. A resposta
completa do local que a conferência mandaria refazer fica, com "modo sem internet" na rota (lote 63). Sem rede, o selo
aparece e some sozinho, conferido a cada resposta e a cada minuto (lote 68).
*Cenário:* dado o modo sem internet, quando o pesquisador pede a busca na web, então a tela recusa na hora e nada é
chamado; quando uma pergunta passa do contexto local, então a tela diz "Sem internet: esta pergunta precisa do
Gemini (…)".
