# Validação do lote 28 — o AL-IAdo no grafo do Obsidian

Verificação local em **03/10/2026**, sobre o commit `436582a` (lote 27, versão 0.3.0). **Nenhuma chamada paga:**
a exportação não usa modelo, e a conferência no navegador usou um modelo simulado. O assistente não fez commit,
push nem tag.

## Testes

30 testes novos em `tests/test_obsidian.py`, que rodam 111 casos:
- **Notas e links:**
  - os links dos três tipos de nota resolvem; a citação de uma versão antiga leva ao documento atual; documento e conversa apagados viram texto;
  - o resultado só depende dos dados: a ordem de chegada não muda nada;
  - nomes válidos no Windows e num link, únicos sem diferenciar maiúsculas, e estáveis quando chega outro nome repetido;
  - correções vindas da web e anotações em conflito são agrupadas e contadas como na aba Memória;
  - nenhum caminho de pasta, trecho ou passagem recuperada chega às notas.
- **Limpeza do texto:**
  - 76 textos montados para furá-la, cada um conferido na resposta e em todos os campos de todas as notas (título, ficha, pendências, anotações, propriedades);
  - blocos de linguagens que o Obsidian executa vão como texto; títulos ficam abaixo de "Resposta";
  - respostas comuns (fórmulas, tabelas, código, listas, links de sites) continuam na forma normal;
  - registros malformados e linhas enormes não derrubam nem seguram a exportação.
- **Gravação:**
  - a segunda rodada não grava nada, nem o registro; a edição numa nota gerada é substituída; o renomeado sai;
  - arquivos do pesquisador não são cobertos nem apagados, também com o nome de uma nota gerada ou com um nome só parecido;
  - um registro adulterado não apaga fora das três pastas, nem com barras do Windows; com o registro ocupado, a rodada para antes de mudar qualquer coisa;
  - uma nota que não dá para ler, gravar ou apagar não segura as outras; uma gravação que falha não perde a nota antiga;
  - uma pasta que aponta para fora do cofre é deixada em paz (só no Windows);
  - a data de criação do arquivo segue a do registro (só no Windows).
- **Fila e servidor:**
  - pedidos durante uma rodada viram uma rodada a mais; três tentativas quando um arquivo ou banco está ocupado; o aviso sai uma vez, sem caminho de pasta;
  - ler e gravar conversas ao mesmo tempo não falha;
  - os disparos: resposta, revisor, renomear e apagar conversa, envio, versão que não pôde ser lida, ficha editada, "Completar fichas", conferência na web, anotação criada e revogada, apagar documento;
  - uma falha da exportação não derruba o chat; desligada, ela não cria pasta; pastas do próprio AL-IAdo são recusadas.

**591 testes passaram** (480 do lote 27 e 111 novos), no Python 3.12.14. O Ruff não apontou problemas.

## Revisão por agentes

Três rodadas. Cada defeito veio com um trecho de código que o reproduz.

| Rodada | Agentes | Apontamentos | Resultado |
|---|---|---:|---|
| 1 | 2 revisores e 2 verificadores céticos | 22 | Texto e links: 11 confirmados, 1 refutado. Gravação e servidor: 10, sem verificação (o verificador parou no limite de uso). |
| 2 | 2 revisores | 16 novos | 24 correções da rodada 1 conferidas. |
| 3 | 1 revisor | 8 novos | 17 correções da rodada 2 conferidas; 7 ainda falhavam em algum caso. |

Todos os apontamentos aceitos foram corrigidos e viraram teste. Os da rodada 1 sem verificação e os das rodadas
2 e 3 foram tratados como válidos, porque traziam a reprodução.

**O que mudou por causa da revisão:**
- **A limpeza do texto passou a conferir o próprio resultado.** A primeira versão protegia código e fórmulas por padrões de texto, e a revisão achou casos em que o Obsidian leria outra coisa (uma crase escapada, um bloco dentro de uma lista, uma fórmula atravessando parágrafos). Agora o texto que vai para a nota é lido por um analisador de Markdown e, se sobrar algo vivo, é refeito sem nenhuma marcação.
- **O que a conferência não via.** Links para arquivos do computador e para scripts, que o analisador recusava em silêncio; links entre notas, comentários e etiquetas, que só o Obsidian interpreta; blocos de linguagens que o Obsidian ou um plugin executa (consultas, diagramas, scripts) e comandos de plugin de modelos. Todos passaram a ser procurados no texto final.
- **Campos de uma linha.** O DOI da ficha podia carregar um link; "# x" virava título dentro de uma anotação; uma barra vertical no título de um site quebrava a tabela. Esses campos saem sempre sem marcação.
- **Gravação.** Um nome que mudava só nas maiúsculas apagava a nota recém-gravada; uma linha adulterada no registro apagava arquivos fora das três pastas; um arquivo do pesquisador com o nome de uma nota gerada era coberto; nomes apenas parecidos ("Weiss" e "Weiß") eram confundidos; uma nota aberta em outro programa parava a rodada inteira. Quem decide agora se dois nomes são o mesmo arquivo é o sistema de arquivos.
- **Servidor.** Faltava o disparo quando uma versão nova não podia ser lida; a pasta do espelho podia cair dentro de uma pasta do AL-IAdo; ler todas as conversas segurava a trava mais do que precisava.
- **Dados malformados e textos enormes.** Uma data impossível ou um campo de outro tipo derrubava a exportação; uma linha de 20 mil caracteres levava segundos. Os dois casos têm teste.

**Sem nova rodada de agentes:** as correções da rodada 3. Elas foram conferidas pelos testes, pela reprodução de
cada caso apontado e por um teste aleatório (abaixo).

**Teste aleatório da limpeza,** depois das correções: 60 mil combinações de marcas do Markdown e do Obsidian.

| Medida | Resultado |
|---|---:|
| Exceções | 0 |
| Textos com algo vivo depois da limpeza | 0 |
| Textos que caíram na forma sem marcação | 159 (0,3%) |
| Textos trocados pela frase fixa | 0 |
| Texto mais lento | 0,002 s |

## Ponta a ponta nos dados reais

Só com leitura sobre `data/`: conversas lidas dos arquivos, catálogo aberto em modo leitura e memória numa cópia.
O cofre de teste ficou em `tmp/lote-28/obsidian`.

| Medida | Resultado |
|---|---|
| Entradas | 7 conversas, 26 documentos, 252 anotações |
| Notas | 63: 7 de conversas, 26 de documentos, 29 de anotações (26 de documentos, 3 de conversas) e a de apresentação |
| Anotações de documentos apagados, deixadas de fora | 16 |
| Links entre notas | 239, nenhum quebrado; nenhum nome repetido |
| Caminhos de pasta, nome de usuário ou e-mail nas notas | nenhum |
| Mensagens que caíram na forma sem marcação | 0 de 90 |
| Tempo da primeira rodada | 0,12 s |
| Segunda rodada, sem mudança nos dados | 0 arquivos gravados, 0,11 s |
| Data de criação dos arquivos | igual à do registro nas 62 notas com data |
| Maior caminho de arquivo | 179 caracteres |

## Conferência no navegador

Servidor de teste em `127.0.0.1:8778`, com a interface, as rotas, a biblioteca e a memória reais, e o modelo, o
revisor e as fichas simulados. Refeita com o código final.

| Ação na tela | Resultado na pasta |
|---|---|
| Abrir o servidor | A apresentação e uma nota por documento, antes de qualquer pergunta. |
| Uma pergunta com a biblioteca ligada | Nota da conversa, com a fórmula intacta e cada documento citado como link para a nota dele. |
| Uma resposta que gera anotação | Nota de anotações da conversa, ligada a ela. |
| Um arquivo enviado pela tela | Nota do documento e nota das anotações da ficha de leitura. |
| Uma anotação criada na aba Memória | Entra na nota de anotações da conversa aberta. |
| Console do navegador | Sem erros. |

## Desvios do plano

- **Agentes na revisão:** o plano falava em uma rodada pequena, de até 5 agentes. Foram 7 em três rodadas, porque cada rodada achou defeitos novos na limpeza do texto. Um verificador da primeira rodada parou no limite de uso.
- **Limpeza do texto:** o plano previa reaproveitar os padrões de fórmulas da tela. Ficaram padrões próprios, mais restritos, e entrou a conferência do resultado por um analisador de Markdown.
- **Linguagens dos blocos de código:** só as que apenas mudam as cores são mantidas. Diagramas (mermaid) aparecem como texto.
- **Arquivos do pesquisador:** o plano dizia que as notas geradas são sempre substituídas. Um arquivo do pesquisador com o mesmo nome, que o AL-IAdo não escreveu, passou a ser preservado.

## Pendências

- **Aceite no Obsidian, com o pesquisador:** abrir `data/obsidian` como cofre e conferir as três cores, a animação do grafo e alguns links. O Obsidian em si não foi usado na validação: a conferência do texto segue as regras gerais do Markdown e procura as marcas próprias dele.
- As correções da rodada 3 não passaram por nova rodada de agentes.
- Renomear uma conversa ou mudar a ficha de um documento troca o nome da nota: o Obsidian vê uma nota apagada e outra criada.
- Notas de rodapé, código recuado sem cerca e uma fórmula em bloco com linha em branco no meio aparecem como texto.
- Um título feito com uma linha de `=` dentro de um item de lista mais fundo não desce de nível.
- Se o registro do cofre for apagado, notas antigas que já deveriam ter saído ficam na pasta até serem apagadas à mão.
- A data de criação dos arquivos só é gravada no Windows.
- A pasta `.obsidian/` criada na raiz do repositório em 03/10 continua lá; ela passou a ser ignorada pelo Git, e apagá-la é decisão do pesquisador.

## Estado final

- `data/obsidian/` foi gerada com os dados reais, pelo mesmo código do servidor, para o aceite. Ela fica fora do Git.
- `tmp/lote-28/` guarda o cofre de teste, a cópia da memória e o servidor de teste. Pode ser apagada depois da revisão.
- `.claude/launch.json` não mudou: a entrada do servidor de teste foi retirada.
- **Com o pesquisador:** o aceite no Obsidian e a autorização do commit do lote 28.
