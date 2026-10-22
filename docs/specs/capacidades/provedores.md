# Capacidade: provedores de modelo

Spec viva: diz o que vale **hoje** para a escolha de quem responde, entre o modelo local e os modelos pagos. Um lote
que mudar esta capacidade atualiza este arquivo e cita na própria spec de mudança os requisitos que acrescenta,
altera ou retira. Cada requisito é citado por pelo menos um teste (`tests/test_specs.py`).

Criada no lote 38 (18/10/2026), pela [spec 0038](../0038-modelo-local.md). O lote 39, pela
[spec 0039](../0039-local-le-texto.md), alterou o PRV-01 e o PRV-03 e acrescentou o PRV-06. O uso do Gemini e as
chaves seguem descritos nas specs 0009 e 0012; o roteador, o teto de 30 mil e o aviso de 300 mil tokens, em
[roteador.md](roteador.md). O lote 44 amplia os cenários de PRV-02, sem alterar os limites de custo. O lote 46, pela
[spec 0046](../0046-correcoes-do-relatorio.md), altera PRV-02, PRV-06 e PRV-07; o lote 48, pela
[spec 0048](../0048-raciocinio-nas-paginas.md), altera o PRV-07.

## Requisitos

**PRV-01. O modelo local responde primeiro.** Com `AL_IADO_LOCAL_MODEL` no .env, todo pedido vai primeiro ao modelo
local, servido pelo Ollama neste computador: a conversa, a reescrita da busca, o revisor de memória, as fichas e a
descrição das figuras. As imagens vão como imagem, e as páginas de PDF, como o texto guardado delas (PRV-06). Sem a
variável, tudo segue pelo Gemini, como antes.
*Cenário:* dado o modelo local ligado, quando chega uma pergunta que cabe nele, então ele responde, a tela mostra o
nome dele e o Gemini não é chamado; sem a variável, responde o Gemini.

**PRV-02. Escalada no limite do raciocínio.** O Gemini Flash só entra quando o modelo local não dá conta do
raciocínio: ele responde "[ESCALAR]" (no começo, depois de um rótulo ou em qualquer ponto da resposta), a saída
estruturada vem inválida ou a resposta vem vazia; na conversa, também quando a resposta do local não cita o que a
busca trouxe, cita o que não foi enviado ou traz números que não conferem com os resultados. A troca acontece uma
vez, antes de a resposta aparecer na tela; se ela já começou, o aviso "O modelo local não chegou lá" apaga o texto
parcial. A linha da rota diz o motivo. Resposta cortada no teto de saída não escala: é limite de tamanho, não de
raciocínio.
Na primeira marca de citação que a conferência reprovaria (BIB-05), o local para de escrever: a conversa fecha o
fluxo, o Ollama deixa de gerar o resto, e o Flash refaz sem esperar o fim do texto (lote 46). A tentativa
interrompida fica no registro de uso sem a contagem de tokens.
A escolha escrita do modelo menor vale antes da escalada: a repetição usa o Flash. Se ele não estiver configurado
ou falhar ao refazer uma resposta local completa reprovada pela conferência do chat, essa resposta é mantida
com os avisos e o motivo na rota, sem nova tentativa automática (lote 44).
*Cenário:* dada uma pergunta à biblioteca com o modelo menor escolhido, quando o local responde sem citar os trechos
enviados, então a pergunta é refeita uma vez pelo Gemini Flash, e a rota diz quem respondeu. Sem Flash ou na falha
dele ao refazer essa resposta completa, ela permanece e o motivo é mostrado. No pedido de ajuda detectado
antes da resposta completa pelo gateway, uma falha do Flash sobe como erro; não há resposta local para manter.

**PRV-03. O que o local não alcança vai direto ao modelo pedido.** A busca na web e um pedido maior que o contexto
local (`AL_IADO_LOCAL_CONTEXT`, padrão 16.384 tokens) não passam pelo modelo local: vão direto ao modelo que o
roteador escolheu, e a linha da rota diz por quê. Não é escalada. As páginas de PDF da leitura não ficam de fora:
vão como texto (PRV-06). Só um PDF sem o texto das páginas, que vai como imagem, fica de fora acima de 4 páginas.
*Cenário:* dado um pedido com busca na web, quando ele é enviado, então o Ollama não é chamado e a rota diz "o
modelo local não alcança este pedido (busca na web)".

**PRV-04. Ollama fora do ar: erro claro, sem gastar.** Com o Ollama fechado, o modelo do .env não baixado ou outra
falha técnica do local, a tela e o terminal dizem o que conferir, e nada vai ao Gemini.
*Cenário:* dado o Ollama fechado, quando chega uma pergunta, então a tela mostra "O modelo local não respondeu…:
abra o Ollama…", a pergunta não é refeita por outro modelo e o registro de uso não ganha linha do Gemini.

**PRV-05. O local não conta no uso pago.** As chamadas ao modelo local ficam no registro de uso, com o provedor
`ollama`, mas não entram no "hoje", no total, no teto de 30 mil nem no aviso diário de 300 mil tokens; na resposta,
os tokens dele aparecem como "tokens locais".
*Cenário:* dada uma resposta do local refeita pelo Gemini, quando a tela mostra o uso do dia, então ele soma só os
tokens do Gemini.

**PRV-06. O local lê as páginas pelo texto guardado.** Na leitura das páginas inteiras, do documento citado ou de
uma trilha, cada parte em PDF leva também o texto guardado das suas páginas (nativo ou por OCR), com o [K...] de
cada uma. Leva ainda a descrição automática das figuras e tabelas da página, quando houver, marcada para conferir no
original.
- **O local:** lê esse texto, sem abrir o PDF e sem limite de páginas; vale o contexto dele. Recebe também uma nota
  de que os PDFs vieram como texto e, quando o pedido traz fontes citáveis, a regra de citar cada afirmação com o
  identificador copiado letra por letra, sem encurtar, sem acrescentar a página e sem juntar dois. A nota e a regra
  não mostram nenhum identificador de exemplo: no lote 45, o local copiou os exemplos nas 4 respostas descartadas.
- **O Gemini:** segue recebendo o PDF e a lista das páginas, como antes, sem tokens a mais.

*Cenário:* dada uma pergunta sobre uma tabela que pede as páginas inteiras, quando o local responde, então ele
recebe o texto e a descrição das 10 páginas, o PDF não é aberto, e a pergunta não vai ao Gemini por ter mais de 4
páginas.

**PRV-07. Sem raciocínio na reescrita da busca e na leitura de páginas.**
- **A reescrita:** vai com raciocínio baixo, no local e no Gemini, porque é uma tarefa mecânica. Com raciocínio, o
  local gastava os 2.048 tokens dela pensando, cerca de 2 minutos, e a reescrita falhava em silêncio.
- **Simples ou por partes:** a reescrita simples pede só a consulta, com até 512 tokens. O plano por partes, com até
  2.048, só vem quando o pedido tem partes. Até o lote 46, o pedido do plano chegava duas vezes à função, o erro era
  calado, e as perguntas com partes seguiam sem a reescrita.
- **As respostas:** os trechos e a conversa seguem com o raciocínio que o roteador decidir. No lote 41, os trechos
  sem raciocínio fizeram o local deixar de citar, e essa parte foi desfeita.
- **A leitura de páginas inteiras ou do documento:** vai sem raciocínio no local (lote 48). Medido com o critério
  fixado antes: a chamada mediana caiu de 133 para 71 s, e 11 das 12 respostas citaram certo. O Gemini segue como
  antes.
- **A segurança da resposta não muda:** a resposta sem citação, com números que não conferem ou com o pedido de ajuda
  é refeita pelo Gemini (PRV-02).

*Cenário:* dada uma pergunta que precisa de reescrita, quando a busca é preparada, então a reescrita sai em segundos,
sem raciocínio, e a resposta é escrita com o raciocínio que o roteador pediu. Dada uma pergunta com partes, então o
plano é pedido uma vez, e a pergunta sem partes pede só a consulta. Dada uma pergunta que lê páginas inteiras ou o
documento, então o local responde sem raciocínio; com trechos, com o raciocínio do roteador.
