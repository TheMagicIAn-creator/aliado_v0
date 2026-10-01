# Lote 26 — resultados no chat e lançamento da 0.3.0

Lote autorizado em 30/09/2026, depois do lote 25 (`36bf84a`). É o último do roteiro da 0.3.0. Até aqui, o
chat não conhecia os resultados da pesquisa: a skill do mestrado mandava olhar a aba Ciência. O
pesquisador quer perguntar no chat, por exemplo, "quantos ensaios cada modelo detecta?" ou "qual a
disponibilidade da CCB?", e receber os números certos, com a fonte.

## Decisões do pesquisador (30/09)

| Tema | Decisão |
|---|---|
| Entrada | Um interruptor **Usar resultados**, ao lado de biblioteca e web. Vem ligado na skill do mestrado e pode ser desligado. |
| Número que não confere | A resposta aparece com um aviso que lista os números e indica a aba Ciência. Ela sai do histórico e da memória de conversas. |
| Conteúdo | 8 blocos resumidos, no formato da aba Ciência. |
| Lançamento | A 0.3.0 sai neste lote, com cerca de 8 perguntas pagas de aceite. O wheel é conferido por hash e instalado fora do projeto. O assistente faz o commit com permissão; a tag `v0.3.0` e o push ficam com o pesquisador. |

## Como os resultados chegam ao modelo

O AL-IAdo não usa chamada de ferramentas: o adaptador do Gemini aceita só texto e JSON, e a busca na web é
a do próprio provedor. Três caminhos foram comparados por um painel de avaliação: os resultados no próprio pedido (nota 8,3), uma
ferramenta de consulta (5,6) e os relatórios guardados na biblioteca (4,7). Ficou o primeiro:
- os números vêm das mesmas funções que alimentam a aba Ciência, e não dos relatórios em texto;
- o pedido não muda quando o interruptor está desligado;
- o custo é fixo e conhecido.

## Escopo implementado

- **Resumo dos resultados** (`science/digest.py`, sem dependências no topo):

  | Bloco | Conteúdo | Estatuto |
  |---|---|---|
  | R1 | Avaliação de 27/09: ensaios detectados, com a faixa dos 5 treinamentos, atraso mediano e as 8 métricas | oficial |
  | R2 | Alarmes falsos nos 52 s saudáveis: observados, por hora, limite superior e janelas acima do limiar | oficial |
  | R3 | Comparação Denso − AE-LSTM nos 5 objetivos, com a diferença, o intervalo e a leitura | oficial |
  | R4 | Cada tipo de falha (F1 a F7, com o nome), com os dois modos somados | oficial |
  | R5 | Reanálise de 30/09: a classe de cada ensaio e os indicadores com o meio do registro e com a mudança observada | secundária |
  | R6 | Reanálise de 30/09: alarmes estimados por hora e faixa esperada pelo limiar | secundária |
  | R7 | FMECA: S, O, D, NPR, ordem pela taxa e pares discordantes, com a fonte | oficial |
  | R8 | Confiabilidade e disponibilidade por grupo e base de tempo, sem as curvas | oficial |

  - Cada bloco traz título, fonte, data, estatuto, a seção da aba onde ele aparece, a tabela e as notas dos indicadores.
  - Os números saem com a mesma escrita da tela (2,04 s; 0,402; 207 por hora).
  - As notas vão uma vez só no pedido, e cada bloco diz onde vê-lo na aba.
  - O cabeçalho diz que a avaliação de 27/09 é a oficial e que a reanálise é secundária.
  - Se faltar uma parte (a reanálise, a avaliação, o numpy ou um arquivo truncado), entram os blocos que funcionarem, e o cabeçalho diz em palavras o que faltou.
  - O resumo fica em cache e só é refeito quando um arquivo de origem muda.
  - Ficam de fora os 14 ensaios de cada modelo, a grade de percentis, as curvas e as explorações.
- **Pedido** (`agent.py`): `prepare_request(..., results=…)` acrescenta as regras dos resultados e a mensagem "Resultados da pesquisa (dados de consulta)", depois das referências da skill e antes da memória.
  - Os blocos são dados, não instruções.
  - Cada número tirado deles leva a marca [Rn] na mesma frase, linha ou item, escrito como está.
  - O oficial vem antes do secundário, e o secundário aparece identificado.
  - Se o número pedido não está nos blocos, a resposta diz isso e indica a seção da aba.
- **Conferência dos números** (`numbers.py`, só com a biblioteca padrão):
  - cada trecho fechado por [Rn] tem os números comparados aos impressos nos blocos citados e nas notas enviadas;
  - só a escrita pode diferir: 2.041 e 2041; 0,402 e 0.402; 63,7e-6 e 63,7 × 10⁻⁶;
  - o trecho fechado por uma marca de documento [K…] ou da web [Wn] pertence a essa fonte e fica fora;
  - linha de tabela e item de lista sem marca herdam as marcas da linha que os abre;
  - datas, referências (autor e ano, tabela, página, norma) e nomes de ensaio (F1L) não contam como número;
  - marcas agrupadas, como [R1, R4] ou [R1-R3], são separadas antes da conferência.
- **Estados da resposta:**

  | Estado | O que acontece |
  |---|---|
  | Conferido | Todos os números marcados estão nos blocos citados. |
  | Sem citação | A resposta não usou nenhum bloco. Não há aviso. |
  | Números não conferidos | A resposta aparece com o aviso e a lista dos números, e sai do histórico e da memória de conversas. |
  | Marca inventada | Um [Rn] que não foi enviado troca a resposta por um aviso, como já acontece com uma citação de documento inventada. |

- **Interface:**
  - o interruptor, guardado por skill no navegador;
  - a marca [Rn] vira um botão, e a resposta ganha o link "N resultado(s)";
  - a janela de fontes ganha o grupo "Resultados da pesquisa", antes dos documentos. Cada cartão tem o título, a fonte e a data, o selo de secundária quando cabe, a tabela, as notas e o botão **Ver na aba Ciência**.
- **Uso:** o registro de uso passa a guardar os tokens de entrada lidos do cache do provedor, quando ele informa.
- **Memória:** o revisor não anota como fato os números marcados com [Rn].
- **Linha de comando:** `aliado preparar --resultados` mostra o pedido com os blocos, sem custo.
- **Skill do mestrado 0.2.2:** usa só os números dos blocos, com a marca, ou indica a aba.
- **Aba Ciência:** os cartões do Resumo e as Métricas por falha passaram a 3 casas e ao mesmo formato de segundos do resumo, para a tela e o chat mostrarem o mesmo número.

## Limites assumidos

- Um número sem a marca [Rn] não é conferido. A resposta conta os números sem marca que não estão em nenhum bloco, e a tela avisa.
- A conferência compara números, não frases: um número certo, atribuído ao indicador errado dentro do mesmo bloco, passa.
- O chat não calcula. Somas, médias e conversões de unidade sobre os resultados não são feitas.
- Com o interruptor desligado, uma marca [Rn] fica como texto.
- O resumo tem 15,3 mil caracteres, com teto de 16 mil. O plano previa 8 mil e teto de 14 mil: as notas dos indicadores e os dois cenários de reparo pesaram mais.

## Lançamento 0.3.0

- A versão passa a 0.3.0 em `pyproject.toml`, a única fonte.
- O README, o registro de mudanças, o roteiro, o `AGENTS.md` e o mapa de migração foram atualizados.
- O wheel é gerado em `dist/v0.3.0`, conferido arquivo por arquivo contra `src` e instalado numa pasta fora do projeto.
- A tag `v0.3.0` e o push ficam com o pesquisador.

## Critérios de aceitação

- **Testes sem rede:**
  - os 8 blocos, o estatuto de R5 e R6, a escrita igual à da tela, o teto de tamanho e os blocos parciais;
  - nenhum termo interno no que vai ao modelo;
  - com os dados reais: 10 e 8 ensaios, 2,04 s, 0,402, 19,4, NPR 168 e 99,091%;
  - a conferência: separadores, datas e nomes ignorados, e número inventado, arredondado ou convertido apontado;
  - o pedido igual sem resultados, a posição das mensagens e os quatro estados;
  - a interface e o resumo abrem sem numpy nem torch.
- **Revisão por agentes**, com verificação adversarial de cada defeito apontado, antes do aceite.
- **No navegador:** o interruptor, a janela de fontes com o grupo novo, a tela estreita e o console sem erros.
- **Aceite pago, 8 perguntas:** detectados, atraso oficial e da reanálise, alarmes falsos, NPR da CCB, disponibilidade da CCB, uma pergunta sem números e uma com a web. Registrar os tokens e os números não conferidos.
- **Pacote:** o wheel igual ao `src`, sem testes, documentos ou dados, e a instalação de fumaça.

## Fora do escopo

- Chamada de ferramentas pelo modelo e cálculo sob demanda no chat.
- Os resultados por ensaio, as curvas e as explorações no chat.
- A cópia de segurança da memória, que ficou fora da 0.3.0.
