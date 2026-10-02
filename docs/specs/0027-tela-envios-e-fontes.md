# Lote 27 — tela inicial, pop-up de envios e respostas com várias fontes

Lote autorizado em 01/10/2026, depois da 0.3.0 (`ae24885`). Parte de três apontamentos do pesquisador no uso real:
1. ao abrir de novo ou recarregar, a página voltava para a última conversa, e não para a tela de apresentação;
2. faltava um aviso com o avanço dos documentos enviados e indexados;
3. ele pediu o conceito de MCC (Manutenção Centrada na Confiabilidade) e só recebeu a definição por fonte na quarta pergunta.

## O que a investigação mostrou

- **Tela inicial:** a página guardava o identificador da última conversa no navegador e a reabria.
- **Envios:**
  - os cartões de progresso ficavam dentro do chat; um envio pela aba Biblioteca não mostrava nada;
  - o servidor informava a leitura por página, o reconhecimento de texto e o começo da indexação, mas não o avanço dentro dela;
  - a tarefa só terminava depois das duas fichas (chamadas ao modelo), embora o documento já pudesse ser buscado antes.
- **Caso da MCC, refeito com a consulta guardada:**
  - em 30/09, a busca falhou, e a consulta reescrita do lote 22 já tinha corrigido isso;
  - em 01/10, os 10 trechos da primeira pergunta traziam definição de 4 documentos, todos foram ao modelo, e a resposta usou um;
  - não houve falha do provedor. A regra pedia a opção de cada fonte, mas a pergunta dizia "uma literatura ao menos", e nada conferia o resultado;
  - os trechos têm cerca de 68 palavras, e o da NASA terminava no meio da frase.

## Decisões do pesquisador (01/10)

| Tema | Decisão |
|---|---|
| Escopo | A tela inicial, o pop-up de envios e as três correções das respostas com várias fontes. |
| Medição | Uma bateria paga de cerca de 100 chamadas, antes e depois da correção. |
| Troca de dataset | Era só uma pergunta: não entra em lote nem em registro. |

**Decisões de 02/10,** depois da revisão e da bateria:

| Tema | Decisão |
|---|---|
| Regra das respostas | Ajustar a frase que fazia o modelo maior comentar documentos fora do assunto e medir de novo, só nele. |
| Posição do aviso de envios | Canto inferior direito, na aba Biblioteca e no chat, sem cobrir nenhum botão. |
| Commit e limpeza | Commit do lote depois da regra ajustada; a pasta de teste é apagada no fim. |

## Escopo implementado

### Tela inicial

- A página abre sempre na tela de apresentação. A última conversa não fica mais guardada no navegador e continua na lista, a um clique.

### Pop-up de envios

- **Na página:** um aviso fixo no canto inferior direito, visível nas quatro abas. Ele substitui os cartões e o contador que ficavam no chat.
  - No chat, fica logo acima da caixa de mensagem. Enquanto ele está à vista, a área da aba termina acima dele: a faixa do aviso fica reservada, e ele não cobre botão, link nem campo.
  - Com um documento: o nome, a etapa em palavras e a barra.
  - Com vários: "Documentos: X de N prontos · K com falha", a barra geral e o documento atual. O atual muda quando a indexação dele termina.
  - Etapas: lendo a página, reconhecendo o texto da página, indexando os trechos, criando a ficha do documento e criando a ficha de leitura.
  - Tudo certo some em 6 s. Falhas e documentos indexados só em parte ficam até serem fechados, reaparecem mesmo com o aviso escondido ou recolhido, e continuam à vista quando um lote novo começa.
  - Recolher deixa uma linha; fechar só esconde, sem cancelar o envio.
  - Ao recarregar com envios em andamento, o aviso volta com os totais do lote.
  - Soltar um arquivo em qualquer aba envia sem trocar de tela.
- **No servidor:**
  - o documento fica pronto quando a indexação termina. As fichas viram uma segunda etapa na mesma fila: os arquivos que o servidor já recebeu são indexados antes de qualquer ficha, e a página envia até três de cada vez para o lote chegar junto;
  - a indexação avisa o progresso a cada 32 trechos. O tamanho da fatia é múltiplo do lote interno do encoder, o que mantém os vetores idênticos;
  - a rota `GET /api/biblioteca/tarefas` lista os envios do lote mais recente;
  - a tarefa termina sempre, mesmo com erro inesperado na leitura ou nas fichas, e um erro de arquivo chega à tela em palavras;
  - "Completar fichas" reconfere cada título antes de chamar o modelo.

### Respostas com várias fontes

- **Regra reescrita:** em pedidos de definição, conceito ou valor, a resposta apresenta o que cada documento recuperado diz, cada um com a referência e a citação.
  - "Uma fonte", "ao menos uma" ou "outra fonte" é o mínimo, não o limite.
  - Documento cujo trecho não trata do pedido não é mencionado, comentado nem citado, nem em nota no fim: a janela de fontes já mostra o que a busca trouxe e a resposta não usou. Se só um tratar, a resposta diz que foi o único.
  - Essa frase foi ajustada em 02/10. A primeira versão ("deixe de fora o documento cujo trecho não trata do pedido") fazia o modelo maior comentar esses documentos em 13 de 21 respostas; com a frase ajustada, em nenhuma.
  - Citação direta: entre aspas, no idioma original; a tradução vem identificada como tradução.
- **Trechos agrupados por documento:** o pedido leva os trechos por documento, e o cabeçalho diz quantos trechos e quantos documentos distintos a busca trouxe.
- **Passagem com os vizinhos:** cada trecho vai ao modelo unido ao anterior e ao seguinte da mesma página, sem repetir a parte comum.
  - A ordem é a de gravação dos trechos; não foi preciso reprocessar documentos nem mudar o banco.
  - O trecho indexado continua guardado como a busca o achou.
  - A união só acontece quando o encaixe é seguro: com um encaixe possível, une; com dois (prosa em que a parte comum começa e termina com o mesmo termo), vale o maior, se a divisão que criou os trechos devolver os dois a partir da união; com três ou mais (texto repetitivo), não une.
  - Numa página com texto repetido na extração, o trecho que já vai inteiro em outra passagem não é ampliado.
- **O que a busca trouxe e a resposta não citou:** fica guardado com a resposta.
  - A linha da resposta mostra, por exemplo, "citou 2 dos 6 documentos que a busca trouxe".
  - A janela de fontes ganha o grupo "A busca também trouxe", com a referência, a página e a passagem.

### Resposta cortada e conferência dos números

- **Teto de tamanho:** o raciocínio do modelo conta no teto de saída. Ele passou de 4.096 para 8.192 tokens, e a resposta que ainda assim for cortada aparece com aviso e fica fora do histórico.
- **Conferência dos números (lote 26):** as respostas por documento trazem referências, itens de norma e traduções. A conferência passou a reconhecê-los, para não avisar de "números sem marca" numa resposta que só cita documentos. No trecho fechado por uma marca de resultado, "Nome, ano" só é referência entre parênteses.

## Limites assumidos

- O avanço geral do pop-up é uma estimativa: metade de cada documento para a leitura e metade para a indexação.
- Arquivos que ainda não tinham sido enviados ao servidor se perdem se a página for recarregada no meio do envio.
- Uma definição que atravessa a quebra de página não é completada.
- A passagem ampliada acrescenta cerca de 2 mil tokens de entrada por pergunta com a biblioteca.
- A contagem "citou X dos Y documentos" inclui documentos que a busca trouxe e que não tratam do assunto.
- A regra orienta o modelo, mas não o obriga: a janela de fontes mostra o que ficou de fora.
- Enquanto o aviso de envios está à vista, a aba perde a altura dele. Com uma falha listada em tela estreita, isso chega a cerca de um terço da tela; recolher o aviso o deixa com uma linha.
- Um arquivo muito grande, enviado junto com um muito pequeno, pode ser indexado depois das fichas do pequeno.
- A marca de resposta cortada só é preenchida para o Gemini.

## Fora do escopo

- Escolher os trechos pelo tipo de pedido e reconhecer NASA e IEEE como documento citado.
- Mudar o texto da consulta reescrita e limpar cabeçalhos repetidos dos documentos.
- Trocar o dataset do experimento pela interface.

## Critérios de aceitação

- **Testes sem rede:**
  - a união de trechos tira só a parte repetida, e a passagem é um pedaço exato da página;
  - um vizinho nunca é usado duas vezes, e documentos apagados ou com versão nova não quebram a ordem;
  - a indexação em fatias dá os mesmos vetores e avisa o progresso a cada fatia;
  - os trechos vão agrupados, com a contagem, e a regra pede cada documento e a citação no original;
  - os trechos não citados são guardados, também na resposta sem citação;
  - o documento fica pronto antes das fichas, os envios em fila são indexados antes das fichas, a lista traz só o lote atual, e a tarefa termina mesmo se a ficha falhar;
  - a página abre na apresentação e tem o pop-up.
- **No navegador:** recarregar e abrir uma segunda aba, um PDF pela aba Biblioteca, vários arquivos com um inválido, recarregar no meio do lote, um PDF digitalizado, a janela de fontes, a tela de 360 px e o console sem erros.
- **Revisão por agentes**, com verificação adversarial de cada defeito, e conferência das correções.
- **Bateria paga**, antes e depois, com os números na validação, e complemento para as perguntas cujo pedido mudar depois da revisão.
- **Regra ajustada (02/10):** nova rodada paga só no modelo maior, com os pedidos conferidos contra o código final.
- **Posição do aviso (02/10):** nas quatro abas, a 1.280 e a 360 px, aberto e recolhido, nenhum botão, link, campo ou item de lista fica embaixo do aviso.
