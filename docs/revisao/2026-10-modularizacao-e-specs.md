# Revisão da modularização e do desenvolvimento por specs

Estado: proposta de 17/10/2026, revista no mesmo dia com as decisões do pesquisador (seção 6). Nada no código mudou.
As medições são do diretório de trabalho nesse dia (lotes 01–33, com os lotes 32 e 33 sem commit), e os comandos para
repeti-las estão no fim.

## 1. O que a fundação combinou

A [spec 0001](../specs/0001-fundacao.md) definiu três alicerces:

- **Núcleo independente de domínio.** As especializações entram como skills. O requisito F04 diz que, sem a skill,
  o núcleo não contém regras do mestrado.
- **O mestrado isolado.** O passo 3 da sequência é "isolar e validar as ferramentas e os experimentos do mestrado".
- **Specs com requisitos e cenários verificáveis**, em Markdown, no estilo do OpenSpec, sem depender da ferramenta dele.

O `AGENTS.md` repete o primeiro ponto: "o mestrado é uma especialização, isolada do núcleo geral".

## 2. Como está hoje

### 2.1 O mestrado dentro do núcleo

Na tabela, **menções** é o número de linhas que citam GPVS, inversor ou mestrado. Esse número mede o quanto o arquivo
depende da pesquisa: num arquivo do núcleo, o esperado é zero.

| Onde | Linhas | Menções | O que faz | Camada certa |
|---|---:|---:|---|---|
| `science/detection/gpvs.py` | 369 | 16 | lê e prepara os dados do GPVS | especialização |
| `science/detection/training.py` | 272 | 14 | treina os autoencoders do GPVS | especialização (o laço de treino pode ser do núcleo) |
| `science/detection/evaluation.py` | 456 | 13 | avaliação nos ensaios de teste | especialização |
| `science/detection/reanalysis.py` | 333 | 23 | início das falhas, preso à rodada de 27/09 | especialização |
| `science/detection/summary.py` | 337 | 22 | resumo da aba, preso à rodada de 27/09 | especialização |
| `science/detection/onset.py` | 156 | 9 | início observado das falhas | especialização |
| `science/detection/registry.py` | 110 | 3 | registro de consultas ao teste | núcleo (é regra de método, não de domínio) |
| `science/explorer.py` | 292 | 23 | exploradores da aba | especialização |
| `science/digest.py` | 387 | 13 | resumo dos resultados para o chat | especialização |
| `interfaces/web/gpvs_runs.py` | 292 | 20 | botões e rotas `/api/ciencia/gpvs/*` | sai: vira o executor do experimento |
| `interfaces/web/science.py` | 371 | 15 | aba Ciência, com tipos de pasta "gpvs-…" | núcleo, sem os nomes |
| `interfaces/web/app.py` | 1.454 | 15 | servidor inteiro, com `data/gpvs` e a skill padrão | núcleo, sem os nomes |
| `cli.py` | 465 | 36 | comandos `preparar-gpvs`, `treinar-gpvs`… | núcleo + comandos da especialização |
| `routing_examples.py` | 91 | 9 | frases de exemplo do roteador | especialização |
| `routing.py` | 349 | 2 | skill padrão e a palavra "gpvs" na regra de resultados | núcleo, sem os nomes |
| `agent.py` | 791 | 1 | junta a skill de confiabilidade à do mestrado | núcleo, sem os nomes |

- **Ao todo, são 238 linhas em 18 dos arquivos Python, num total de 14.622 linhas.** Fora de `science/`, ficam 98.
- **A tela também cita o GPVS:** 14 vezes em `ciencia.js`, uma em `graficos.js` e uma em `index.html`.
- **O que já é genérico** e serve a outro domínio: `protocol.py` (o próprio arquivo diz "independente do conjunto de
  dados"), `metrics.py`, `threshold.py` e `models.py` na detecção, e `ram.py`, `fmeca.py` e `components.py` no cálculo
  de confiabilidade.
- **A skill do mestrado só tem texto.** O código dela mora no núcleo. Os dados dela também estão espalhados:
  `docs/pesquisa-inversores/` (FMECA, cenários, reparos) e `data/gpvs/`.

### 2.2 Nomes escritos direto no código

A rodada de 27/09 (`gpvs-avaliacao-001`, com `gpvs-modelos-002`) está fixada em cinco lugares:
`summary.py:26`, `explorer.py:26`, `reanalysis.py:40`, `registry.py:17` e os valores padrão em `cli.py:123-124`.
Por isso, uma rodada nova nunca aparece na aba. A skill do mestrado também está fixada como padrão em três lugares:
`routing.py:22`, `app.py:57` e `app.py:419`.

### 2.3 Dependências que cruzam as camadas

Uma camada de baixo não deveria depender de uma de cima, nem o núcleo de uma especialização.

- `agent.py` (núcleo) importa `science.digest` (mestrado), e `agent.py:493` junta à força a skill de confiabilidade
  quando a skill é a do mestrado.
- `knowledge/rewrite.py` (biblioteca) importa `routing` (decisão do chat): a camada de baixo depende da de cima.
- `interfaces/web/app.py` registra as rotas do GPVS diretamente (`app.py:33` e `:1388`).

### 2.4 Tamanho

`interfaces/web/app.py` tem 1.454 linhas. A função que trata cada mensagem vai da linha 418 à 860 e decide, ao mesmo
tempo, rota, custo, confirmação, leitura, segunda chamada e aprendizado. Isso é difícil de testar e de mudar por
partes. Os outros arquivos grandes, `knowledge/library.py` (1.018) e `obsidian.py` (1.126), têm um assunto só cada.

### 2.5 Specs

| Indicador | Valor | O que mede |
|---|---:|---|
| Specs de lote | 33 (2.590 linhas) | uma por lote, descrevendo a mudança |
| Com requisitos numerados (F01, F02…) | 3 (0001–0003) | se dá para verificar cada promessa |
| Com cenários ("quando… então") | 8 de 33 | se o comportamento esperado está escrito como caso |
| Specs vivas por capacidade | 0 | existe um lugar com o que vale hoje para o chat, a biblioteca etc. |
| Testes que citam um requisito | 0 de 757 | se cada promessa tem teste |
| Linhas do `AGENTS.md` | 80, com 31 menções a lote | quanto das regras ficou no lugar errado |
| Código sem spec | 1 caso achado (05/10) | o plano por partes, adotado no lote 33 |

- **Para saber como o chat funciona hoje, é preciso ler as specs 0010, 0018, 0026, 0030, 0031, 0032 e 0033 em ordem**
  e somar as mudanças de cabeça.
- **O `AGENTS.md` virou um diário dos lotes.** As regras de custo e de autorização estão misturadas com o histórico.

## 3. Estrutura alvo (proposta)

```
src/aliado/
  llm/  skills/  agent.py  routing.py  knowledge/  memory/   núcleo, sem domínio
  experiments/        NOVO: rodada atual, resultados em JSON e Markdown, PDF por pedido
  science/            núcleo: métodos genéricos
    ram.py fmeca.py components.py
    detection/        protocol.py metrics.py threshold.py models.py registry.py
  interfaces/web/     núcleo: telas sem nomes de domínio
  specializations/
    mestrado/         a pesquisa do pesquisador, num pacote só
      gpvs.py         leitura da base de dados GPVS
      autoencoders.py o experimento "AE Denso × AE-LSTM" (a definição; usa training, evaluation, onset e reanalysis)
      summary.py explorer.py digest.py routing_examples.py
      skills/pesquisa-inversores/  (a skill de hoje, movida)
```

- **GPVS é a base de dados, não o experimento.** O experimento é a **comparação AE Denso × AE-LSTM**, que hoje usa
  essa base. Os nomes no código e na tela seguem essa diferença.
- **Sem mecanismo de descoberta por enquanto.** Hoje existe uma especialização só. O núcleo deixa de importá-la pelo
  nome: uma lista de registro, com uma linha por experimento, fica nas interfaces (web e terminal). As frases do
  roteador e a skill que acompanha a do mestrado vêm do pacote dela.
  Atalho com limite conhecido: quando houver a segunda especialização, a lista vira descoberta automática.

**O executor do experimento:**

- **É do próprio experimento, não um encadeador genérico de comandos.** "Rodar experimento" roda de fato o experimento
  inteiro, do início ao fim: preparo da base, treino dos dois autoencoders com todas as sementes, limiar, avaliação,
  início das falhas e o resumo.
- **A tela mostra os parâmetros da rodada atual**, para alterar: separação entre blocos, sementes e teto de épocas.
  - Se já existe um resultado com os mesmos parâmetros, **"Rodar experimento" fica desativado**, com uma nota dizendo
    por quê: a rodada é determinística, e o resultado seria o mesmo.
  - Alterou um parâmetro, o botão volta a ficar ativo.
- **A aba mostra só a rodada atual.** As pastas antigas, inclusive as de 27/09, ficam no disco sem mudança.
- **Os resultados ficam em JSON e Markdown**, como as etapas já gravam hoje (`relatorio.json` e `relatorio.md`), mais
  um `resultado.json` da rodada inteira, com os parâmetros, os números e os hashes.
- **O PDF só sai por pedido.** O pesquisador escolhe o experimento e clica em "Baixar PDF", e o PDF é montado nessa hora.
  - O modelo é técnico, formal, limpo e apresentável: capa com título, data e parâmetros, sumário, seções numeradas
    (método, resultados por modelo, limiar, início das falhas e como reproduzir), tabelas com legenda e notas para cada
    indicador.
  - O `resultado.json` vai anexado dentro do PDF.
- **Aplicar de novo num teste:** "Comparar com resultado salvo" recebe um PDF baixado antes, ou o `resultado.json`, e
  mostra lado a lado o guardado e a rodada atual, com as diferenças.

**Mapa de cada peça:**

| Hoje | Destino | Lote |
|---|---|---|
| `interfaces/web/gpvs_runs.py` (`run_subprocess`, tarefas) | o executor do experimento AE Denso × AE-LSTM | 34 |
| constantes `gpvs-avaliacao-001` | `experiments` (rodada atual), com a de 27/09 como plano B | 34 |
| `science/detection/{gpvs,training,evaluation,onset,reanalysis,summary}.py`, `science/{explorer,digest}.py` | `specializations/mestrado/` | 36 |
| comandos `ciencia *-gpvs` em `cli.py` | registrados pela especialização | 36 |
| `routing_examples.py` (parte do domínio), `routing.py:22,48`, `agent.py:493` | `specializations/mestrado/` | 35–36 |
| `skills/builtin/pesquisa-inversores/` | `specializations/mestrado/skills/` | 36 |

Também foram achados, mas **ficam fora do roteiro por decisão do pesquisador**: dividir a função que trata cada
mensagem em `app.py` (seção 2.4) e inverter a dependência `knowledge/rewrite.py → routing` (seção 2.3).

## 4. Desenvolvimento por specs (proposta)

Proponho o formato do OpenSpec, sem a ferramenta dele:

- **Specs vivas** em `docs/specs/capacidades/`, uma por capacidade: `chat`, `roteador`, `biblioteca`, `memoria`,
  `experimentos`, `ciencia` e `interface`.
  - Cada uma diz o que vale **hoje**, com requisitos numerados por capacidade (EXP-01, ROT-03…) e um cenário por requisito.
  - Exemplo:

    > **EXP-02. Parâmetros iguais não rodam de novo.** Com um resultado salvo, "Rodar experimento" fica desativado
    > enquanto os parâmetros forem os mesmos.
    > *Cenário:* dado um resultado com separação 11 e cinco sementes, quando a tela abre com esses valores, então o
    > botão fica desativado; quando a separação muda para 2, então ele fica ativo.

- **Specs de mudança:** a spec de cada lote (0034 em diante) diz quais requisitos acrescenta, altera ou retira. Ao fim
  do lote, a spec viva é atualizada. As specs 0001–0033 ficam como registro, sem alteração.
- **Testes ligados aos requisitos:** cada teste novo cita o requisito no nome ou na docstring, por exemplo
  `test_exp_02_para_na_falha`. Um teste simples no pytest confere que todo requisito vivo é citado por pelo menos um
  teste. É assim que um código sem spec ou uma spec sem teste aparecem.
- **O `AGENTS.md` volta a ser regra de colaboração:**
  - ficam os limites de custo, as autorizações e quem faz os commits;
  - o histórico dos lotes vai para o `roteiro-v0.md`;
  - o comportamento do sistema vai para as specs vivas.
- **As specs vivas são escritas aos poucos:** primeiro a de `experimentos`, no lote 34; as outras quando um lote mexer
  na capacidade, a partir das specs de lote que já existem.

## 5. Ordem da migração

Cada lote é combinado antes.

1. **Lote 34, 0.7.0: o experimento AE Denso × AE-LSTM na aba Ciência.**
   - O executor roda o experimento inteiro, e "Rodar experimento" fica desativado com os mesmos parâmetros.
   - A rodada atual substitui as constantes de 27/09.
   - Os resultados ficam em JSON e Markdown, com o PDF formal só por pedido e a comparação com um resultado salvo.
   - A spec viva `experimentos`.
2. **Lote 35:** o chat com tela mínima e a análise da situação no roteador. Spec viva `roteador`.
3. **Lote 36:** mover o código do mestrado para `specializations/mestrado/` e tirar as rotas `/api/ciencia/gpvs/*`.
   Um teste confere que o núcleo não tem nenhuma menção ao domínio.

**Ficam como estão:** os resultados no disco, inclusive os de 27/09; o registro de consultas ao teste, que só cresce;
os limites de 30 mil tokens por pergunta e 300 mil por dia; a descrição de figuras só por pedido; e os commits, que
continuam com o pesquisador.

## 6. Decisões do pesquisador

Respondidas em 17/10/2026:

- **Sem descoberta de especializações por enquanto:** aceito. Uma lista de registro basta até haver a segunda.
- **Aplicar de novo num teste:** fica como foi pedido, com o resultado salvo comparável à rodada atual.
- **Teste que liga cada requisito a um teste:** mantido.
- **Dividir `app.py` e inverter `knowledge → routing`:** não executar.
- **O executor:** é do próprio experimento e roda tudo, do início ao fim. "Rodar experimento" fica desativado quando
  nenhum parâmetro mudou.
- **O PDF:** só por clique, num modelo técnico e formal. Os resultados ficam guardados em JSON e Markdown.
- **Os nomes:** o GPVS é a base de dados; o experimento é a comparação AE Denso × AE-LSTM.

- **Nomes no código:** em inglês (`experiments`, `specializations`), como os de hoje; as telas seguem em português.
- **Pacote do mestrado:** dentro do AL-IAdo, em `src/aliado/specializations/mestrado/`.
- **`AGENTS.md`:** no lote 34, o histórico dos lotes vai para o roteiro, e ficam só as regras de custo, autorização e commits.

Todas as decisões foram tomadas. O próximo passo é a spec 0034.

Ajustes da execução, na revisão do plano de 17/10/2026, registrados nas specs 0034 a 0036:

- **Sem nome no núcleo:** a lista de registro com o nome da especialização seria uma menção no núcleo; o núcleo
  percorre a pasta `specializations` e acha os pacotes.
- **Registro de consultas:** fica no núcleo, e o nome da pasta da avaliação oficial chega de quem o chama. A
  consulta é aberta logo antes de pontuar o teste, uma por rodada.
- **Confirmação e rótulos:** antes de rodar, a frase "consultar o teste"; "oficial" só para a avaliação de 27/09,
  e uma rodada nova leva a data e o número da consulta.
- **No chat (lote 35):** a web só por pedido escrito, sem a regra de "fato recente"; o apoio da skill de
  confiabilidade vem da própria skill ou de um pedido escrito. Uma mensagem que é só um pedido refaz a anterior.
- **Escopo do PDF:** o primeiro PDF só tem texto e tabelas, sem figuras.

## 7. Como refazer as medições

```bash
grep -rci "gpvs\|inversor\|mestrado" src/aliado --include=*.py | grep -v ":0$"
```

```bash
grep -rn "gpvs-avaliacao-001\|gpvs-modelos-002\|pesquisa-inversores" src/aliado --include=*.py
```

```bash
grep -c '^| [A-Z]\{1,3\}[0-9]' docs/specs/*.md
```

```bash
grep -rnE "^\s*(from|import) aliado\." src/aliado/agent.py src/aliado/knowledge/rewrite.py
```
