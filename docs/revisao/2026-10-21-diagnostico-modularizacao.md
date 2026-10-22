# AL-IAdo — diagnóstico: o necessário, o resíduo e a modularização

Data: 21/10/2026. Pedido do pesquisador, antes de prosseguir: dizer o que é necessário, o que é lixo residual e o
que pode melhorar na modularização. Pedido também que considere o que o diagnóstico enviado ao Gemini já apontava e
que ficou de fora: a falta de rastreabilidade fácil, o laço dos testes e as funções de autoencoders acessíveis.

Base: o diretório de trabalho em 21/10, com os lotes 37 a 48 ainda sem commit sobre `77fb76d`. Tudo foi conferido
por leitura e por comandos que só leem: tamanhos, buscas no código, o grafo de importações e os tempos da bateria
do lote 48. Nada foi alterado ou apagado, e não houve chamada a modelo. Dados privados só foram contados, sem
leitura do conteúdo.

## 1. Conclusão

- **O produto não tem muito código morto.** Pela busca de nomes, das funções de topo, só duas não são usadas pelo
  produto, e as duas são usadas pelos testes. O resíduo está em outro lugar:
  - **no disco:** cerca de 14 GB, sendo 12 GB de cópias da biblioteca em `tmp/` e 2,2 GB de um reordenador que o
    código não usa;
  - **em ramos do código legado:** os da v0.1.0;
  - **em ajudantes repetidos:** quatro funções de hash de arquivo.
- **A rastreabilidade é o ponto mais fraco hoje.**
  - Há 12 lotes sem commit.
  - O pacote instalado diz 0.7.0, enquanto o código é 0.8.0 com mais quatro lotes. Uma rodada feita hoje gravaria
    "0.7.0" como versão.
  - Nenhuma rodada grava o commit do código.
  - As evidências e os scripts das medições vivem em `tmp/`, fora do Git.
- **O laço dos testes é lento e amarrado.**
  - 5 arquivos científicos levam 55% dos 235 s, com 48 dos 834 testes.
  - Não há marcação para rodar só o rápido.
  - 13 arquivos de teste importam outros arquivos de teste.
  - Os testes com dados reais são pulados em silêncio em outro computador.
- **As funções de autoencoders não têm porta de entrada pública.**
  - Elas existem e estão testadas, mas espalhadas em módulos internos.
  - O que o pesquisador consegue consultar sem código são os comandos de lote e a aba Ciência; o chat só recebe um
    resumo.
  - Não há como pedir "os erros por variável do ensaio F3L" ou "compare estas duas rodadas" por comando ou pelo
    chat.
- **O maior acoplamento do produto:** a conversa inteira mora dentro da função que monta o servidor web,
  `create_app`, com 1.149 linhas. Só a mensagem do chat tem 583.

## 2. O que é necessário

| Área | Módulos | Linhas | Situação |
|---|---|---:|---|
| Conversa (pergunta e resposta) | `agent.py`, `routing.py`, `numbers.py`, `skills/` | ~1.750 | Essencial |
| Biblioteca | `knowledge/` (catálogo, extração e OCR, trechos, busca, páginas, reescrita) | ~3.300 | Essencial |
| Memória | `memory/` | ~700 | Essencial |
| Provedores | `llm/` (Gemini, local, gateway, contratos) | ~1.400 | Essencial |
| Provedor OpenAI | `llm/providers/openai.py` (apelidos luna, terra e sol) | 142 | **Dormente:** testado, sem chave configurada; decidir |
| Ciência geral | `science/` (detecção, RAM, FMECA, componentes, resumo citável) | ~1.600 | Essencial |
| Pesquisa do mestrado | `specializations/mestrado/` | ~3.300 | Essencial |
| Experimentos | `experiments/` (rodadas, comparação, PDF) | ~560 | Essencial |
| Interface web | `interfaces/web/` sem o Obsidian | ~2.200 | Essencial |
| Espelho no Obsidian | `interfaces/web/obsidian.py` (111 testes) | 1.126 | **Opcional:** a sua conferência no Obsidian ainda está pendente desde o lote 28; decidir se fica |

Também são necessários e ficam:
- as skills de desenvolvimento em `.claude/` e `.agents/` e o guarda de Git;
- as specs 0001 a 0048, que são o registro dos lotes;
- os manifestos e validações em `docs/migracao/`, que são a proveniência;
- os mapas de 05/10, como registro datado;
- `requirements-dev.lock` e as pastas de `dist/` das versões.

## 3. O que é resíduo e o que não é

### 3.1. No disco, fora do Git

| O quê | Tamanho | Classificação |
|---|---:|---|
| Cópias da biblioteca e dos resultados nas medições dos lotes 39 a 46 (`tmp/lote-*/medicao`, `rodada-*`, `final`, `library-snapshot`) | ~10 GB | **Resíduo.** Os arquivos pequenos (JSON e scripts) são evidência e ficam; os manifestos guardam o hash deles. |
| `tmp/lote-29/biblioteca` e `tmp/lote-29/backup` | 2,8 GB | **Resíduo provável:** cópia e backup de antes da reindexação de 03/10. Confirmar com você. |
| `data/models/reranker-bge` | 2,2 GB | **Resíduo:** nenhum código o usa (o padrão é `data/models/reranker`). |
| `data/models/reranker-mmarco` | 130 MB | **Duplicata** de `data/models/reranker`: o modelo tem o mesmo SHA-256. |
| `data/ciencia/erros-*.npz` (dois) | 17 MB | **Resíduo:** a chave nova do lote 46 não os lê mais. |
| `data/validacao-lote-32`, `data/validacao-lote-33*` | 159 MB | **Resíduo provável:** cópias de validações antigas. |
| `data/models/minilm`, `data/models/reranker`, `data/tools/tesseract` | 350 MB | **Necessário:** busca, reordenação e OCR. |

### 3.2. No repositório

- **`docs/revisao/2026-10-20-diagnostico-arquitetura-complementado.txt`:** é cópia exata do `.md` → resíduo.
- **`.smart-env/` e `.codex-remote-attachments/`:** não estão no `.gitignore` e aparecem como arquivos novos a cada
  `git status` → risco de commit acidental. Devem entrar no `.gitignore`.

### 3.3. No código

| O quê | Onde | Classificação |
|---|---|---|
| `provider == "local"` (a resposta sem modelo da v0.1.0) | 5 pontos em `app.py` | **Morto** para respostas novas: nenhum código produz mais "local", e eu mesmo o confundi com o Ollama no lote 46 |
| O mesmo teste em `app.js` (3) e `obsidian.py` (1) | — | **Necessário:** 1 das 17 conversas gravadas ainda tem uma resposta assim |
| `library._join` e `reanalysis.reanalyze` | — | **Só testados:** o produto usa `_overlap` e `run`; manter ou apagar com os testes |
| Hash de arquivo implementado 4 vezes | `library._hash`, `training._sha256`, `evaluation._sha256`, `gpvs.sha256_file` | **Duplicação:** uma função só bastaria |
| Hash da configuração repetido 3 vezes | `training`, `evaluation`, `onset` | **Duplicação pequena** |
| Imports de funções privadas entre módulos | o explorador usa `_onset` da avaliação; `web/experiments.py` usa `_shown`; `obsidian.py` usa as expressões privadas de `rendering.py` | **Sinal de API faltando** (seção 6) |

## 4. Rastreabilidade fácil

| Pergunta que deveria ter resposta fácil | Hoje |
|---|---|
| Qual código produziu este resultado? | **Não dá:** o HEAD é `77fb76d`, e os 12 lotes posteriores só existem no diretório. As rodadas gravam a versão do pacote instalado, que diz 0.7.0, e nenhum commit nem estado do código |
| Esta rodada usou quais pesos, dados e atributos? | **Em partes:** os hashes estão espalhados em `configuracao.json`, `relatorio.json` e `resultado.json`; o `resultado.json` não tem o hash dos pesos nem a ordem dos 24 atributos |
| Como foi formado o escore desta janela? | **Só refazendo a inferência:** a matriz de erros por variável fica num cache do explorador, não na rodada |
| Estas duas rodadas são comparáveis? | **Não por inteiro:** a regra "mesmos parâmetros" compara só os parâmetros da tela, e não código, dados e ambiente |
| Qual medição sustenta a decisão do lote N? | **Os manifestos têm os hashes,** mas os scripts e os resultados das medições estão em `tmp/`, fora do Git, e cada lote copiou os scripts do anterior |
| Qual teste garante o requisito X? | **Fraco:** o teste das specs só confere se o código do requisito aparece escrito em algum teste, não se o teste o verifica, e não há relatório requisito → teste |
| Onde está o estado atual? | **Disperso:** o roteiro tem 640 linhas, o CHANGELOG 591 e o README 400; falta uma página curta de "estado atual" |

## 5. O laço dos testes

- **Tempo, na bateria do lote 48:** 834 testes em 235 s, um processo por arquivo.
  - `test_detection_evaluation`, `test_detection_training`, `test_reanalysis`, `test_experiments` e
    `test_detection` somam 130 s (55%) para 48 testes, porque treinam redes (a fixture `origin_gpvs_runs` treina
    uma vez por sessão) ou leem o GPVS real.
  - Os outros 41 arquivos somam cerca de 105 s.
- **Sem marcação:** o `pyproject.toml` só define a pasta dos testes. Não há como rodar só o rápido, e a bateria por
  arquivo depende de um script copiado em `tmp/lote-NN/bateria.py`, fora do Git.
- **Testes amarrados entre si:** 13 arquivos importam outros arquivos de teste.
  - Ciclo não há, mas a cadeia chega a 5 arquivos: `test_learning → test_web → test_routing → test_reading →
    test_figures`.
  - A fixture `env` do chat é importada de `test_web`.
  - Ajudantes repetidos: um codificador falso em 5 arquivos, uma biblioteca falsa em 4, `ask` em 5 e fluxos falsos
    em 16.
  - Rodar um arquivo carrega outros, e mudar um ajudante quebra testes de outro assunto.
- **Testes amarrados aos dados privados:** 9 testes, além das duas fixtures, são pulados quando o GPVS ou a
  avaliação oficial não estão no computador.
  - O pulo é silencioso no resumo: "834 passaram" aqui não quer dizer o mesmo em outra máquina.

## 6. Funções de autoencoders acessíveis

**O que existe hoje:**
- **Comandos de lote:** `aliado ciencia preparar-gpvs | treinar-gpvs | avaliar-gpvs | reanalisar-gpvs` e
  `aliado experimento rodar | exportar`. Eles produzem pastas de rodada.
- **A aba Ciência:** o explorador do limiar e o de alarmes e detecção, com erro por variável, escores, limiar e
  alarmes, mas só pela tela.
- **O chat:** recebe um resumo citável ([R1]…[R8]), sem poder consultar detalhes.
- **Por código:** `aliado.science.detection` não exporta nada no pacote. É preciso conhecer submódulos (`models`,
  `threshold`, `metrics`, `protocol`) e funções da especialização (`load_training`, `gpvs.prepare`,
  `segment_errors`, `score_all`, `run_metrics`).
  - O próprio explorador importa uma função privada, `_onset`.

**O que falta:** uma porta de entrada pública e documentada que reaproveite o que o explorador e a avaliação já
calculam, sem cálculo novo:
- **ler uma rodada:** a configuração, os hashes (dados, pesos e código), os modelos e o limiar;
- **erros e escores:** os erros por variável e os escores de um ensaio, com os nomes dos 24 atributos e o índice da
  janela;
- **limiar e alarmes:** com os parâmetros oficiais ou explorados;
- **comparar duas rodadas:** as diferenças e a compatibilidade de dados, código e protocolo.

**Como chegar a isso:**
- A mesma porta vira comandos (`aliado ciencia rodada mostrar | comparar | erros`), com saída em JSON ou CSV.
- Depois, se você quiser, vira ferramentas do chat, as `read_run` e `compare_runs` do diagnóstico enviado ao
  Gemini.
- O explorador passa a ser só a tela sobre ela.

## 7. Modularização: onde dividir e onde não

1. **A conversa fora do servidor web.** `create_app` tem 1.149 linhas, e a mensagem do chat (583 linhas, com o
   gerador `events` de 379) faz tudo: rota, leitura, trilhas, reescrita, escalada, subida da escada, registro de
   uso e resposta.
   - **O ganho:** a conversa ficaria testável sem HTTP e utilizável pelo terminal e pelos scripts de medição, que
     hoje sobem um servidor para medir.
   - **A decisão anterior:** na revisão de 17/10, você deixou essa divisão fora do roteiro. Proponho reabrir, com
     esta evidência.
2. **Ciclos entre pacotes**, pequenos e baratos:
   - **biblioteca ↔ provedores:** `local.py` importa o cadeado do PDFium de `knowledge.extraction`;
   - **biblioteca ↔ roteador:** `rewrite.py` usa `routing.terms`, e o roteador usa `knowledge.metadata`;
   - **especialização → interface web:** `mestrado/web.py` usa `interfaces.web.science`.
3. **Ciência, onde vale mexer:**
   - tirar de dentro dos módulos de cálculo os relatórios Markdown que eles montam (treino, avaliação, reanálise e
     preparo do GPVS);
   - um hash de arquivo único;
   - o manifesto da rodada (seção 4);
   - a porta de entrada (seção 6).
4. **Ciência, onde não vale agora:** dividir `models.py` (189 linhas) em cinco arquivos, ou a árvore `core/`/`agent/`
   do anexo. Isso troca nomes de pastas sem tirar acoplamento; o acoplamento real está nos itens acima.
5. **Moderado, depois:**
   - `agent.py` (854 linhas): a conferência de citações e de números pode virar um módulo próprio;
   - `DocumentLibrary` (899 linhas): separar a busca da entrada de documentos.
6. **Testes:** os ajudantes e as fixtures vão para `conftest.py` e um módulo de apoio, e os testes param de se
   importar.

## 8. Sequência proposta, em pequenos lotes

| Ordem | Lote | Muda código? | Precisa de você |
|---|---|---|---|
| 0 | Os commits pendentes (patches dos lotes 46 a 48 prontos) | Não | Fazer os commits |
| 1 | **Limpeza:** remover os itens 3.1 e 3.2 confirmados e completar o `.gitignore` (libera ~14 GB) | Não | Autorizar a lista exata |
| 2 | **Laço dos testes:** marcações "lento" e "dados reais", um laço rápido padrão (estimo de 1 a 2 min), a bateria por arquivo no repositório, os pulos listados no resumo e os ajudantes em `conftest.py` | Só testes e ferramentas | — |
| 3 | **Identidade da rodada:** commit, estado do código e versão da fonte na rodada; hash dos pesos e ordem dos atributos no `resultado.json`; corrigir a versão instalada | Sim, sem mudar cálculos | — |
| 4 | **Porta de entrada dos autoencoders**, com os comandos `rodada mostrar`, `comparar` e `erros` | Sim, sem cálculo novo | Aprovar os nomes e as saídas |
| 5 | Os ciclos entre pacotes e os relatórios Markdown fora do cálculo | Sim, pequeno | — |
| 6 | **A conversa fora do servidor web** | Sim, o maior | Reabrir a decisão de 17/10 |

**Os scripts de medição e de patch:** proponho que vão de `tmp/` para uma pasta versionada de ferramentas, no lote
2. As saídas continuam fora do Git.

## 9. Decisões que são suas

- **Limpeza:** autorizar a lista do item 3.1. Em especial, o backup de antes da reindexação (`tmp/lote-29/backup`)
  e as validações antigas em `data/`.
- **Obsidian e OpenAI:** se o espelho no Obsidian e o provedor OpenAI continuam.
- **Conversa fora do servidor web:** se reabre a decisão de 17/10.
- **O arquivo oficial dos erros da rodada:** o formato e o instante da janela (começo, centro ou fim), que seguem
  pendentes.
