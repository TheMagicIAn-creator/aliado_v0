# Registro de mudanças

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). As versões
seguem o [versionamento semântico](https://semver.org/lang/pt-BR/).

## [0.4.0] — 2026-10-03

Lotes 27 a 29, a partir do uso real. Detalhes nas specs [0027](docs/specs/0027-tela-envios-e-fontes.md),
[0028](docs/specs/0028-grafo-no-obsidian.md) e [0029](docs/specs/0029-indexacao-figuras-e-frases.md).

### Adicionado

- **Figuras e tabelas na biblioteca.** Antes, de uma página com figura o índice guardava só a legenda.
  - **Texto dentro das figuras:** ao indexar, o Tesseract lê o recorte de cada figura embutida, e o que a página ainda não tem entra como trecho próprio. Sem custo.
  - **Descrição pelo modelo:** na ficha do documento, **Descrever figuras e tabelas** envia cada página com figura, desenho, tabela ou legenda ao modelo, como imagem, numa chamada por página. Só por pedido: o aviso diz o número de chamadas, o modelo e a estimativa de tokens, e dá para parar no meio sem perder o que já foi lido.
  - O modelo propõe e o código confere: o rótulo ("Figure 2") e a legenda só ficam se estiverem no texto da página, e a parcela das palavras e dos números que também aparecem na página fica registrada.
  - Cada figura ou tabela vira um trecho próprio, marcado como descrição automática. A legenda achada na busca traz a descrição junto, e a resposta a usa sem aspas, com o aviso de conferir no original.
  - Comandos `biblioteca figuras` (sem `--executar`, só mostra as páginas e a estimativa) e `biblioteca reindexar`.
- **Trechos por frase:** os trechos da busca passam a ser frases inteiras, com até 110 tokens e sem repetir o fim do anterior. A legenda de figura ou tabela começa sempre um trecho novo. Trechos sem pontuação no fim caíram de 86% para 25%; os que restam são linhas de tabela, fórmulas, legendas e frases que continuam na página seguinte.
- **Reindexar sem ler de novo:** `biblioteca reindexar` refaz os trechos a partir do texto de página já guardado, sem repetir o reconhecimento de texto e aproveitando os vetores que não mudaram. A extração anterior continua guardada.
- **Na biblioteca de hoje,** 1.291 das 1.293 páginas com figura ou tabela foram descritas pelo modelo maior: 1.539 figuras e tabelas, com 2,0 milhões de tokens de entrada e 1,4 milhão de saída.
- **Perguntas de referência sobre figuras e tabelas:** 16 perguntas novas, medidas pela página esperada. Antes, nenhuma trazia o conteúdo da figura; agora 12 trazem com a pergunta direta e 9 com a consulta reescrita do chat.

- **Espelho para o Obsidian** em `data/obsidian/`, para ver no grafo como as conversas, os documentos e as anotações se ligam e crescem.
  - Uma nota por conversa, uma por documento da biblioteca e uma de anotações por fonte (documento ou conversa). Cada documento citado numa resposta vira um link.
  - As notas são refeitas sozinhas depois de cada resposta e quando a biblioteca ou a memória mudam, sem chamadas pagas.
  - O caminho é um só, do AL-IAdo para o Obsidian: edições nas notas geradas são substituídas, e as suas notas não são tocadas.
  - Cada arquivo leva a data do registro, para a animação do grafo mostrar o crescimento real (no Windows). As cores do grafo por pasta são criadas na primeira vez.
  - As notas não levam caminhos de pasta do computador, e o texto das respostas é limpo do que o Obsidian executaria ou buscaria na rede.
  - `aliado web --sem-obsidian` desliga o espelho.

- **Aviso de envios no canto inferior direito**, visível em todas as abas, no lugar dos cartões que ficavam no chat.
  - No chat, fica logo acima da caixa de mensagem. A área da aba termina acima dele, e ele não cobre nenhum botão.
  - Com um documento: o nome, a etapa e a barra. Com vários: quantos estão prontos, a barra geral e o documento atual.
  - As etapas aparecem em palavras: leitura das páginas, reconhecimento de texto, indexação e fichas.
  - Falhas e documentos indexados só em parte ficam até serem fechados. Recarregar a página traz o aviso de volta.
- **Avanço dentro da indexação:** o progresso é informado a cada 32 trechos, com os mesmos vetores de antes.
- **Passagem com os trechos vizinhos:** cada trecho recuperado vai ao modelo com o anterior e o seguinte da mesma página. A definição da NASA para MCC, que chegava cortada, passa a chegar inteira.
- **O que a busca trouxe e a resposta não citou:** a resposta mostra "citou 2 dos 6 documentos que a busca trouxe", e a janela de fontes lista os outros, com a passagem.

### Alterado

- **Índice limpo:** as linhas de cabeçalho e de rodapé que se repetem nas bordas das páginas saem dos trechos (3.292 linhas na biblioteca de hoje). O sumário e a lista de referências ficam marcados e fora da busca comum; voltam quando a pergunta os pede. Um trecho repetido palavra por palavra entra uma vez. O texto guardado de cada página não muda.
- **O que sai do computador:** a descrição das figuras envia páginas dos documentos ao Gemini como imagem. Antes, só trechos de texto iam. Ela nunca roda sozinha.
- **Busca:** as descrições de figuras ficam fora da parte da busca que compara palavras e chegam pelo significado ou junto com a legenda. Com elas, a biblioteca de hoje foi de 13.953 para 20.000 trechos, e cada busca de 2,65 s para 3,9 s.
- **Perguntas de referência do lote 19:** com a consulta reescrita, as 16 continuam acertando; em 3 delas o documento esperado desceu de posição (de 0,94 para 0,84 na média do primeiro acerto). Com a pergunta direta, os acertos foram de 13 para 14.
- **Tela inicial:** abrir ou recarregar a página cai sempre na apresentação. As conversas continuam na lista.
- **Respostas com várias fontes:**
  - a regra passa a pedir o que cada documento recuperado diz, mesmo quando o pedido fala em "uma fonte ao menos";
  - os documentos que não tratam do pedido não são mencionados nem comentados na resposta: a janela de fontes já os mostra;
  - os trechos vão ao modelo agrupados por documento, com a contagem de documentos distintos;
  - citações diretas vêm no idioma original, com a tradução identificada.
- **Fichas depois da indexação:** o documento fica pronto para a busca assim que é indexado. Com vários arquivos, todos são indexados antes de qualquer ficha.
- **Teto de tamanho da resposta:** de 4.096 para 8.192 tokens, porque o raciocínio do modelo conta nele. Uma resposta cortada aparece com aviso e fica fora do histórico.
- **Envios:** a página manda até três arquivos de cada vez, e uma falha reaparece mesmo com o aviso fechado ou recolhido.
- **Medição com 113 respostas pagas**, antes e depois, em 14 pedidos de definição, 2 controles e o caso real:
  - o Flash já citava todos os documentos que tratam do pedido; o Flash-Lite cita cerca de três quartos, antes e depois;
  - no Flash-Lite, as respostas com uma fonte só caíram de 3 em 14 para 1 em 16, e o caso real foi de 1 para 2 fontes;
  - as citações diretas que conferem com a passagem foram de 18 para 83 no Flash e de 0 para 10 no Flash-Lite;
  - no Flash, a primeira versão da regra fazia 13 de 21 respostas comentarem documentos que não tratam do pedido. Com a frase ajustada, nenhuma comenta, e os documentos citados fora do assunto caíram de 1,28 para 0,56 por resposta;
  - no Flash, as respostas ficaram com cerca do dobro do tamanho de antes (de 459 para 879 tokens de saída), pelas citações no original com a tradução.

### Corrigido

- Um erro inesperado na leitura ou nas fichas deixava o envio preso em andamento e bloqueava o apagar de documentos.
- "Completar fichas" podia pagar duas vezes pela ficha de um documento enviado enquanto a tarefa esperava.
- A aba Biblioteca tinha rolagem lateral em telas estreitas quando havia fichas pendentes.
- Referências, itens de norma e traduções das respostas por documento eram contados como números sem marca de resultado.
- A união de trechos vizinhos cortava repetições em texto repetitivo, e uma página com texto repetido mandava o mesmo parágrafo duas vezes ao modelo.
- Um erro de arquivo no envio chegava à tela com código do sistema e caminho de pasta.
- No Windows, ler uma conversa no instante em que ela era regravada podia fazer a gravação falhar. Leitura e gravação do mesmo arquivo de conversa não se cruzam mais.
- O leitor de PDF não aceita chamadas simultâneas, e o processo podia cair com um envio e uma descrição de figuras ao mesmo tempo. Todo uso dele passa por uma trava.
- Com vários pedidos ao Gemini começando juntos, a conexão de um podia ser fechada pela criação da de outro.
- Uma resposta do Gemini cortada no meio de uma saída estruturada não entrava no registro de uso, embora fosse cobrada.

## [0.3.0] — 2026-10-01

Lotes 22 a 26, a partir da avaliação da 0.2.0 pelo pesquisador para o mestrado. Detalhes nas specs
[0022](docs/specs/0022-correcoes-confianca.md), [0023](docs/specs/0023-aba-ciencia-nova.md),
[0024](docs/specs/0024-inicio-das-falhas.md), [0025](docs/specs/0025-confiabilidade-por-componente.md) e
[0026](docs/specs/0026-resultados-no-chat.md).

### Adicionado

- **Resultados da pesquisa no chat.** Na skill do mestrado, o interruptor **Usar resultados** vem ligado e pode ser desligado.
  - O agente recebe 8 blocos com os números da aba Ciência: a avaliação oficial de 27/09 (resumo, alarmes falsos, comparação e cada tipo de falha), a reanálise de 30/09 (sempre marcada como secundária), a FMECA e a confiabilidade por grupo.
  - Os blocos saem das mesmas funções da aba, com a mesma escrita dos números e as notas dos indicadores.
  - Cada número tirado deles leva a marca **[Rn]**, que abre o bloco na janela de fontes, com a tabela, as notas e o botão **Ver na aba Ciência**.
  - O chat não calcula: para um número que não está nos blocos, ele indica a seção da aba.
- **Conferência dos números.** Cada número marcado é comparado ao bloco citado.
  - Só a escrita pode diferir: 2.041 e 2041; 63,7e-6 e 63,7 × 10⁻⁶.
  - Um número arredondado, convertido ou inventado faz a resposta aparecer com um aviso que lista os números, e ela sai do histórico e da memória de conversas.
  - Uma marca [Rn] que não foi enviada troca a resposta por um aviso.
  - No aceite, as 7 respostas com números saíram conferidas, sem nenhum número fora dos blocos.
- **`aliado preparar --resultados`** mostra o pedido com os blocos, sem custo.
- **Tokens do cache** no registro de uso, quando o provedor informa.

- **Início observado das falhas do GPVS.** Os arquivos não marcam o disparo, e a avaliação de 27/09 usou o meio do registro.
  - Um detector de mudança (PELT) sobre as 24 variáveis, sem os autoencoders, acha onde cada falha aparece nos sinais. Nos dois ensaios saudáveis, ele não acha mudança nenhuma.
  - Em 8 ensaios, a mudança é clara: F1, F2, F3 e F5, nos dois modos. Em F1, F2 e F3, ela vem de 1,5 a 3,8 s depois do meio.
  - F6 e F7 mudam pouco, e F4 não muda. Esses ensaios ficam no meio.
- **Reanálise dos mesmos escores com o início observado** (`aliado ciencia reanalisar-gpvs`):
  - sem rodar os modelos de novo e registrada como consulta nº 2 ao teste; a avaliação de 27/09 continua sendo a oficial;
  - com o início nominal, repete o relatório oficial bit a bit;
  - com a mudança, a detecção não muda (Denso 10 de 14 e AE-LSTM 8 de 14), e o atraso mediano cai de 2,04 s e 1,70 s para 60 ms;
  - nos 8 ensaios de mudança clara, a sensibilidade vai de 0,67 para 1,00 nos dois modelos. A demora de 27/09 era a espera até a falha aparecer nas variáveis.
- **Alarmes falsos estimados pelo encadeamento das janelas** (cadeia de Markov, Brook e Evans, 1972): Denso com 19 por hora (0 a 53) e AE-LSTM com 56 por hora (0 a 263), nos 52 s saudáveis. A cadeia previu 3,9 e 5,3 sequências de 2 janelas, e houve 4 e 5.
- **Faixa esperada pelo limiar:** com o limiar no 191º de 192 escores de calibração, a chance de alarme por janela fica entre 0,13% e 2,87% (Vovk, 2012). O observado cabe nela.
- **Confiabilidade por componente:** um painel para cada grupo da FMECA, com R(t) e F(t) nas duas bases de tempo (linha cheia na operação, tracejada no calendário) e um seletor entre elas. Um gráfico reúne os 4 grupos.
- **Disponibilidade de cada grupo** (`docs/pesquisa-inversores/reparos.json`), em dois cenários conferidos nas páginas:
  - o reparo ativo do IEEE 493-2007 (inversores, 26 h, Tab. 10-4, p. 290);
  - a parada de campo de Baschel et al. (2018), com 1 dia para detectar e 5 para reparar (Fig. 7);
  - a disponibilidade vai de 99,09% a 99,99%, e a CCB para até 80 h por ano.
- **Matriz de criticidade S × O** na FMECA, com a detecção no rótulo.
- **Seção "Início das falhas" na aba Ciência**, com o início por ensaio, os indicadores com cada início, a sensibilidade e o atraso por ensaio e a comparação. Os escores ganharam a linha da mudança observada.

- **Aba Ciência nova**, organizada pelas perguntas: Resumo · Escores por ensaio · Métricas por falha · Confiabilidade · FMECA · Explorar · Rodar e arquivos.
  - **Resumo:** a comparação Denso × AE-LSTM por objetivo, os indicadores de cada modelo e as matrizes de confusão, com filtro por falha e por ensaio.
  - **Escores por ensaio:** um contêiner por ensaio, com um carrossel na ordem Denso → AE-LSTM → Ambos, no mesmo tamanho e na mesma escala. "Mostrar em todos" troca o gráfico de todos os ensaios de uma vez. Mostram escore ÷ limiar em escala log, as fases, o início nominal e os alarmes.
  - **Métricas por falha:** barras agrupadas por tipo de falha, mapas de calor por ensaio e as métricas gerais com a faixa dos 5 treinamentos repetidos.
  - **Gráficos em D3 v7**, copiado do projeto antigo, com as cores das figuras da dissertação.
  - **Exportação:** SVG e PNG de 300 dpi em fundo branco, e CSV que o Excel em português abre direto.
  - **Uma nota em cada índice e indicador**, ao passar o mouse, ao focar ou ao tocar.
  - As telas mostram os dados em palavras, sem os códigos internos do protocolo.

- **Consulta da busca reescrita:** com a biblioteca ligada, o modelo mais barato transforma cada mensagem numa consulta completa. O assunto vem da conversa, as siglas vão por extenso, e os termos vão em português e em inglês.
  - Continuações como "Traga a definição… uma citação direta" passam a achar o assunto da pergunta anterior.
  - A busca não se prende a um autor só porque a resposta anterior o citou.
  - Nas 16 perguntas de referência, os acertos foram de 13 para 16 e o MRR, de 0,78 para 0,97.
  - Custa uma chamada barata a mais por mensagem, e se ela falhar, a busca segue pela própria pergunta.
  - A janela de fontes mostra o que foi buscado.
  - `aliado biblioteca avaliar --reescrever --env-file .env` mede a busca do mesmo jeito.
- **Mais referências por resposta:** a busca do chat traz 10 trechos em vez de 6, e, quando documentos diferentes tratam do pedido, a resposta mostra a opção de cada fonte, com a citação, para você escolher.
- **Fonte do texto:** um seletor na barra do topo troca a letra da interface. Há 8 opções: Padrão, Arial, Calibri, Verdana, Georgia, Cambria, Times New Roman e monoespaçada. A escolha fica guardada no navegador.
- **Apagar documento** na aba Biblioteca (`DELETE /api/biblioteca/{doc}`): tira de vez todas as versões, a extração, o índice e a ficha. O original só sai se nenhum outro documento o usa. As anotações que o agente deduziu do documento são revogadas, e as suas ficam. Enquanto um envio ou as fichas estão em andamento, a biblioteca pede para esperar.

### Alterado

- **Resumo da aba Ciência:** os alarmes falsos por hora passam a usar os 52 s saudáveis (o teste saudável e o trecho antes da falha), e não só os 5 s do teste. O limite superior do Denso cai de 2.050 para 207 por hora. Entram também a estimativa pela cadeia e as janelas saudáveis acima do limiar, com a faixa esperada.
- **Skill do mestrado 0.2.2:** a disponibilidade usa os dois cenários de reparo, e os números dos resultados vêm só dos blocos, com a marca, ou a resposta indica a aba Ciência.
- **Aba Ciência:** os cartões do Resumo e as Métricas por falha mostram 3 casas e o mesmo formato de segundos dos blocos do chat.
- **Custo:** com os resultados ligados, cada pergunta leva cerca de 5,5 mil tokens de entrada a mais.
- **Cenários e FMECA na tela:** "Horizonte de 20 anos (M12)" virou "o das diretrizes da pesquisa", e uma ressalva da FMECA deixou de citar commit e caminho do projeto anterior.
- **Skill do mestrado** (versão 0.2.0):
  - descreve a situação atual: há memória, o acervo tem os PDFs e a aba Ciência executa o experimento;
  - registra a tabela e a página de cada taxa e das notas da FMECA;
  - pede ao modelo que explique em palavras, sem citar os códigos das diretrizes.
  - Nas diretrizes, só a seção "Aplicação e limites atuais" mudou; o texto de M09 a M14 ficou idêntico.
- **Taxas e notas da FMECA conferidas nos PDFs:**
  - Sarquis Filho et al. (2020), Tab. III, p. 3;
  - Baschel et al. (2018), Tab. 1, p. 5 e 6;
  - Cristaldi et al. (2017), Tab. 6, p. 6.
  - Os valores não mudaram. Os 8 cenários e a FMECA citam agora tabela e página.
  - O IGBT de Baschel (8,9e-6/h) é o valor extrapolado dos relatórios de O&M da juwi. O valor que o próprio estudo usa é 11,4e-6/h.

### Removido

- Da biblioteca do pesquisador, os dois recortes do manual de Lafraia (o capítulo 7 e uma digitalização). O manual completo cobre os dois. As 16 anotações deduzidas deles foram revogadas.

## [0.2.0] — 2026-09-28

Lotes 18 a 21, a partir dos apontamentos do pesquisador no uso real da v0.1.0. Detalhes nas
specs [0018](docs/specs/0018-biblioteca-memoria-anexos.md), [0019](docs/specs/0019-qualidade-da-busca.md),
[0020](docs/specs/0020-aba-ciencia.md) e [0021](docs/specs/0021-gpvs-interface.md).

### Adicionado

- **GPVS pela interface** (seção Rodar GPVS da aba Ciência):
  - preparar, treinar e avaliar com progresso e botão de cancelar, pelos próprios comandos do terminal;
  - o treino aceita separação, sementes e teto de épocas, e uma rodada fora da configuração canônica fica marcada como exploratória;
  - uma nova avaliação exige digitar "consultar o teste", entra no registro de consultas ao teste (M14) e é não canônica;
  - no aceite, treino e avaliação pela interface reproduziram bit a bit a rodada de 27/09.

- **Aba Ciência:**
  - resultados com gráficos e tabelas;
  - explorador do limiar (k de 1 a 24 e percentil, só na calibração);
  - explorador de alarme e detecção (k, percentil e m, marcado como exploração pós-teste pelo M14). Com os parâmetros canônicos, ele repete a avaliação de 27/09;
  - confiabilidade que recalcula sem gravar e salva o cenário só com fonte e hipóteses;
  - FMECA com as duas ordens.
  - Os gráficos são em SVG próprio, sem dependência nova.
- **`aliado web --resultados --gpvs`** para escolher as pastas da aba Ciência.

- **Ficha do documento:** título, autores, ano e DOI, lidos do começo do texto pelo modelo mais barato e conferidos no próprio texto. A ficha fica marcada "inferida" até você editá-la. O botão **Completar fichas** cria as que faltam. As fontes e o catálogo mostram "Baschel et al., 2018", e "segundo Baschel" acha o artigo.
- **Medição da busca:** `aliado biblioteca avaliar` mede, com perguntas de referência, os acertos, a posição e a diversidade dos resultados.

- **Perfil na memória:** o que você conta sobre si (nome, instituição, pesquisa) vale em todas as conversas. O revisor guarda até 8 anotações por troca.
- **Memória de conversas:** cada troca fica guardada no computador, e até 3 trocas de outras conversas, parecidas com o assunto, entram como contexto. As conversas que já existiam são indexadas na primeira abertura.
- **Catálogo no modo biblioteca:** o agente recebe a lista dos documentos e responde sobre o acervo.
- **Busca com contexto:** mensagens curtas, como "tente novamente", buscam junto com a pergunta anterior.

### Alterado

- **Busca da biblioteca:**
  - a parte por palavras ignora palavras vazias em português e em inglês e pesa metade da parte por significado;
  - cada documento ocupa no máximo 2 dos 6 resultados (4 se for citado na pergunta).
  - Nas 16 perguntas de referência, os acertos passaram de 12 para 13 e o MRR, de 0,66 para 0,78.
- **Resposta sem citação** no modo biblioteca: aparece com o aviso "Esta resposta não cita trechos dos seus documentos" e entra no histórico. Citação inventada continua bloqueada.
- **Fontes e memória** abrem numa janela sobre a resposta, que fecha com Esc ou com um clique fora. O painel lateral saiu.
- **Anexos:** fila de até 3 cartões com contador; os que dão certo somem em 6 s.
- **Conversa apagada** deixa de ser lembrada. As anotações que saíram dela continuam.
- Sem anotação sobre algo, o agente diz que não tem isso anotado, e não que não tem memória.

### Corrigido

- Anotações e trocas com mais de 128 tokens ficavam sem vetor e nunca eram achadas por semelhança. As que faltam são preenchidas na abertura.
- O navegador guardava versões antigas da interface depois de uma atualização.

## [0.1.0] — 2026-09-27

Primeira versão do AL-IAdo retrabalhado a partir do repositório `mestrado-utfpr`: um agente
local, de uso individual, com a pesquisa em inversores fotovoltaicos como primeira
especialização. O detalhe de cada lote está nas [specs](docs/specs/) e no
[mapa de migração](docs/migracao/README.md).

### Núcleo e provedores

- **Contratos e gateway** para OpenAI e Gemini, com aliases configurados no `.env`, sem modelo presumido.
- **Registro local de uso:** data, modelo, tokens (inclusive de raciocínio) e número de buscas, nunca o texto.
- **Skills do AL-IAdo:** `pesquisa-inversores` 0.1.5, `confiabilidade` e `engenharia`, com as decisões M01–M16.

### Interface local

- **Navegador em `127.0.0.1`**, sem login: conversas com histórico e lixeira, respostas em fluxo com botão de parar, escolha de skill e modelo, e tokens por resposta.
- **Envio de PDF, Markdown e JSON pelo chat**, com progresso por página, ficha de leitura e citações com trecho e página.
- **Fórmulas** com KaTeX incluído no pacote, sem CDN.

### Biblioteca, memória e web

- **Biblioteca:** OCR em português e inglês, versão Markdown de cada documento e busca híbrida com encoder local de revisão fixa.
- **Memória persistente por origem:**
  - o feedback do pesquisador vale na hora, e as inferências ficam marcadas;
  - conflitos ficam para decisão do pesquisador, e correções nunca apagam o histórico;
  - apagar uma conversa não apaga a memória.
- **Busca na web** pelo Gemini, com fontes numeradas e separadas dos documentos, e "Conferir na web" para as anotações.

### Ciência

- **Cálculos RAM** por cenário explícito: confiabilidade exponencial e Weibull, sistemas em série e em paralelo, mantenabilidade e disponibilidade inerente. Taxas horárias são convertidas pelo serviço (`time_base`).
- **8 cenários dos quatro grupos** da FMECA, em duas bases temporais.
- **FMECA:** NPR calculado das notas da fonte e, separada, a leitura pelas taxas (MTBF, chance de falhar e falhas esperadas).

### Experimento de detecção (GPVS)

- **Protocolo M14 executável:** divisão 50/15/15/20 com 11 janelas de separação, normalização só no treino e verificação de autocorrelação.
- **Autoencoders Denso e AE-LSTM** (PyTorch 2.12.0, CPU):
  - parada pela validação e limiar p99 na calibração;
  - 5 sementes e configuração congelada com hashes;
  - com a configuração da origem, reproduzem os modelos antigos bit a bit.
- **Avaliação M13:**
  - alarme com 3 janelas seguidas;
  - falsos alarmes por hora com limite superior, detecção e atraso por ensaio;
  - bootstrap em blocos e comparação pareada por objetivo, sem vencedor geral.

### Não incluído

- Site com domínio e vários usuários, MCP, roteador de modelos e importação das memórias antigas, previstos para a v1.
- Disponibilidade dos inversores, por falta de fonte de tempo de reparo.
