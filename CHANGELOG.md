# Registro de mudanças

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). As versões
seguem o [versionamento semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Lote 49: os laços dos testes dos autoencoders

- **Os treinos:** cada treino de rede dos testes é feito uma vez por bateria. Eram 28, agora são 18, e o treino com os
  dados reais roda uma vez (eram duas). Os testes da ciência caem de 180 para 124 s, e a bateria inteira, de 280 para
  217 s.
- **As pastas dos testes:**
  - os testes da ciência e do mestrado ficam em `tests/science/` e `tests/mestrado/`, um arquivo por pasta;
  - nenhum teste importa outro;
  - os dados reais entram por fixtures numa pasta temporária, e nada é gravado em `data/`.
- **O protocolo fixo (EXP-12):** os 24 atributos, a janela, a normalização, a divisão, o escore, o limiar e o alarme
  viram requisito com teste.
- **Ferramentas:**
  - `ferramentas/bateria.py`, com `--rapida`, que deixa de fora os testes que treinam ou leem os dados reais;
  - `ferramentas/equivalencia.py`, que prova que mudar arquivos de lugar não muda nenhum número.
- **O relatório em LaTeX de 21/10:** conferido em `docs/revisao/2026-10-21-relatorio-latex-conferido.md`.
- **Estado:** commits locais autorizados pelo pesquisador; o produto não muda.

### Lote 48: sem raciocínio na leitura de páginas e do documento

- **A mudança:** o modelo local responde sem o raciocínio oculto quando lê páginas inteiras ou o documento. Os trechos
  e a conversa continuam com ele, e o Gemini não muda.
- **A medição, com critério fixado antes:** nas 6 perguntas de páginas e de documento, duas vezes, sem token pago,
  a chamada mediana caiu de 133 para 71 s. Houve 1 descarte em 12, e o documento esperado foi citado em 10 de 12.
- **Estado:** adotado; commit c2768f1.

### Lote 47: roteador e intervalo de páginas

- **Roteador:** "como se calcula…" e as perguntas sobre uma tese, um TCC ou uma monografia vão à biblioteca, mesmo
  com palavras dos resultados da pesquisa. Nas 16 perguntas aprovadas, só a P7 e a E3 mudaram de rota, e as duas
  agora vão à biblioteca; antes iam aos resultados.
- **Citações:** o intervalo de páginas de um documento numa marca só (`[K…p1–K…p6]`), com todas as páginas enviadas,
  vale como cada uma delas.
- **Estado:** validado sem modelo; a conferência real vai junto da medição do lote 48.

### Lote 46: correções do relatório de eficiência

O relatório de eficiência do modelo local foi conferido com as medições; a versão corrigida está em
`docs/revisao/2026-10-20-relatorio-eficiencia-conferido.md`. O pacote fechado da 0.8.0 não muda.
- **Citações do local:** as instruções não mostram mais identificadores de exemplo, que o local copiava. A marca que
  aponta um único trecho enviado vale como ele, e o `[K...]` literal sai do texto.
- **Parada cedo:** na primeira marca que não confere, o local para de escrever, e o Gemini Flash refaz sem esperar.
- **Reescrita por partes:** desde a 0.6.0, o plano das perguntas com partes nunca chamava o modelo. Volta a chamar, e
  a reescrita simples pede só a consulta.
- **Ciência:** o cache dos erros por variável fica ligado aos pesos e à ordem das variáveis; nenhum número muda.
- **Medição:** nas 16 perguntas reais, sem custo, o local respondeu 12 (eram 10), e as respostas descartadas por
  marca caíram de 4 para 2.
- **Estado:** validado localmente, com 827 testes; commit 71afeed, com o lote 45.

## [0.8.0] — em fechamento local (20/10/2026)

Lotes 37 a 44: o modelo local (Ollama, `qwen3.5:9b`) como principal, com o Gemini Flash só no limite dele, e a leitura
das páginas da biblioteca sem pendências falsas. Entram também as correções feitas depois da 0.7.0.

### Lote 44: revisão e fechamento

- Anexo e primeira pergunta compartilham a criação da conversa; navegar não muda o destino do anexo nem deixa
  respostas atrasadas substituírem a conversa escolhida.
- A escalada usa o Gemini Flash inclusive com o modelo menor escolhido. Ao refazer uma resposta local completa
  reprovada na conferência do chat, a falta ou falha do Flash mantém essa resposta com o motivo na rota, sem nova tentativa automática.
- Registros 35/36 preservados; validação final e pacote a partir de fontes limpos no lote 44.
- Estado: validado localmente; aguardando revisão e commit do pesquisador.

### Lote 43: temperatura 0,6 no modelo local

O `aliado-local` passa a responder com temperatura 0,6; o `qwen3.5` vem com 1. Não há código novo.
- **Estabilidade:** em duas rodadas das 16 perguntas reais, sem custo, 13 tiveram o mesmo desfecho nas duas, contra 7
  com 1.
- **Respostas:** o local respondeu 13 e 11 (antes, 9 e 10) e citou o documento esperado em 8 (antes, 7).
- **Gemini e tempo:** as chamadas ao Gemini caíram para 4 e 5, e o tempo médio para 90 e 96 s.

Detalhes na [spec 0043](docs/specs/0043-temperatura-local.md) e na
[validação do lote 43](docs/migracao/validacao-lote-43.md).

### Lote 42: o modelo local quase todo na VRAM

O `aliado-local` passa a usar toda a VRAM: 32 das 33 camadas na placa (pico de 5,64 GB dos 6 GB), no lugar do limite
de 4 GB. A escrita foi de 15 para 25 tokens/s, e de 9 para 23 com o contexto quase cheio. O tempo médio nas 16
perguntas caiu de 158 para 102 s. A RAM não foi poupada, porque no Windows o que vai para a placa também conta na
memória reservada. Não há código novo. Detalhes na [spec 0042](docs/specs/0042-local-na-vram.md) e na
[validação do lote 42](docs/migracao/validacao-lote-42.md).

### Lote 41: o local mais rápido; OCR por página conferido

- **A reescrita da busca sai sem raciocínio:** antes, o local gastava 2 minutos nela e falhava em silêncio, e a busca
  seguia com a pergunta original. Agora sai em segundos, e o tempo médio por pergunta caiu de 265 para 158 s.
- **Os trechos sem raciocínio foram experimentados e desfeitos,** pela trava de qualidade combinada.
- **OCR página por página,** do documento "Por que o Aliado local está lento": já existia desde a 0.1.0. Ganhou o
  requisito BIB-04 e os testes do PDF todo digital e do todo escaneado. A calibração na biblioteca real manteve o
  limite de 20 caracteres.
- Detalhes na [spec 0041](docs/specs/0041-local-mais-rapido.md) e na
  [validação do lote 41](docs/migracao/validacao-lote-41.md).

### Lote 40: contexto de 32 mil tokens no modelo local

O `aliado-local` passa a ter 32 mil tokens de contexto, com 20 camadas na placa (pico de 3,999 GB, abaixo dos 4 GB), e
o `.env` ganha `AL_IADO_LOCAL_CONTEXT=32768`. Não há código novo. Nas 16 perguntas reais, sem custo, o local respondeu
14, contra 6 no lote 39; 10 citaram o documento esperado, nenhuma foi refeita e só 2 foram ao Gemini. Em troca, as
respostas do local levam 5 minutos na mediana. Detalhes na [spec 0040](docs/specs/0040-contexto-32k.md) e na
[validação do lote 40](docs/migracao/validacao-lote-40.md).

### Lote 39: o modelo local lê as páginas pelo texto guardado

Detalhes na [spec 0039](docs/specs/0039-local-le-texto.md) e na
[validação do lote 39](docs/migracao/validacao-lote-39.md).

- **Páginas como texto:** na leitura das páginas inteiras, do documento citado ou de uma trilha, o modelo local recebe
  o texto guardado de cada página, com o identificador de citação. Recebe também a descrição automática das figuras
  e tabelas, marcada para conferir no original. Não há mais o limite de 4 páginas; vale o contexto dele. O Gemini
  segue recebendo o PDF, sem tokens a mais.
- **Notas para o local:** uma diz que os PDFs vieram como texto; outra, com fontes no pedido, que cada afirmação se
  cita com o `[K…]`.
- **Medido nas 16 perguntas reais, sem custo:**
  - o local respondeu 6, contra 3 no lote 38;
  - 3 citaram o documento esperado, contra 1;
  - 7 foram direto ao Gemini, agora pelo contexto de 16 mil tokens, e não pelas páginas;
  - com 32 mil, 6 delas caberiam.

### Lote 38: o modelo local como principal (Etapas 2 e 3)

Detalhes na [spec 0038](docs/specs/0038-modelo-local.md) e na
[validação do lote 38](docs/migracao/validacao-lote-38.md). O modelo local fica desligado até entrar no `.env`.

- **Modelo local primeiro:** com `AL_IADO_LOCAL_MODEL` no `.env`, um modelo aberto no Ollama responde primeiro a
  tudo: a conversa, a reescrita da busca, o revisor de memória, as fichas e a descrição das figuras. Imagens e páginas
  de PDF vão como imagem. Sem a variável, nada muda.
- **Gemini Flash só no limite:** ele entra quando o local pede ajuda ("[ESCALAR]"), erra o formato pedido ou não
  responde nada; na conversa, também quando a resposta do local não cita o que a busca trouxe ou erra números. A
  pergunta é refeita uma vez, com o aviso "O modelo local não chegou lá", e a rota diz o motivo. A resposta cortada
  no teto de tamanho não escala.
- **Direto ao Gemini:** a busca na web e os pedidos maiores que o contexto local ou com mais de 4 páginas de PDF.
- **Ollama fechado:** a tela e o terminal dizem o que conferir, e nada vai ao Gemini.
- **Uso do dia:** os tokens do local ficam no registro, mas não contam no "hoje", no teto de 30 mil nem no aviso de
  300 mil; sob a resposta, aparecem como "tokens locais".
- O README ganhou a seção "Modelo local": a instalação, a quantização em 4 bits, o contexto, a placa até 4 GB e o
  SSD como reserva.
- **Etapa 3, neste computador:**
  - **Instalação:** o Ollama 0.40.6 e o `qwen3.5:9b` em 4 bits, criado como `aliado-local`, com 22 camadas na placa
    (3,9 GB).
  - **`use_mmap`:** os pesos fora da placa são lidos do arquivo no SSD. Sem ele, no Windows, o Ollama os copia e
    reserva 8,6 GB em vez de 6,6 GB.
  - **Velocidade:** entrada de 700 tokens/s e saída de 15 a 16 tokens/s.
  - **Escalada nas 16 perguntas reais da biblioteca, sem custo:**
    - 3 respondidas pelo local;
    - 8 direto ao Gemini, porque o documento ou as páginas inteiras passam de 4 páginas de PDF;
    - 3 refeitas pelo Gemini, porque o local citou por extenso, sem as marcas de citação.
- **Corrigido:** o pedido de ajuda que o modelo escrevia depois de um rótulo ("Resposta ao usuário: [ESCALAR]")
  aparecia na tela. Agora ele passa a vez ao Gemini.

### Lote 37: páginas sem pendência falsa

Detalhes na [spec 0037](docs/specs/0037-paginas-sem-leitura.md) e na
[validação do lote 37](docs/migracao/validacao-lote-37.md).

- **Página em branco:** é reconhecida pela imagem (a 100 dpi, menos de 0,1% de pontos no miolo) e não deixa o
  documento "parcial".
- **Página já descrita pelo modelo:** com OCR fraco ou sem texto, deixa de ser pendência, porque o conteúdo dela está
  na busca como descrição automática.
- **OCR fraco:** a página com confiança média abaixo de 50 entra na lista da descrição de figuras e tabelas, que
  continua só por pedido.

### Correções depois da 0.7.0

- **Anexos sempre fixados:** o documento anexado na conversa fica fixado nela pelo servidor, mesmo que a página mude
  de conversa ou seja recarregada antes de terminar a leitura. Na tela de apresentação, anexar já cria a conversa. O
  painel Documentos mostra primeiro os mais novos.
- **Testes com dados reais:** passam a ler uma cópia da avaliação de 27/09, e não a rodada atual da pasta de
  resultados, que muda quando o pesquisador roda um experimento.

## [0.7.0] — 2026-10-18

Lotes 34 a 36: a fundação revista, pela [revisão da modularização e das specs](docs/revisao/2026-10-modularizacao-e-specs.md).

### Lote 36: o mestrado fora do núcleo

Detalhes na [spec 0036](docs/specs/0036-mestrado-fora-do-nucleo.md) e na
[validação do lote 36](docs/migracao/validacao-lote-36.md).

- **Zero menções ao domínio no núcleo:** o código da pesquisa (preparo da base, treino, avaliação, início das
  falhas, reanálise, rodada atual, exploradores e o resumo dos resultados no chat) e a skill `pesquisa-inversores`
  foram para `src/aliado/specializations/mestrado/`. O teste que mede as menções exige zero.
- **O que a especialização entrega ao núcleo:** a skill padrão, as pastas da base e das referências, as frases do
  roteador, o assunto da reescrita da busca, o glossário da aba Ciência, os comandos `aliado ciencia *-gpvs`, as
  rotas da rodada atual e dos exploradores e os resultados do chat. O núcleo lê tudo isso quando precisa, nunca ao
  abrir.
- **O apoio da skill** (a de confiabilidade junto com a da pesquisa) passou a ser declarado no SKILL.md
  (`metadata.apoio`), em vez de estar no código.
- **O glossário da aba** (63 notas) passou a ter uma fonte só, na especialização; o resumo do chat usa as mesmas.
- Para quem usa, nada muda: os mesmos comandos, a mesma aba e as mesmas respostas.

### Lote 35: chat com tela mínima e pedidos escritos

Detalhes na [spec 0035](docs/specs/0035-chat-tela-minima.md) e na
[validação do lote 35](docs/migracao/validacao-lote-35.md).

- **Tela mínima:** saem do chat os seletores de skill, modelo, leitura e teto e as chaves de biblioteca, web,
  resultados e "+ confiabilidade". O AL-IAdo escolhe sozinho, como já fazia no modo automático; a biblioteca e os
  resultados ficam à mão do roteador, e a web só entra por pedido.
- **Pedido escrito:** quem quer escolher escreve na mensagem, no começo ou no fim de uma frase: "use o modelo
  maior", "só trechos", "use as páginas inteiras", "leia o documento inteiro", "leitura ampla", "busque na web",
  "sem biblioteca", "sem os resultados" ou "use a skill engenharia". O pedido sai do texto que vai ao modelo, e a
  linha sob a resposta diz "seguiu o seu pedido". Um botão da tela vale sobre o pedido; o pedido, sobre o que foi
  aprendido.
- **Mensagem só com o pedido:** "busque na web" sozinho refaz a pergunta anterior com a busca.
- **Leitura ampla** só por pedido escrito, com a confirmação do custo todas as vezes, mesmo abaixo de 30 mil
  tokens. "Ler mais fundo" para no documento inteiro. Os limites de 30 mil tokens por pergunta e de 300 mil por
  dia não mudaram.
- **Aprendizado:** o modelo, a skill e a leitura pedidos por escrito valem de novo numa mensagem muito parecida;
  a leitura ampla e a web nunca ficam guardadas.
- "Lembrar…" e os envios de documentos ficam com a skill da conversa; "Completar pesquisa" lê as páginas inteiras.

### Lote 34: experimentos do zero, rodada atual e PDF por pedido

Detalhes na [spec 0034](docs/specs/0034-experimentos.md) e na [validação do lote 34](docs/migracao/validacao-lote-34.md).

#### Adicionado

- **Rodar experimento.** Na aba Ciência, a seção **Experimento** roda de novo, do zero e de ponta a ponta, o
  experimento **AE Denso × AE-LSTM** na base de dados GPVS:
  - preparo da base, treino dos dois modelos em cada repetição, limiar, avaliação nos ensaios de teste, início
    observado das falhas e resumo, num processo só, com o andamento na tela e o botão de cancelar;
  - os parâmetros (separação entre blocos, repetições do treino e teto de épocas) ficam na tela, cada um com a
    sua nota; com os mesmos da rodada mostrada, o botão fica desativado e diz por quê;
  - antes de rodar, a janela diz quantas vezes os dados de teste já foram usados e pede a frase "consultar o
    teste"; cada rodada entra no registro de consultas;
  - com os parâmetros de 27/09, a rodada repete a avaliação de 27/09 bit a bit.
- **A rodada atual em toda a aba.** Resumo, escores, métricas, início das falhas, exploradores e os resultados no
  chat passam a ser os da rodada completa mais nova; sem nenhuma, os da avaliação oficial de 27/09. "Oficial" fica
  só para ela; uma rodada nova aparece com a data e o número da consulta ao teste.
- **Resultados em JSON e Markdown** (`resultado.json` e `resultado.md`) em cada rodada, numa pasta nova
  `data/resultados/ae-denso-lstm/rodada-NNN/`.
- **Baixar PDF:** um relatório técnico e formal da rodada atual (capa, sumário, seções numeradas, tabelas com
  legenda e notas, página n de N), montado só no clique e com o `resultado.json` anexado.
- **Comparar com resultado salvo:** o PDF baixado antes, ou o `resultado.json`, ao lado da rodada atual, indicador
  por indicador, com o botão para reaplicar os parâmetros guardados.
- **Terminal:** `aliado experimento listar`, `aliado experimento rodar` e `aliado experimento pdf`.
- **Specs vivas** por capacidade em `docs/specs/capacidades/`, com requisitos numerados, e o teste que confere que
  cada requisito tem teste; o teste que impede menções novas ao domínio no núcleo.

#### Alterado

- A seção "Rodar e arquivos" deu lugar à seção "Experimento": saem os botões de preparar, treinar e avaliar por
  etapa e a lista das pastas de resultados. Os comandos por etapa do terminal continuam.
- `aliado web --gpvs` passou a `--base`; as pastas antigas de resultados ficam no disco, sem mudança.
- `AGENTS.md` ficou só com as regras; a lista dos lotes e das specs foi para o roteiro.
- Botões desativados ficam esmaecidos em todo o app.

## [0.6.0] — 2026-10-17

Lotes 32 e 33, a partir do uso real.

### Lote 33: reescrita seletiva, aprendizado com o uso e resultados

Detalhes na [spec 0033](docs/specs/0033-reescrita-aprendizado-resultados.md) e na
[validação do lote 33](docs/migracao/validacao-lote-33.md).

- **Reescrita seletiva:** a pergunta que já diz o assunto vai direto à busca, sem a chamada de reescrita; a que
  depende da conversa ou traz sigla é reescrita como antes; o plano por partes só entra quando o pedido tem
  partes. A linha da rota diz como a busca foi preparada.
- **Plano por partes** (acrescentado em 05/10 sem registro, agora com spec e testes): uma busca e uma conferência
  para cada parte do pedido. Os títulos por parte só aparecem com duas partes ou mais. A segunda chamada, para as
  partes sem citação, só acontece se houver material novo a ler, dentro de 30 mil tokens e antes do aviso diário;
  fora disso, a resposta fica e aparece "Completar pesquisa". No pedido real de 05/10 ("uma fonte para cada um"),
  as três partes saíram com fonte, contra uma antes.
- **Trilhas:** o atalho do lote 31 volta para perguntas de uma parte só cuja resposta anterior bastou.
- **Aprendizado com o uso**, local e sem tokens: a escolha fixada na tela vale de novo numa mensagem muito
  parecida ("repetiu uma escolha sua"); "Ler mais fundo", a pergunta refeita e a reclamação enfraquecem a trilha
  da resposta anterior e guardam a leitura por páginas. A reclamação lê páginas inteiras da pergunta anterior.
- **Resultados:** o roteador reconhece os modelos, os ensaios e as métricas do próprio resumo dos resultados.
  Nas perguntas guardadas antes da mudança, 9 de 10 foram reconhecidas, contra 7.
- **Conversa solta** depois de uma resposta da biblioteca não volta à biblioteca nem ao modelo maior.
- **Medição:** 757 testes e Ruff; teste pago com 5 chamadas e 27 mil tokens de entrada, do limite de 8 e 80 mil.
  A segunda chamada não ocorreu com o modelo real e ficou conferida só nos testes.
- **Correções da auditoria:** uma leitura aprendida não leva mais uma conversa solta à biblioteca; uma parte do
  pedido só conta como citada pela própria seção; "E a FMECA?" depois de uma vírgula continua na biblioteca;
  "denso" como adjetivo não vai para os resultados; "ambos" recupera as partes do pedido anterior.

### Lote 32: busca e memória

Detalhes na [spec 0032](docs/specs/0032-busca-e-memoria.md) e na
[validação do lote 32](docs/migracao/validacao-lote-32.md).

- **Busca em memória:** os vetores são normalizados uma vez e comparados em conjunto. O cache acompanha
  os commits no catálogo, inclusive atualizações e exclusões por outra conexão. No catálogo sintético de
  20 mil trechos, a mediana das buscas seguintes caiu de 3,33 s para 0,082 s, com os mesmos 20 resultados.
- **Reordenação local das páginas:** uma segunda rede multilíngue avalia até 60 candidatos antes da
  leitura por páginas. O preparo explícito baixa cerca de 136 MB com revisão e hashes fixos; perguntas
  não baixam nada. Sem o modelo ou se ele falhar, segue a seleção anterior. A leitura conserva o número
  de páginas e a prioridade de documentos citados, fixados e trilhas.
- **Revisor de memória seletivo:** cumprimentos e consultas comuns deixam de gerar uma chamada extra.
  Pedidos de guardar algo, perfil, preferências, correções, decisões e declarações ambíguas continuam
  sendo revisados. A memória de conversas e as fichas documentais continuam funcionando.
- **Limites:** os ensaios são sintéticos e locais; não medem respostas reais do Gemini nem a economia
  de tokens do acervo. A reordenação acrescentou 1,37 s para 60 candidatos no ensaio. Os limites de
  30 mil tokens e 300 mil tokens por dia permanecem configurados como no lote 31.

## [0.5.0] — 2026-10-04

Lotes 30 e 31, a partir do uso real. Detalhes nas specs [0030](docs/specs/0030-leitura-integral.md) e
[0031](docs/specs/0031-roteador-e-escada.md) e nas validações dos lotes [30](docs/migracao/validacao-lote-30.md)
e [31](docs/migracao/validacao-lote-31.md). A 0.4.1, preparada no lote 30, não foi lançada: o padrão dela (ler
até 400 mil tokens em toda pergunta) gastou demais no primeiro dia de uso.

### Adicionado

- **Escolha automática do modelo, da skill e da leitura** (lote 31). Antes de qualquer chamada paga, um roteador local decide o que a mensagem precisa, por regras e por frases de exemplo comparadas pelo modelo local de busca.
  - **Modelo:** o menor, com pouco raciocínio, para conversa, perguntas sobre o acervo e fatos pontuais; o maior para síntese, figuras, tabelas, método e resultados.
  - **Skill:** a da conversa fica até a mensagem mudar de assunto; conversa solta vai sem skill.
  - A linha sob a resposta mostra a rota, com o motivo ao passar o mouse. Os seletores ganharam "automático", que é o padrão, e continuam servindo para fixar uma escolha.
- **Escada de leitura** (lote 31): sem a biblioteca, só trechos, páginas inteiras (as 10 mais próximas da pergunta, em PDF), o documento citado ou fixado e a leitura ampla.
  - A leitura automática começa pelo degrau mais barato. Se a resposta por trechos não cita nenhum documento, ela sobe para as páginas inteiras, dentro de 30 mil tokens.
  - **Acima de 30 mil tokens estimados,** o servidor não chama o modelo: a tela mostra o custo e os documentos e pergunta antes. Depois de 300 mil tokens no dia, toda leitura acima dos trechos pergunta.
  - **Ler mais fundo**, sob a resposta, refaz a pergunta no degrau seguinte, com o custo estimado no botão.
- **Perguntas já respondidas** (lote 31): cada resposta com citações conferidas guarda as páginas citadas. Uma pergunta com o mesmo assunto e o mesmo pedido recebe aquela troca e as páginas dela, sem nova busca, e o modelo escreve uma resposta nova. As conversas já gravadas ganham as trilhas na primeira abertura.
- **Contagem exata de termos** (lote 31): em perguntas sobre o acervo e nas que citam um documento, o modelo recebe em quais documentos e páginas cada termo aparece, na biblioteca inteira, pelo índice de palavras.
- **Na medição do lote 31,** com as 12 perguntas do piloto pela leitura automática: 144 mil tokens de entrada, contra 3,2 milhões da leitura ampla; documento esperado citado nas 12 e página esperada nas 6 que têm uma; as três respostas que só a leitura ampla completava saíram completas; de 10 a 35 segundos por pergunta. Uma mensagem de conversa custou 459 tokens.
- **Leitura ampla dos documentos** (lote 30), uma das escolhas da leitura. Antes, só cerca de 10 trechos iam ao modelo por pergunta.
  - A busca escolhe os documentos, e o modelo recebe o PDF das páginas inteiras, com figuras, tabelas e fórmulas.
  - Um documento de até 40 páginas vai inteiro. Um livro ou uma norma vai em blocos fixos de 10 páginas: os blocos em que a busca achou algo e os vizinhos.
  - Um **teto** por pergunta, escolhido na tela: 150 mil tokens, 400 mil (padrão) ou o limite do modelo. Uma página de PDF custa 560 tokens. Todo documento que a busca traz recebe um mínimo, e nenhum leva mais de um quarto do teto antes de os outros entrarem.
  - A resposta cita a página, com um identificador por página que não muda de uma pergunta para a outra. A linha "leu 9 documentos (7 inteiros e 2 em parte) · 640 páginas" abre a lista do que foi lido e do que não coube.
  - O modo anterior continua na tela, como **Só trechos**.
- **Documentos fixados na conversa:** o arquivo solto na conversa, ou anexado pelo clipe, fica fixado nela e vai inteiro nas perguntas que consultam os documentos, com a biblioteca ligada ou não. Etiquetas acima da caixa de mensagem mostram os fixados; o painel de documentos e a janela de fontes também fixam.
- **Painel Documentos** no chat, aberto pelo botão ao lado de **Usar biblioteca**: a lista da biblioteca e, por documento, fixar na conversa, abrir o original, a ficha, as figuras e apagar.
- **Envio pelo serviço de arquivos do Google:** os PDFs lidos sobem uma vez e servem às perguntas seguintes por até 48 horas. O painel mostra quantos estão lá, com o botão **Apagar de lá**, e há o comando `biblioteca arquivos` (`--apagar` tira de lá).
- **No piloto do lote 30** com 12 perguntas da lista de referência, por trechos e pela leitura ampla:
  - as duas formas citaram o documento esperado nas 12; a página esperada, 5 de 6 por trechos e 6 de 6 com os documentos inteiros;
  - em três perguntas, o modo de trechos disse que o dado não estava no material ou trouxe só parte dele, e a leitura integral trouxe as escalas, a linha da tabela e a tabela completa;
  - com o teto de 150 mil, o modelo leu de 234 a 242 páginas por pergunta; com o de 400 mil, de 637 a 642.

### Alterado

- **A aba Biblioteca saiu.** O que ela fazia está no painel Documentos. A visualização da extração em Markdown saiu da tela.
- **O que sai do computador mudou:** nas leituras por páginas e por documentos, os PDFs das páginas lidas vão ao Gemini e ficam no serviço de arquivos do Google por até 48 horas. Antes, só trechos de texto iam, e nada ficava guardado.
- **A parte fixa de cada pergunta encolheu** (lote 31):
  - a lista completa dos documentos só segue em perguntas sobre o acervo; nas outras, só os nomes;
  - o material de referência da skill e os **resultados da pesquisa** só seguem em perguntas de método ou de resultados. O botão **Usar resultados** passa a permitir o envio, e não a enviar sempre;
  - uma conversa anterior lembrada, em vez de três, nas perguntas à biblioteca.
- **Usar biblioteca** começa ligado e passa a permitir a consulta: o AL-IAdo só vai aos documentos quando a pergunta pede.
- **O contador "Hoje"** vira à meia-noite deste computador; antes, virava no horário de Greenwich.
- **Custo e tempo da leitura ampla:** de cerca de 11 mil para 150 ou 385 mil tokens de entrada por pergunta, e de 7 a 13 segundos para 31 segundos a 12,5 minutos, sem relação com o tamanho do pedido.
- A descrição automática das figuras (lote 29) não vai ao modelo nas leituras por páginas e por documentos, porque a página vai como ela é. Ela continua servindo à busca e ao modo de trechos.
- O limite de tamanho da resposta é de 32.768 tokens nas leituras por páginas e por documentos: o modelo raciocina mais com as páginas inteiras, e duas respostas do piloto foram cortadas com limites menores.
- Com **Buscar na web** ligada, a leitura segue por trechos, e a resposta avisa.

### Corrigido

- **O documento citado na mensagem fica na busca.** "E o pertile?" virou "percentil" na consulta reescrita, e a busca não trouxe o documento de Pertile. A referência do documento citado pelo autor, pelo título ou pelo DOI volta à consulta quando a reescrita a perde.
- **Aviso de reinício:** a página é lida do disco a cada carga, e o programa em execução só muda quando é reiniciado. Com a página nova e o programa antigo, a tela mostrava escolhas que não tinham efeito. Agora ela avisa e pede para reiniciar.

## [0.4.0] — 2026-10-03

Lotes 27 a 29, a partir do uso real. Detalhes nas specs [0027](docs/specs/0027-tela-envios-e-fontes.md),
[0028](docs/specs/0028-grafo-no-obsidian.md) e [0029](docs/specs/0029-indexacao-figuras-e-frases.md).

### Adicionado

- **Figuras e tabelas na biblioteca.** Antes, de uma página com figura o índice guardava só a legenda.
  - **Texto dentro das figuras:** ao indexar, o Tesseract lê o recorte de cada figura embutida, e o que a página ainda não tem entra como trecho próprio. Sem custo.
  - **Descrição pelo modelo:** na ficha do documento, **Descrever figuras e tabelas** envia cada página com figura, desenho, tabela ou legenda ao modelo, como imagem, numa chamada por página. Só por pedido: o aviso diz o número de chamadas, o modelo e a estimativa de tokens, e dá para parar no meio sem perder o que já foi lido.
  - O modelo propõe e o código confere: o rótulo ("Figure 2") e a legenda só ficam se estiverem no texto da página, e a parcela das palavras e dos números que também aparecem na página fica registrada.
  - Cada figura ou tabela vira um trecho próprio, marcado como descrição automática. A legenda achada na busca traz a descrição junto, e a resposta a usa sem aspas, com o aviso de conferir no original.
  - Comandos `biblioteca figuras` (sem `--executar`, só mostra as páginas e a estimativa) e `biblioteca reindexar`.
- **Trechos por frase:** os trechos da busca passam a ser frases inteiras, com até 110 tokens e sem repetir o fim do anterior. A legenda de figura ou tabela começa sempre um trecho novo. Trechos sem pontuação no fim caíram de 86% para 25%; os que restam são linhas de tabela, fórmulas, legendas e frases que continuam na página seguinte.
- **Reindexar sem ler de novo:** `biblioteca reindexar` refaz os trechos a partir do texto de página já guardado, sem repetir o reconhecimento de texto e aproveitando os vetores que não mudaram. A extração anterior continua guardada.
- **Na biblioteca de hoje,** 1.291 das 1.293 páginas com figura ou tabela foram descritas pelo modelo maior: 1.539 figuras e tabelas, com 2,0 milhões de tokens de entrada e 1,4 milhão de saída.
- **Perguntas de referência sobre figuras e tabelas:** 16 perguntas novas, medidas pela página esperada. Antes, nenhuma trazia o conteúdo da figura; agora 12 trazem com a pergunta direta e 9 com a consulta reescrita do chat.

- **Espelho para o Obsidian** em `data/obsidian/`, para ver no grafo como as conversas, os documentos e as anotações se ligam e crescem.
  - Uma nota por conversa, uma por documento da biblioteca e uma de anotações por fonte (documento ou conversa). Cada documento citado numa resposta vira um link.
  - As notas são refeitas sozinhas depois de cada resposta e quando a biblioteca ou a memória mudam, sem chamadas pagas.
  - O caminho é um só, do AL-IAdo para o Obsidian: edições nas notas geradas são substituídas, e as suas notas não são tocadas.
  - Cada arquivo leva a data do registro, para a animação do grafo mostrar o crescimento real (no Windows). As cores do grafo por pasta são criadas na primeira vez.
  - As notas não levam caminhos de pasta do computador, e o texto das respostas é limpo do que o Obsidian executaria ou buscaria na rede.
  - `aliado web --sem-obsidian` desliga o espelho.

- **Aviso de envios no canto inferior direito**, visível em todas as abas, no lugar dos cartões que ficavam no chat.
  - No chat, fica logo acima da caixa de mensagem. A área da aba termina acima dele, e ele não cobre nenhum botão.
  - Com um documento: o nome, a etapa e a barra. Com vários: quantos estão prontos, a barra geral e o documento atual.
  - As etapas aparecem em palavras: leitura das páginas, reconhecimento de texto, indexação e fichas.
  - Falhas e documentos indexados só em parte ficam até serem fechados. Recarregar a página traz o aviso de volta.
- **Avanço dentro da indexação:** o progresso é informado a cada 32 trechos, com os mesmos vetores de antes.
- **Passagem com os trechos vizinhos:** cada trecho recuperado vai ao modelo com o anterior e o seguinte da mesma página. A definição da NASA para MCC, que chegava cortada, passa a chegar inteira.
- **O que a busca trouxe e a resposta não citou:** a resposta mostra "citou 2 dos 6 documentos que a busca trouxe", e a janela de fontes lista os outros, com a passagem.

### Alterado

- **Índice limpo:** as linhas de cabeçalho e de rodapé que se repetem nas bordas das páginas saem dos trechos (3.292 linhas na biblioteca de hoje). O sumário e a lista de referências ficam marcados e fora da busca comum; voltam quando a pergunta os pede. Um trecho repetido palavra por palavra entra uma vez. O texto guardado de cada página não muda.
- **O que sai do computador:** a descrição das figuras envia páginas dos documentos ao Gemini como imagem. Antes, só trechos de texto iam. Ela nunca roda sozinha.
- **Busca:** as descrições de figuras ficam fora da parte da busca que compara palavras e chegam pelo significado ou junto com a legenda. Com elas, a biblioteca de hoje foi de 13.953 para 20.000 trechos, e cada busca de 2,65 s para 3,9 s.
- **Perguntas de referência do lote 19:** com a consulta reescrita, as 16 continuam acertando; em 3 delas o documento esperado desceu de posição (de 0,94 para 0,84 na média do primeiro acerto). Com a pergunta direta, os acertos foram de 13 para 14.
- **Tela inicial:** abrir ou recarregar a página cai sempre na apresentação. As conversas continuam na lista.
- **Respostas com várias fontes:**
  - a regra passa a pedir o que cada documento recuperado diz, mesmo quando o pedido fala em "uma fonte ao menos";
  - os documentos que não tratam do pedido não são mencionados nem comentados na resposta: a janela de fontes já os mostra;
  - os trechos vão ao modelo agrupados por documento, com a contagem de documentos distintos;
  - citações diretas vêm no idioma original, com a tradução identificada.
- **Fichas depois da indexação:** o documento fica pronto para a busca assim que é indexado. Com vários arquivos, todos são indexados antes de qualquer ficha.
- **Teto de tamanho da resposta:** de 4.096 para 8.192 tokens, porque o raciocínio do modelo conta nele. Uma resposta cortada aparece com aviso e fica fora do histórico.
- **Envios:** a página manda até três arquivos de cada vez, e uma falha reaparece mesmo com o aviso fechado ou recolhido.
- **Medição com 113 respostas pagas**, antes e depois, em 14 pedidos de definição, 2 controles e o caso real:
  - o Flash já citava todos os documentos que tratam do pedido; o Flash-Lite cita cerca de três quartos, antes e depois;
  - no Flash-Lite, as respostas com uma fonte só caíram de 3 em 14 para 1 em 16, e o caso real foi de 1 para 2 fontes;
  - as citações diretas que conferem com a passagem foram de 18 para 83 no Flash e de 0 para 10 no Flash-Lite;
  - no Flash, a primeira versão da regra fazia 13 de 21 respostas comentarem documentos que não tratam do pedido. Com a frase ajustada, nenhuma comenta, e os documentos citados fora do assunto caíram de 1,28 para 0,56 por resposta;
  - no Flash, as respostas ficaram com cerca do dobro do tamanho de antes (de 459 para 879 tokens de saída), pelas citações no original com a tradução.

### Corrigido

- Um erro inesperado na leitura ou nas fichas deixava o envio preso em andamento e bloqueava o apagar de documentos.
- "Completar fichas" podia pagar duas vezes pela ficha de um documento enviado enquanto a tarefa esperava.
- A aba Biblioteca tinha rolagem lateral em telas estreitas quando havia fichas pendentes.
- Referências, itens de norma e traduções das respostas por documento eram contados como números sem marca de resultado.
- A união de trechos vizinhos cortava repetições em texto repetitivo, e uma página com texto repetido mandava o mesmo parágrafo duas vezes ao modelo.
- Um erro de arquivo no envio chegava à tela com código do sistema e caminho de pasta.
- No Windows, ler uma conversa no instante em que ela era regravada podia fazer a gravação falhar. Leitura e gravação do mesmo arquivo de conversa não se cruzam mais.
- O leitor de PDF não aceita chamadas simultâneas, e o processo podia cair com um envio e uma descrição de figuras ao mesmo tempo. Todo uso dele passa por uma trava.
- Com vários pedidos ao Gemini começando juntos, a conexão de um podia ser fechada pela criação da de outro.
- Uma resposta do Gemini cortada no meio de uma saída estruturada não entrava no registro de uso, embora fosse cobrada.

## [0.3.0] — 2026-10-01

Lotes 22 a 26, a partir da avaliação da 0.2.0 pelo pesquisador para o mestrado. Detalhes nas specs
[0022](docs/specs/0022-correcoes-confianca.md), [0023](docs/specs/0023-aba-ciencia-nova.md),
[0024](docs/specs/0024-inicio-das-falhas.md), [0025](docs/specs/0025-confiabilidade-por-componente.md) e
[0026](docs/specs/0026-resultados-no-chat.md).

### Adicionado

- **Resultados da pesquisa no chat.** Na skill do mestrado, o interruptor **Usar resultados** vem ligado e pode ser desligado.
  - O agente recebe 8 blocos com os números da aba Ciência: a avaliação oficial de 27/09 (resumo, alarmes falsos, comparação e cada tipo de falha), a reanálise de 30/09 (sempre marcada como secundária), a FMECA e a confiabilidade por grupo.
  - Os blocos saem das mesmas funções da aba, com a mesma escrita dos números e as notas dos indicadores.
  - Cada número tirado deles leva a marca **[Rn]**, que abre o bloco na janela de fontes, com a tabela, as notas e o botão **Ver na aba Ciência**.
  - O chat não calcula: para um número que não está nos blocos, ele indica a seção da aba.
- **Conferência dos números.** Cada número marcado é comparado ao bloco citado.
  - Só a escrita pode diferir: 2.041 e 2041; 63,7e-6 e 63,7 × 10⁻⁶.
  - Um número arredondado, convertido ou inventado faz a resposta aparecer com um aviso que lista os números, e ela sai do histórico e da memória de conversas.
  - Uma marca [Rn] que não foi enviada troca a resposta por um aviso.
  - No aceite, as 7 respostas com números saíram conferidas, sem nenhum número fora dos blocos.
- **`aliado preparar --resultados`** mostra o pedido com os blocos, sem custo.
- **Tokens do cache** no registro de uso, quando o provedor informa.

- **Início observado das falhas do GPVS.** Os arquivos não marcam o disparo, e a avaliação de 27/09 usou o meio do registro.
  - Um detector de mudança (PELT) sobre as 24 variáveis, sem os autoencoders, acha onde cada falha aparece nos sinais. Nos dois ensaios saudáveis, ele não acha mudança nenhuma.
  - Em 8 ensaios, a mudança é clara: F1, F2, F3 e F5, nos dois modos. Em F1, F2 e F3, ela vem de 1,5 a 3,8 s depois do meio.
  - F6 e F7 mudam pouco, e F4 não muda. Esses ensaios ficam no meio.
- **Reanálise dos mesmos escores com o início observado** (`aliado ciencia reanalisar-gpvs`):
  - sem rodar os modelos de novo e registrada como consulta nº 2 ao teste; a avaliação de 27/09 continua sendo a oficial;
  - com o início nominal, repete o relatório oficial bit a bit;
  - com a mudança, a detecção não muda (Denso 10 de 14 e AE-LSTM 8 de 14), e o atraso mediano cai de 2,04 s e 1,70 s para 60 ms;
  - nos 8 ensaios de mudança clara, a sensibilidade vai de 0,67 para 1,00 nos dois modelos. A demora de 27/09 era a espera até a falha aparecer nas variáveis.
- **Alarmes falsos estimados pelo encadeamento das janelas** (cadeia de Markov, Brook e Evans, 1972): Denso com 19 por hora (0 a 53) e AE-LSTM com 56 por hora (0 a 263), nos 52 s saudáveis. A cadeia previu 3,9 e 5,3 sequências de 2 janelas, e houve 4 e 5.
- **Faixa esperada pelo limiar:** com o limiar no 191º de 192 escores de calibração, a chance de alarme por janela fica entre 0,13% e 2,87% (Vovk, 2012). O observado cabe nela.
- **Confiabilidade por componente:** um painel para cada grupo da FMECA, com R(t) e F(t) nas duas bases de tempo (linha cheia na operação, tracejada no calendário) e um seletor entre elas. Um gráfico reúne os 4 grupos.
- **Disponibilidade de cada grupo** (`docs/pesquisa-inversores/reparos.json`), em dois cenários conferidos nas páginas:
  - o reparo ativo do IEEE 493-2007 (inversores, 26 h, Tab. 10-4, p. 290);
  - a parada de campo de Baschel et al. (2018), com 1 dia para detectar e 5 para reparar (Fig. 7);
  - a disponibilidade vai de 99,09% a 99,99%, e a CCB para até 80 h por ano.
- **Matriz de criticidade S × O** na FMECA, com a detecção no rótulo.
- **Seção "Início das falhas" na aba Ciência**, com o início por ensaio, os indicadores com cada início, a sensibilidade e o atraso por ensaio e a comparação. Os escores ganharam a linha da mudança observada.

- **Aba Ciência nova**, organizada pelas perguntas: Resumo · Escores por ensaio · Métricas por falha · Confiabilidade · FMECA · Explorar · Rodar e arquivos.
  - **Resumo:** a comparação Denso × AE-LSTM por objetivo, os indicadores de cada modelo e as matrizes de confusão, com filtro por falha e por ensaio.
  - **Escores por ensaio:** um contêiner por ensaio, com um carrossel na ordem Denso → AE-LSTM → Ambos, no mesmo tamanho e na mesma escala. "Mostrar em todos" troca o gráfico de todos os ensaios de uma vez. Mostram escore ÷ limiar em escala log, as fases, o início nominal e os alarmes.
  - **Métricas por falha:** barras agrupadas por tipo de falha, mapas de calor por ensaio e as métricas gerais com a faixa dos 5 treinamentos repetidos.
  - **Gráficos em D3 v7**, copiado do projeto antigo, com as cores das figuras da dissertação.
  - **Exportação:** SVG e PNG de 300 dpi em fundo branco, e CSV que o Excel em português abre direto.
  - **Uma nota em cada índice e indicador**, ao passar o mouse, ao focar ou ao tocar.
  - As telas mostram os dados em palavras, sem os códigos internos do protocolo.

- **Consulta da busca reescrita:** com a biblioteca ligada, o modelo mais barato transforma cada mensagem numa consulta completa. O assunto vem da conversa, as siglas vão por extenso, e os termos vão em português e em inglês.
  - Continuações como "Traga a definição… uma citação direta" passam a achar o assunto da pergunta anterior.
  - A busca não se prende a um autor só porque a resposta anterior o citou.
  - Nas 16 perguntas de referência, os acertos foram de 13 para 16 e o MRR, de 0,78 para 0,97.
  - Custa uma chamada barata a mais por mensagem, e se ela falhar, a busca segue pela própria pergunta.
  - A janela de fontes mostra o que foi buscado.
  - `aliado biblioteca avaliar --reescrever --env-file .env` mede a busca do mesmo jeito.
- **Mais referências por resposta:** a busca do chat traz 10 trechos em vez de 6, e, quando documentos diferentes tratam do pedido, a resposta mostra a opção de cada fonte, com a citação, para você escolher.
- **Fonte do texto:** um seletor na barra do topo troca a letra da interface. Há 8 opções: Padrão, Arial, Calibri, Verdana, Georgia, Cambria, Times New Roman e monoespaçada. A escolha fica guardada no navegador.
- **Apagar documento** na aba Biblioteca (`DELETE /api/biblioteca/{doc}`): tira de vez todas as versões, a extração, o índice e a ficha. O original só sai se nenhum outro documento o usa. As anotações que o agente deduziu do documento são revogadas, e as suas ficam. Enquanto um envio ou as fichas estão em andamento, a biblioteca pede para esperar.

### Alterado

- **Resumo da aba Ciência:** os alarmes falsos por hora passam a usar os 52 s saudáveis (o teste saudável e o trecho antes da falha), e não só os 5 s do teste. O limite superior do Denso cai de 2.050 para 207 por hora. Entram também a estimativa pela cadeia e as janelas saudáveis acima do limiar, com a faixa esperada.
- **Skill do mestrado 0.2.2:** a disponibilidade usa os dois cenários de reparo, e os números dos resultados vêm só dos blocos, com a marca, ou a resposta indica a aba Ciência.
- **Aba Ciência:** os cartões do Resumo e as Métricas por falha mostram 3 casas e o mesmo formato de segundos dos blocos do chat.
- **Custo:** com os resultados ligados, cada pergunta leva cerca de 5,5 mil tokens de entrada a mais.
- **Cenários e FMECA na tela:** "Horizonte de 20 anos (M12)" virou "o das diretrizes da pesquisa", e uma ressalva da FMECA deixou de citar commit e caminho do projeto anterior.
- **Skill do mestrado** (versão 0.2.0):
  - descreve a situação atual: há memória, o acervo tem os PDFs e a aba Ciência executa o experimento;
  - registra a tabela e a página de cada taxa e das notas da FMECA;
  - pede ao modelo que explique em palavras, sem citar os códigos das diretrizes.
  - Nas diretrizes, só a seção "Aplicação e limites atuais" mudou; o texto de M09 a M14 ficou idêntico.
- **Taxas e notas da FMECA conferidas nos PDFs:**
  - Sarquis Filho et al. (2020), Tab. III, p. 3;
  - Baschel et al. (2018), Tab. 1, p. 5 e 6;
  - Cristaldi et al. (2017), Tab. 6, p. 6.
  - Os valores não mudaram. Os 8 cenários e a FMECA citam agora tabela e página.
  - O IGBT de Baschel (8,9e-6/h) é o valor extrapolado dos relatórios de O&M da juwi. O valor que o próprio estudo usa é 11,4e-6/h.

### Removido

- Da biblioteca do pesquisador, os dois recortes do manual de Lafraia (o capítulo 7 e uma digitalização). O manual completo cobre os dois. As 16 anotações deduzidas deles foram revogadas.

## [0.2.0] — 2026-09-28

Lotes 18 a 21, a partir dos apontamentos do pesquisador no uso real da v0.1.0. Detalhes nas
specs [0018](docs/specs/0018-biblioteca-memoria-anexos.md), [0019](docs/specs/0019-qualidade-da-busca.md),
[0020](docs/specs/0020-aba-ciencia.md) e [0021](docs/specs/0021-gpvs-interface.md).

### Adicionado

- **GPVS pela interface** (seção Rodar GPVS da aba Ciência):
  - preparar, treinar e avaliar com progresso e botão de cancelar, pelos próprios comandos do terminal;
  - o treino aceita separação, sementes e teto de épocas, e uma rodada fora da configuração canônica fica marcada como exploratória;
  - uma nova avaliação exige digitar "consultar o teste", entra no registro de consultas ao teste (M14) e é não canônica;
  - no aceite, treino e avaliação pela interface reproduziram bit a bit a rodada de 27/09.

- **Aba Ciência:**
  - resultados com gráficos e tabelas;
  - explorador do limiar (k de 1 a 24 e percentil, só na calibração);
  - explorador de alarme e detecção (k, percentil e m, marcado como exploração pós-teste pelo M14). Com os parâmetros canônicos, ele repete a avaliação de 27/09;
  - confiabilidade que recalcula sem gravar e salva o cenário só com fonte e hipóteses;
  - FMECA com as duas ordens.
  - Os gráficos são em SVG próprio, sem dependência nova.
- **`aliado web --resultados --gpvs`** para escolher as pastas da aba Ciência.

- **Ficha do documento:** título, autores, ano e DOI, lidos do começo do texto pelo modelo mais barato e conferidos no próprio texto. A ficha fica marcada "inferida" até você editá-la. O botão **Completar fichas** cria as que faltam. As fontes e o catálogo mostram "Baschel et al., 2018", e "segundo Baschel" acha o artigo.
- **Medição da busca:** `aliado biblioteca avaliar` mede, com perguntas de referência, os acertos, a posição e a diversidade dos resultados.

- **Perfil na memória:** o que você conta sobre si (nome, instituição, pesquisa) vale em todas as conversas. O revisor guarda até 8 anotações por troca.
- **Memória de conversas:** cada troca fica guardada no computador, e até 3 trocas de outras conversas, parecidas com o assunto, entram como contexto. As conversas que já existiam são indexadas na primeira abertura.
- **Catálogo no modo biblioteca:** o agente recebe a lista dos documentos e responde sobre o acervo.
- **Busca com contexto:** mensagens curtas, como "tente novamente", buscam junto com a pergunta anterior.

### Alterado

- **Busca da biblioteca:**
  - a parte por palavras ignora palavras vazias em português e em inglês e pesa metade da parte por significado;
  - cada documento ocupa no máximo 2 dos 6 resultados (4 se for citado na pergunta).
  - Nas 16 perguntas de referência, os acertos passaram de 12 para 13 e o MRR, de 0,66 para 0,78.
- **Resposta sem citação** no modo biblioteca: aparece com o aviso "Esta resposta não cita trechos dos seus documentos" e entra no histórico. Citação inventada continua bloqueada.
- **Fontes e memória** abrem numa janela sobre a resposta, que fecha com Esc ou com um clique fora. O painel lateral saiu.
- **Anexos:** fila de até 3 cartões com contador; os que dão certo somem em 6 s.
- **Conversa apagada** deixa de ser lembrada. As anotações que saíram dela continuam.
- Sem anotação sobre algo, o agente diz que não tem isso anotado, e não que não tem memória.

### Corrigido

- Anotações e trocas com mais de 128 tokens ficavam sem vetor e nunca eram achadas por semelhança. As que faltam são preenchidas na abertura.
- O navegador guardava versões antigas da interface depois de uma atualização.

## [0.1.0] — 2026-09-27

Primeira versão do AL-IAdo retrabalhado a partir do repositório `mestrado-utfpr`: um agente
local, de uso individual, com a pesquisa em inversores fotovoltaicos como primeira
especialização. O detalhe de cada lote está nas [specs](docs/specs/) e no
[mapa de migração](docs/migracao/README.md).

### Núcleo e provedores

- **Contratos e gateway** para OpenAI e Gemini, com aliases configurados no `.env`, sem modelo presumido.
- **Registro local de uso:** data, modelo, tokens (inclusive de raciocínio) e número de buscas, nunca o texto.
- **Skills do AL-IAdo:** `pesquisa-inversores` 0.1.5, `confiabilidade` e `engenharia`, com as decisões M01–M16.

### Interface local

- **Navegador em `127.0.0.1`**, sem login: conversas com histórico e lixeira, respostas em fluxo com botão de parar, escolha de skill e modelo, e tokens por resposta.
- **Envio de PDF, Markdown e JSON pelo chat**, com progresso por página, ficha de leitura e citações com trecho e página.
- **Fórmulas** com KaTeX incluído no pacote, sem CDN.

### Biblioteca, memória e web

- **Biblioteca:** OCR em português e inglês, versão Markdown de cada documento e busca híbrida com encoder local de revisão fixa.
- **Memória persistente por origem:**
  - o feedback do pesquisador vale na hora, e as inferências ficam marcadas;
  - conflitos ficam para decisão do pesquisador, e correções nunca apagam o histórico;
  - apagar uma conversa não apaga a memória.
- **Busca na web** pelo Gemini, com fontes numeradas e separadas dos documentos, e "Conferir na web" para as anotações.

### Ciência

- **Cálculos RAM** por cenário explícito: confiabilidade exponencial e Weibull, sistemas em série e em paralelo, mantenabilidade e disponibilidade inerente. Taxas horárias são convertidas pelo serviço (`time_base`).
- **8 cenários dos quatro grupos** da FMECA, em duas bases temporais.
- **FMECA:** NPR calculado das notas da fonte e, separada, a leitura pelas taxas (MTBF, chance de falhar e falhas esperadas).

### Experimento de detecção (GPVS)

- **Protocolo M14 executável:** divisão 50/15/15/20 com 11 janelas de separação, normalização só no treino e verificação de autocorrelação.
- **Autoencoders Denso e AE-LSTM** (PyTorch 2.12.0, CPU):
  - parada pela validação e limiar p99 na calibração;
  - 5 sementes e configuração congelada com hashes;
  - com a configuração da origem, reproduzem os modelos antigos bit a bit.
- **Avaliação M13:**
  - alarme com 3 janelas seguidas;
  - falsos alarmes por hora com limite superior, detecção e atraso por ensaio;
  - bootstrap em blocos e comparação pareada por objetivo, sem vencedor geral.

### Não incluído

- Site com domínio e vários usuários, MCP, roteador de modelos e importação das memórias antigas, previstos para a v1.
- Disponibilidade dos inversores, por falta de fonte de tempo de reparo.
