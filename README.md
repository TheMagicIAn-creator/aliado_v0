# AL-IAdo

Agente modular para pesquisa e engenharia, de uso **local e individual**. A pesquisa de
mestrado sobre detecção de falhas em inversores fotovoltaicos é sua primeira
especialização. Versão **0.3.0**. As mudanças estão em [CHANGELOG.md](CHANGELOG.md).

## O que ele faz

- **Conversa pelo navegador** com o Gemini ou a OpenAI, com skills que orientam cada tema.
- **Biblioteca de referências:** PDF, Markdown e JSON enviados pelo chat, com OCR, busca local e citações com a página.
- **Memória persistente:** lembra quem você é, o que você ensina e as conversas anteriores sobre o mesmo assunto. O que o agente deduz fica marcado para revisão, e correções não apagam o histórico.
- **Busca na web** com as fontes citadas.
- **Cálculos de confiabilidade** por cenário explícito e a **FMECA** dos inversores.
- **Experimento de detecção** Denso × AE-LSTM no GPVS-Faults, reproduzível e com relatórios.
- **Resultados no chat:** na skill do mestrado, as respostas usam os números já gravados da pesquisa, com a marca **[Rn]**, e cada número é conferido.

Cálculos, FMECA e experimento rodam por comando próprio ou pela aba **Ciência** da interface; o
chat não os executa sozinho: ele só consulta os resultados já gravados.

## Instalação

Requisitos:
- Windows com Python 3.12 ou superior.
- Rede na primeira instalação, para baixar pacotes e o encoder da busca.
- Para OCR, o [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html) com os idiomas `por` e `eng`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m aliado biblioteca preparar-modelo
```

- **O arquivo `requirements-dev.lock`** fixa o ambiente validado no Windows, com Python 3.12 e 3.14, inclusive o PyTorch só CPU, que ocupa cerca de 550 MB.
- **Em outro ambiente**, use `pip install -e ".[dev,llm,knowledge,science,web,ml]"`. `pip install -e .` basta para listar skills e preparar pedidos.
- **O encoder** é baixado do Hugging Face numa revisão fixa, cerca de 122 MB, com os hashes conferidos, para `data/models/minilm`.
- **O Tesseract** é procurado nesta ordem: em `AL_IADO_TESSERACT_CMD`, no PATH e, por fim, em `data/tools/tesseract/tesseract.exe`. Veja o [guia da biblioteca](docs/biblioteca/uso.md).

Testes:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Nenhum teste chama provedores pagos ou acessa a rede. Os testes que usam os dados reais são pulados se faltar `data/gpvs/`, a avaliação oficial em `data/resultados/` ou o encoder da busca.

## Configuração

Copie `.env.example` para `.env`, que fica fora do Git, e preencha só o provedor que for usar:

- `GOOGLE_API_KEY` e os identificadores reais dos modelos: `AL_IADO_GEMINI_MODEL_FLASH` e `AL_IADO_GEMINI_MODEL_FLASH_LITE`. Por exemplo, `gemini-3.8-flash` e `gemini-3.5-flash-lite`.
- Opcional: `OPENAI_API_KEY` e `AL_IADO_OPENAI_MODEL_LUNA`, `_TERRA` e `_SOL`.
- Opcional: `AL_IADO_TESSERACT_CMD`, se o Tesseract estiver em outro lugar. A interface lê essa variável
  do `.env`; os comandos da biblioteca a leem das variáveis do sistema.

Os campos de modelo recebem identificadores, nunca chaves. O AL-IAdo só lê o `.env` que você
indicar, e variáveis do sistema têm precedência sobre ele.

## Uso no dia a dia: a interface

```powershell
.\.venv\Scripts\python.exe -m aliado web --env-file .env
```

Abre `http://127.0.0.1:8765`, acessível só pelo seu computador. Rode a partir da pasta do projeto.

- **Conversas:**
  - Ao abrir ou recarregar, a página mostra a tela de apresentação; as conversas ficam na lista ao lado.
  - Respostas em fluxo, com botão para parar, e os tokens de cada resposta.
  - Escolha da skill e do modelo.
  - Histórico em `data/conversas/`. Conversas apagadas vão para a lixeira e deixam de ser lembradas; as anotações que saíram delas continuam.
  - O link no fim da resposta abre uma janela com as fontes e a memória usada, que fecha com Esc.
- **Documentos:**
  - Arraste um PDF, Markdown ou JSON para a conversa, ou use o clipe. O arquivo entra na biblioteca `data/bibliotecas/principal`, com progresso por página.
  - Um aviso no canto inferior direito, visível em todas as abas, mostra o avanço dos envios. No chat, ele fica logo acima da caixa de mensagem, e a tela reserva a faixa dele para não cobrir nenhum botão.
    - Com um documento: o nome, a etapa (leitura das páginas, reconhecimento de texto, indexação e fichas) e a barra.
    - Com vários: quantos já estão prontos, a barra geral e o documento atual, que muda quando a indexação dele termina.
    - O documento fica pronto para a busca assim que é indexado; as fichas são criadas depois de todos os arquivos enviados.
    - Tudo certo some em 6 s. Falhas e documentos indexados só em parte ficam até você fechar. Fechar o aviso não cancela o envio.
    - Se você recarregar a página no meio do envio, o aviso volta com os totais.
  - Cada documento ganha uma ficha de leitura na memória e uma **ficha do documento** (título, autores, ano e DOI), conferida no próprio texto e editável na aba **Biblioteca**. **Completar fichas** cria as que faltam.
  - **Figuras e tabelas:** o texto dentro das figuras é reconhecido no seu computador ao indexar. Na ficha do documento, **Descrever figuras e tabelas** envia ao modelo cada página com figura, desenho, tabela ou legenda, como imagem, numa chamada por página. O aviso diz quantas chamadas são antes de enviar, e dá para parar no meio.
    - A descrição entra na busca marcada como automática. A resposta a usa para dizer o que a figura mostra, com o aviso de conferir no original, e a janela de fontes leva à página.
    - O rótulo e a legenda só ficam se estiverem no texto da página.
  - **Trechos:** os trechos da busca são frases inteiras, sem os cabeçalhos e rodapés repetidos das páginas. O sumário e a lista de referências ficam fora da busca comum e voltam quando a pergunta os pede.
  - **Apagar**, na aba Biblioteca, tira o documento de vez, com todas as versões, a extração e o índice, e revoga as anotações que o agente deduziu dele. As suas anotações ficam. Não tem volta.
  - Com **Usar biblioteca**, o agente recebe a lista dos documentos, com autor e ano, e as respostas citam **[n]** com o trecho e a página. Uma resposta que não cita trechos aparece com um aviso.
  - Antes de buscar, o modelo mais barato reescreve a mensagem com o assunto da conversa, as siglas por extenso e os termos em português e inglês. É uma chamada barata a mais por mensagem, e a janela de fontes mostra o que foi buscado.
  - A busca traz até 10 trechos, e cada um vai ao modelo com os trechos vizinhos da mesma página, para a frase não chegar cortada.
  - Em pedidos de definição, conceito ou valor, a resposta apresenta o que cada documento diz, com a citação. Citações diretas vêm no idioma original, com a tradução identificada.
  - A resposta mostra quantos dos documentos trazidos pela busca ela citou, e a janela de fontes lista os outros em **A busca também trouxe**, com a passagem.
- **Fonte do texto:** o seletor **Aa**, na barra do topo, troca a letra da interface entre 8 opções. A escolha fica guardada no navegador.
- **Memória** (`data/memoria/`):
  - O que você diz ou corrige vale na hora; o que o agente deduz fica marcado como "inferida".
  - O que você conta sobre si vira **perfil** e vale em todas as conversas.
  - Cada troca fica guardada, e até 3 trocas de outras conversas, parecidas com o assunto, entram como contexto.
  - Diga "lembre que…" ou use **Lembrar…**.
  - A aba **Memória** mostra histórico, edição, revogação e conflitos para você decidir. Nada é apagado.
  - `data/` fica fora do Git e sem cópia automática. Copie `data/memoria` e `data/conversas` se quiser guardá-los.
- **Resultados da pesquisa no chat:** o interruptor **Usar resultados** vem ligado na skill do mestrado e pode ser desligado; a escolha fica guardada por skill.
  - O agente recebe 8 blocos com os números da aba Ciência: a avaliação oficial de 27/09 (resumo, alarmes falsos, comparação e cada tipo de falha), a reanálise de 30/09 (início das falhas e alarmes estimados, sempre marcada como secundária), a FMECA e a confiabilidade por grupo.
  - Cada número tirado deles leva a marca **[Rn]**, que abre o bloco na janela de fontes, com a tabela, as notas dos indicadores e o botão **Ver na aba Ciência**.
  - O AL-IAdo confere cada número com o bloco citado. Só a escrita pode diferir (2.041 e 2041). Um número arredondado, convertido ou inventado faz a resposta aparecer com um aviso que lista os números, e ela sai do histórico e da memória de conversas.
  - Um número sem marca não é conferido. O chat não recalcula nada: para um número que não está nos blocos, ele indica a seção da aba.
  - Os blocos acrescentam cerca de 5,5 mil tokens de entrada a cada pergunta.
- **Busca na web:** ligue **Buscar na web**. As fontes da web aparecem como **[Wn]**, separadas dos seus documentos. Na aba Memória, **Conferir na web** checa uma anotação.
- **Ciência:** organizada pelas perguntas, com os números da avaliação oficial de 27/09. O navegador só desenha, com gráficos em D3.
  - Cada gráfico pode ser baixado em **SVG** ou **PNG de 300 dpi**, em fundo branco, e cada tabela em **CSV**.
  - Todo índice e indicador tem uma nota **i**.
  - **Resumo:** a comparação Denso × AE-LSTM por objetivo, os indicadores de cada modelo e as matrizes de confusão, com filtro por falha e por ensaio.
  - **Escores por ensaio:** para cada um dos 14 ensaios e o teste saudável, um carrossel (Denso → AE-LSTM → Ambos), com os gráficos no mesmo tamanho. Mostram escore ÷ limiar, as fases, o início nominal e os alarmes.
  - **Métricas por falha:** barras por tipo de falha, mapas de calor por ensaio e as métricas gerais com a faixa dos 5 treinamentos.
  - **Início das falhas:** onde cada falha aparece nos sinais, contra o meio do registro, e os indicadores com cada início. Os números vêm da reanálise dos mesmos escores; a avaliação de 27/09 continua sendo a oficial.
  - **Confiabilidade:** um painel por grupo da FMECA (CCB, contatores, IGBT e ventiladores), com R(t) e F(t) nas duas bases de tempo (4.015 h/ano de operação e 8.760 h/ano de calendário), e um seletor entre elas.
    - A disponibilidade de cada grupo usa dois cenários de reparo: o reparo ativo do IEEE 493-2007 (26 h) e a parada de campo de Baschel et al. (2018), de 6 dias.
    - No fim, um explorador de qualquer λ, que salva o cenário numa pasta nova só com fonte e hipóteses. Aceita também qualquer cenário em JSON.
  - **FMECA:** a tabela, a matriz de criticidade S × O, as ordens pelo NPR e pela taxa e o relatório numa pasta nova.
  - **Explorar:** e se o limiar fosse outro?
    - O limiar usa só a calibração.
    - O alarme reusa os ensaios de teste: serve para explorar, e os números oficiais continuam os de 27/09.
    - Com k = 5, percentil 99 e 3 janelas seguidas, repete a avaliação oficial.
  - **Rodar e arquivos:** preparar, treinar e avaliar pelos mesmos comandos do terminal, uma etapa por vez, com progresso e botão de cancelar, e os resultados gravados.
    - Mudar os ajustes do treino marca a rodada como exploração.
    - Avaliar de novo exige digitar "consultar o teste", fica registrado em `registro-consultas-teste.jsonl` e não substitui a avaliação oficial.
  - As visões e os exploradores precisam de `data/gpvs/` e da avaliação de 27/09 em `data/resultados/`. O erro por variável fica em `data/ciencia/`, e `--resultados` e `--gpvs` mudam essas pastas.
- **Custo:** cada resposta chama o provedor, e a busca na web pode ter custo à parte no Google. O registro `data/uso/chamadas.jsonl` guarda data, modelo, tokens e número de buscas, sem o texto.

## Ver no Obsidian

O AL-IAdo mantém em `data/obsidian/` um espelho em Markdown das conversas, dos documentos e das anotações da
memória, para você ver no grafo do Obsidian como eles se ligam e crescem.

- **Como abrir:** no Obsidian, escolha **Abrir pasta como cofre** e aponte para `data/obsidian`. Abra essa pasta, e não a raiz do projeto: na raiz, o grafo também mostraria a documentação e o texto extraído dos PDFs.
- **O que há no cofre:**
  - **Conversas:** uma nota por conversa. Cada documento citado numa resposta vira um link para a nota dele.
  - **Documentos:** uma nota por documento da biblioteca, com a ficha. O nome da nota é a referência curta ("Lafraia, 2001").
  - **Anotações:** as anotações da memória, agrupadas pela fonte: uma nota por documento e uma por conversa de onde saíram anotações.
  - **Sobre esta pasta:** o que significa cada propriedade das notas.
- **Cores do grafo:** conversas em azul, documentos em verde e anotações em laranja. Elas são criadas só na primeira vez; se você mudar as cores, as suas ficam.
- **Linha do tempo:** o botão de animação do grafo mostra as notas na ordem em que surgiram, porque cada arquivo leva a data do registro (no Windows).
- **Atualização:** as notas são refeitas sozinhas depois de cada resposta e quando a biblioteca ou a memória mudam. Não há chamada paga nisso.
- **Caminho de mão única:** o que você escrever numa nota gerada é substituído na próxima atualização, e nada do que fizer no Obsidian muda o AL-IAdo. Notas suas, criadas fora das pastas Conversas, Documentos e Anotações, não são tocadas.
- **Como as respostas aparecem:** com as fórmulas, as tabelas e o código, como no chat. Imagens, links que não levam a um site e blocos de diagramas ou consultas aparecem como texto. Uma resposta com algo que o Obsidian executaria ou buscaria por conta própria aparece inteira como texto simples.
- **Privacidade:** `data/` fica fora do Git. As notas não levam caminhos de pasta do seu computador.
- **Desligar:** `aliado web --sem-obsidian`.

## Linha de comando

```powershell
.\.venv\Scripts\python.exe -m aliado skills
.\.venv\Scripts\python.exe -m aliado preparar "Quais decisões da pesquisa estão pendentes?"
.\.venv\Scripts\python.exe -m aliado perguntar "Quais taxas foram decididas?" --provider google --model-alias flash --env-file .env
```

- **`preparar`** mostra o pedido montado, sem enviar nada. Com `--resultados`, inclui os blocos de resultados, como no chat.
- **`perguntar`** chama o provedor.
- **A skill** padrão é a da pesquisa, com apoio da skill `confiabilidade`. Troque com `--skill engenharia`, `--skill confiabilidade` ou `--skill nenhuma`; `--apoio` compõe as duas.
- **A biblioteca** também tem comandos próprios:

```powershell
.\.venv\Scripts\python.exe -m aliado biblioteca adicionar "C:\caminho\referencia.pdf" --biblioteca data/bibliotecas/principal
.\.venv\Scripts\python.exe -m aliado biblioteca buscar "tempo médio de reparo" --biblioteca data/bibliotecas/principal
.\.venv\Scripts\python.exe -m aliado biblioteca verificar --biblioteca data/bibliotecas/principal
.\.venv\Scripts\python.exe -m aliado biblioteca avaliar --biblioteca data/bibliotecas/principal --saida data/resultados/busca-001
.\.venv\Scripts\python.exe -m aliado biblioteca reindexar --biblioteca data/bibliotecas/principal
.\.venv\Scripts\python.exe -m aliado biblioteca figuras --biblioteca data/bibliotecas/principal
```

`reindexar` refaz os trechos a partir do texto já guardado, sem ler os arquivos de novo. `figuras` mostra
as páginas com figura ou tabela ainda não descritas e a estimativa de tokens; só com `--executar` ele
chama o modelo.

`avaliar` mede a busca com as perguntas de referência de `data/avaliacao-busca/perguntas.json`,
que ficam fora do Git. Com `--reescrever --env-file .env`, mede com a consulta reescrita, como no chat:
são 16 chamadas ao modelo mais barato. Veja o [guia da biblioteca](docs/biblioteca/uso.md).

## Confiabilidade e FMECA

```powershell
.\.venv\Scripts\python.exe -m aliado ciencia calcular --cenario docs/ciencia/exemplo-sintetico.json --saida data/resultados/exemplo-001 --grafico
.\.venv\Scripts\python.exe -m aliado ciencia fmeca --saida data/resultados/fmeca-001
```

- **Cenários:** cada cálculo parte de um cenário JSON com parâmetros, fontes e hipóteses.
  - Uma taxa em 1/h com horizonte em anos usa `time_base`; a conversão é feita pelo serviço.
  - Os 8 cenários dos inversores (4 grupos × 2 bases) estão em `docs/pesquisa-inversores/cenarios/`.
- **FMECA:** o relatório traz duas leituras separadas, sem fundi-las numa nota:
  - o NPR = S × O × D, calculado das notas de Cristaldi et al. (2017);
  - ao lado, a leitura pelas taxas: MTBF, chance de falhar e falhas esperadas em 1 e 20 anos.
- Modelos e hipóteses estão em [docs/ciencia/confiabilidade.md](docs/ciencia/confiabilidade.md).
- Cada saída vai para uma pasta nova e nunca sobrescreve outra.

## Experimento de detecção (GPVS)

Os 16 CSVs do GPVS-Faults (Bakdi et al., 2020, DOI 10.17632/n76t439f65.1) ficam em
`data/gpvs/`, fora do Git. Junto deles fica `proveniencia.json`, com o SHA-256 de cada
arquivo, conferido a cada preparo.

```powershell
.\.venv\Scripts\python.exe -m aliado ciencia preparar-gpvs --saida data/resultados/gpvs-preparo-001
.\.venv\Scripts\python.exe -m aliado ciencia treinar-gpvs --saida data/resultados/gpvs-modelos-002
.\.venv\Scripts\python.exe -m aliado ciencia avaliar-gpvs --modelos data/resultados/gpvs-modelos-002 --saida data/resultados/gpvs-avaliacao-001
```

1. **Preparo (protocolo M14):**
   - divisão temporal 50/15/15/20, com 11 janelas de separação entre os blocos;
   - normalização ajustada só no treino;
   - verificação de autocorrelação.
2. **Treino:**
   - Denso e AE-LSTM em 5 sementes, com a validação decidindo a parada e o limiar p99 fixado na calibração;
   - tudo congelado com hashes.
   - `--separacao 2 --sementes 42 --teto-epocas 150` reproduz exatamente os modelos da origem.
3. **Avaliação:**
   - alarme com 3 janelas seguidas;
   - falsos alarmes por hora com limite superior, ensaios detectados, atraso em ms e intervalos por bootstrap em blocos;
   - comparação pareada por objetivo, sem vencedor geral.

A avaliação oficial já foi feita em 27/09/2026. Mudanças de protocolo depois disso exigem
uma avaliação independente (M14).

4. **Reanálise com o início observado:**
   - acha onde cada falha aparece nas 24 variáveis, com o PELT e sem os modelos;
   - recalcula as métricas com esse início sobre os mesmos escores de 27/09;
   - estima os alarmes falsos por hora e a faixa esperada pelo limiar;
   - grava numa pasta nova e entra no registro de consultas ao teste.

```powershell
.\.venv\Scripts\python.exe -m aliado ciencia reanalisar-gpvs --saida data/resultados/gpvs-reanalise-001
```

## Pacote

```powershell
.\.venv\Scripts\python.exe -m build --wheel --outdir dist/v0.4.0
```

O wheel inclui a interface, com o KaTeX e o D3 v7 (licença ISC, copiada junto), e as skills do AL-IAdo. Documentação, cenários e dados
ficam no repositório. As skills de `.agents/` e `.claude/` orientam os assistentes de
desenvolvimento e não entram no pacote.

## Documentação

- [Roteiro da v0](docs/roteiro-v0.md): critérios de pronto, lotes, decisões de escopo e os lotes depois da v0.1.0.
- [Specs dos lotes](docs/specs/): o que cada lote entregou, com critérios de aceitação.
- [Mapa de migração](docs/migracao/README.md): o que veio do repositório de origem, com manifestos e validações de cada lote.
- [Regras de colaboração](AGENTS.md).

## Pendências conhecidas

- A 0.3.0 (lotes 22 a 26, no [roteiro](docs/roteiro-v0.md)) trouxe a aba Ciência nova, o início das falhas no GPVS, a confiabilidade por componente com disponibilidade e os resultados no chat. A 0.4.0 (lotes 27 a 29) trouxe a tela de envios, o espelho para o Obsidian e a indexação com figuras, tabelas e trechos por frase.
- A descrição de uma figura é feita por um modelo e pode errar. O que o código confere são o rótulo, a legenda e as palavras que também estão no texto da página; a ligação entre os elementos de um diagrama não tem como ser conferida. Veja a [validação do lote 29](docs/migracao/validacao-lote-29.md).
- Uma página digitalizada sem legenda não entra na descrição das figuras, e uma tabela com mais de 40 linhas é transcrita até a 40ª.
- Com a consulta reescrita do chat, algumas perguntas sobre uma figura específica não acham a página dela: a reescrita troca a referência à figura por termos gerais.
- Cada busca compara a pergunta com todos os trechos, um a um. Com as descrições das figuras, a biblioteca de hoje passou de 14 mil para 20 mil trechos, e a busca de 2,65 s para 3,9 s.
- No chat, a conferência vale para os números com a marca [Rn]. Um número sem marca não é conferido, e o chat não calcula: ele repete o que está gravado.
- Em pedidos de definição, o modelo maior cita todos os documentos que tratam do assunto; o menor cita cerca de três quartos. A janela de fontes mostra o que ficou de fora. Veja a [validação do lote 27](docs/migracao/validacao-lote-27.md).
- Com o modelo maior, as respostas a pedidos de definição ficaram com cerca do dobro do tamanho, pelas citações no original com a tradução. Elas não comentam mais os documentos que não tratam do pedido: a janela de fontes mostra o que a busca trouxe e a resposta não usou.
- Uma resposta que para no limite de tamanho aparece com aviso e fica fora do histórico; a marca do corte só existe para o Gemini.
- Nenhuma fonte traz o tempo de reparo de cada componente: a disponibilidade usa o tempo do inversor inteiro, em dois cenários.
- No GPVS, o início observado vale só para os 8 ensaios de mudança clara. F4 não muda as 24 variáveis, e F6 e F7 mudam pouco: para eles, a falta de detecção é, em boa parte, das variáveis.
- Os alarmes falsos contam com só 52 s saudáveis: a taxa por hora é uma estimativa com intervalo largo.
- Com a consulta reescrita, a busca acerta as 16 perguntas de referência. São só 16 perguntas: um conjunto maior diria mais. Veja a [validação do lote 22](docs/migracao/validacao-lote-22.md).
- Os exploradores da aba Ciência usam só a avaliação oficial de 27/09; rodadas novas aparecem nos arquivos de resultados, em **Rodar e arquivos**.
- Para a v1: site com domínio e vários usuários, MCP, roteador de modelos e importação das memórias antigas.
