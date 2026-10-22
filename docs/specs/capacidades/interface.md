# Capacidade: interface

Spec viva criada no lote 44 (20/10/2026), pela [spec 0044](../0044-revisao-fechamento.md). Começa pelo vínculo dos
anexos à conversa; os demais comportamentos continuam descritos nas specs de lote anteriores.
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
