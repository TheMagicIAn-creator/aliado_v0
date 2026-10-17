# Validação do lote 33

Trabalho local em 16 e 17/10/2026, sobre o lote 32 (sem commit), com as decisões do pesquisador nas perguntas e
respostas de 17/10. Escopo na [spec 0033](../specs/0033-reescrita-aprendizado-resultados.md). Nenhum commit, push
ou publicação. Uma única rodada paga, dentro do limite autorizado, sem envio ao serviço de arquivos do Google.

## Ponto de partida

Em 05/10, às 18h25, depois da validação do lote 32, entrou no código um plano por partes (`knowledge/coverage.py`
e trechos de `rewrite.py`, `agent.py`, `app.py` e `app.js`), sem spec nem testes. Ele respondia a um pedido real
daquele dia: "uma fonte para cada um" (MCC, FMEA e FMECA) tinha saído só com a MCC, por uma página de uma resposta
antiga. Com ele, a suíte tinha 737 testes passando e 2 falhando. O pesquisador decidiu adotá-lo e corrigi-lo.

## O que foi entregue

- **Reescrita seletiva.** Uma decisão local, sem tokens, escolhe entre três caminhos:
  - **sem reescrita:** a mensagem já diz o assunto, com dois termos ou mais, sem sigla e sem depender da conversa;
  - **reescrita simples:** a mensagem depende da conversa ("isso", "outra fonte", "e o segundo?"), continua ou
    aprofunda a anterior, ou traz uma sigla, que a reescrita escreve por extenso e em inglês ("MCC" e "RCM");
  - **plano por partes:** o pedido tem uma lista, uma comparação, ou um "cada um" depois de um pedido com lista.
- **Plano por partes corrigido:**
  - a regra de um título por parte só vai ao modelo quando há duas partes ou mais;
  - a segunda chamada só acontece se uma parte sem citação tiver material que a busca achou e não enviou, ou se
    a primeira leitura foi por trechos; parte sem nenhum candidato não gera chamada;
  - a segunda chamada é automática dentro do teto de 30 mil e antes do aviso de 300 mil por dia; fora disso,
    a resposta fica e aparece o botão "Completar pesquisa", com a estimativa;
  - uma segunda leitura que não melhora a resposta é descartada, e a rota mostra quanto ela custou.
- **Trilhas do lote 31 de volta.** A pergunta muito parecida com uma já respondida volta a partir das páginas
  daquela resposta, sem nova busca, quando tem uma parte só e a trilha não está fraca. Com mais partes, as páginas
  de antes só apoiam a busca. A linha da rota volta a dizer "partiu de uma resposta anterior".
- **Aprendizado com o uso**, em `data/memoria/memoria.sqlite3` (tabela nova `route_lessons` e coluna `weak` nas
  trocas):
  - o modelo, a skill ou a leitura fixados na tela, quando diferem da escolha automática, ficam guardados para a
    mensagem; numa mensagem muito parecida (semelhança de 0,85 ou mais), a escolha automática repete a sua, e a
    linha da rota diz "repetiu uma escolha sua", com a data e a mensagem na dica;
  - a leitura aprendida nunca é a ampla, e o documento inteiro só vale quando a mensagem nova cita um documento;
  - "Ler mais fundo", a pergunta refeita em seguida e a reclamação ("você não conseguiu…", "faltou…") marcam a
    trilha da resposta anterior como fraca e guardam a pergunta com a leitura por páginas;
  - a reclamação depois de uma resposta da biblioteca lê páginas inteiras da pergunta anterior;
  - apagar a conversa apaga também o que foi aprendido nela.
- **Vocabulário dos resultados.** O roteador reconhece os modelos, os ensaios e as métricas que aparecem no resumo
  dos resultados montado para o chat ("Denso", "AE-LSTM", "F1L", "sensibilidade", "atraso mediano"…). Um modelo
  ou um ensaio basta; uma métrica precisa de um objeto da pesquisa ou de um valor obtido ("maior", "detectou");
  um pedido de fonte ou de conceito ("o que é", "segundo a literatura") continua na biblioteca. O resumo é montado
  no máximo uma vez por mensagem, e só quando a pergunta precisa dele ou na primeira vez.
- **Conversa solta** depois de uma resposta da biblioteca ("kkkk", "valeu", "relaxa") não volta à biblioteca,
  salvo se pedir algo dela ("Valeu! E a segunda fonte?").

## Medição sem tokens

Script: [medir-lote-33.py](medir-lote-33.py). Resumo, sem o texto das conversas: [medicao-lote-33.json](medicao-lote-33.json).
O roteador anterior foi carregado do commit `98be273`. As perguntas guardadas estão em
[perguntas-lote-33.json](perguntas-lote-33.json), escritas em 17/10 antes de qualquer mudança e não usadas para
ajustar as regras. As regras foram ajustadas com outras 10 perguntas de 16/10 e com as mensagens reais.

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
.venv/Scripts/python.exe docs/migracao/medir-lote-33.py --saida data/validacao-lote-33-nova
```

| Perguntas guardadas | Antes | Lote 33 |
|---|---:|---:|
| Sobre os resultados, sem a palavra "resultados" (meta: 9 de 10) | 7 de 10 | 9 de 10 |
| De literatura tratadas como resultados (o certo é 0) | 1 de 5 | 1 de 5 |
| Conversa solta depois da biblioteca, fora da biblioteca | 0 de 4 | 4 de 4 |
| Pedidos à biblioteca depois da biblioteca, mantidos | 4 de 4 | 4 de 4 |
| Reclamações com leitura mais funda | 0 de 2 | 2 de 2 |
| Pedidos com partes e perguntas simples, divididos certo | — | 5 de 5 |
| Reescrita dispensada ou mantida como esperado | — | 4 de 4 |

- A pergunta de resultados que ficou de fora: "Quais falhas passaram sem ser percebidas pelos autoencoders?".
- A de literatura tratada como resultados: "Segundo a literatura, o que é um autoencoder LSTM?". O classificador
  por frases a aproxima dos resultados; como pede a literatura, ela vai com trechos e com os resultados, como antes.
- **Mensagens reais (59):** 3 mudaram de rota. Duas conversas soltas deixaram a biblioteca e o modelo maior; a
  reclamação "Você não conseguiu me trazer nenhuma definição." passou de trechos a páginas inteiras.
- **Reescrita nas 24 mensagens reais que iriam à biblioteca:** 5 sem reescrita, 17 com a reescrita simples e 2 com
  o plano. Cada uma das 5 deixa de gastar a reescrita: 580 tokens no registro de uso de 05/10, e 483 tokens de
  entrada na reescrita do teste pago. O tempo poupado não foi medido.
- **Busca sem reescrita, na biblioteca real (só leitura):** das 5, as 2 perguntas de literatura (Lafraia e o
  artigo "Fault Detection Algorithms…") trouxeram, pela própria pergunta, o primeiro documento que a consulta
  reescrita trazia. As outras 3 não são respondidas pela biblioteca (sobre o próprio AL-IAdo e o mestrado), e as
  duas buscas trouxeram documentos diferentes e sem relação com elas.

## Teste pago

Autorizado: até 8 chamadas e 80 mil tokens de entrada. Usado: **5 chamadas e 27.380 tokens de entrada**.
Roteiro em `tmp/lote-33/verificar.py`, numa pasta de dados limpa, com a biblioteca real só para leitura e o
registro de uso próprio. Sem o registro do serviço de arquivos: nada foi enviado ao Google Files.

| Pergunta | Chamadas | Entrada | Tempo | O que saiu |
|---|---:|---:|---:|---|
| "Traga da literatura os principais conceitos de confiabilidade, como manutenção centrada em confiabilidade, FMEA e FMECA" | 2 | 9.102 | 43 s | plano com 3 partes, as 3 citadas; 8 páginas de 5 documentos |
| "Traga com base na literatura uma fonte para cada um. No caso, é a MCC, não somente a confiabilidade." | 2 | 11.159 | 19 s | as 3 partes recuperadas da mensagem anterior, uma fonte citada para cada |
| "Como se calcula a disponibilidade de um sistema reparável?" | 1 | 7.119 | 16 s | sem reescrita; 3 páginas citadas de 2 documentos |

- Em 05/10, o segundo pedido tinha saído só com a MCC, por uma página. Agora: MCC pela IEEE 493 (p. 134), FMEA por
  Patil et al. (2024) e FMECA pelo material "FMEA – Análise dos Modos de Falha e seus Efeitos" (p. 7). O trecho de
  Patil et al. descreve usos do FMEA, e não uma definição: a conferência confere a citação, não o conteúdo.
- **A segunda chamada não aconteceu com o modelo real:** nas duas perguntas com partes, as três saíram citadas na
  primeira resposta. Ela foi conferida só nos testes locais.
- Modelos: `gemini-3.8-flash` nas respostas e `gemini-3.5-flash-lite` nas duas reescritas.

## Testes

Em 17/10/2026: **757 testes passaram** em 197 s, já com as correções da auditoria, com o aviso já existente do `starlette.testclient`; **Ruff sem
problemas**. Os 2 que falhavam (trilha e texto da rota) voltaram a passar. Novos: `test_coverage.py` (plano,
partes, conferência, reescrita seletiva e segunda chamada no chat), `test_learning.py` (escolhas aprendidas,
trilha fraca, reclamação e "Ler mais fundo") e três casos em `test_routing.py` (vocabulário, resultados e conversa
solta). Um teste antigo de trilhas passou a conferir também o aprendizado da pergunta refeita.

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
```

## Correções da auditoria (17/10/2026)

Uma auditoria do repositório, pedida pelo pesquisador, achou cinco problemas no código deste lote. Cada um foi
reproduzido antes da correção e ganhou um teste com o mesmo caso.

- **Leitura aprendida numa conversa solta:** o seletor de leitura fica guardado na tela entre as sessões, e um
  "Oi, tudo bem?" enviado com "Páginas inteiras" fixado fazia o mesmo "Oi" no modo automático ler 10 páginas.
  Agora a leitura aprendida só vale quando o roteador já iria à biblioteca.
- **Parte marcada como citada sem fonte:** com as partes "Confiabilidade" e "Manutenção Centrada na
  Confiabilidade", a seção da segunda contava para as duas. Agora cada seção vale só para a parte de nome mais
  longo que o título dela traz.
- **"Nossa, que interessante. E a FMECA?"** era tratada como conversa solta: o pedido "e a…" só era reconhecido
  no começo da mensagem. Agora vale também depois de um ponto ou de uma vírgula.
- **"Esse capítulo é denso…"** ia para os resultados: "denso" também é adjetivo. Agora o nome de um modelo só
  conta junto de uma métrica, de uma palavra da pesquisa ou de outro modelo.
- **"Agora traga uma fonte para ambos."** era reconhecida como pedido com partes, mas o plano local não
  recuperava a lista anterior. As duas listas de palavras de continuação passaram a usar a mesma constante.

A medição sem tokens, refeita depois das correções, deu os mesmos números (o resumo ficou idêntico).

## Limites

- As perguntas guardadas são poucas (31 casos); o roteador continua sendo um conjunto de regras e frases, e erra
  em mensagens escritas de jeitos que elas não cobrem.
- O aprendizado só reconhece mensagens muito parecidas com a da escolha; não generaliza para outros assuntos. Uma
  escolha fixada na tela durante uma conversa inteira vira uma escolha por mensagem.
- Sem a reescrita, a trilha é procurada pela própria pergunta; as trilhas antigas foram gravadas pela consulta
  reescrita, e a semelhança entre as duas tende a ser menor.
- A segunda chamada com o modelo real e a conferência por parte numa resposta com partes sem citação ficaram só
  nos testes locais.
- Os limites de 30 mil e 300 mil tokens não mudaram. Para usar o código novo, é preciso reiniciar o AL-IAdo.
