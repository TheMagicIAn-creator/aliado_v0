# Validação do lote 27 — tela inicial, pop-up de envios e respostas com várias fontes

Verificação local em **01 e 02/10/2026**, sobre o commit `ae24885` (lote 26, versão 0.3.0). Houve **132 chamadas
pagas**, todas autorizadas: 129 na bateria (100 na medição, 8 no complemento e 21 na regra ajustada) e 3 na
conferência final no navegador. O assistente não fez push nem tag.

## Testes

32 testes novos:
- **`tests/test_passages.py`, 18 testes:**
  - a união de dois trechos tira só a parte repetida;
  - com dois encaixes possíveis, vale o maior, e só se a divisão da união devolver os dois trechos; com três ou mais, os trechos não são unidos;
  - a passagem é um pedaço exato da seção e não passa para outra seção nem para outra versão do documento;
  - um vizinho nunca é usado duas vezes, e o trecho que já vai inteiro em outra passagem da mesma página não é ampliado;
  - documentos apagados, versões novas e trechos desconhecidos não quebram a ordem;
  - a indexação avisa o progresso a cada 32 trechos, e as fatias dão os mesmos vetores de uma chamada só (com o encoder real);
  - os trechos vão agrupados por documento, com a contagem no cabeçalho e os campos que as regras citam;
  - os trechos não citados voltam com a resposta, também quando ela é barrada por uma marca de resultado inexistente;
  - o teto de saída é de 8.192 tokens, e a resposta cortada sai marcada, mesmo cortada antes de qualquer texto.
- **`tests/test_web.py`, 12 testes:**
  - o documento fica pronto antes das fichas, e os envios já recebidos são indexados antes de qualquer ficha;
  - a lista de envios traz só o lote atual, sem tarefas de outras abas nem caminhos;
  - a tarefa termina com falha num erro inesperado da leitura e termina normalmente se as fichas falharem, também em "Completar fichas";
  - um erro de arquivo chega à tela em palavras, sem código do sistema nem caminho de pasta;
  - o reenvio de um documento indexado só em parte volta como "já estava na biblioteca";
  - a resposta cortada fica marcada e fora do histórico;
  - a resposta guarda o que a busca trouxe e não foi citado;
  - a página abre na apresentação e tem o pop-up, com uma trava de texto para cada correção da tela, a posição do aviso e a faixa reservada para ele.
- **Outros:** o provedor avisa o corte pelo teto de tokens, e o comando `perguntar` mostra o aviso.
- **Testes ajustados:** o texto da regra, o formato dos trechos no pedido e as formas de referência na conferência dos números.

**480 testes passaram** (448 do lote 26 e 32 novos), no Python 3.12.14. O Ruff não apontou problemas, e
`app.js`, `ciencia.js` e `graficos.js` passaram na checagem de sintaxe. A suíte foi refeita em 02/10, depois da
regra ajustada e da nova posição do aviso, com o mesmo resultado.

## Revisão por agentes

A primeira tentativa parou no limite de uso, com uma das cinco frentes concluída. Ela foi retomada em 02/10
e terminou. Foram três rodadas, sempre com um verificador cético para cada defeito apontado.

| Rodada | Frentes | Confirmados | Refutados |
|---|---|---:|---:|
| 1 | passagens | 2 | 0 |
| 2 | envios no servidor, envios na tela, passagens, pedido e citações, janela de fontes e testes | 23 (20 distintos) | 0 |
| 3 | conferência das correções: tela, servidor e pedido, testes | 12 | 0 |

**O que mudou por causa da revisão:**
- **Resposta cortada pelo teto de tamanho.** O raciocínio do modelo conta no teto de saída, e 4.096 tokens cortaram uma resposta da bateria no meio da frase. O teto passou a 8.192; a resposta cortada aparece com aviso e fica fora do histórico.
- **União de trechos.** Em texto repetitivo (pontilhado de sumário, células iguais de tabela), a união cortava repetições. Com três ou mais encaixes possíveis, os trechos não são mais unidos; com dois, vale o maior, se a divisão confirmar.
- **Página com texto repetido na extração.** O mesmo parágrafo ia duas vezes ao modelo. O trecho que já vai inteiro em outra passagem da mesma página não é mais ampliado.
- **Conferência dos números.** O formato por documento gerava o aviso falso de "números sem marca" em 12 das 42 respostas da bateria. A conferência passou a reconhecer a referência no título, "(2017, p. 2)", "item 2.2.1", normas militares, os números de referência do texto citado e a linha de tradução. No trecho fechado por uma marca de resultado, "Nome, ano" só é referência entre parênteses.
- **Envios.** Arquivos enviados três de cada vez, para o lote entrar na fila antes das fichas do primeiro; falha que reaparece e expande o aviso mesmo fechado ou recolhido; avisos do lote anterior mantidos; aviso das fichas que não puderam ser criadas; foco do teclado preservado; "Completar fichas" que termina sempre; erro de arquivo em palavras.
- **Janela de fontes.** O link abre no grupo dos trechos não citados; cada trecho mostra que abre ao clicar e o começo do texto; os trechos abertos não fecham quando a memória é revisada; as quebras de linha do PDF viram espaço.

**Decidido pelo pesquisador em 02/10:** a revisão apontou que o aviso, no canto superior direito, podia cobrir
os links do documento aberto na aba Biblioteca. Ele passou para o canto inferior direito, nessa aba e no chat,
com a faixa dele reservada (veja "Posição do aviso" abaixo).

**Sem verificação adversarial:** 8 apontamentos de gravidade baixa da rodada 2. Cinco foram corrigidos mesmo
assim; ficaram três: o aviso de dois lotes em duas abas ao recarregar, o texto enviado ao revisor de memória
(o trecho, e não a passagem) e parte das lacunas de teste.

**Conferência no catálogo real, só leitura,** depois das correções:
- todos os 13.852 trechos: a passagem ampliada contém o trecho e é um pedaço exato do texto da página, sem exceção;
- 36 buscas reais (360 trechos): ampliar os 10 trechos de uma busca leva 3 ms (mediana), contra cerca de 2,7 s da própria busca;
- dos 89 pares de trechos vizinhos com mais de um encaixe possível, 24 são unidos com segurança e 65 ficam sem união.

## Bateria paga

**Como foi feita:**
- **Perguntas:** 14 pedidos de conceito ou definição (MCC, confiabilidade, disponibilidade, taxa de falha, MTBF, MTTR, MTTF, FMEA, FMECA, NPR, curva da banheira, Weibull, manutenção preventiva e Isolation Forest), 2 controles com poucas fontes e o seu caso real, com o histórico da conversa.
- **Condições:** antes e depois da correção, no Flash e no Flash-Lite. Quatro perguntas rodaram duas vezes.
- **Mesma busca:** as consultas foram reescritas uma vez, e os trechos recuperados foram conferidos pelo identificador nas duas condições.
- **Marcação cega:** dois agentes independentes, sem ver as respostas, marcaram quais dos 100 documentos recuperados tratam de cada pedido, e um terceiro decidiu o único desacordo. Tratam do pedido 51 documentos só com o trecho e 57 com a passagem ampliada.
- **Como no chat de hoje:** a skill do mestrado, a biblioteca e os resultados ligados, sem memória e sem revisor.

**Complemento com o código final (02/10).** O pedido de cada pergunta foi refeito com o código final e comparado,
mensagem por mensagem, com o pedido medido:
- em 14 das 17 perguntas, o pedido é idêntico;
- em 3 (MTBF, MTTF e o controle de manutenção preditiva), uma passagem ficou menor, pelas correções da revisão. A marcação dos documentos continua valendo: o texto que a sustenta está nas passagens finais;
- uma resposta do Flash sobre NPR tinha sido cortada pelo teto de tamanho.

As 3 perguntas foram refeitas nos dois modelos, e a de NPR, duas vezes no Flash: 8 chamadas. A coluna "depois"
abaixo já traz essas respostas no lugar das antigas.

**Resultado nas 14 perguntas** (18 respostas por coluna):

| Medida | Flash, antes | Flash, depois | Flash-Lite, antes | Flash-Lite, depois |
|---|---:|---:|---:|---:|
| Documentos que tratam do pedido, citados, em média | 3,39 de 3,39 | 3,72 de 3,72 | 2,44 de 3,39 | 2,72 de 3,72 |
| Cobertura dos documentos que tratam | 100% | 100% | 77% | 77% |
| Respostas com uma fonte só, havendo duas ou mais | 0 de 14 | 0 de 16 | 3 de 14 | 1 de 16 |
| Documentos citados que não tratam do pedido, em média | 0,72 | 1,28 | 0,44 | 0,17 |
| Citações diretas que conferem com a passagem | 18 de 19 | 86 de 95 | 0 de 3 | 10 de 16 |
| Respostas com citação inventada | 0 | 0 | 1 | 0 |
| Tokens de saída por resposta | 459 | 1.033 | 416 | 441 |

Notas da tabela:
- **Cobertura:** dos documentos recuperados que tratam do pedido, a fração que a resposta citou.
- **Citações diretas:** trechos entre aspas com 30 caracteres ou mais, seguidos da marca do documento. "Conferem" as iguais ao texto e as que diferem só por espaços ou por erro de leitura corrigido. As outras são traduções ou paráfrases entre aspas.
- **Antes do complemento,** a coluna "Flash, depois" tinha cobertura de 99% (3,67 de 3,72): a diferença era a resposta cortada.

**Seu caso real** (a primeira pergunta sobre MCC, com o histórico da conversa):

| Modelo | Antes | Depois |
|---|---|---|
| Flash-Lite | 1 dos 4 documentos que tratam (só o IEEE, como na sua conversa) | 2 dos 4 (IEEE e NASA, com a frase da NASA completa) |
| Flash | 4 dos 4 | 4 dos 4 |

**Controles** (pedidos com uma ou duas fontes): os dois modelos citaram todos os documentos que tratam, antes e
depois. No Flash, os documentos citados que não tratam do pedido foram de 2 para 2,5 por resposta; no
Flash-Lite, de 1 para 0,5.

**Leitura dos números:**
- **O modelo pesa mais que a regra.** O Flash já citava todos os documentos que tratam do pedido antes da correção. O Flash-Lite cita cerca de três quartos, antes e depois.
- **O que melhorou no Flash-Lite:** menos respostas com uma fonte só (3 de 14 para 1 de 16), menos documentos fora do assunto e nenhuma citação inventada. No seu caso real, foi de 1 para 2 fontes.
- **O que melhorou nos dois:** as citações diretas passaram a vir no idioma original e conferem com a passagem. Antes, o Flash-Lite punha traduções entre aspas.
- **O que piorou no Flash:** as respostas ficaram com o dobro do tamanho, e em 13 das 21 há uma nota sobre os documentos que não tratam do pedido. A regra mandava deixar esses documentos de fora, e o Flash os comentava. A regra ajustada, abaixo, tratou disso.
- **Uma rodada por pergunta** (duas em quatro delas): diferenças pequenas podem ser acaso.

### Regra ajustada (02/10)

Por decisão do pesquisador, a frase "deixe de fora o documento cujo trecho não trata do pedido" virou "não
mencione, não comente e não cite os documentos cujos trechos não tratam do pedido, nem em nota no fim". As 17
perguntas foram refeitas só no Flash (21 chamadas, com as mesmas 4 repetições). Os 17 pedidos do código final
são idênticos, mensagem por mensagem, aos dessa rodada.

**Flash nas 14 perguntas** (18 respostas por coluna):

| Medida | Regra medida | Regra ajustada |
|---|---:|---:|
| Documentos que tratam do pedido, citados, em média | 3,72 de 3,72 | 3,67 de 3,72 |
| Cobertura dos documentos que tratam | 100% | 98% |
| Respostas com uma fonte só, havendo duas ou mais | 0 de 16 | 0 de 16 |
| Documentos citados que não tratam do pedido, em média | 1,28 | 0,56 |
| Citações diretas que conferem com a passagem | 86 de 95 | 83 de 85 |
| Respostas com citação inventada | 0 | 0 |
| Tokens de saída por resposta | 1.033 | 879 |

**Nas 21 respostas do Flash** (14 perguntas, 2 controles e o caso real):

| Medida | Regra medida | Regra ajustada |
|---|---:|---:|
| Respostas com nota sobre documentos que não tratam do pedido | 13 | 0 |
| Palavras por resposta, em média | 561 | 487 |

Notas:
- **Nota sobre documentos de fora:** contada por busca de expressões ("não trata", "os demais documentos", "ficou de fora"…) e conferida lendo, na rodada ajustada, as linhas que falam da busca: todas são a abertura da resposta.
- **Cobertura de 98%:** numa das duas respostas sobre taxa de falha, o Flash citou 2 dos 3 documentos que tratam do pedido, numa resposta curta. Na repetição da mesma pergunta, citou os 3. É uma resposta em 18.
- **Controles:** os documentos citados que não tratam do pedido foram de 2,5 para 1 por resposta, e a saída, de 786 para 588 tokens.
- **Caso real:** 4 dos 4 documentos, como antes.
- **O Flash-Lite não foi medido de novo.** Ele já citava menos documentos fora do assunto (0,17 por resposta) e não fazia a nota.
- **Uma rodada por pergunta:** a queda das notas (13 para 0) é clara; a diferença de cobertura (uma resposta) pode ser acaso.

**Avisos de número nas 113 respostas, com a conferência final:** nenhum aviso falso de "número sem marca". Um
aviso verdadeiro: o Flash-Lite somou 24 h e 120 h e escreveu 144 h com a marca de um resultado.

**Custo da bateria:** 129 chamadas, com 2.009.470 tokens de entrada (654.161 lidos do cache do provedor),
73.328 de saída e 119.562 de raciocínio. A rodada da regra ajustada respondeu por 379.786 de entrada, 17.903 de
saída e 50.693 de raciocínio. Cada resposta levou cerca de 17 a 19 mil tokens de entrada. A correção acrescentou
cerca de 0,8 mil por pergunta: as passagens ampliadas pesam mais, e o pedido agrupado repete menos.

**Desvios do plano:**
- 4 perguntas repetidas, em vez de 6, porque os 2 controles não estavam no orçamento;
- a marcação foi feita por dois agentes independentes e um juiz, e não só pelo assistente;
- o complemento de 8 chamadas e a rodada de 21 da regra ajustada, autorizados pelo pesquisador em 02/10, levaram o total a 132 chamadas pagas.

## Aceite no navegador

Servidor de teste em `127.0.0.1:8777`, com a interface, as rotas, a biblioteca e a busca reais, e o modelo e as
fichas simulados (sem custo). A conferência final usou o servidor real em `127.0.0.1:8776`, numa cópia da biblioteca.

| Item | Resultado |
|---|---|
| Tela inicial | Recarregar com uma conversa aberta e abrir uma segunda aba caem na apresentação. A conversa continua na lista. |
| Um PDF pela aba Biblioteca | O aviso mostra o nome, a etapa e a barra: indexando 32 de 81 trechos, pronto para buscar, as duas fichas e o resumo final. Some cerca de 6 s depois. |
| Vários arquivos e um tipo inválido | De "Documentos: 0 de 4 prontos" até "3 de 4 prontos · 1 com falha". O documento atual é o que está sendo indexado, e as fichas vêm depois de todos. O arquivo inválido gera só um aviso rápido. |
| Falha | O documento com defeito fica listado até ser fechado, e reaparece expandido mesmo com o aviso fechado e recolhido. A linha de falha continua à vista quando um lote novo começa. |
| Recarregar no meio do lote | O aviso volta com "1 de 3 prontos" e segue até o fim, com a página na apresentação. |
| PDF digitalizado | "Reconhecendo o texto da página 2 de 2". |
| Recolher, fechar e teclado | Recolhido, fica com uma linha e a barra. Fechar esconde sem cancelar. Ao fechar um aviso ou o pop-up, o foco vai para a caixa de mensagem ou para o botão da aba aberta. |
| Posição | Canto inferior direito, nas quatro abas; no chat, logo acima da caixa de mensagem. Veja "Posição do aviso" abaixo. |
| Janela de fontes | A resposta mostra "citou 1 dos 7 documentos que a busca trouxe". O link abre a janela no grupo "A busca também trouxe", e cada trecho mostra o começo do texto e abre ao clicar. |
| Tela de 360 px, temas claro e escuro | Sem rolagem lateral. O resumo com a contagem de falhas aparece inteiro. |
| Console | Sem erros. |
| Pergunta real da MCC, no Flash-Lite | A primeira resposta citou 3 dos 6 documentos que a busca trouxe (NASA, IEEE e Lafraia). A janela mostra Muqauwim et al., p. 1, entre os que ficaram de fora. |

Os prints foram feitos por Chrome headless e enviados ao pesquisador.

### Posição do aviso (02/10)

O aviso foi para o canto inferior direito. Enquanto ele está à vista, a área da aba termina acima dele; no
chat, a faixa fica entre as mensagens e a caixa de mensagem, que não sai do lugar. Conferência no servidor de
teste, por Chrome headless, a 1.280 × 800 (tema claro) e a 360 × 740 (tema escuro):

| Situação | Resultado |
|---|---|
| Aba Biblioteca, quatro arquivos em andamento | Nenhum botão, link, campo ou item de lista embaixo do aviso. |
| Aba Biblioteca, fim com uma falha listada | Idem. A faixa reservada tem a altura do aviso (226 px na tela larga e 260 px na estreita). |
| Chat, com uma conversa aberta e a falha listada | Idem. O aviso fica logo acima da caixa de mensagem. |
| Aviso recolhido | Idem. A faixa cai para 65 a 93 px. |
| As quatro abas, com o aviso aberto e recolhido | Idem, nas duas larguras. Sem rolagem lateral. |
| Caixa de mensagem com um texto de 12 linhas | A caixa cresce, e o aviso sobe junto, sempre 8 px acima dela; volta quando o texto sai. |
| Aviso fechado | A faixa é devolvida. |
| Console | Sem erros. |

A primeira tentativa (um espaço no fim das listas, para o conteúdo poder rolar para cima do aviso) deixava, a
360 px, dois documentos da lista e um link "Editar" embaixo do aviso até rolar. Foi trocada pela faixa reservada.

## Defeitos encontrados e corrigidos no aceite

1. **Rolagem lateral na aba Biblioteca a 360 px,** com "Completar fichas" e "Adicionar documento" lado a lado. Os botões passaram a quebrar a linha. O defeito já existia e só aparece quando há fichas pendentes.
2. **Contagem de falhas cortada** no título do pop-up em tela estreita. O resumo passou a quebrar a linha.
3. **"Tudo pronto" com um documento com falha.** O texto final passou a "Envio terminado" quando há falha.
4. **"1 anotações"** no resumo da ficha de leitura. Corrigido para o singular.
5. **Aviso falso de número sem marca** numa resposta da biblioteca, pelo ano de uma referência como "(Autor, 2008)".
6. **Tarefa presa num erro inesperado da leitura.** Como nas fichas, a tarefa passou a terminar com falha.
7. **Fichas de outro documento na linha do aviso.** Com os envios em paralelo, a linha mostrava o primeiro documento enquanto as fichas criadas eram de outro. Passou a mostrar o documento cujas fichas estão sendo criadas.

## Pendências

- No Flash, as respostas a pedidos de definição continuam com cerca do dobro do tamanho de antes do lote (879 tokens de saída, contra 459), porque trazem a citação no original e a tradução de cada documento.
- No Flash, ainda entra em média meio documento por resposta que a marcação não considerou como tratando do pedido (0,56; antes do lote, 0,72).
- O Flash-Lite continua citando menos fontes que o Flash. A janela de fontes mostra o que ficou de fora.
- Enquanto o aviso de envios está à vista, a aba perde a altura dele; com uma falha listada em tela estreita, cerca de um terço da tela, até recolher ou fechar.
- O envio só garante "indexados antes das fichas" para os arquivos que o servidor já recebeu: um arquivo muito grande, enviado junto com um muito pequeno, pode ser indexado depois das fichas do pequeno.
- Quatro pares de trechos vizinhos de prosa, em 11.649, ficam sem união porque a divisão não confirma o encaixe; a passagem fica mais curta, nunca errada.
- A marca de resposta cortada só é preenchida para o Gemini.
- As mensagens de pendência vindas da leitura do documento ainda trazem termos como "modelo local".

## Estado final

- `.claude/launch.json` ganhou a entrada `aliado-web-lote-27`.
- `tmp/lote-27` guardava a cópia da biblioteca usada na conferência (504 MB), os arquivos de teste e o registro de uso da bateria. Foi apagada no fim, com a autorização do pesquisador.
- **Commit:** autorizado pelo pesquisador em 02/10, depois da regra ajustada, como "AL-IAdo lote 27", sem push.
- **Com o pesquisador:** a tag `v0.3.0`, que continua apontando para `ae24885`, e o push.
