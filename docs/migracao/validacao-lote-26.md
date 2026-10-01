# Validação do lote 26 — resultados no chat e lançamento da 0.3.0

Verificação local em **01/10/2026**, sobre o commit `36bf84a` (lote 25). Houve **16 chamadas pagas**, todas
no aceite autorizado: 8 respostas e 8 revisões de memória. O assistente não fez push nem tag.

## Testes

32 testes novos:
- **`tests/test_numbers.py`, 11 testes:**
  - datas, referências, marcas e nomes de ensaio não contam como número;
  - fórmulas e potências de 10 são lidas como números;
  - só a escrita pode diferir;
  - cada trecho é conferido contra o bloco citado;
  - o trecho de um documento ou da web fica fora;
  - tabelas e listas herdam as marcas da linha que as abre;
  - marcas agrupadas são separadas, e marcas inventadas são apontadas.
- **`tests/test_results_digest.py`, 9 testes:**
  - a escrita dos números e as notas iguais às da aba Ciência;
  - os 8 blocos, com fonte, data e estatuto;
  - as notas enviadas uma vez só, e a seção da aba em cada bloco;
  - os blocos parciais, com o que faltou dito em palavras;
  - o cache;
  - a interface e o resumo abrem sem numpy nem torch;
  - com os dados reais: 10 e 8 ensaios, 2,04 s, 0,402, 207 por hora, 0,06 s, 19,4, NPR 168 e 99,091%.
- **`tests/test_results_chat.py`, 9 testes:**
  - a posição dos resultados no pedido, e o pedido igual sem eles;
  - os quatro estados da resposta;
  - a citação de documento conferida antes;
  - o fluxo, a marca [Rn] na tela e o comando `preparar --resultados`.
- **`tests/test_web.py`, 3 testes novos:**
  - o interruptor chega ao agente e vale ligado só na skill do mestrado;
  - os blocos citados são gravados e exibidos, e a resposta com número não conferido sai do histórico;
  - uma falha ao montar o resumo não derruba a conversa.
- **Testes que já existiam:** o do provedor passou a conferir os tokens do cache, e o da skill, a versão 0.2.2.

**448 testes passaram** (416 do lote 25 e 32 novos), no Python 3.12.14. O Ruff não apontou problemas, e
`app.js`, `ciencia.js` e `graficos.js` passaram na checagem de sintaxe.

## Revisão por agentes antes do aceite

Cinco revisores leram as mudanças, e cada defeito apontado passou por uma verificação adversarial. **25
defeitos foram confirmados e corrigidos:**

| Onde | Defeito |
|---|---|
| Leitura dos números | Frações como "11/14" eram lidas como datas e passavam sem conferência. |
| Leitura dos números | Números dentro de fórmulas `$…$` eram ignorados. |
| Leitura dos números | Tabelas e listas abertas por uma frase marcada não eram conferidas. |
| Avisos falsos | Intervalos como "0%–1,9%", datas por extenso, anos de referências e números de documentos na mesma linha geravam aviso. |
| Marcas | Grupos mistos, como [R1, Kabc], não eram separados. |
| Resumo | Um arquivo truncado derrubava o resumo inteiro, e uma reanálise quebrada tirava os blocos oficiais. |
| Resumo | O bloco dos alarmes estimados sumia sem a pasta do treino. |
| Tela e chat | Os decimais do resumo diferiam dos da aba Ciência. |
| Pedido | O modelo não recebia os nomes das seções da aba. |
| Interface | A janela de fontes não rolava até o bloco, as tabelas vazavam, e a barra de envio estourava na tela estreita. |

Depois das duas primeiras respostas do aceite, a contagem de números sem marca foi revista: ela contava
títulos numerados e números que estavam nos blocos. Passou a contar só os números sem marca que não estão
em nenhum bloco enviado.

## Aceite pago

A interface de teste rodou em `127.0.0.1:8775`, com cópias em `tmp/lote-26`, a skill do mestrado, a
biblioteca desligada e os resultados ligados.

| Pergunta | Modelo | Estado | Blocos | Tokens de entrada |
|---|---|---|---|---:|
| Quantos ensaios cada modelo detectou na avaliação oficial? | Flash | conferido | R1 | 10.922 |
| Qual foi o atraso mediano na avaliação oficial e na reanálise? | Flash | conferido | R1, R5 | 11.182 |
| Quantos alarmes falsos por hora? Existe estimativa além do observado? | Flash | conferido | R2, R6 | 11.572 |
| Qual o NPR da CCB e a posição pela taxa de falha? | Flash | conferido | R7 | 11.956 |
| Qual a disponibilidade da CCB nos dois cenários de reparo? | Flash | conferido | R8 | 12.171 |
| Em uma frase: para que serve a FMECA no meu trabalho? | Flash | sem citação | nenhum | 11.237 |
| Em quais tipos de falha o Denso detectou e o AE-LSTM não? | Flash-Lite | conferido | R4 | 11.785 |
| A taxa de falha do IGBT é parecida com a da literatura? (web ligada) | Flash-Lite | conferido | R7 | 11.890 |

- **Números:** nenhum número ficou fora dos blocos citados nas 7 respostas com números.
- **Conteúdo das respostas, lido uma a uma:**
  - os números são os da aba Ciência: 10 e 8 de 14 ensaios; 2,04 s e 1,7 s; 0 e 68,9 alarmes por hora, com limites de 207 e 327; NPR 168, com S 7, O 4 e D 6; 99,924% a 99,091%, com 6,65 a 80,4 h paradas por ano;
  - a reanálise apareceu depois do oficial, identificada como secundária;
  - a pergunta sem números foi respondida em uma frase, sem marca e sem aviso;
  - com a web ligada, os números da literatura ficaram com a marca da web, e os da FMECA, com [R7].
- **Custo:**
  - cada pergunta levou de 10,9 a 12,2 mil tokens de entrada. Os blocos respondem por cerca de 5,5 mil;
  - o provedor informou tokens lidos do cache em uma chamada (2.827); nas outras, não informou;
  - no total, as 16 chamadas somaram 108.420 tokens de entrada: 69.040 no Flash e 39.380 no Flash-Lite.

## Aceite no navegador

| Item | Resultado |
|---|---|
| Interruptor | Aparece ao lado de biblioteca e web, ligado na skill do mestrado, com a explicação ao passar o mouse. |
| Resposta | As marcas [Rn] viram botões, e a resposta traz o link "N resultado(s)". |
| Janela de fontes | O grupo "Resultados da pesquisa" traz os blocos citados, com a tabela, as notas e o selo de secundária na reanálise. **Ver na aba Ciência** abre a seção certa. |
| Termos na tela | Nenhum código interno, nome de pasta ou de arquivo nos cartões. |
| Tela estreita (360 e 320 px) | Sem rolagem lateral no chat e na janela de fontes. As tabelas rolam dentro da própria caixa. |
| Console | Sem erros. |

Os prints foram feitos por Chrome headless e enviados ao pesquisador.

## Pedido sem custo

`aliado preparar --resultados "Quantos ensaios cada modelo detecta?"` mostra o pedido com os 8 blocos. O
resumo tem 15.347 caracteres, sem termos internos, com o oficial antes da reanálise.

**Desvio do plano:** o teto do resumo era de 14 mil caracteres e passou a 16 mil. As notas dos indicadores
e os dois cenários de reparo pesaram mais que o previsto.

## Pacote 0.3.0

- **Arquivo:** `dist/v0.3.0/aliado-0.3.0-py3-none-any.whl`, 93 arquivos, 687 kB, SHA-256 `bd3dc2ba9d85d0d22172f47b5ac6b705dcf8e5eb26cf02004477483da953ca2b`.
- **Conteúdo, conferido arquivo por arquivo contra `src`:**
  - os 88 arquivos do pacote têm o mesmo hash dos de `src`, e nenhum arquivo de `src` ficou de fora;
  - entraram o resumo, a conferência, `graficos.js` e o D3 com a licença;
  - nada de testes, documentação ou dados, e nenhuma sobra de build antigo. A conferência foi feita com a pasta `build/` ainda no lugar.
- **Teste fora do projeto:** instalado com `--target` em `tmp/lote-26/pkg`. O código carregado veio do pacote, e a versão lida foi 0.3.0.
  - `aliado skills`, rodado de outra pasta, listou as 3 skills, e `aliado ciencia fmeca` gerou o relatório.
  - A interface respondeu 200 em `/`, `app.js`, `ciencia.js`, `graficos.js`, `app.css`, no D3 e na licença dele, em `/api/estado`, `/api/ciencia`, `/api/ciencia/resumo`, `/api/ciencia/inicio`, `/api/ciencia/componentes` e `/api/ciencia/fmeca`.
  - O resumo montado pelo pacote trouxe os 8 blocos, sem nada faltando.

## Auditoria dos arquivos públicos

Nos 238 arquivos rastreados e nos novos do lote: nenhum `.env`, nada de `data/`, `tmp/`, `dist/` ou
`build/`, nenhum PDF, `.npz`, `.jsonl` ou modelo, e nenhuma chave. O caminho pessoal continua só em
`lote-10.json`, como registrado antes.

## Estado final

- `.claude/launch.json` ganhou a entrada `aliado-web-lote-26`.
- As cópias do aceite em `tmp/` e a pasta `build/`, com sobras de builds antigos, foram apagadas depois da revisão, a pedido do pesquisador (01/10). O wheel em `dist/v0.3.0` ficou.
- O commit do lote 26 foi feito pelo assistente, com a autorização do pesquisador (01/10), sem tag e sem push.
- `main` fica 5 commits à frente do GitHub (lotes 22 a 26).
- **Com o pesquisador:** a tag `v0.3.0` e o push.
