# AL-IAdo

Agente modular para pesquisa e engenharia, de uso **local e individual**. A pesquisa de
mestrado sobre detecção de falhas em inversores fotovoltaicos é sua primeira
especialização. Versão **0.8.0**, validada localmente; aguarda revisão e commit do pesquisador. As mudanças estão em [CHANGELOG.md](CHANGELOG.md).

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
.\.venv\Scripts\python.exe -m aliado biblioteca preparar-reordenador
```

- **O arquivo `requirements-dev.lock`** fixa o ambiente validado no Windows, com Python 3.12 e 3.14, inclusive o PyTorch só CPU, que ocupa cerca de 550 MB.
- **Em outro ambiente**, use `pip install -e ".[dev,llm,knowledge,science,web,ml]"`. `pip install -e .` basta para listar skills e preparar pedidos.
- **O encoder** é baixado do Hugging Face numa revisão fixa, cerca de 122 MB, com os hashes conferidos, para `data/models/minilm`.
- **O reordenador de páginas** é uma segunda rede local, cerca de 136 MB, em `data/models/reranker`.
  O preparo confere revisão e hashes; perguntas não baixam modelos. Ele roda só na leitura por páginas
  e não usa tokens de API. Sem os arquivos, a busca continua pela ordem anterior. A pasta pode ser
  indicada em `AL_IADO_RERANKER_DIR`.
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

## Modelo local (lote 38)

Com `AL_IADO_LOCAL_MODEL` no `.env`, um modelo aberto servido pelo [Ollama](https://ollama.com), neste computador,
responde primeiro, sem custo por uso. O Gemini Flash só entra quando o local não dá conta do raciocínio: ele pede
ajuda, erra o formato pedido ou, na conversa, não cita o que a busca trouxe ou erra números. O que o local não alcança
vai direto ao Gemini: a busca na web ou um pedido maior que o contexto dele. As páginas de PDF da leitura vão ao local
como o texto guardado, com a descrição automática das figuras e tabelas, e o Gemini segue recebendo o PDF (lote 39).
A linha sob a resposta diz quem respondeu e por quê. Com o Ollama fechado, o erro diz o que conferir, e nada vai ao
Gemini. Os tokens do local não entram no uso do dia.

A configuração abaixo foi feita e medida neste computador em 18 e 19/10/2026, com o Ollama 0.40.6. O modelo local só passa
a responder depois do passo 5.

1. Instale o Ollama para Windows e baixe o modelo quantizado em 4 bits (Q4_K_M), que lê texto e imagem:
   `ollama pull qwen3.5:9b` (6,6 GB).
2. Crie o modelo do AL-IAdo com um `Modelfile`:

   ```text
   FROM qwen3.5:9b
   PARAMETER num_ctx 32768
   PARAMETER num_gpu 32
   PARAMETER use_mmap true
   PARAMETER temperature 0.6
   ```

   e rode `ollama create aliado-local -f Modelfile`.
   - **`num_ctx`:** o Ollama corta em silêncio o que passa do contexto. O AL-IAdo confere o tamanho antes e manda
     ao Gemini o que não cabe; `AL_IADO_LOCAL_CONTEXT` precisa ter o mesmo número (lote 40: 32.768; antes, 16.384).
   - **`num_gpu`:** o número de camadas na placa de vídeo, das 33. Desde o lote 42, o modelo usa toda a VRAM. Com 32
     camadas, a placa fica em 5,4 GB com o cache em q4_0 (lote 58; com o q8_0, 5,6 GB, com pico de 5,64 GB numa
     entrada de 27 mil tokens), dos 6,0 GB livres. As 33 não
     cabem: com o texto todo na placa, o Ollama põe também o leitor de imagens (0,9 GB). Cada camada soma cerca de
     0,14 GB.
   - **`temperature`:** 0,6 desde o lote 43; o `qwen3.5` vem com 1. Com 0,6, 13 das 16 perguntas reais tiveram o
     mesmo desfecho em duas rodadas, contra 7 com 1. Vale só para as respostas do local: a reescrita, as fichas e as
     figuras já usam 0.
   - **`use_mmap`:** no Windows com placa NVIDIA, o Ollama copia os pesos para a memória e reserva 8,6 GB. Ligado,
     os pesos que não cabem na placa são lidos do arquivo do modelo, no SSD. Com 20 camadas na placa, a reserva medida
     caiu para 6,4 GB, com a mesma
     velocidade.
3. Nas variáveis de ambiente do usuário, para o serviço do Ollama:
   - `OLLAMA_FLASH_ATTENTION=1` e `OLLAMA_KV_CACHE_TYPE=q4_0`: o contexto de 32 mil tokens ocupa 288 MiB, contra
     544 MiB em q8_0 e cerca de 1 GiB sem quantizar. No lote 58, o q4_0 deu 248 MiB a mais de folga na placa, sem
     piorar as respostas nas 16 perguntas de teste;
   - `OLLAMA_NUM_PARALLEL=1` e `OLLAMA_MAX_LOADED_MODELS=1`;
   - `OLLAMA_KEEP_ALIVE=10m`: o modelo sai da memória depois de 10 minutos parado.
4. Antes de usar, feche os programas pesados (navegador, VS Code, Obsidian, WSL ou Docker) e abra o Ollama pelo
   menu Iniciar. O `ollama ps` mostra o modelo carregado e a divisão entre placa e processador.
5. Para ligar: no `.env`, `AL_IADO_LOCAL_MODEL=aliado-local` e `AL_IADO_LOCAL_CONTEXT=32768`, o mesmo número do
   Modelfile, e reinicie o AL-IAdo. O endereço padrão é `http://localhost:11434/v1` (`AL_IADO_LOCAL_BASE_URL`).

**Memória: placa, RAM e SSD (medida).**
- **Só a placa dá velocidade.** A placa calcula o que está na própria VRAM; o resto é calculado pelo processador, a
  partir da RAM. Com 20 camadas (59% na placa), a escrita ia a 15 tokens/s; com 32 (85%), vai a 25.
- **A memória virtual no SSD é reserva, não velocidade:** evita travar quando falta RAM e deixa os pesos serem lidos
  do arquivo do modelo (`use_mmap`). Por isso, desde o lote 42, toda a VRAM vai para o modelo, no lugar do limite de
  4 GB.
- **Placa:** 5,6 GB com 32 camadas e 32 mil de contexto; pico de 5,64 GB numa entrada de 27 mil tokens.
- **RAM:** carregado, o modelo ainda reserva cerca de 8 GB de memória. No Windows, o que um programa reserva na placa
  também conta na memória reservada do sistema, então pôr mais na placa não poupou RAM. O leitor de imagens (0,9 GB)
  fica na RAM.
- **O limite deste computador é a memória reservada:** 35,2 GB, que somam os 16 GB de RAM e cerca de 19,5 GB de
  paginação no SSD. Com os programas do dia abertos, o modelo não carregou; fechando-os, carregou. A paginação é
  configuração do sistema e fica com você.
- **Modelos maiores, lidos do SSD:** ficam em 1 a 3 tokens por segundo e não compensam, porque o caso que o 9B não
  alcança vai ao Gemini Flash.

**Velocidade (medida, com 32 camadas).**
- **Carga:** de 10 a 13 s com o arquivo em cache. A primeira, lendo o SSD, chega a 41 s.
- **Leitura da entrada:** cerca de 1.090 tokens por segundo. Uma entrada de 27 mil tokens leva 25 s.
- **Escrita:** 25 tokens por segundo com pouco contexto, e 23 com o contexto quase cheio.
- **Com raciocínio:** uma resposta da biblioteca leva de 1 a 4 minutos, com mediana de pouco mais de 2.

**O que foi medido (lote 43, duas rodadas).** Nas 16 perguntas reais da avaliação da busca, com o modelo local
real e o Gemini simulado, sem chamadas pagas; os encaminhamentos abaixo indicam quando o Gemini seria chamado:
- **O local respondeu 13 e 11 delas,** e cita o documento esperado em 8. Com temperatura 1, eram 9 a 10 e 7.
- **De 2 a 3 seriam refeitas pelo Gemini,** pela conferência das citações e dos números. Outras 2 iriam direto, por
  passarem de 32 mil tokens: são de 4 a 5 encaminhamentos ao Gemini simulado em 16 perguntas.
- **O tempo médio por pergunta caiu de 265 s (lote 40) para 90 a 96 s.**
  - No lote 41, a reescrita da busca passou a sair sem raciocínio. Antes, gastava 2 minutos e falhava em silêncio.
  - No lote 42, o modelo passou a usar toda a VRAM.
  - No lote 43, a temperatura passou a 0,6.

Detalhes nas validações dos lotes [43](docs/migracao/validacao-lote-43.md), [42](docs/migracao/validacao-lote-42.md),
[41](docs/migracao/validacao-lote-41.md), [40](docs/migracao/validacao-lote-40.md),
[39](docs/migracao/validacao-lote-39.md) e [38](docs/migracao/validacao-lote-38.md).

## Uso no dia a dia: a interface

```powershell
.\.venv\Scripts\python.exe -m aliado web --env-file .env
```

Abre `http://127.0.0.1:8765`, acessível só pelo seu computador. Rode a partir da pasta do projeto.

- **Conversas:**
  - Ao abrir ou recarregar, a página mostra a tela de apresentação; as conversas ficam na lista ao lado.
  - Respostas em fluxo, com botão para parar, e os tokens de cada resposta.
  - **Escolha automática** da skill, do modelo e da leitura dos documentos: antes de gastar tokens, um roteador local decide o que a mensagem precisa. A linha sob cada resposta mostra a escolha, e o motivo aparece ao passar o mouse.
  - **Pedidos escritos:** a tela não tem seletores. Para escolher, escreva o pedido na própria mensagem, no começo ou no fim de uma frase: "use o modelo maior" ou "menor", "só trechos", "use as páginas inteiras", "leia o documento inteiro", "leitura ampla", "busque na web", "sem biblioteca", "sem os resultados" ou "use a skill engenharia". O pedido sai do texto que vai ao modelo, e a linha sob a resposta diz "seguiu o seu pedido". Uma mensagem só com o pedido ("busque na web") refaz a pergunta anterior com ele. Um pedido parecido feito antes vale de novo ("repetiu uma escolha sua"), menos a leitura ampla e a web.
  - Histórico em `data/conversas/`. Conversas apagadas vão para a lixeira e deixam de ser lembradas; as anotações que saíram delas continuam.
  - O link no fim da resposta abre uma janela com as fontes e a memória usada, que fecha com Esc.
- **Documentos:**
  - Arraste um PDF, Markdown ou JSON para a conversa, ou use o clipe. O arquivo entra na biblioteca `data/bibliotecas/principal`, com progresso por página, e fica **fixado** naquela conversa: vai inteiro ao modelo em todas as perguntas dela. As etiquetas acima da caixa de mensagem mostram os fixados, com o × para soltar.
  - O botão **Documentos**, ao lado do clipe, abre o painel com a lista da biblioteca, os mais novos primeiro. Por documento: fixar na conversa, abrir o original, a ficha, as figuras e apagar. A aba Biblioteca não existe mais.
  - Um aviso no canto inferior direito, visível em todas as abas, mostra o avanço dos envios. No chat, ele fica logo acima da caixa de mensagem, e a tela reserva a faixa dele para não cobrir nenhum botão.
    - Com um documento: o nome, a etapa (leitura das páginas, reconhecimento de texto, indexação e fichas) e a barra.
    - Com vários: quantos já estão prontos, a barra geral e o documento atual, que muda quando a indexação dele termina.
    - O documento fica pronto para a busca assim que é indexado; as fichas são criadas depois de todos os arquivos enviados.
    - Tudo certo some em 6 s. Falhas e documentos indexados só em parte ficam até você fechar. Fechar o aviso não cancela o envio.
    - Se você recarregar a página no meio do envio, o aviso volta com os totais.
  - Cada documento ganha uma ficha de leitura na memória e uma **ficha do documento** (título, autores, ano e DOI), conferida no próprio texto e editável no painel **Documentos**. **Completar fichas** cria as que faltam.
  - **Figuras e tabelas:** o texto dentro das figuras é reconhecido no seu computador ao indexar. Na ficha do documento, **Descrever figuras e tabelas** envia ao modelo cada página com figura, desenho, tabela ou legenda, como imagem, numa chamada por página. O aviso diz quantas chamadas são antes de enviar, e dá para parar no meio.
    - A descrição entra na busca marcada como automática. A resposta a usa para dizer o que a figura mostra, com o aviso de conferir no original, e a janela de fontes leva à página.
    - O rótulo e a legenda só ficam se estiverem no texto da página.
  - **Trechos:** os trechos da busca são frases inteiras, sem os cabeçalhos e rodapés repetidos das páginas. O sumário e a lista de referências ficam fora da busca comum e voltam quando a pergunta os pede.
  - **Apagar**, no painel Documentos, tira o documento de vez, com todas as versões, a extração e o índice, e revoga as anotações que o agente deduziu dele. As suas anotações ficam. Não tem volta.
  - A biblioteca fica à mão do roteador: o AL-IAdo só vai aos documentos quando a pergunta pede, e "sem biblioteca" na mensagem a deixa de fora. As respostas citam **[n]** com o trecho e a página. Uma resposta que não cita trechos aparece com um aviso.
  - Antes de buscar, o modelo mais barato reescreve a mensagem com o assunto da conversa, as siglas por extenso e os termos em português e inglês. É uma chamada barata a mais por mensagem, e a janela de fontes mostra o que foi buscado.
  - **Leitura dos documentos:** o AL-IAdo começa pelo mais barato que responde à pergunta e só lê mais quando preciso; para pedir uma leitura, escreva-a na mensagem.
    - **Sem a biblioteca:** conversa, memória, tarefas e resultados da pesquisa. Uma mensagem de conversa custa menos de mil tokens.
    - **Só trechos:** a busca traz até 10 trechos, e cada um vai ao modelo com os vizinhos da mesma página. Cerca de 5 a 8 mil tokens.
    - **Páginas inteiras:** as 10 páginas mais próximas da pergunta, em PDF, com figuras, tabelas e fórmulas. É o que vai quando a pergunta fala de figura ou tabela, ou quando os trechos não bastaram. Cerca de 11 a 12 mil tokens.
    - **Documento inteiro:** o documento citado na pergunta, se for pequeno, ou o fixado na conversa. De 11 a 17 mil tokens num artigo.
    - **Leitura ampla:** os documentos que a busca escolher, inteiros, de 150 a 400 mil tokens e de 31 segundos a 12 minutos por pergunta. Só por pedido escrito ("leitura ampla" ou "leia todos os documentos inteiros"), e a tela pergunta antes todas as vezes.
    - **Acima de 30 mil tokens,** a tela mostra a estimativa e pergunta antes de enviar. Depois de 300 mil tokens no dia, toda leitura acima dos trechos pergunta.
    - **Ler mais fundo**, sob a resposta, refaz a pergunta no degrau seguinte, até o documento inteiro, com o custo estimado no botão.
    - Os PDFs lidos sobem para o serviço de arquivos do Google e ficam lá por até 48 horas, para as perguntas seguintes não enviarem de novo. O painel **Documentos** mostra quantos estão lá e tem o botão **Apagar de lá**.
    - Com a busca na web, a leitura segue por trechos.
  - **Perguntas já respondidas:** quando uma pergunta tem o mesmo assunto e o mesmo pedido de uma já respondida, o modelo recebe aquela troca e as páginas que ela citou, sem nova busca, e escreve uma resposta nova. A linha da resposta diz "partiu de uma resposta anterior".
  - **Contagem exata:** em perguntas sobre o acervo ("há alguma literatura sobre…"), o modelo recebe em quais documentos e páginas o termo aparece, na biblioteca inteira.
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
- **Resultados da pesquisa no chat:** ficam à mão do roteador e só seguem quando a pergunta é sobre eles; "sem os resultados" na mensagem os deixa de fora.
  - O agente recebe 8 blocos com os números da aba Ciência: a avaliação oficial de 27/09 (resumo, alarmes falsos, comparação e cada tipo de falha), a reanálise de 30/09 (início das falhas e alarmes estimados, sempre marcada como secundária), a FMECA e a confiabilidade por grupo.
  - Cada número tirado deles leva a marca **[Rn]**, que abre o bloco na janela de fontes, com a tabela, as notas dos indicadores e o botão **Ver na aba Ciência**.
  - O AL-IAdo confere cada número com o bloco citado. Só a escrita pode diferir (2.041 e 2041). Um número arredondado, convertido ou inventado faz a resposta aparecer com um aviso que lista os números, e ela sai do histórico e da memória de conversas.
  - Um número sem marca não é conferido. O chat não recalcula nada: para um número que não está nos blocos, ele indica a seção da aba.
  - Os blocos acrescentam cerca de 5,5 mil tokens de entrada a cada pergunta.
- **Busca na web:** só por pedido escrito ("busque na web"). As fontes da web aparecem como **[Wn]**, separadas dos seus documentos. Na aba Memória, **Conferir na web** checa uma anotação.
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

## Experimento AE Denso × AE-LSTM (base GPVS)

Os 16 CSVs do GPVS-Faults (Bakdi et al., 2020, DOI 10.17632/n76t439f65.1) ficam em
`data/gpvs/`, fora do Git. Junto deles fica `proveniencia.json`, com o SHA-256 de cada
arquivo, conferido a cada preparo.

**Rodar de novo, do zero:** na aba Ciência, seção **Experimento**, ou pelo terminal. A rodada inteira (preparo,
treino, limiar, avaliação, início das falhas e resumo) vai para uma pasta nova
`data/resultados/ae-denso-lstm/rodada-NNN/`, com `resultado.json` e `resultado.md`, e a aba passa a mostrá-la.
A rodada usa os dados de teste: pede a frase de confirmação e entra no registro de consultas. O PDF da rodada
atual sai pelo botão **Baixar PDF** ou pelo comando `pdf`.

```powershell
.\.venv\Scripts\python.exe -m aliado experimento rodar ae-denso-lstm --parametro separacao=2 --frase "consultar o teste"
.\.venv\Scripts\python.exe -m aliado experimento pdf ae-denso-lstm --saida rodada-atual.pdf
```

**Etapa por etapa,** como na pesquisa de origem:

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
$raizPacote = (Get-Location).Path
$fontesPacote = Join-Path $raizPacote ("tmp/pacote-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $fontesPacote | Out-Null
Copy-Item -LiteralPath 'pyproject.toml','README.md' -Destination $fontesPacote
Copy-Item -LiteralPath 'src' -Destination $fontesPacote -Recurse
.\.venv\Scripts\python.exe -m build --wheel --no-isolation --outdir "$raizPacote/dist/v0.8.0-fechamento" $fontesPacote
```

O wheel inclui a interface, com o KaTeX e o D3 v7 (licença ISC, copiada junto), e as skills do AL-IAdo, inclusive as da especialização do mestrado (`src/aliado/specializations/mestrado/skills/`). Documentação, cenários e dados
ficam no repositório. As skills de `.agents/` e `.claude/` orientam os assistentes de
desenvolvimento e não entram no pacote.

O fechamento do lote 44 monta o wheel numa cópia limpa dos fontes, sem reutilizar o cache `build/` da pasta de
trabalho. O [relatório do lote 44](docs/migracao/validacao-lote-44.md) registra a conferência e o hash do pacote.
Para os testes de concorrência da interface, use Node instalado; eles entram no pytest, sem pacotes JavaScript extras.

## Documentação

- [Roteiro da v0](docs/roteiro-v0.md): critérios de pronto, lotes, decisões de escopo e os lotes depois da v0.1.0.
- [Specs dos lotes](docs/specs/): o que cada lote entregou, com critérios de aceitação.
- [Mapa de migração](docs/migracao/README.md): o que veio do repositório de origem, com manifestos e validações de cada lote.
- [Regras de colaboração](AGENTS.md).

## Pendências conhecidas

- A 0.3.0 (lotes 22 a 26, no [roteiro](docs/roteiro-v0.md)) trouxe a aba Ciência nova, o início das falhas no GPVS, a confiabilidade por componente com disponibilidade e os resultados no chat. A 0.4.0 (lotes 27 a 29) trouxe a tela de envios, o espelho para o Obsidian e a indexação com figuras, tabelas e trechos por frase. A 0.5.0 (lotes 30 e 31) trouxe a leitura de páginas e documentos inteiros, tirou a aba Biblioteca e pôs a escolha automática do modelo, da skill e da leitura. A 0.6.0 (lotes 32 e 33) trouxe a busca em memória, a reordenação local das páginas, o revisor de memória seletivo, a reescrita seletiva, o plano por partes e o aprendizado com o uso. A 0.7.0 (lotes 34 a 36) trouxe o experimento rodado do zero pela aba Ciência, com o PDF por pedido, o chat sem seletores, com os pedidos escritos, e o código do mestrado fora do núcleo. A 0.8.0 (lotes 37 a 44) trouxe o modelo local no Ollama como principal, com o Gemini Flash só no limite dele, a leitura das páginas como texto e com as descrições das figuras, o contexto de 32 mil tokens, o modelo quase todo na placa de vídeo e as páginas sem pendência falsa.
- O roteador erra: quando ele escolhe uma leitura menor do que a pergunta pedia, a resposta sai sem o que precisava. Os remédios são **Ler mais fundo** e pedir a leitura por escrito. Uma pergunta sobre os resultados da pesquisa sem as palavras que ele conhece ("GPVS", "nossos resultados", "ensaios") vai sem eles. Veja a [validação do lote 31](docs/migracao/validacao-lote-31.md).
- A leitura por páginas inteiras lê 10 páginas. Se a resposta estiver em outras, ela diz quais leu, e **Ler mais fundo** lê o documento.
- Uma pergunta já respondida parte das páginas que a resposta anterior citou: se aquela resposta ficou incompleta, a nova também fica. Refazer a pergunta em seguida, na mesma conversa, ou **Ler mais fundo** fazem uma leitura nova.
- A leitura ampla demora: no piloto, de 31 segundos a 12 minutos por pergunta, sem relação com o tamanho do pedido. Ela custa de 13 a 34 vezes o modo de trechos, e os PDFs lidos ficam no serviço de arquivos do Google por até 48 horas. Veja a [validação do lote 30](docs/migracao/validacao-lote-30.md).
- Na leitura de documentos inteiros, a busca continua escolhendo os documentos, e de um livro só os blocos escolhidos são lidos. O modelo pode citar a página errada: o código confere que a página citada foi enviada, e não que a afirmação está nela.
- A descrição de uma figura é feita por um modelo e pode errar. O que o código confere são o rótulo, a legenda e as palavras que também estão no texto da página; a ligação entre os elementos de um diagrama não tem como ser conferida. Veja a [validação do lote 29](docs/migracao/validacao-lote-29.md).
- Uma página digitalizada sem legenda não entra na descrição das figuras, e uma tabela com mais de 40 linhas é transcrita até a 40ª.
- Com a consulta reescrita do chat, algumas perguntas sobre uma figura específica não acham a página dela: a reescrita troca a referência à figura por termos gerais.
- A busca mantém os vetores em memória e compara todos de uma vez; a primeira consulta após mudar o
  catálogo precisa carregá-los. Na leitura por páginas, a segunda rede avalia até 60 candidatos e pode
  acrescentar tempo. As medições do lote 32 usam documentos sintéticos; não são medidas do acervo real.
- O revisor de memória poupa cumprimentos e consultas comuns. Preferências, correções, decisões,
  informações pessoais e pedidos de guardar algo continuam sendo revisados. As conversas aceitas
  continuam na memória de conversas e os documentos continuam ganhando fichas; uma consulta não gera
  revisão adicional apenas por trazer citações. O filtro local pode errar; o botão **Lembrar** continua disponível.
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
