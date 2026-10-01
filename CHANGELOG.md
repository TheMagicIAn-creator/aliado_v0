# Registro de mudanças

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). As versões
seguem o [versionamento semântico](https://semver.org/lang/pt-BR/).

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
