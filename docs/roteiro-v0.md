# Roteiro para o AL-IAdo v0.1.0

Meta definida pelo pesquisador em 26/09/2026. A redação da dissertação fica fora
deste roteiro. Cada lote continua sendo combinado antes de começar, conforme `AGENTS.md`.

## O que é a v0

Um agente **local e de uso individual** que o pesquisador usa no dia a dia da
pesquisa: conversa pelo navegador, recebe referências pelo chat, lembra do que
aprendeu nas conversas e se corrige, calcula confiabilidade e executa o experimento
de detecção de forma reproduzível.

**Critérios de pronto**

1. Instala do zero seguindo o README.
2. Responde pelo Gemini citando páginas de PDFs enviados pelo chat.
3. Lembra, em outra conversa, de um feedback dado antes e corrige uma anotação
   superada, sem apagar o histórico.
4. Consulta a web quando necessário e cita a fonte.
5. Executa o cálculo de confiabilidade e o experimento Denso × AE-LSTM no GPVS,
   de forma reproduzível e com relatório.
6. Testes e Ruff passam.
7. O pesquisador faz os commits e cria a tag `v0.1.0`. Pela decisão dele, nenhum
   commit é feito antes de a v0 estar concluída.

## Situação dos critérios — 27/09/2026

Os critérios 1 a 6 foram conferidos no lote 17, numa instalação do zero com Python 3.14:
- **1:** instalação pelo README e download do encoder pela rede.
- **2, 3 e 4:** chamadas reais ao Flash-Lite na interface, com PDF citado pela página, memória
  lembrada e corrigida sem apagar e busca na web com fonte.
- **5:** reprodução bit a bit, com os relatórios dos lotes 13–16.
- **6:** 331 testes e o Ruff.

O critério 7 fica com o pesquisador: os commits e a tag `v0.1.0`. Veja a
[validação do lote 17](migracao/validacao-lote-17.md).

## Lotes e progresso

| Lote | Entrega | Peso | Situação |
|---|---|---:|---|
| 01–08 | Transferência, modularização e adequações | 45% | Concluído |
| 09 | Gemini em uso real: identificadores de modelo no `.env` e primeira chamada barata, com custo registrado | 5% | Concluído |
| 10 | Interface web local: chat, escolha da skill, envio de PDF que vai para a biblioteca (com versão Markdown) e citações clicáveis | 10% | Concluído |
| 11 | Memória persistente de conversa, com autocorreção por anotações superadas e histórico preservado | 8% | Concluído |
| 12 | Busca na web pelo Gemini, com fontes citadas, integrada à autocorreção | 4% | Concluído |
| 13 | Dados GPVS e protocolo M14 executável: janelas, partição 50/15/15/20 com intervalos de separação, normalizador ajustado só no treino | 6% | Concluído |
| 14 | Autoencoders Denso e AE-LSTM: treino com parada pela validação, limiar p99 na calibração, configuração versionada e sementes fixas | 8% | Concluído |
| 15 | Avaliação M13: falsos alarmes no teste saudável, detecção nos ensaios com falha, relatório comparativo | 6% | Concluído |
| 16 | FMECA: revisão do NPR e, se desejado, tempos de reparo e disponibilidade | 4% | Concluído |
| 17 | Lançamento: instalação do zero num ambiente limpo, guia de uso, registro de mudanças, wheel | 4% | Concluído |

Progresso atual: **100%**. A soma dos pesos dos lotes concluídos dá o percentual.

## Decisões de escopo — 26/09/2026

- O experimento de detecção entra na v0.
- A interface é web **local**, sem login. Um site com domínio próprio fica para a v1.
- Só o Gemini será usado, por ser a API disponível. OpenAI continua configurável.
- As referências entram pelo chat. A biblioteca gera o Markdown, e o agente cria
  notas próprias citando a página.
- **Memória por origem:** o que vem do feedback explícito do pesquisador vale na
  hora. O que o agente deduz sozinho, de PDF, web ou conclusão própria, também vale,
  mas fica marcado como "inferido" e visível para ser revogado. Nada é apagado:
  anotações corrigidas ficam como superadas. Nenhuma anotação passa por cima de
  M01–M16 ou das skills, e texto de PDF ou web é dado, não instrução.
- A busca na web entra na v0, pelo Gemini, com possível custo por consulta.
- Apagar uma conversa não apaga a memória gerada a partir dela. A conversa vai para
  a lixeira local, e a memória guarda o próprio conteúdo e a referência à origem.
- A ordem prioriza o chat e a memória antes do experimento.

## Decisões do experimento — 27/09/2026

- Separação canônica de 11 janelas entre blocos, pela verificação de autocorrelação do
  lote 13; 2 janelas só para conferir a reprodução da origem.
- Escore top-5 e limiar p99 na calibração; sensibilidade de k ∈ {5, 10, 20} fixada
  antes da avaliação e só relatada.
- Modelos, hiperparâmetros e sementes da origem, com PyTorch 2.12.0 só CPU.
- A validação decide a parada do treino (paciência 20, teto só de segurança); o teto de
  150 épocas da origem cortava 8 dos 10 treinos.
- Avaliação (lote 15):
  - O alarme exige 3 janelas seguidas; a grade {1, 2, 3, 5} é só relatada.
  - Os falsos alarmes são contados no teste saudável e no pré-falha, separados.
  - As métricas principais são as físicas (falsos alarmes por hora com limite superior, ensaios
    detectados, atraso em ms, sensibilidade e especificidade); as da origem ficam como secundárias.
  - A incerteza vem de bootstrap em blocos de 12 janelas.
  - A semente 42 é a referência, com a faixa das 5 ao lado.
  - A comparação é pareada por ensaio e por objetivo, sem vencedor geral.

## Decisões da FMECA — 27/09/2026

- O NPR usa as notas de Cristaldi et al. (2017), Tab. 6, com a CCB herdando o item "PCB" (a reconferir
  no PDF). S e D são os da fonte, e os detectores não os alteram (M09).
- A ocorrência O não é recalculada pelas taxas. O ranking pelas taxas fica numa leitura separada, sem
  nota agregada, e a divergência é relatada.
- A partir das taxas entram MTBF e falhas esperadas em 1 e 20 anos. A disponibilidade espera uma
  fonte de tempo de reparo.

## Depois da v0.1.0: a 0.2.0

Os lotes partem dos apontamentos do pesquisador no uso real e continuam sendo combinados antes
de começar. A 0.2.0 saiu com o lote 21 (commit `50c4a63`, tag `v0.2.0`, enviada ao GitHub em 29/09).

| Lote | Entrega | Situação |
|---|---|---|
| 18 | Biblioteca com catálogo e resposta sem citação exibida com aviso; memória com perfil e memória de conversas; fila de anexos; fontes numa janela sobre a resposta | Concluído em 28/09/2026 (commit `f23855d`) |
| 19 | Qualidade da busca: palavras vazias ignoradas e mais peso ao significado, ficha de cada documento (título, autores, ano e DOI) e limite de trechos por documento, medidos com perguntas de referência | Concluído em 28/09/2026 (commit `fb366c4`) |
| 20 | Aba Ciência: resultados com gráficos, exploradores do limiar e de alarme e detecção com os dados reais, confiabilidade e FMECA pela interface | Concluído em 28/09/2026 (commit `4d38e19`) |
| 21 | GPVS pela interface: preparar, treinar e avaliar com progresso; nova avaliação com confirmação e registro da consulta ao teste (M14); lançamento da 0.2.0 | Concluído em 28/09/2026 (commit `50c4a63`, tag `v0.2.0`) |

### Decisões de 28/09/2026

- Uma resposta sem citação no modo biblioteca aparece com aviso e entra no histórico. Citação inventada continua bloqueada.
- A memória guarda o **perfil** do pesquisador e **todas as trocas**. Até 3 trocas parecidas de outras conversas entram como contexto.
- Uma conversa apagada deixa de ser lembrada. As anotações que saíram dela ficam, como decidido em 26/09.
- A aba Ciência faz tudo pela interface. O explorador de alarme e detecção pode usar o teste e os ensaios com falha, com o rótulo "exploração pós-teste, não canônica (M14)"; os resultados oficiais continuam os da avaliação de 27/09.
- **A busca vem antes da aba Ciência**, no lote 19. Perguntas em português favorecem documentos em português, e o catálogo não tem autor nem ano; veja a [validação do lote 18](migracao/validacao-lote-18.md).
  - Entram três correções: ignorar palavras vazias e dar mais peso ao significado, a ficha de cada documento e um limite de trechos por documento.
  - A tradução da pergunta para o inglês fica de fora, e só volta a ser considerada depois da medição.
  - A melhora é medida com perguntas de referência, antes e depois.
  - Os parâmetros da busca são fixados antes de medir, e as fichas da biblioteca real são preenchidas depois de uma cópia de segurança do catálogo.
- **A aba Ciência foi dividida em dois lotes:** o 20 (resultados, exploradores, confiabilidade e FMECA) e o 21 (GPVS pela interface).
- **Uma nova avaliação do GPVS pela interface é permitida com registro:** aviso, confirmação explícita e registro da consulta com data e configuração. Ela fica marcada como não canônica, e a oficial continua a de 27/09.
- **Confiabilidade pela interface:** explorar é livre e não grava; salvar como cenário exige fonte e hipóteses.

### Resultado do lote 19

Nas 16 perguntas de referência, os acertos passaram de 12 para 13 e o MRR, de 0,66 para 0,78. O
ganho veio das fichas: as 4 perguntas que citam o autor passaram a acertar, com MRR de 0,40 para
0,88. As perguntas de conteúdo ficaram em 9 de 12. Continuam fora dos 6 resultados três
perguntas de conteúdo em outro idioma, e é aí que a tradução da pergunta poderia ajudar. Veja a
[validação do lote 19](migracao/validacao-lote-19.md).

### Resultado dos lotes 20 e 21

A aba Ciência faz tudo pela interface. Com os parâmetros oficiais, os exploradores repetem a
avaliação de 27/09. O treino e a avaliação feitos pela interface reproduziram bit a bit a rodada
canônica, e a nova avaliação entrou no registro como consulta nº 2, não canônica (na cópia usada
no aceite). Veja as validações dos lotes [20](migracao/validacao-lote-20.md) e [21](migracao/validacao-lote-21.md).

## Depois da 0.2.0: a 0.3.0

Em 30/09, o pesquisador avaliou a 0.2.0 para o mestrado:
- a aba Ciência está confusa e os gráficos estão ruins;
- faltam visões do projeto antigo: os escores divididos por ensaio, a matriz de confusão e as métricas para comparar;
- a confiabilidade deveria ter uma curva por componente;
- a biblioteca tem recortes repetidos do Lafraia.

O plano da 0.3.0 foi aprovado no mesmo dia. Cada lote a partir do 23 foi detalhado e combinado
antes de começar. A 0.3.0 sai com o lote 26; a tag `v0.3.0` e o envio ao GitHub ficam com o pesquisador.

| Lote | Entrega | Situação |
|---|---|---|
| 22 | Correções de confiança: skill do mestrado atualizada, taxas e notas da FMECA conferidas nos PDFs, apagar documentos da biblioteca e os 2 recortes do Lafraia, consulta da busca reescrita a partir da conversa, em português e inglês, 10 trechos por resposta e fonte do texto | Concluído em 30/09/2026 (commit `cdcd141`) |
| 23 | Aba Ciência nova, parte 1: navegação pelas perguntas, gráficos com D3, Resumo com as matrizes de confusão, Escores por ensaio, Métricas por falha, Explorar e exportação das figuras | Concluído em 30/09/2026 (commit `745880a`) |
| 24 | Início das falhas no GPVS: a mudança observada nos sinais, a reanálise dos mesmos escores com ela, os alarmes falsos estimados e a faixa esperada pelo limiar, com a seção nova na aba Ciência | Concluído em 30/09/2026 (commit `0cc8f78`) |
| 25 | Confiabilidade por componente (um painel por grupo, nas duas bases de tempo), matriz de criticidade S × O na FMECA e disponibilidade com os tempos de reparo do IEEE 493 e de Baschel et al. (2018) | Concluído em 30/09/2026 (commit `36bf84a`) |
| 26 | Resultados no chat: 8 blocos com os números da aba Ciência, marca [Rn] em cada número e conferência contra o bloco citado; lançamento da 0.3.0 | Concluído em 01/10/2026 (commit `ae24885`) |

### Decisões de 30/09/2026

- **"Métricas entre componentes"** são por **tipo de falha do GPVS** (F1 a F7, com o nome), Denso contra LSTM, nos modos L e M. A regra de não ligar as falhas do GPVS aos componentes da FMECA continua valendo.
- **Os dois recortes do Lafraia** (o capítulo 7 e a digitalização) são **apagados de vez**. O manual completo cobre os dois. As 16 anotações deduzidas deles são revogadas.
- **A aba Ciência** é organizada pelas perguntas: o resultado primeiro, e as ferramentas no fim.
- **Os gráficos novos** usam o D3 v7, copiado do projeto antigo, como foi feito com o KaTeX.
- **As telas apresentam dados, não o versionamento do trabalho.**
  - Nada de códigos internos (M11, M14), "semente", "canônica" ou nomes de pasta sem explicação.
  - Os números mostrados são os do modelo de referência do relatório oficial.
  - As regras continuam valendo por dentro.
- **Todo índice ou indicador tem uma nota**, ao passar o mouse ou ao tocar, dizendo o que significa.
- **Entram na 0.3:** o início das falhas no GPVS, os resultados no chat e a disponibilidade. **Fica de fora:** a cópia de segurança da memória.
- **A busca nas continuações, decidida depois, no mesmo dia.** Uma pergunta de continuação sobre a definição de MCC não achou a definição, que estava na biblioteca.
  - A pergunta passa a ser reescrita pelo modelo mais barato, em português e inglês, ainda no lote 22.
  - Isso trouxe de volta a tradução da pergunta, que tinha ficado de fora.

### Resultado do lote 22

- **Conferência nos PDFs.** As taxas e as notas da FMECA batem com as fontes: Sarquis Filho et al. (2020), Tab. III, p. 3; Baschel et al. (2018), Tab. 1, p. 5 e 6; e Cristaldi et al. (2017), Tab. 6, p. 6.
  - O 8,9e-6/h do IGBT é o valor extrapolado dos relatórios de O&M da juwi. O valor que o próprio Baschel usa é 11,4e-6/h.
- **Biblioteca.** Ficou com 25 documentos, e a busca manteve 13 das 16 perguntas de referência.
- **Consulta reescrita.**
  - Com ela, a busca passou a acertar **15 das 16** perguntas de referência, com MRR de 0,91.
  - Depois, a busca parou de se prender a um autor só porque a resposta anterior o citou. Com isso, foram **16 de 16**, com MRR de 0,97.
  - A continuação sobre MCC passou a trazer a citação direta do IEEE 493, p. 134. Com 10 trechos, ela traz definições de 6 documentos.
- **Mais referências e fonte do texto.**
  - O pedido "mais opções de fontes" era de fontes de texto. Antes do esclarecimento, a busca já tinha passado a 10 trechos, com a opção de cada autor na resposta, e o pesquisador decidiu manter.
  - O seletor de fonte do texto tem 8 opções.
- Veja a [validação do lote 22](migracao/validacao-lote-22.md).

### Resultado do lote 23

- **Aba Ciência nova**, organizada pelas perguntas: Resumo, Escores por ensaio, Métricas por falha, Confiabilidade, FMECA, Explorar e Rodar e arquivos.
- **Gráficos em D3 v7**, com exportação em SVG, PNG de 300 dpi e CSV, e uma nota em cada índice e indicador.
- **Conferência com os dados reais:** o Resumo repete o relatório de 27/09, e as matrizes de confusão repetem as contagens de cada ensaio.
- Veja a [validação do lote 23](migracao/validacao-lote-23.md).

### Decisões e resultado do lote 24 (30/09/2026)

- **Ordem.** Depois da análise crítica dos resultados, o pesquisador pediu para corrigir o que tivesse solução. O início das falhas passou a ser o lote 24, e a confiabilidade por componente, o 25.
- **Regras da reanálise.** O trecho entre o meio do registro e a mudança observada fica fora das métricas por janela. F4, F6 e F7, sem mudança clara, ficam no meio. As médias saem para os 14 ensaios e para os 8 de mudança clara.
- **Resultado.**
  - Em F1, F2 e F3, a mudança vem de 1,5 a 3,8 s depois do meio; em F5, coincide com ele.
  - Com a mudança, a detecção não muda. O atraso mediano cai para 60 ms, e a sensibilidade nos 8 ensaios de mudança clara vai de 0,67 a 1,00.
  - A avaliação de 27/09 continua sendo a oficial.
- **Alarmes falsos.** A estimativa pela cadeia dá 19 por hora no Denso (0 a 53) e 56 no AE-LSTM (0 a 263). As janelas acima do limiar cabem na faixa esperada, de 0,13% a 2,87%.
- Veja a [validação do lote 24](migracao/validacao-lote-24.md).

### Decisões e resultado do lote 25 (30/09/2026)

- **Tempos de reparo:**
  - dois cenários: o reparo ativo do IEEE 493-2007 (inversores, 26 h, Tab. 10-4, p. 290) e a parada de campo de Baschel et al. (2018), com 1 dia para detectar e 5 para reparar (Fig. 7);
  - os contatores usam o tempo do inversor;
  - nenhuma fonte traz o tempo de reparo de cada componente.
- **Base de tempo:** as duas no gráfico e um seletor. **FMECA:** entra a matriz S × O.
- **Resultado:** a disponibilidade vai de 99,09% (CCB, calendário, parada de campo) a 99,99% (contatores e IGBT na operação, reparo ativo). A CCB para até 80 h por ano.
- Veja a [validação do lote 25](migracao/validacao-lote-25.md).

### Decisões e resultado do lote 26 (30/09 e 01/10/2026)

- **Decisões:**
  - um interruptor **Usar resultados**, ligado na skill do mestrado e desligável;
  - 8 blocos resumidos, no formato da aba Ciência;
  - uma resposta com número que não confere aparece com aviso e sai do histórico e da memória de conversas;
  - o lançamento da 0.3.0 fica neste lote, com 8 perguntas pagas de aceite.
- **Caminho escolhido:** os resultados vão no próprio pedido, gerados por código das mesmas funções da aba. Uma ferramenta de consulta e os relatórios na biblioteca foram comparados e ficaram de fora.
- **Revisão antes do aceite:** uma revisão por agentes, com verificação adversarial, confirmou 25 defeitos, todos corrigidos. Os principais estavam na leitura dos números: frações lidas como datas, fórmulas ignoradas e tabelas que não eram conferidas.
- **Resultado do aceite:**
  - nas 8 perguntas, as 7 respostas com números saíram conferidas, e a pergunta sem números não citou bloco nenhum;
  - nenhum número ficou fora dos blocos citados;
  - a reanálise apareceu identificada como secundária, depois do oficial;
  - cada pergunta custou cerca de 11 mil tokens de entrada, contra cerca de 5,5 mil sem os resultados.
- **Limites:** um número sem marca não é conferido, e o chat não calcula.
- Veja a [validação do lote 26](migracao/validacao-lote-26.md).

## Depois da 0.3.0

A 0.3.0 saiu com o lote 26 (commit `ae24885`). Os lotes seguintes partem do uso real e continuam sendo
combinados antes de começar. A 0.4.0 sai com o lote 29 e reúne os lotes 27 a 29; a 0.5.0 sai com o lote 31 e
reúne os lotes 30 e 31 (a 0.4.1, preparada no lote 30, não chegou a ser lançada).
As tags e o envio ao GitHub ficam com o pesquisador.

| Lote | Entrega | Situação |
|---|---|---|
| 27 | Tela de apresentação ao abrir ou recarregar; aviso de envios em todas as abas, com o documento pronto antes das fichas; respostas com várias fontes: regra reescrita, trechos agrupados por documento, passagem com os trechos vizinhos e a lista do que a busca trouxe e não foi citado | Concluído em 02/10/2026 |
| 28 | Espelho para o Obsidian em `data/obsidian/`: uma nota por conversa, uma por documento e uma de anotações por fonte, ligadas por links e refeitas depois de cada resposta | Concluído em 03/10/2026 |
| 29 | Indexação: cabeçalhos, sumário e referências fora dos trechos; trechos por frase; texto reconhecido dentro das figuras; descrição de figuras e tabelas pelo modelo, por pedido; lançamento da 0.4.0 | Concluído em 03/10/2026 |

| 30 | Leitura integral: a busca escolhe os documentos, e o modelo recebe o PDF das páginas inteiras, dentro de um teto por pergunta; documentos fixados na conversa; a aba Biblioteca dá lugar ao painel de documentos | Concluído em 04/10/2026 |
| 31 | Roteador local e escada de leitura: o AL-IAdo escolhe a skill, o modelo e a leitura antes de gastar; confirmação acima de 30 mil tokens e aviso diário em 300 mil; parte fixa enxuta; contagem exata de termos; trilhas das perguntas já respondidas; lançamento da 0.5.0 | Concluído em 04/10/2026 |
| 32 | Busca em memória com atualização pelo catálogo; reordenação local de até 60 candidatos para a leitura por páginas; revisor seletivo, preservando perfil, preferências e decisões | Concluído em 05/10/2026; lançado na 0.6.0 |
| 33 | Reescrita seletiva, plano por partes, aprendizado com o uso e vocabulário dos resultados; lançamento da 0.6.0 com o lote 32 | Concluído em 17/10/2026 (commit `30f1681`, tag `v0.6.0`) |

### Decisões e resultado do lote 27 (01 e 02/10/2026)

- **Origem:** três apontamentos do uso real: a página reabria a última conversa, os envios não mostravam o avanço fora do chat, e a definição de MCC por fonte só veio na quarta pergunta.
- **Diagnóstico da MCC:**
  - em 30/09, a busca falhou, e a consulta reescrita do lote 22 já tinha corrigido;
  - em 01/10, a busca trouxe definição de 4 documentos na primeira pergunta, e a resposta usou um. Não houve falha do provedor.
- **Decisões:**
  - entram a tela, o aviso de envios e as três correções das respostas;
  - uma bateria paga de cerca de 100 chamadas mede o antes e o depois;
  - a troca de dataset do experimento era só uma pergunta e não virou lote.
- **Resultado da bateria** (92 respostas, com marcação cega dos documentos que tratam de cada pedido):
  - o modelo pesa mais que a regra: o Flash cita todos os documentos que tratam do pedido, antes e depois; o Flash-Lite, cerca de três quartos;
  - no Flash-Lite, as respostas com uma fonte só caíram de 3 em 14 para 1 em 16, e o caso real foi de 1 para 2 fontes;
  - as citações diretas passaram a vir no idioma original e a conferir com a passagem;
  - no Flash, as respostas ficaram com o dobro do tamanho e comentavam documentos que não tratam do pedido (tratado na regra ajustada, abaixo).
- **Revisão por agentes:** interrompida pelo limite de uso e retomada em 02/10. Em três rodadas, com verificação adversarial, confirmou 34 defeitos distintos, quase todos de gravidade baixa; os principais foram uma resposta cortada pelo teto de tamanho, a união errada de trechos em texto repetitivo e avisos falsos de número sem marca.
- **Complemento da bateria:** com o código final, o pedido de 14 das 17 perguntas é idêntico ao medido. As 3 que mudaram e a resposta cortada foram refeitas (8 chamadas), e a cobertura do Flash ficou em 100%.
- **Decisões de 02/10:**
  - **Regra ajustada:** a frase que fazia o Flash comentar documentos fora do assunto foi trocada e medida de novo, só no Flash (21 chamadas). As respostas com esse comentário foram de 13 em 21 para nenhuma; os documentos citados que não tratam do pedido, de 1,28 para 0,56 por resposta; a saída, de 1.033 para 879 tokens. A cobertura ficou em 98%: uma resposta em 18 citou 2 de 3 documentos, e a repetição dela citou os 3.
  - **Aviso de envios:** foi para o canto inferior direito, na aba Biblioteca e no chat, com a faixa dele reservada. Nas quatro abas, a 1.280 e a 360 px, nada fica embaixo dele.
  - **Commit** do lote autorizado depois da regra ajustada, e a pasta de teste apagada no fim.
- **Total de chamadas pagas:** 132 (129 na bateria e 3 no navegador).
- **Pendências:** no Flash, as respostas a pedidos de definição continuam com cerca do dobro do tamanho de antes do lote; o Flash-Lite continua citando menos fontes.
- Veja a [validação do lote 27](migracao/validacao-lote-27.md).

### Decisões e resultado do lote 28 (03/10/2026)

- **Origem:** o pesquisador quis abrir os dados do AL-IAdo no Obsidian para ver o grafo crescer. Conversas em JSON e memória em banco de dados não são lidas pelo Obsidian como notas.
- **Decisões:**
  - os nós são as conversas, os documentos e as anotações da memória;
  - as anotações ficam agrupadas pela fonte, numa nota própria ligada ao documento ou à conversa;
  - o cofre fica em `data/obsidian/`, fora do Git;
  - a atualização é automática, depois de cada resposta, sem botão e sem chamada paga.
- **Resultado nos dados de hoje:** 63 notas (7 conversas, 26 documentos, 29 de anotações e a de apresentação), 239 links, nenhum quebrado, em cerca de um décimo de segundo. Uma segunda rodada sem mudança não grava nada.
- **Linha do tempo:** cada arquivo leva a data do registro, para a animação do grafo mostrar o crescimento desde 27/09.
- **Revisão por agentes:** três rodadas, 46 apontamentos, quase todos na limpeza do texto das respostas e na gravação da pasta. O principal foi trocar a proteção por padrões de texto por uma conferência do resultado: o texto pronto é lido por um analisador de Markdown e, se sobrar algo que o Obsidian executaria, buscaria ou ligaria por conta própria, sai sem marcação.
- **Correção de passagem:** no Windows, ler uma conversa no instante em que ela era regravada podia fazer a gravação falhar; as conversas ganharam uma trava.
- **Pendências:** o aceite do pesquisador no Obsidian (cores, animação e links), e as correções da terceira rodada, conferidas por testes e não por uma nova rodada de agentes.
- Veja a [validação do lote 28](migracao/validacao-lote-28.md).

### Decisões e resultado do lote 29 (03/10/2026)

- **Origem:** o pesquisador notou que muitos trechos e todas as imagens dos documentos não eram considerados.
- **Diagnóstico:** o texto corrido estava todo no índice. Faltava o conteúdo visual de 60% das páginas (figura, desenho, tabela ou legenda), 86% dos trechos eram cortados no meio da frase e 11% levavam um cabeçalho ou rodapé repetido.
- **Decisões:**
  - entram a leitura de figuras e tabelas, os trechos por frase e a limpeza do índice; a busca mais rápida ficou de fora;
  - as figuras são lidas de duas formas: o texto dentro delas, reconhecido no computador, e a descrição pelo modelo;
  - a descrição envia páginas como imagem e só roda por pedido;
  - o lote 28 vai no mesmo commit, e a versão passa a 0.4.0.
- **Piloto pago** com 20 páginas nos dois modelos: os dois acharam as mesmas 32 figuras e tabelas; o Flash copiou as legendas inteiras e transcreveu as tabelas sem lacunas. O pesquisador escolheu o Flash.
- **Leitura completa** da biblioteca com o Flash: 1.291 das 1.293 páginas, 1.539 figuras e tabelas, 2,0 milhões de tokens de entrada e 1,4 milhão de saída, em 42 minutos.
- **Resultado na biblioteca real:**
  - trechos sem pontuação no fim: de 86% para 25%; os que restam são tabelas, fórmulas, legendas e frases que continuam na página seguinte;
  - das 16 perguntas novas sobre figuras e tabelas, nenhuma trazia o conteúdo da figura; agora 12 trazem com a pergunta direta e 9 com a consulta reescrita;
  - as 16 perguntas de referência continuam acertando com a consulta reescrita; em 3 delas o documento esperado desceu de posição;
  - a busca ficou mais lenta, de 2,65 s para 3,9 s, porque o índice foi de 14 mil para 20 mil trechos.
- **Correções de passagem:** o leitor de PDF não aceita chamadas simultâneas e ganhou uma trava; o cliente do Gemini passou a ser criado uma vez só; a resposta cortada no meio de uma saída estruturada passou a entrar no registro de uso.
- **Chamadas pagas:** 80 nas medições e no piloto, e cerca de 1.310 na leitura completa.
- **Limpeza:** a biblioteca real foi reindexada três vezes no lote, para corrigir a divisão das descrições; as duas extrações intermediárias foram apagadas com a autorização do pesquisador, e a pasta ficou com 1,0 GB (era 0,53 GB antes do lote).
- **Pendências:** a busca mais rápida; a consulta reescrita, que perde a página em perguntas sobre uma figura específica; duas páginas que o modelo não conseguiu descrever.
- Veja a [validação do lote 29](migracao/validacao-lote-29.md).

### Decisões e resultado do lote 30 (03 e 04/10/2026)

- **Origem:** o pesquisador pediu que o AL-IAdo lesse os documentos como os assistentes leem um anexo: inteiros, com as imagens, sem fracionar, mesmo custando mais. E que a aba Biblioteca saísse.
- **Diagnóstico:** só cerca de 10 trechos iam ao modelo por pergunta. A biblioteca inteira não cabe num pedido, mas os documentos cabem um a um. Uma página de PDF custa 560 tokens no Gemini.
- **Decisões:**
  - a busca escolhe os documentos; artigos vão inteiros, livros e normas em blocos de páginas inteiras;
  - imagem de todas as páginas enviadas; teto de 400 mil tokens por pergunta, ajustável;
  - a aba Biblioteca sai, e um painel no chat fica com a lista, a ficha, as figuras e apagar;
  - a regra que reparte o teto ficou com o assistente.
- **O que mudou do plano, pelas medições:**
  - o texto guardado não segue junto com o PDF, só as primeiras palavras de cada página: ele seria dois terços do custo;
  - os documentos grandes vão em blocos fixos de 10 páginas, para o envio ser reaproveitado;
  - todo PDF sobe pelo serviço de arquivos do Google, onde fica por até 48 horas;
  - todo documento que a busca traz recebe um mínimo do teto.
- **Piloto pago** com 12 perguntas nos dois modos, no Flash (30 chamadas, 4,5 milhões de tokens de entrada):
  - as duas formas citaram o documento esperado nas 12; a página esperada, 5 de 6 por trechos e 6 de 6 com os documentos inteiros;
  - em três perguntas, o modo de trechos disse que o dado não estava no material ou trouxe parte dele, e a leitura integral trouxe as escalas, a linha da tabela e a tabela completa;
  - o custo foi de 11 mil para 150 ou 385 mil tokens de entrada por pergunta;
  - o tempo foi de 7 a 13 segundos para 31 segundos a 12,5 minutos, sem relação com o tamanho do pedido.
- **Primeiro uso (04/10):** o pesquisador usou a tela nova com o programa antigo ainda em execução, e as respostas saíram por trechos sem aviso; numa delas a consulta reescrita trocou "pertile" por "percentil". Duas correções: o documento citado na mensagem volta à consulta, e a tela avisa quando o programa é anterior a ela. A verificação pedida: o documento de Pertile (2023) não fala de autoencoder; o termo aparece em 6 dos 26 documentos.
- **Pendências:** o tempo de resposta; a busca na web junto com a leitura integral; a busca mais rápida; uma contagem exata de um termo na biblioteca inteira.
- Veja a [validação do lote 30](migracao/validacao-lote-30.md).

### Decisões e resultado do lote 31 (04/10/2026)

- **Origem:** "gastamos metade do orçamento total em um dia". O pesquisador pediu o gasto mínimo de tokens e que o AL-IAdo escolhesse o modelo e a skill, como era a ideia do roteamento.
- **Diagnóstico:** a regra do lote 30 lia até 400 mil tokens em toda pergunta com a biblioteca ligada (uma pergunta de conversa custou 386 mil); e a parte fixa de uma pergunta comum era maior que os trechos.
- **Decisões:** escada automática de leitura; teto de 30 mil tokens sem confirmação; o AL-IAdo escolhe o modelo e a skill e mostra a escolha; aviso diário em 300 mil; trilhas das perguntas já respondidas, sem botão e sem repetir a resposta antiga.
- **O que mudou do plano:**
  - a trilha é achada pela consulta de busca (o assunto) e pela frase (o pedido), e a consulta continua sendo reescrita: a frase sozinha confundia pedidos de assuntos diferentes;
  - o documento citado só vai inteiro se for pequeno; de um livro, vão as páginas mais próximas;
  - os resultados da pesquisa e o material de referência da skill só seguem quando a pergunta é de resultados ou de método.
- **Medição paga** (30 chamadas e 281 mil tokens de entrada, do limite de 30 e 500 mil), com as 12 perguntas do piloto do lote 30:
  - 144 mil tokens de entrada nas 12, contra 3,2 milhões da leitura ampla e 138 mil dos trechos;
  - documento esperado citado nas 12, e página esperada nas 6 que têm uma;
  - as três respostas que só a leitura ampla completava saíram completas;
  - 10 a 35 segundos por pergunta, contra 7 a 13 dos trechos e 31 segundos a 12,5 minutos da leitura ampla;
  - uma mensagem de conversa custou 459 tokens, no modelo menor.
- **Correção vinda da medição:** do documento citado que é grande iam as 10 páginas mais próximas de toda a biblioteca, e a tabela pedida de uma norma de 426 páginas ficava de fora. Agora vão as páginas do documento citado, e a tabela entra.
- **Com o Gemini, depois da primeira entrega** (7 das 30 chamadas): a pergunta já respondida foi reconhecida com a consulta reescrita; a subida de degrau e a confirmação acima do teto funcionaram. A trilha não poupou tokens (5.962 contra 4.086 por trechos), e subir um degrau num assunto ausente custou 20 mil tokens.
- **Pendências:** a busca leva cerca de 4 segundos; a pergunta já respondida repete o alcance da resposta anterior e não poupa tokens; o roteador foi ajustado nas mesmas mensagens em que foi medido, e deixa sem os resultados da pesquisa 3 de 10 perguntas escritas de outro jeito.
- Veja a [validação do lote 31](migracao/validacao-lote-31.md).

### Decisões e resultado do lote 32 (04 e 05/10/2026)

- **Origem:** continuação autorizada do trabalho interrompido do Claude, a partir do cache parcial
  existente em `knowledge/library.py`. Escopo na [spec 0032](specs/0032-busca-e-memoria.md).
- **Busca em memória:** o retrato acompanha alterações do catálogo feitas por qualquer conexão.
  No catálogo sintético de 20 mil trechos, a mediana das buscas seguintes caiu de 3,33 s para 0,082 s;
  os 20 resultados permaneceram iguais. A primeira carga levou 2,82 s.
- **Segunda rede local:** reordena até 60 candidatos na leitura por páginas, preservando as prioridades
  de documentos e trilhas. Modelo quantizado de cerca de 136 MB, com preparo explícito e hashes fixos.
  Em 12 perguntas sintéticas, a passagem esperada passou de primeiro lugar em 5 para primeiro em 12;
  a presença entre as dez primeiras ficou em 12 nos dois casos. O ensaio isola a reordenação e não
  mede a resposta final do modelo. Sessenta candidatos levaram 1,37 s.
- **Revisor seletivo:** consultas e cumprimentos poupam uma chamada. As seis mensagens com informações
  para guardar foram mantidas no ensaio de 22 mensagens; o revisor seria chamado seis vezes, em vez
  de 22. A memória de conversas e as fichas continuam funcionando.
- **Validação:** 739 testes e Ruff passaram. Sem chamadas pagas ou reindexação do acervo real;
  versão 0.5.0 preservada, sem commit nem pacote novo.
- **Pendências:** ensaio com perguntas novas sobre o acervo real, dentro de escopo e orçamento
  combinados; reescrita seletiva; limitações das trilhas e do roteador já registradas no lote 31.
  Para usar o código novo, reiniciar o processo do AL-IAdo.
- Veja a [validação do lote 32](migracao/validacao-lote-32.md).

### Decisões e resultado do lote 33 (16 e 17/10/2026)

- **Origem:** o que ficou fora do lote 32 (reescrita seletiva, aprendizado com o uso e vocabulário dos resultados)
  e um plano por partes acrescentado ao código em 05/10, depois da validação do lote 32, sem spec nem testes.
  Escopo na [spec 0033](specs/0033-reescrita-aprendizado-resultados.md).
- **Decisões do pesquisador (17/10):** adotar e corrigir o plano por partes; segunda chamada automática só dentro
  do teto e antes do aviso diário; aprender só com as escolhas da tela e com perguntas refeitas ou reclamações,
  sem lista para revisar; teste pago de até 8 chamadas e 80 mil tokens.
- **Resultado sem tokens:** 9 de 10 perguntas novas sobre os resultados reconhecidas (antes, 7); conversa solta
  depois da biblioteca fora dela em 4 de 4 (antes, 0); reclamações com leitura mais funda em 2 de 2. Nas mensagens
  reais, 5 de 24 perguntas à biblioteca dispensam a reescrita.
- **Resultado pago** (5 chamadas e 27 mil tokens de entrada): o pedido "uma fonte para cada um" de 05/10 saiu com
  as três partes citadas, contra uma antes; a pergunta sem reescrita saiu com três páginas citadas.
- **Validação:** 757 testes e Ruff, já com as cinco correções da auditoria. A versão continuava 0.5.0; os lotes 32 e 33 saíram juntos como 0.6.0 em 17/10/2026.
- **Pendências:** a segunda chamada com o modelo real; trilhas procuradas pela pergunta quando não há reescrita;
  o roteador continua errando em frases que as regras e os exemplos não cobrem. Reiniciar o AL-IAdo para usar.
- Veja a [validação do lote 33](migracao/validacao-lote-33.md).

## Depois da 0.6.0: a fundação revista

Em 17/10/2026 o pesquisador pediu uma recapitulação das versões (a 0.4.0, a 0.5.0 e a 0.6.0 foram lançadas em
ordem no mesmo dia; ver a [recapitulação](recapitulacao-0.4-0.6.md)) e uma
[revisão da modularização e das specs](revisao/2026-10-modularizacao-e-specs.md), que ordena os três lotes
seguintes. Eles saem juntos como 0.7.0, com um commit por lote, feito pelo pesquisador.

| Lote | Entrega | Situação |
|---|---|---|
| 34 | Experimento AE Denso × AE-LSTM rodado do zero pela aba Ciência, que mostra só a rodada atual; resultados em JSON e Markdown; PDF formal por pedido, com o resultado anexo; comparação com um resultado salvo; specs vivas e o teste que liga cada requisito a um teste | Concluído localmente em 17/10/2026 |
| 35 | Chat com tela mínima: o roteador local decide o que eram seletores e chaves; o pedido escrito vale como escolha; a leitura ampla só por pedido escrito, sempre confirmada | Concluído localmente em 18/10/2026 |
| 36 | O código do mestrado na especialização `src/aliado/specializations/mestrado/`, com zero menções ao domínio no núcleo; lançamento da 0.7.0 | Concluído localmente em 18/10/2026 |

### Decisões e resultado do lote 34 (17/10/2026)

- **Decisões do pesquisador:** o experimento é a comparação AE Denso × AE-LSTM, e o GPVS é a base de dados;
  "Rodar experimento" roda tudo de ponta a ponta e fica desativado sem parâmetro novo; a aba mostra só a rodada
  atual; os resultados ficam em JSON e Markdown, e o PDF formal só sai por clique; a frase "consultar o teste"
  continua; "oficial" só para a avaliação de 27/09. Escopo na [spec 0034](specs/0034-experimentos.md).
- **Resultado:** com os parâmetros de 27/09, uma rodada do zero numa cópia dos resultados repetiu a avaliação de
  27/09 bit a bit (pesos, escores, relatórios e início das falhas), em 2 min 16 s. Pela tela, uma rodada com
  separação de 2 janelas e teto de 150 épocas.
- Veja a [validação do lote 34](migracao/validacao-lote-34.md).

### Decisões e resultado do lote 35 (18/10/2026)

- **Decisões do pesquisador:** tela mínima, sem os seletores e as chaves do chat; o pedido escrito vale como
  escolha dele; a leitura ampla só por pedido escrito, sempre com confirmação; uma mensagem que é só um pedido
  refaz a pergunta anterior; os limites de 30 mil e 300 mil tokens não mudam. Escopo na
  [spec 0035](specs/0035-chat-tela-minima.md); requisitos vivos em [capacidades/roteador.md](specs/capacidades/roteador.md).
- **Resultado:** num servidor de teste, sem custo, "Use o modelo maior. ..." respondeu com o modelo maior, e
  "Faça a leitura ampla." sozinha refez a pergunta anterior, perguntou antes de ler e leu os 3 documentos inteiros.
- Veja a [validação do lote 35](migracao/validacao-lote-35.md).

### Decisões e resultado do lote 36 (18/10/2026)

- **Decisões do pesquisador:** o código do mestrado na especialização, dentro do AL-IAdo; zero menções ao domínio
  em qualquer arquivo do núcleo; sem descoberta por YAML; lançamento da 0.7.0 com os lotes 34 a 36. Escopo na
  [spec 0036](specs/0036-mestrado-fora-do-nucleo.md); requisitos vivos em [capacidades/nucleo.md](specs/capacidades/nucleo.md).
- **Resultado:** as menções no núcleo caíram de 294 linhas em 27 arquivos, na 0.6.0, para 227 em 22 no lote 34 e
  para zero. A especialização
  entrega ao núcleo a skill padrão, as pastas, as frases do roteador, o glossário, os comandos, as rotas da aba
  Ciência e os resultados do chat; o núcleo os lê só quando precisa. Para quem usa, nada muda.
- Veja a [validação do lote 36](migracao/validacao-lote-36.md).

## Depois da 0.7.0: o modelo local (0.8.0)

Os lotes 37 a 44 saem juntos como 0.8.0, num commit só feito pelo pesquisador. Os lotes mexem nos mesmos arquivos e
não dá para separá-los em commits.

| Lote | Entrega | Situação |
|---|---|---|
| 37 | Leitura das páginas: página em branco sem aviso, página descrita pelo modelo sem pendência, OCR fraco na lista da descrição | Concluído em 18/10/2026 ([spec 0037](specs/0037-paginas-sem-leitura.md), [validação](migracao/validacao-lote-37.md)); a reindexação da biblioteca real fica com o pesquisador, pela tela |
| 38 | Modelo local (Ollama) como principal, com o Gemini Flash na escalada | Etapas 2 e 3 concluídas localmente em 18/10/2026: código com testes simulados; Ollama e `qwen3.5:9b` instalados e medidos. Depois, ele ligou o local no `.env` |
| 39 | O modelo local lê as páginas pelo texto guardado, com as descrições das figuras | Concluído e medido localmente em 18/10/2026 |
| 40 | Contexto de 32 mil tokens no local, com 20 camadas na placa, abaixo de 4 GB | Aplicado e medido em 18/10/2026: o local respondeu 14 das 16 perguntas reais, contra 6; 5 min de mediana por resposta ([spec 0040](specs/0040-contexto-32k.md), [validação](migracao/validacao-lote-40.md)) |
| 41 | Reescrita da busca sem raciocínio no local; trechos sem raciocínio experimentados e desfeitos; OCR por página conferido (já existia) | Concluído e medido em 18/10/2026: tempo médio de 265 para 158 s; a reescrita volta a funcionar ([spec 0041](specs/0041-local-mais-rapido.md), [validação](migracao/validacao-lote-41.md)) |
| 42 | O modelo local quase todo na VRAM: 32 das 33 camadas na placa, no lugar do limite de 4 GB | Aplicado e medido em 19/10/2026: escrita de 15 para 25 tokens/s; tempo médio de 158 para 102 s ([spec 0042](specs/0042-local-na-vram.md), [validação](migracao/validacao-lote-42.md)) |
| 43 | Temperatura 0,6 no modelo local, medida em duas rodadas | Aplicado e medido em 19/10/2026: o mesmo desfecho nas duas rodadas em 13 de 16 perguntas, contra 7; o local respondeu 13 e 11; 4 a 5 chamadas ao Gemini ([spec 0043](specs/0043-temperatura-local.md), [validação](migracao/validacao-lote-43.md)) |
| 44 | Revisão e fechamento da 0.8.0: anexos, navegação, escalada explícita ao Flash, registros e pacote | Validado localmente em 20/10/2026: 814 testes e Ruff; aguarda revisão e commit |

### Decisões e resultado do lote 44 (20/10/2026)

- **Decisões do pesquisador:** revisar toda a 0.8.0, registrar as correções num lote novo e preparar os arquivos
  para um único commit dele. Escopo na [spec 0044](specs/0044-revisao-fechamento.md).
- **Correções:** criação compartilhada da conversa para anexo e pergunta, navegação protegida e destino explícito
  no Flash quando a resposta local não passa na conferência. Os registros originais dos lotes 35/36 são preservados.
- **Estado:** validado localmente: 814 testes, 13 cenários JavaScript, Ruff e wheel conferido; aguarda revisão
  e commit. As medições com modelo local dos lotes 38 a 43
  continuam sendo as de 18 e 19/10, com o Gemini simulado. A revisão atual não repete essas chamadas.
- Veja a [validação do lote 44](migracao/validacao-lote-44.md).

### Decisões e resultado do lote 38, Etapa 2 (18/10/2026)

- **Decisões do pesquisador:**
  - os modelos locais e quantizados são os principais; o Gemini Flash entra no limite do raciocínio deles, e não no
    de tokens, sem um caminho de troca entre provedores;
  - com o Ollama fora do ar, erro claro, sem gastar;
  - placa até 4 GB e o SSD como complemento (a conferência da ordem está no README);
  - só testes simulados, sem baixar nada, e parar para a revisão dele antes da Etapa 3.

  Escopo na [spec 0038](specs/0038-modelo-local.md); requisitos vivos em
  [capacidades/provedores.md](specs/capacidades/provedores.md).
- **Resultado:**
  - o adapter `ollama`, a cascata no gateway e a escalada da conversa, com 14 testes novos e nenhuma chamada paga;
  - sem o Ollama instalado, o terminal termina com a mensagem do que conferir, e o registro de uso não ganha linha.
- Veja a [validação do lote 38](migracao/validacao-lote-38.md).

### Decisões e resultado do lote 38, Etapa 3 (18/10/2026)

- **Decisões do pesquisador:**
  - autorizou instalar o Ollama, baixar o `qwen3.5:9b` quantizado, criar o `aliado-local` e medir memória,
    velocidade e escalada;
  - com a linha lenta, deixou baixando;
  - fechou os programas pesados para o modelo carregar.
- **Resultado:**
  - **Instalação:** o Ollama 0.40.6 e o modelo, conferidos.
  - **Memória:** 22 camadas na placa (3,9 GB). Com `use_mmap`, os pesos fora da placa vêm do SSD, e a reserva fica
    em 6,6 GB, em vez de 8,6 GB.
  - **Velocidade:** saída de 15 a 16 tokens/s; com raciocínio, uma resposta da biblioteca leva de 1 a 4 minutos.
  - **Escalada nas 16 perguntas reais da biblioteca, sem custo:**
    - 3 respondidas pelo local;
    - 8 direto ao Gemini, porque o documento ou as páginas inteiras passam de 4 páginas de PDF;
    - 3 refeitas pelo Gemini, porque o local citou sem as marcas;
    - 1 com o pedido de ajuda no meio do texto, que apareceu na tela e foi corrigido.
- **Para o próximo lote, a escolher por ele:**
  - ler o documento e as páginas como texto no local;
  - as marcas de citação no local;
  - o raciocínio nos trechos;
  - o roteador na E3.

### Decisões e resultado do lote 39 (18/10/2026)

- **Decisões do pesquisador:**
  - ligou o modelo local no `.env`;
  - escolheu como próximo lote a leitura das páginas como texto no local.

  Escopo na [spec 0039](specs/0039-local-le-texto.md); requisitos vivos em
  [capacidades/provedores.md](specs/capacidades/provedores.md): PRV-01 e PRV-03 alterados e PRV-06, novo.
- **Resultado nas 16 perguntas reais, sem custo:**
  - o local respondeu 6, contra 3;
  - 3 citaram o documento esperado, contra 1;
  - 7 foram direto ao Gemini, agora pelo contexto de 16 mil tokens: só as regras e a skill somam cerca de 7 mil;
  - 3 foram refeitas por citação;
  - 806 testes passam.
- **Para o próximo lote, a escolher por ele:**
  - o contexto de 32 mil tokens, com 20 camadas na placa: 6 das 7 caberiam;
  - o identificador entre crases na conferência;
  - o raciocínio desligado na reescrita da busca, que levou 2 minutos;
  - o roteador na E3.
- Veja a [validação do lote 39](migracao/validacao-lote-39.md).

## Depois da 0.8.0

| Lote | Entrega | Situação |
|---|---|---|
| 45 | Comparação real das 16 perguntas: o modelo local com escalada × o Gemini direto | Executada em 20/10/2026, sem mudança no produto: Gemini direto 80% mais rápido; 4 respostas locais descartadas ([spec 0045](specs/0045-comparacao-real.md), [validação](migracao/validacao-lote-45.md)) |
| 46 | Correções do relatório de eficiência, conferidas com as medições: citação do local, marca inequívoca, parada cedo, reescrita por partes e cache da Ciência | Validado em 20 e 21/10/2026: 827 testes; o local respondeu 12 das 16 perguntas reais, contra 10; aguarda revisão e commit ([spec 0046](specs/0046-correcoes-do-relatorio.md), [validação](migracao/validacao-lote-46.md)) |
| 47 | Roteador na P7 e na E3 e intervalo de páginas nas marcas | Validado sem modelo em 21/10/2026: só a P7 e a E3 mudaram de rota, e as duas agora vão à biblioteca; aguarda revisão e commit ([spec 0047](specs/0047-roteador-e-intervalos.md), [validação](migracao/validacao-lote-47.md)) |
| 48 | Sem raciocínio no local na leitura de páginas e do documento, medido com critério fixado antes | Adotado em 21/10/2026: chamada mediana de 133 para 71 s; 1 descarte em 12; documento esperado citado em 10 de 12; aguarda revisão e commit ([spec 0048](specs/0048-raciocinio-nas-paginas.md), [validação](migracao/validacao-lote-48.md)) |

### Decisões e resultado do lote 46 (20 e 21/10/2026)

- **Pedido:** o pesquisador pediu as correções e os testes do relatório de eficiência em PDF, seguindo os lotes 44 e
  45. O relatório foi conferido afirmação por afirmação; a versão corrigida está em
  [docs/revisao](revisao/2026-10-20-relatorio-eficiencia-conferido.md).
  - **O diagnóstico de memória e de prefill não confere:** o cache já é q8_0, o modelo é híbrido e o pico cabe na
    placa.
  - **O tempo vai para o raciocínio oculto:** 54% do tempo das respostas locais, medido.
- **Decisões do pesquisador:** as quatro correções do chat, a chave do cache da Ciência, a medição das 16 perguntas
  só no local com o Gemini simulado e a configuração do Ollama mantida.
- **Correções:**
  - instruções do local sem identificador de exemplo;
  - marca que aponta um só trecho enviado aceita como ele;
  - parada do local na primeira marca que não confere;
  - o plano das perguntas com partes, que nunca chamava o modelo desde a 0.6.0;
  - o cache dos erros ligado aos pesos.
- **Resultado:**
  - 827 testes;
  - o local respondeu 12 das 16 perguntas, contra 10;
  - as respostas descartadas por marca caíram de 4 para 2, as duas paradas cedo;
  - nenhum token pago.
- **Para o próximo lote, a escolher por ele:**
  - medir o raciocínio desligado nas páginas e no documento;
  - aceitar intervalos de páginas nas marcas (a E2);
  - o roteador na E3 e na P7;
  - a subida da escada que volta ao local depois da escalada;
  - a folga da placa depois do erro 500 passageiro da P6;
  - o arquivo oficial dos erros da rodada.

### Decisões e resultado do lote 47 (21/10/2026)

- **Pedido:** o pesquisador pediu que eu decidisse o próximo passo com um planejamento. Decidi corrigir primeiro o
  que se prova sem gastar nada; o raciocínio desligado nas páginas fica para o lote 48, com critério de adoção fixado
  antes da medição.
- **Correções:**
  - a P7 ("como se calcula a confiabilidade…") e a E3 (o TCC da UFSC) vão à biblioteca, e não mais aos resultados;
  - o intervalo de páginas numa marca, como o da E2, vale quando todas as páginas foram enviadas.
- **Resultado sem modelo:** nas 16 perguntas aprovadas, só a P7 e a E3 mudaram de rota; as outras 14 ficaram
  idênticas às do lote 46.

### Decisões e resultado do lote 48 (21/10/2026)

- **Decisão (planejamento aprovado em 21/10):** desligar o raciocínio do local nas leituras de páginas e do
  documento só se uma medição passasse em três critérios fixados antes. Limites: no máximo 30 chamadas locais e
  nenhum token pago.
- **Resultado, com 21 chamadas locais:** os três passaram.
  - A chamada mediana caiu de 133,0 para 71,3 s.
  - Houve 1 descarte em 12, contra 2 em 12 na base.
  - O documento esperado foi citado em 10 de 12.
  - A mudança foi adotada no provedor local (PRV-07).
- **Lote 47 com o modelo real:** a P7 caiu de 201 para 74 s e passou a citar o manual esperado; a E3 passou a citar
  o TCC.
- **Para o próximo lote, a escolher por ele:**
  - o `[K1]` copiado do exemplo `[K1][K2]` das regras comuns, o único descarte da medição;
  - a folga da placa;
  - o arquivo oficial dos erros da rodada.

## Specs de cada lote

As specs 0001 a 0033 são o registro de cada lote, sem alteração; o que vale hoje está em
[specs/capacidades](specs/capacidades/).

| Lotes | Spec |
|---|---|
| 01 | [0001](specs/0001-fundacao.md) |
| 02 | [0002](specs/0002-preparacao-triagem.md) |
| 03 | [0003](specs/0003-diretrizes-aprovadas.md) |
| 04–06 | [0004](specs/0004-biblioteca-documental.md), [0005](specs/0005-aprendizados.md), [0006](specs/0006-ciencia-geral.md) |
| 07 | [0007](specs/0007-decisoes-cenarios-skills.md) |
| 08 (correções) | [0008](specs/0008-correcoes-revisao.md) |
| 09–17 | [0009](specs/0009-gemini-uso-real.md), [0010](specs/0010-interface-local.md), [0011](specs/0011-memoria-persistente.md), [0012](specs/0012-busca-web.md), [0013](specs/0013-gpvs-protocolo-m14.md), [0014](specs/0014-autoencoders-limiar.md), [0015](specs/0015-avaliacao-m13.md), [0016](specs/0016-fmeca.md), [0017](specs/0017-lancamento.md) |
| 18–26 | [0018](specs/0018-biblioteca-memoria-anexos.md), [0019](specs/0019-qualidade-da-busca.md), [0020](specs/0020-aba-ciencia.md), [0021](specs/0021-gpvs-interface.md), [0022](specs/0022-correcoes-confianca.md), [0023](specs/0023-aba-ciencia-nova.md), [0024](specs/0024-inicio-das-falhas.md), [0025](specs/0025-confiabilidade-por-componente.md), [0026](specs/0026-resultados-no-chat.md) |
| 27–33 | [0027](specs/0027-tela-envios-e-fontes.md), [0028](specs/0028-grafo-no-obsidian.md), [0029](specs/0029-indexacao-figuras-e-frases.md), [0030](specs/0030-leitura-integral.md), [0031](specs/0031-roteador-e-escada.md), [0032](specs/0032-busca-e-memoria.md), [0033](specs/0033-reescrita-aprendizado-resultados.md) |
| 34 | [0034](specs/0034-experimentos.md) |
| 35 | [0035](specs/0035-chat-tela-minima.md) |
| 36 | [0036](specs/0036-mestrado-fora-do-nucleo.md) |
| 37 | [0037](specs/0037-paginas-sem-leitura.md) |
| 38 | [0038](specs/0038-modelo-local.md) |
| 39 | [0039](specs/0039-local-le-texto.md) |
| 40 | [0040](specs/0040-contexto-32k.md) |
| 41 | [0041](specs/0041-local-mais-rapido.md) |
| 42 | [0042](specs/0042-local-na-vram.md) |
| 43 | [0043](specs/0043-temperatura-local.md) |
| 44 | [0044](specs/0044-revisao-fechamento.md) |
| 45 | [0045](specs/0045-comparacao-real.md) |
| 46 | [0046](specs/0046-correcoes-do-relatorio.md) |
| 47 | [0047](specs/0047-roteador-e-intervalos.md) |
| 48 | [0048](specs/0048-raciocinio-nas-paginas.md) |

## Fica para a v1

Site com domínio e acesso de vários usuários com convite, MCP (M15), roteador de
modelos com fallback e observabilidade, e importação das memórias antigas.

## Entradas necessárias do pesquisador

| Lote | Entrada |
|---|---|
| 09 | Atendido: `gemini-3.8-flash` (flash) e `gemini-3.5-flash-lite` (flash_lite) |
| 10–11 | As referências, enviadas pelo chat quando ele estiver pronto |
| 13 | Local dos dados do GPVS e versão do repositório antigo usada como referência do pipeline |
| 16 | Decisões sobre NPR e reparos, em perguntas e respostas |
