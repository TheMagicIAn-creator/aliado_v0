# AL-IAdo

Agente modular para pesquisa e engenharia, de uso **local e individual**. A pesquisa de
mestrado sobre detecção de falhas em inversores fotovoltaicos é sua primeira
especialização. Versão **0.1.0**, com as mudanças dos lotes 18 a 20 ainda não lançadas. Tudo
está em [CHANGELOG.md](CHANGELOG.md).

## O que ele faz

- **Conversa pelo navegador** com o Gemini ou a OpenAI, com skills que orientam cada tema.
- **Biblioteca de referências:** PDF, Markdown e JSON enviados pelo chat, com OCR, busca local e citações com a página.
- **Memória persistente:** lembra quem você é, o que você ensina e as conversas anteriores sobre o mesmo assunto. O que o agente deduz fica marcado para revisão, e correções não apagam o histórico.
- **Busca na web** com as fontes citadas.
- **Cálculos de confiabilidade** por cenário explícito e a **FMECA** dos inversores.
- **Experimento de detecção** Denso × AE-LSTM no GPVS-Faults, reproduzível e com relatórios.

Cálculos, FMECA e experimento rodam por comando próprio ou pela aba **Ciência** da interface; o
chat não os executa sozinho. O treino e a avaliação do GPVS pela interface entram no lote 21.

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
  - Com **Usar biblioteca**, o agente recebe a lista dos documentos, com autor e ano, e as respostas citam **[n]** com o trecho e a página. Uma resposta que não cita trechos aparece com um aviso.
- **Memória** (`data/memoria/`):
  - O que você diz ou corrige vale na hora; o que o agente deduz fica marcado como "inferida".
  - O que você conta sobre si vira **perfil** e vale em todas as conversas.
  - Cada troca fica guardada, e até 3 trocas de outras conversas, parecidas com o assunto, entram como contexto.
  - Diga "lembre que…" ou use **Lembrar…**.
  - A aba **Memória** mostra histórico, edição, revogação e conflitos para você decidir. Nada é apagado.
  - `data/` fica fora do Git e sem cópia automática. Copie `data/memoria` e `data/conversas` se quiser guardá-los.
- **Busca na web:** ligue **Buscar na web**. As fontes da web aparecem como **[Wn]**, separadas dos seus documentos. Na aba Memória, **Conferir na web** checa uma anotação.
- **Ciência:** os números vêm do serviço científico, e o navegador só desenha.
  - **Resultados:** os relatórios de `data/resultados/`, com gráficos (curvas, escores de calibração) e tabelas.
  - **Limiar:** k de 1 a 24 e percentil sobre os escores reais da calibração, com o erro das 24 variáveis de uma janela. Não usa o teste.
  - **Alarme e detecção:** k, percentil e m sobre o teste e os ensaios com falha, com a linha do tempo de cada ensaio. É **exploração pós-teste, não canônica (M14)**, e mostra os valores oficiais ao lado. Com k = 5, p99 e m = 3, repete a avaliação de 27/09.
  - **Confiabilidade:** λ, horas por ano, base e horizonte recalculam R(t) e F(t) sem gravar nada. Para salvar o cenário numa pasta nova, fonte e hipóteses são obrigatórias. Aceita também qualquer cenário em JSON.
  - **FMECA:** a tabela, as ordens pelo NPR e pela taxa e o relatório numa pasta nova.
  - Os exploradores do GPVS precisam de `data/gpvs/` e das rodadas `gpvs-modelos-002` e `gpvs-avaliacao-001`. O erro por variável fica em `data/ciencia/`, e `--resultados` e `--gpvs` mudam essas pastas.
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
que ficam fora do Git. Veja o [guia da biblioteca](docs/biblioteca/uso.md).

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

## Pacote

```powershell
.\.venv\Scripts\python.exe -m build --wheel --outdir dist/v0.1.0
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

- Reconferir nos PDFs as taxas de falha e as notas da FMECA, quando entrarem na biblioteca.
- Tempos de reparo e disponibilidade só entram com fonte.
- No GPVS, o início nominal das falhas (o meio do registro) não coincide com a mudança observada no sinal. Os atrasos medidos refletem isso.
- A busca ainda erra algumas perguntas de conteúdo em outro idioma: 3 das 16 perguntas de referência. A tradução da pergunta ficou para depois. Veja a [validação do lote 19](docs/migracao/validacao-lote-19.md).
- Preparar, treinar e avaliar o GPVS pela aba **Ciência** fica para o lote 21. Uma nova avaliação vai exigir confirmação e ficar registrada como nova consulta ao teste (M14).
- Para a v1: site com domínio e vários usuários, MCP, roteador de modelos e importação das memórias antigas.
