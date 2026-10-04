# Lote 28 — o AL-IAdo no grafo do Obsidian

Lote autorizado em 03/10/2026, sobre o commit `436582a` (lote 27). O pesquisador quer abrir os dados do AL-IAdo
no Obsidian para ver o grafo crescer: as conversas, os documentos da biblioteca e as anotações da memória.

## O que a investigação mostrou

- **Os dados não eram legíveis pelo Obsidian.** As conversas ficam em JSON (`data/conversas/`), a memória num
  banco SQLite (`data/memoria/`) e a biblioteca noutro. O Obsidian monta o grafo com notas em Markdown ligadas
  por `[[links]]`.
- **O que há para ligar:**
  - cada resposta guarda os documentos citados, as anotações usadas e criadas e as conversas lembradas;
  - das 252 anotações da memória, 244 vieram das fichas de leitura dos documentos;
  - todos os 26 documentos têm uma referência curta única ("Lafraia, 2001").
- **A raiz do repositório foi aberta como cofre** em 03/10, e a pasta `.obsidian/` criada ali não estava
  ignorada pelo Git.
- **Uma corrida de arquivos no Windows.** Ler um arquivo de conversa no instante em que ele é regravado fazia
  a gravação falhar, e a resposta em andamento se perderia. Qualquer leitor a mais das conversas esbarraria nisso.
- **A linha do tempo do grafo** (o botão "Animate" do Obsidian) segue a data de criação de cada arquivo.

## Decisões do pesquisador (03/10)

| Tema | Decisão |
|---|---|
| Nós do grafo | Conversas, documentos e memórias. |
| Memórias | Agrupadas por fonte, numa nota própria ligada ao documento ("Anotações – Lafraia, 2001"). |
| Local | Pasta própria fora do Git, `data/obsidian/`, aberta como cofre separado. |
| Atualização | Automática, depois de cada resposta, sem botão. |

A decisão revê o registro de arquitetura, que tratava o espelho do Obsidian como integração posterior e nunca
como efeito de outra ação. O caminho é um só, do AL-IAdo para o Obsidian. Não há chamadas pagas.

## Escopo implementado

### Notas geradas

- **`Conversas/AAAA-MM-DD <título>.md`**, uma por conversa com mensagens; as da lixeira ficam de fora.
  - Propriedades: tipo, criada, atualizada e perguntas.
  - Cada troca aparece como "Pergunta N", com a data, e "Resposta".
  - As marcas de citação viram texto legível:
    - a de um documento vira o link da nota dele, com o lugar citado: `[[Lafraia, 2001]] (página PDF 244)`;
    - a de um documento que saiu da biblioteca vira texto simples;
    - a de uma fonte da web vira um link para o site;
    - a de um resultado da pesquisa vira "(resultado da pesquisa: título)".
  - Uma linha simples avisa quando a resposta foi barrada, cortada, ficou fora do histórico ou tem números não conferidos.
  - Um bloco recolhido "Fontes e memória" lista os documentos citados, as fontes da web, os resultados, as anotações usadas e criadas e as conversas lembradas.
- **`Documentos/<referência>.md`**, uma por documento, na versão mais recente que pôde ser lida.
  - O nome é a referência curta da ficha; sem ficha, o nome do arquivo.
  - Propriedades: tipo, arquivo, versão, situação, adicionado e referência; o nome do arquivo entra como nome alternativo.
  - Corpo: a ficha (título, autores, ano e DOI, com a origem "sua" ou "inferida"), as pendências da leitura e as versões.
- **`Anotações/Anotações – <fonte>.md`**, uma por documento ou conversa de onde saíram anotações, com link para a fonte.
  - Primeiro o resumo; depois as anotações em vigor por tipo, com os rótulos da aba Memória ("p. 244 · inferida", "sua", "em conflito").
  - As superadas e as revogadas ficam num bloco recolhido.
  - Anotações de uma versão antiga entram na nota do documento atual.
  - A correção vinda de uma conferência na web fica junto da anotação que ela corrige.
  - As revogadas de documentos que saíram da biblioteca ficam de fora.
  - O que não tem documento nem conversa vai para "Outras anotações".
- **`Sobre esta pasta.md`**: o que há no cofre, como ele é atualizado e uma nota para cada propriedade.
- **Cores do grafo:** conversas em azul, documentos em verde e anotações em laranja. A configuração é criada só quando o cofre ainda não tem uma.
- **Linha do tempo:** cada arquivo recebe como data de criação a do registro (o começo da conversa, a chegada do documento, a primeira anotação). Vale no Windows.

### Segurança do texto

- Os campos saem por lista do que pode sair. Caminhos de pasta do computador, trechos e passagens recuperados nunca vão para as notas.
- O texto das respostas é limpo do que o Obsidian executaria, buscaria na rede ou interpretaria por acidente:
  - HTML cru e imagens viram texto; ficam os links automáticos `<https://…>` e `<mailto:…>` e as marcas `<br>`, `<sub>` e `<sup>` sem atributos, no meio da frase;
  - um link só continua link se o destino for `http`, `https` ou e-mail; os outros (outro protocolo, outra nota, um caminho) viram texto, e as definições de link por referência também, menos as que levam a um site;
  - o comando de plugin de modelos (`<%`) é desfeito em qualquer lugar, também dentro de código e nas propriedades;
  - `[[`, `%%` e `#palavra` são neutralizados;
  - blocos de código cercados ficam como vieram, também dentro de listas e citações; código na linha e fórmulas também; `\(x\)` vira `$x$`, e um `$` solto ("R$ 5") é protegido;
  - a linguagem do bloco de código só fica quando serve apenas para colorir (Python, JSON, LaTeX…). Blocos de linguagens que o Obsidian ou um plugin executa ou desenha (consultas, diagramas, scripts) vão como texto, e a consulta de plugin em código na linha perde o prefixo;
  - dentro de uma fórmula, o que poderia virar HTML, imagem, link, comentário ou etiqueta ganha um espaço, sem mudar a conta;
  - os títulos da resposta descem dois níveis, também os de dentro de citações e listas; o título feito com uma linha de `=` ou `-` vira texto; um bloco de código sem fim é fechado.
- **Conferência do resultado.** O texto que vai para a nota é lido por um analisador de Markdown; só os links gerados pelo AL-IAdo são trocados por uma palavra antes. O texto é refeito numa forma em que nenhuma marcação é interpretada (código e fórmulas inclusive) se ainda sobrar:
  - HTML, imagem ou link de outro tipo;
  - uma marca própria do Obsidian (`[[`, `%%`, `#palavra`) em texto corrido;
  - um bloco de código numa linguagem que não seja só de cores, ou uma consulta de plugin em código na linha;
  - um bloco aberto que engoliria o resto da nota.
  Se nem a forma sem marcação passar, entra uma frase fixa no lugar do texto.
- Títulos, anotações, campos da ficha e pendências, que ocupam uma linha, saem sempre na forma sem marcação. Nas propriedades da nota, `[[` e `<%` são separados por um espaço.
- Um registro malformado (data impossível, campo de outro tipo) não derruba a exportação.
- **Nomes de arquivo:** válidos no Windows e num link; sem ponto no fim; únicos no cofre inteiro, sem diferenciar maiúsculas. O nome repetido que chega depois ganha "(2)", para os links existentes não mudarem.

### Gravação

- Só a nota que mudou é reescrita: uma segunda rodada com os mesmos dados não grava nada.
- Um registro (`.aliado-exportacao.json`) lista o que o AL-IAdo escreveu. Só as notas desse registro, dentro das três pastas, são apagadas quando deixam de existir.
- Arquivos do pesquisador e a pasta `.obsidian/` não são tocados. Um arquivo dele com o mesmo nome de uma nota gerada fica como está: a nota gerada não o cobre.
- Quem diz se dois nomes são o mesmo arquivo é o sistema de arquivos. Uma nota que muda só nas maiúsculas é trocada, e não apagada; dois nomes apenas parecidos ("Weiss" e "Weiß") são arquivos diferentes.
- Uma nota que não puder ser lida, gravada ou apagada agora (aberta em outro programa) não impede as outras; a rodada avisa a falha e a seguinte tenta de novo. Uma nota que não chegou a ser gravada não entra no registro.
- Se uma das três pastas, ou a `.obsidian/`, apontar para outro lugar do computador, nada é gravado nem apagado através dela; as outras pastas seguem.
- Uma falha de leitura dos dados ou do registro cancela a rodada antes de gravar ou apagar: o cofre anterior continua inteiro.

### Disparo automático

- A exportação corre em fila própria, uma rodada por vez. Pedidos que chegam durante uma rodada viram uma rodada a mais.
- **Pontos de disparo:**
  - cada resposta salva, antes do aviso de fim, para valer mesmo se a página for fechada;
  - as anotações criadas pelo revisor;
  - renomear ou apagar conversa;
  - documento indexado, fichas prontas, "Completar fichas", ficha editada e documento apagado;
  - anotação criada, revogada, editada, aceita, mantida ou corrigida pela web;
  - a abertura do servidor.
- Uma falha nunca chega ao chat: sai uma linha simples no terminal, sem caminho, e a próxima mudança tenta de novo.
- **Conversas com trava:** leitura e gravação do mesmo arquivo de conversa não se cruzam mais.
- **Configuração:** ligado por padrão em `<dados>/obsidian`; `aliado web --sem-obsidian` desliga. É recusada a pasta que for, contiver ou ficar dentro de uma pasta que o AL-IAdo usa (conversas, memória, registro de uso, envios, biblioteca, resultados, dados do experimento).

### Repositório

- `.obsidian/` passou a ser ignorada pelo Git.

## Limites assumidos

- O que for escrito numa nota gerada é substituído na próxima atualização.
- Renomear uma conversa, ou mudar a ficha de um documento, troca o nome da nota: o Obsidian vê uma nota apagada e outra criada.
- A data de criação dos arquivos só é gravada no Windows.
- A exportação refaz todas as notas em memória a cada mudança. Com os dados de hoje, leva menos de um décimo de segundo.
- Os links das fontes da web são os endereços de redirecionamento guardados na resposta, que podem expirar.
- A conferência do texto usa as regras gerais do Markdown e procura as marcas próprias do Obsidian. O Obsidian em si não foi usado para conferir: o que ele desenha na tela depende do aceite do pesquisador.
- Diagramas (mermaid) e consultas em blocos de código aparecem como texto, sem serem desenhados.
- Código recuado com quatro espaços, sem cerca, é tratado como texto comum: ganha as mesmas proteções e pode aparecer com barras a mais.
- Notas de rodapé (`[^1]: …`) aparecem como texto, e não como rodapé; uma fórmula em bloco com uma linha em branco no meio aparece como texto.
- Na forma sem marcação, o texto perde os blocos de código, as fórmulas desenhadas e os links; ela só entra quando a conferência acusa algo. Nas 90 mensagens guardadas hoje, não entrou em nenhuma; num teste com 60 mil combinações aleatórias de marcas, entrou em 0,3%.
- Se o registro do cofre for apagado ou ficar ilegível, notas antigas que já deveriam ter saído ficam na pasta até serem apagadas à mão.
- O cofre aberto na raiz do repositório também mostraria a documentação e o texto extraído dos PDFs. O recomendado é abrir `data/obsidian`.

## Fora do escopo

- Trazer para o AL-IAdo o que for escrito no Obsidian.
- Um comando de exportação manual e um indicador na tela.
- Uma nota por anotação, e os trechos recuperados e não citados como ligações.
- Código, dados ou notas do espelho do Obsidian do repositório de origem.

## Critérios de aceitação

- **Testes sem rede:**
  - os links dos três tipos de nota resolvem, e os casos de documento apagado, conversa apagada e versão antiga viram o texto certo;
  - nomes válidos, únicos e estáveis;
  - a limpeza do texto, com código e fórmulas preservados, e textos montados para furá-la conferidos por um analisador de Markdown;
  - nenhum caminho de pasta nem trecho recuperado nas notas;
  - a segunda rodada não grava nada; notas do pesquisador sobrevivem, também com o nome de uma nota gerada; um registro adulterado não apaga fora das três pastas;
  - uma nota ocupada não impede as outras, e um nome que muda só nas maiúsculas não some;
  - a data de criação segue o registro (no Windows);
  - a fila junta pedidos e sobrevive a falhas;
  - leitura e gravação de conversas ao mesmo tempo não falham;
  - os disparos: resposta, revisor, renomear e apagar conversa, envio, ficha, apagar documento e ações de memória;
  - uma falha da exportação não derruba o chat; desligada, ela não cria pasta.
- **Ponta a ponta nos dados reais,** só com leitura sobre `data/`: contagens, links, caminhos e tempo.
- **No navegador,** num servidor de teste com modelo simulado: uma pergunta, um envio e uma anotação atualizam a pasta.
- **Revisão por agentes,** com verificação adversarial.
- **Aceite do pesquisador no Obsidian:** as três cores, a animação e alguns links.
