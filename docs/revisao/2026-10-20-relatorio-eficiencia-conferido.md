# AL-IAdo — relatório de eficiência do modelo local, conferido

Data: 20/10/2026. Confere, afirmação por afirmação, o "Relatório de Melhoria e Eficiência do Modelo Local" (PDF de
7 páginas, 20/10/2026) com as medições do próprio projeto. Diz o que confere, o que não confere e o que o lote 46
fez com cada proposta, na [spec 0046](../specs/0046-correcoes-do-relatorio.md).

Fontes:
- os registros do lote 45 (`tmp/lote-45/calls.json` e os 16 casos, fora do Git; resumo na
  [validação 45](../migracao/validacao-lote-45.md));
- `ollama show --verbose aliado-local`, as variáveis do servidor do Ollama e o log dele de 18/10;
- as medições do lote 42 e o código.

Não foi lido o `.env`. As contas usam GiB = 1.024³ bytes e MiB = 1.024² bytes.

## 1. Conclusão

- **O objetivo do relatório vale:** o local mais rápido, menos respostas descartadas e nenhuma falha de memória.
- **O diagnóstico não confere:**
  - o cache K/V já é q8_0, com flash attention;
  - o modelo é híbrido, e a 32 mil tokens o cache ocupa 544 MiB, não de 2,25 a 4,5 GiB;
  - com as 32 camadas na placa, o pico medido é de 5.641 MiB, dentro dos 6.143 MiB dela;
  - a geração já anda perto do limite de banda da placa.
- **Onde o tempo vai:** para a **saída**, e quase toda ela é raciocínio oculto, que não aparece na tela. Nas 14
  respostas locais do lote 45, o tempo acompanha os tokens de saída com correlação de 0,99; com o tamanho do pedido,
  0,59.
- **As 4 respostas descartadas:** não foram falha de formato. O modelo alterou os identificadores de citação e copiou
  os exemplos das instruções. O lote 46 corrigiu essa causa.
- **Propostas que não se aplicam:** contexto de 8 mil, orçamento de 3 mil tokens, PLD, gramática, modelo de 3B,
  torch.compile e HDF5. Os motivos estão abaixo.

Nota: a correlação vai de −1 a 1 e mede o quanto duas grandezas sobem juntas; 0,99 quer dizer que o tempo
praticamente segue a quantidade de tokens de saída.

## 2. Memória da placa (seção 2 do relatório)

| Item | O relatório | O que vale | Fonte |
|---|---|---|---|
| Memória da placa | 6,00 GB = 5,588 GiB | **6.143 MiB (6 GiB)**; 6.002 MiB livres sem nada aberto | log do CUDA; `nvidia-smi` |
| Camadas | 36 com atenção | **32 blocos; só 8 com atenção completa** (1 a cada 4); os outros 24 são recorrentes, com estado fixo de 50 MiB | `qwen35.block_count`, `full_attention_interval`; log |
| Cabeças K/V × dimensão | 8 × 128 (ou 4 × 128) | **4 × 256** | `head_count_kv`, `key_length`, `value_length` |
| Cache K/V a 32.768 tokens | 4,5 GiB (FP16) ou 2,25 GiB | **1,0 GiB em FP16; 544 MiB em q8_0**, que é o que está em uso | 2 × 8 × 4 × 256 × 32.768 × 2 bytes; log com 272 MiB a 16.384 |
| Tipo do cache | FP16 | **q8_0, com flash attention** | `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_FLASH_ATTENTION=1`; log "K (q8_0), V (q8_0)" |
| Total | 7,515 GiB, déficit de 1,9 GiB | **pico de 5.641 MiB** com 32 camadas e 32 mil de contexto | lote 42 |

- **Os pesos:** os 9 bilhões de parâmetros incluem cerca de 2 bilhões da tabela de vocabulário, que tem 248.320
  tokens: a de entrada fica fora da placa, e a de saída (Q6_K, cerca de 0,8 GB) fica dentro. O arquivo de 6,6 GB
  traz também o projetor de imagens, de 0,9 GB, que fica fora da placa. Com 33 camadas, ele iria junto e não
  caberia (lote 42).
- **As falhas da P2:** foram duas, uma de alocação no CUDA e outra de reserva interna de memória. Elas aconteceram
  com o Firefox e o VS Code abertos e sumiram depois de fechá-los, sem mudar o modelo (validação 45). No pico,
  sobram cerca de 500 MiB para os outros programas.
  - **Decisão do pesquisador (20/10):** manter as 32 camadas, o contexto de 32 mil e o cache q8_0. O cuidado é
    fechar programas pesados antes de perguntas longas.
  - Outras opções de folga, como o cache q4_0 (cerca de 255 MiB a mais) ou 31 camadas (cerca de 130 MB a mais,
    uns 4% mais lento), ficam para quando ele quiser medir.
- **A banda (equações 8 e 9):** a fórmula serve como modelo, mas não descreve a situação de hoje. Só 1 dos 32 blocos
  fica na CPU. A placa lê cerca de 5 GB de pesos por token: os 31 blocos e a camada de saída. Isso dá um teto
  teórico de cerca de 32 tokens/s a 168 GB/s. O medido, de 23 a 25 tokens/s (cerca de 78% do teto), é o esperado
  na prática. Não há perda de 46% a recuperar.

## 3. Tempo de resposta (seção 3 do relatório)

**Ajuste das 14 respostas locais completas do lote 45**, por mínimos quadrados:

`segundos ≈ −2,6 + 0,0399 × tokens de saída + 0,0016 × tokens de entrada`

Isso dá cerca de **25 tokens/s na saída** e o equivalente a **620 tokens/s na leitura do pedido**, já com o custo da
atenção em contextos longos.
- Num pedido de 20 mil tokens, ler leva cerca de 32 s.
- Escrever 4 mil tokens leva cerca de 160 s.

| Pergunta | Leitura | Entrada | Saída | Segundos | Texto visível |
|---|---|---:|---:|---:|---:|
| E5 | páginas inteiras | 21.599 | 4.510 | 213,8 | 1.388 caracteres |
| E6 | páginas inteiras | 10.696 | 4.845 | 209,5 | 2.448 caracteres |
| P3 | páginas inteiras | 17.375 | 3.905 | 182,5 | 3.090 caracteres |
| P7 | sem a biblioteca | 11.142 | 4.110 | 181,1 | 2.664 caracteres |
| P2 | documento inteiro | 20.508 | 1.191 | 81,6 | 2.185 caracteres |
| P4 | trechos | 7.179 | 442 | 36,6 | — |

Notas:
- "Entrada" e "Saída" são os tokens informados pelo Ollama.
- A saída inclui o raciocínio que não aparece na tela. Na E5, foram 4.510 tokens para 1.388 caracteres visíveis
  (cerca de 400 tokens).
- **O primeiro texto em 83,7 s:** não vem do prefill. É a leitura do pedido, de 10 a 35 s, mais o raciocínio
  oculto, que vem antes do texto.
  - Medido no fluxo do Ollama, nas 11 respostas locais com raciocínio do lote 46: a leitura do pedido levou em média
    14,1 s (14% do tempo), o raciocínio oculto 56,3 s (54%) e o texto visível 33,2 s (32%).
  - O raciocínio teve 5.687 caracteres em média, contra 2.860 do texto.
- **"Páginas 5,4× mais lentas":** o fator mistura a saída com a entrada. A E6 leva 209 s com um pedido menor que o
  da P2 (81,6 s), porque escreveu 4 vezes mais. A P7, sem biblioteca nenhuma, levou 181 s.
- **Equações 16 e 17:** conferem. Foram 4 descartes em 14 tentativas locais. Na E8, 148,2 s do local foram jogados
  fora, e o Gemini levou mais 42,7 s.

## 4. As 4 respostas locais descartadas

A conferência das citações reprovou as respostas porque havia marcas fora do que foi enviado:

| Pergunta | Marca escrita pelo local | O que era |
|---|---|---|
| P5 | `[Ke3935f2b1256498p5]` | o identificador do trecho `Ke3935f2b12564980`, truncado, mais o "p5" do exemplo `[K12ab34p5]` |
| P8 | `[K2fef6efcbcb34f98p11]` | o trecho certo, da página 11, com a página colada |
| E7 | `[K12ab97c6d0504cd8]` | o começo do exemplo `[K12ab34p5]`, misturado com um identificador real |
| E8 | `[K...]` e `[K2d575284p64]` | o formato das regras copiado e, no formato das páginas, um trecho da página 64 que foi enviado |

**O que o lote 46 fez:**
- **Instruções:** tirou os exemplos das instruções do local e pediu o identificador copiado letra por letra (PRV-06).
- **Marcas inequívocas:** aceita só as duas formas que apontam um único trecho enviado, as da P8 e da E8, e tira o
  `[K...]` literal do texto (BIB-05). As da P5 e da E7 continuam reprovando.
- **Parada cedo:** na primeira marca que não confere, o local para de escrever e o Gemini Flash refaz na hora
  (PRV-02).

A proposta de gramática restrita (seção 4.4) não resolveria isso. O erro era de conteúdo, um identificador errado,
e não de formato. No Ollama, a restrição só existe por esquema JSON, que obrigaria a resposta a vir em JSON e
quebraria o texto em fluxo.

## 5. As propostas da seção 4

| Proposta | Situação | Decisão |
|---|---|---|
| 4.1 Cache K/V em q4_0 e contexto de 8 mil | Já é q8_0. Com 8 mil, as leituras de páginas e de documento (15 a 22 mil tokens no lote 45) iriam ao Gemini: no lote 39, com 16 mil, 7 das 16 perguntas foram | Fica como está (decisão de 20/10) |
| 4.2 Fusão RRF e orçamento de 3 mil tokens | A RRF já existe em `library.py`: k = 60, peso 1,0 no significado, 0,5 nas palavras (BM25 do FTS5) e 1,0 no documento citado, com reordenação das páginas por um cross-encoder local. O orçamento tiraria as páginas inteiras que o roteador escolhe para figuras e tabelas e pouparia, no máximo, cerca de 30 s de leitura | Não adotado |
| 4.3 PLD (decodificação por busca no pedido) | O Ollama 0.40.6 não tem essa opção nem a especulativa (variáveis de `ollama serve --help`) | Fora do alcance sem trocar o servidor |
| 4.4 Gramática restrita | Ver seção 4 | Substituída pelas correções do lote 46 |
| 4.5 Modelo de 3B para a reescrita e os números | A conferência dos números é código, sem modelo (`numbers.py`). A reescrita já vai sem raciocínio (7,7 a 11 s no lote 45). O 3B pediria download e troca de modelo na placa, que comporta um modelo por vez (`OLLAMA_MAX_LOADED_MODELS=1`) | Não adotado |

**Defeito achado na revisão, fora do relatório:** desde a 0.6.0, o plano das perguntas com partes nunca chamava o
modelo. A função recebia o pedido do plano duas vezes, o erro era calado, e a busca seguia sem a reescrita. O lote
46 corrigiu (PRV-07).

## 6. O pipeline científico (seção 5 do relatório)

**As fórmulas 32 a 38 conferem com o código:**
- **Janelas e atributos:** 24 atributos por janela de 200 amostras (20 ms a 10 kHz).
- **Os dois modelos:** o MLP por janela; o LSTM com 8 janelas, pontuado só pelo último passo (`models.py:164-165`).
- **Erro e escore:** o erro é o quadrado da diferença por atributo; o escore é a média dos 5 maiores.
- **Limiar:** o percentil 99 da calibração, pela posição `ceil((n−1)·p/100)` dos escores ordenados, sem
  interpolação. Com n = 192, é o 2º maior escore.
- **Alarme:** comparação estrita (escore > limiar) em 3 janelas seguidas (`metrics.py`).

Nota: o limiar é o valor do escore acima do qual a janela conta como anômala. O alarme só soa depois de 3 janelas
seguidas acima dele.

- **torch.compile (5.2, item 1):** não adotado.
  - No Windows, ele depende do Triton, que não tem suporte oficial.
  - O treino roda com algoritmos determinísticos, e um teste exige reprodução bit a bit.
  - A inferência não é o gargalo de nada que o pesquisador usa.
- **Matriz de erros (5.2, item 2):** o cache NPZ do explorador era identificado só pela configuração e pelos dados.
  - **O que o lote 46 fez:** a chave passou a incluir os hashes dos pesos e a ordem das 24 variáveis, sem
    dependência nova. Nenhum número muda.
  - **Arquivo oficial da rodada, em HDF5 ou outro formato:** fica para um lote com as decisões do pesquisador.
    Falta definir o formato e se o tempo de uma janela é o começo, o centro ou o fim dela. O diagnóstico de 20/10
    pede que isso não seja preenchido por suposição.

## 7. Projeção e próximos passos (seções 6 e 7 do relatório)

As projeções do relatório (18 a 24 s por resposta, primeiro texto abaixo de 6 s, autonomia total) partem do
diagnóstico de memória e de prefill, que não confere. Elas não se sustentam com os números acima.

O que as medições apontam, em ordem de efeito:
1. **O raciocínio oculto:** é a maior parte do tempo. Desligá-lo nas páginas e no documento ou limitá-lo precisa de
   uma medição autorizada. No lote 41, desligá-lo nos trechos fez o local deixar de citar, mas na época as
   instruções ainda tinham os exemplos copiáveis.
2. **Os descartes:** corrigidos no lote 46. Nas 16 perguntas, o local passou a responder 12 (eram 10).
   - As marcas descartadas caíram de 4 para 2, as duas paradas cedo.
   - Apareceram duas alterações novas: um identificador sem o primeiro caractere e um intervalo de páginas.
   - Detalhes na [validação do lote 46](../migracao/validacao-lote-46.md).
3. **O roteador:** a E3 (o TCC) e a P7 (série e paralelo) foram para os resultados da pesquisa sem a biblioteca, e
   a P7 levou 181 s sem citar o manual esperado.

A mesma validação traz o resultado das 16 perguntas com o modelo local real depois das correções.
