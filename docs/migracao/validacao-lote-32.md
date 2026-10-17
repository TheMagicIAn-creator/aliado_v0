# Validação do lote 32

Trabalho local em 04–05/10/2026, sobre `98be273` (lotes 30 e 31). A alteração parcial deixada em
`knowledge/library.py` foi revisada e continuada. Nenhum commit, push, publicação ou chamada paga.
O modelo novo foi baixado de um repositório público; nenhum documento foi enviado. O acervo real não
foi lido integralmente nem reindexado.

## O que foi entregue

- Retratos dos vetores em memória, com conexão SQLite de observação e `PRAGMA data_version`.
  A versão é comparada sempre na mesma conexão, sob trava, e a carga usa transação curta.
  Adição, reprocessamento, exclusão e `UPDATE` por outra conexão invalidam o retrato; WAL também foi testado.
  Sumário e referências conservam o filtro anterior. A integridade dos originais continua sendo
  conferida antes de devolver os trechos. O cálculo vetorial usa `numpy.einsum`, sem o produto BLAS.
- Reordenação na leitura por páginas: até 60 candidatos da busca híbrida, no máximo dois trechos
  avaliados por página, com o melhor escore ordenando a página. O escore não é uma probabilidade.
  A pergunta original acompanha a consulta reescrita, para conservar referências a figuras/tabelas.
  Documentos citados, documentos fixados, páginas prioritárias e páginas reservadas das trilhas mantêm
  precedência. Nenhum novo documento é procurado pela segunda rede.
- Filtro local para o revisor: consultas e cumprimentos são poupados; informações do usuário,
  preferências, decisões, correções, pedidos de guardar algo e declarações ambíguas continuam passando.
  Uma confirmação curta também passa quando responde a uma proposta de escolha.
  A resposta continua sendo guardada na memória de conversas, mesmo sem chamar o revisor.
- Comando `biblioteca preparar-reordenador`, configuração opcional `AL_IADO_RERANKER_DIR`,
  integração automática no servidor e estado da reordenação no resumo guardado de cada leitura.
  Sem os artefatos, com hash divergente ou diante de uma falha de inferência, a seleção anterior é usada.

## Modelo local

[Cross-encoder multilíngue mMARCO](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1),
revisão `1427fd652930e4ba29e8149678df786c240d8825`, ONNX quantizado para CPU. O modelo recebe pares
de consulta e texto e devolve escores de relevância. Não se treina uma rede com os documentos do usuário.

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `tokenizer.json` | 17.082.660 | `62c24cdc13d4c9952d63718d6c9fa4c287974249e16b7ade6d5a85e7bbb75626` |
| `onnx/model_quint8_avx2.onnx` | 118.620.016 | `6c2513767fb63d008a4377bef7a7a3555433d9436342bb53e35a3a72ffc52d4b` |

Foi preparado em `data/models/reranker`, fora do Git. A carga verifica os hashes. A inferência usa CPU,
uma thread por operação e lotes de oito pares; cada par é limitado a 384 tokens do tokenizer local.
Esses tokens locais não são cobrados pela API. Não foi adicionada dependência ao ambiente existente.

## Medição reproduzível

Script: [medir-lote-32.py](medir-lote-32.py). Resultado completo, apenas dados sintéticos:
[medicao-lote-32.json](medicao-lote-32.json). O script cria uma pasta nova, não sobrescreve resultados,
não carrega `.env`, não faz download e não chama provedores.

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
.venv/Scripts/python.exe docs/migracao/medir-lote-32.py --saida data/validacao-lote-32-nova
```

### Busca

Catálogo sintético com 26 documentos, 20 mil trechos e vetores de 384 dimensões. O encoder de consulta
é fixo, para isolar leitura do índice, ordenação e recuperação. O código anterior é carregado em memória
do commit `98be273`, sem mudar o checkout. Quatro buscas iguais em cada implementação: uma inicial e
três seguintes. A matriz ocupa 61,44 MB, além dos textos e demais estruturas em memória.

| Medida | Antes | Lote 32 |
|---|---:|---:|
| Primeira busca | 3,407 s | 2,815 s |
| Mediana das três seguintes | 3,325 s | 0,0824 s |
| Identificadores dos 20 resultados | Referência | Iguais à referência |

A mediana é o valor central das três durações. A busca aquecida foi cerca de 40 vezes mais rápida
neste catálogo. Não é uma medição da latência total do chat nem do acervo real.

### Reordenação

Doze perguntas em português e 16 passagens em inglês, com a passagem esperada definida antes da
medição. A ordem inicial vem da similaridade do MiniLM local; este ensaio isola a segunda rede,
sem a busca híbrida ou a reescrita do chat. Há também testes de integração da seleção no pedido.

| Medida | Antes da segunda rede | Depois |
|---|---:|---:|
| Passagem esperada em primeiro lugar | 5 de 12 | 12 de 12 |
| Passagem esperada entre as dez primeiras | 12 de 12 | 12 de 12 |

Essas contagens medem a posição da passagem esperada, não a qualidade de uma resposta gerada.
A primeira consulta, incluindo a carga do reordenador, levou 1,19 s; as seguintes com 16 candidatos,
de 0,35 a 0,40 s. Uma consulta com 60 candidatos levou 1,37 s. Não foi reduzido o teto de dez páginas:
o ganho observado foi de ordenação, e não de tokens do pedido final.

### Revisor de memória

Em 22 mensagens sintéticas (12 consultas técnicas, quatro mensagens sem informação duradoura e
seis com perfil, preferência, correção, decisão ou pedido de anotação), o código anterior chamaria o
revisor 22 vezes; o filtro chama em seis. As seis mensagens com informação para guardar foram mantidas.
A contagem vem do filtro local, sem executar o revisor nem estimar um valor monetário. Não é uma taxa
de economia garantida em conversas reais.

## Testes

Resultado final em 05/10/2026: **739 testes passaram**, em 141,43 s, com apenas o aviso já existente
do `starlette.testclient`; **Ruff sem problemas** e `git diff --check` sem erros de whitespace.
Comandos e evidências também estão no manifesto [lote-32.json](lote-32.json).

Uma verificação adicional de cache e reordenação, sem ajustes de variáveis de ambiente, passou nos
**18 testes** de `test_search_cache.py` e `test_reranking.py` em 4,24 s.

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
git diff --check
```

- Cache: reutilização, atualização em SQLite normal e WAL, reprocessamento, exclusão, vetores inválidos,
  mudança de encoder, original alterado, consultas concorrentes e limpeza dos candidatos entre perguntas.
- Reordenação: teto de 60, dois trechos por página, desempate, ausência do modelo, hash inválido,
  saída numérica inválida, prioridade de documentos/trilhas, retorno à seleção anterior e inferência
  real local com perguntas em português e textos em inglês.
- Memória: perguntas sem chamada extra, preservação de perfil/feedback, confirmação contextual,
  gravação e lembrança de conversas, fontes e exportação ao Obsidian.
- Os testes existentes de confirmação de leitura e aviso diário continuam cobrindo os valores do lote 31.

A primeira rodada completa, com `OMP_NUM_THREADS=1` e `MKL_NUM_THREADS=1`, passou em 733 testes e falhou
na reprodução bit a bit do limiar do modelo recorrente: `17,381603240966797` em vez de
`17,381608963012695`. A referência do lote 14 usa dez threads. Repetindo com o número original do
PyTorch (dez), todos os 734 testes daquela rodada passaram. O código científico, os pesos de referência
e as tolerâncias não foram alterados. `OPENBLAS_NUM_THREADS=1` foi usado apenas no processo dos testes
para evitar a falha de alocação observada no ambiente; não foi gravado no `.env` nem no programa.

## Limites e uso

- Conjunto sintético pequeno; falta avaliação autorizada com perguntas novas sobre o acervo real e,
  se desejado, com respostas pagas dentro de orçamento combinado.
- A rede só reordena o que chegou ao conjunto de candidatos. Se a busca omitiu uma página, ela não
  a recupera. Os escores não garantem que a página contenha a resposta completa.
- O revisor deixa de criar fatos adicionais automaticamente a cada consulta. As fichas e a memória
  de conversas permanecem; o filtro pode deixar passar uma informação pessoal escrita como pergunta.
  **Lembrar** e pedidos explícitos continuam disponíveis.
- Primeira carga, atualização do catálogo e execução da segunda rede ainda levam tempo.
- Reescrita de consultas, roteamento entre APIs, trilhas incompletas e alcance dos limites de tokens
  não foram alterados neste lote. Os valores continuam 30 mil e 300 mil.
- É necessário reiniciar o processo do AL-IAdo para carregar o código. Não foi encerrado nem reiniciado
  o servidor real durante o desenvolvimento. A versão continua 0.5.0; não foi criado outro pacote.
