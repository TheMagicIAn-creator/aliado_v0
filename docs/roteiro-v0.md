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
combinados antes de começar.

| Lote | Entrega | Situação |
|---|---|---|
| 27 | Tela de apresentação ao abrir ou recarregar; aviso de envios em todas as abas, com o documento pronto antes das fichas; respostas com várias fontes: regra reescrita, trechos agrupados por documento, passagem com os trechos vizinhos e a lista do que a busca trouxe e não foi citado | Concluído em 02/10/2026 |

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
