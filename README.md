# AL-IAdo

Agente modular para pesquisa e engenharia, de uso **local e individual**. A pesquisa de
mestrado sobre detecção de falhas em inversores fotovoltaicos é sua primeira
especialização. Versão **0.2.0**. As mudanças estão em [CHANGELOG.md](CHANGELOG.md).

## O que ele faz

- **Conversa pelo navegador** com o Gemini ou a OpenAI, com skills que orientam cada tema.
- **Biblioteca de referências:** PDF, Markdown e JSON enviados pelo chat, com OCR, busca local e citações com a página.
- **Memória persistente:** lembra quem você é, o que você ensina e as conversas anteriores sobre o mesmo assunto. O que o agente deduz fica marcado para revisão, e correções não apagam o histórico.
- **Busca na web** com as fontes citadas.
- **Cálculos de confiabilidade** por cenário explícito e a **FMECA** dos inversores.
- **Experimento de detecção** Denso × AE-LSTM no GPVS-Faults, reproduzível e com relatórios.

Cálculos, FMECA e experimento rodam por comando próprio ou pela aba **Ciência** da interface; o
chat não os executa sozinho.

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

Nenhum teste chama provedores pagos ou acessa a rede. Os testes que usam os dados reais do GPVS são pulados se `data/gpvs/` não existir.

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
  - Respostas em fluxo, com botão para parar, e os tokens de cada resposta.
  - Escolha da skill e do modelo.
  - Histórico em `data/conversas/`. Conversas apagadas vão para a lixeira e deixam de ser lembradas; as anotações que saíram delas continuam.
  - O link no fim da resposta abre uma janela com as fontes e a memória usada, que fecha com Esc.
- **Documentos:**
  - Arraste um PDF, Markdown ou JSON para a conversa, ou use o clipe. O arquivo entra na biblioteca `data/bibliotecas/principal`, com progresso por página.
  - Os envios aparecem numa fila de até 3 cartões, com contador. Os que dão certo somem em 6 s.
  - Cada documento ganha uma ficha de leitura na memória e uma **ficha do documento** (título, autores, ano e DOI), conferida no próprio texto e editável na aba **Biblioteca**. **Completar fichas** cria as que faltam.
  - **Apagar**, na aba Biblioteca, tira o documento de vez, com todas as versões, a extração e o índice, e revoga as anotações que o agente deduziu dele. As suas anotações ficam. Não tem volta.
  - Com **Usar biblioteca**, o agente recebe a lista dos documentos, com autor e ano, e as respostas citam **[n]** com o trecho e a página. Uma resposta que não cita trechos aparece com um aviso.
  - Antes de buscar, o modelo mais barato reescreve a mensagem com o assunto da conversa, as siglas por extenso e os termos em português e inglês. É uma chamada barata a mais por mensagem, e a janela de fontes mostra o que foi buscado.
  - A busca traz até 10 trechos. Quando autores diferentes tratam do pedido, a resposta mostra a opção de cada um, com a citação.
- **Fonte do texto:** o seletor **Aa**, na barra do topo, troca a letra da interface entre 8 opções. A escolha fica guardada no navegador.
- **Memória** (`data/memoria/`):
  - O que você diz ou corrige vale na hora; o que o agente deduz fica marcado como "inferida".
  - O que você conta sobre si vira **perfil** e vale em todas as conversas.
  - Cada troca fica guardada, e até 3 trocas de outras conversas, parecidas com o assunto, entram como contexto.
  - Diga "lembre que…" ou use **Lembrar…**.
  - A aba **Memória** mostra histórico, edição, revogação e conflitos para você decidir. Nada é apagado.
  - `data/` fica fora do Git e sem cópia automática. Copie `data/memoria` e `data/conversas` se quiser guardá-los.
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

## Linha de comando

```powershell
.\.venv\Scripts\python.exe -m aliado skills
.\.venv\Scripts\python.exe -m aliado preparar "Quais decisões da pesquisa estão pendentes?"
.\.venv\Scripts\python.exe -m aliado perguntar "Quais taxas foram decididas?" --provider google --model-alias flash --env-file .env
```

- **`preparar`** mostra o pedido montado, sem enviar nada.
- **`perguntar`** chama o provedor.
- **A skill** padrão é a da pesquisa, com apoio da skill `confiabilidade`. Troque com `--skill engenharia`, `--skill confiabilidade` ou `--skill nenhuma`; `--apoio` compõe as duas.
- **A biblioteca** também tem comandos próprios:

```powershell
.\.venv\Scripts\python.exe -m aliado biblioteca adicionar "C:\caminho\referencia.pdf" --biblioteca data/bibliotecas/principal
.\.venv\Scripts\python.exe -m aliado biblioteca buscar "tempo médio de reparo" --biblioteca data/bibliotecas/principal
.\.venv\Scripts\python.exe -m aliado biblioteca verificar --biblioteca data/bibliotecas/principal
.\.venv\Scripts\python.exe -m aliado biblioteca avaliar --biblioteca data/bibliotecas/principal --saida data/resultados/busca-001
```

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

A avaliação canônica já foi feita em 27/09/2026. Mudanças de protocolo depois disso exigem
uma avaliação independente (M14).

4. **Reanálise com o início observado** (lote 24):
   - acha onde cada falha aparece nas 24 variáveis, com o PELT e sem os modelos;
   - recalcula as métricas com esse início sobre os mesmos escores de 27/09;
   - estima os alarmes falsos por hora e a faixa esperada pelo limiar;
   - grava numa pasta nova e entra no registro de consultas ao teste.

```powershell
.\.venv\Scripts\python.exe -m aliado ciencia reanalisar-gpvs --saida data/resultados/gpvs-reanalise-001
```

## Pacote

```powershell
.\.venv\Scripts\python.exe -m build --wheel --outdir dist/v0.2.0
```

O wheel inclui a interface, com o KaTeX, e as skills do AL-IAdo. Documentação, cenários e dados
ficam no repositório. As skills de `.agents/` e `.claude/` orientam os assistentes de
desenvolvimento e não entram no pacote.

## Documentação

- [Roteiro da v0](docs/roteiro-v0.md): critérios de pronto, lotes, decisões de escopo e os lotes depois da v0.1.0.
- [Specs dos lotes](docs/specs/): o que cada lote entregou, com critérios de aceitação.
- [Mapa de migração](docs/migracao/README.md): o que veio do repositório de origem, com manifestos e validações de cada lote.
- [Regras de colaboração](AGENTS.md).

## Pendências conhecidas

- A 0.3.0 está em andamento (lotes 22 a 26, no [roteiro](docs/roteiro-v0.md)): aba Ciência nova, confiabilidade por componente com disponibilidade, início das falhas no GPVS e resultados no chat.
- Nenhuma fonte traz o tempo de reparo de cada componente: a disponibilidade usa o tempo do inversor inteiro, em dois cenários.
- No GPVS, o início observado vale só para os 8 ensaios de mudança clara. F4 não muda as 24 variáveis, e F6 e F7 mudam pouco: para eles, a falta de detecção é, em boa parte, das variáveis (lote 24).
- Os alarmes falsos contam com só 52 s saudáveis: a taxa por hora é uma estimativa com intervalo largo.
- Com a consulta reescrita, a busca acerta as 16 perguntas de referência. São só 16 perguntas: um conjunto maior diria mais. Veja a [validação do lote 22](docs/migracao/validacao-lote-22.md).
- Os exploradores da aba Ciência usam só a rodada canônica; rodadas novas aparecem em Resultados.
- Para a v1: site com domínio e vários usuários, MCP, roteador de modelos e importação das memórias antigas.
