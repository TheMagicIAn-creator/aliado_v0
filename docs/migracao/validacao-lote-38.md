# Validação do lote 38 — o modelo local como principal

Data: 18/10/2026. Escopo na [spec 0038](../specs/0038-modelo-local.md); requisitos vivos em
[capacidades/provedores.md](../specs/capacidades/provedores.md). Nenhuma chamada paga nas duas etapas.

- **Etapa 2:** o código, conferido com um cliente falso, antes de o Ollama existir na máquina.
- **Etapa 3:** autorizada pelo pesquisador. Foram feitos a instalação do Ollama, o download do `qwen3.5:9b`
  quantizado, a criação do `aliado-local` e a medição da memória, da velocidade e da escalada. A escalada foi medida
  com um Gemini falso.

## Etapa 2

### Bateria

| Conferência | Resultado |
|---|---|
| `pytest`, arquivo por arquivo | 802 testes passaram nos 45 arquivos, nenhum falhou, em 253 s |
| `ruff check .` | sem apontamentos |
| `git diff --check` | sem apontamentos |
| Testes novos | `test_local_provider.py` (12) e, em `test_web.py`, a escalada da conversa e o Ollama fechado (2) |
| Teste revisto | `test_results_chat.py`: o gateway falso aceita a opção `local` |
| Requisitos vivos citados por testes | PRV-01 a PRV-05: todos |

**Por que arquivo por arquivo:** a bateria inteira num processo só parou duas vezes por falta de memória.
- Primeiro, o codificador da busca não carregou ("bad allocation").
- Depois, o Windows encerrou o processo durante a renderização de páginas de `test_figures.py` (código 0xe0000008).
- Os dois testes passam sozinhos.

A máquina tinha 1,3 a 1,7 GB de RAM livres e 33,3 de 35,2 GB de memória comprometida. A memória estava com os
programas abertos: a máquina virtual do WSL (4,1 GB), o Claude (3,9 GB), o Firefox (3,2 GB), o VS Code (1,4 GB), o
Obsidian (1,2 GB) e o servidor do AL-IAdo (1,1 GB).

### Prova sem o Ollama (PRV-04)

```text
AL_IADO_LOCAL_MODEL=aliado-local .venv/Scripts/python.exe -m aliado perguntar --provider google --model-alias flash \
  --skill nenhuma --registro-uso <rascunho>/uso-smoke.jsonl "oi"
```

- **Saída:** "O modelo local não respondeu em http://localhost:11434/v1: abra o Ollama e confira o endereço do .env
  (AL_IADO_LOCAL_BASE_URL).", com código 2, em 6,8 s.
- **Registro de uso:** o arquivo não foi criado.
- **Gemini:** o `.env` não foi carregado, e por isso a chave do Gemini não estava disponível. Que o Gemini não é
  chamado com o Ollama fechado é conferido no gateway, com o Gemini falso
  (`test_ollama_down_raises_without_calling_gemini`).

### Pela tela (servidor de teste `aliado-web-lote-38`, porta 8784, sem `.env`)

- **Como:** sem chave nenhuma, logo sem custo possível, com dados de teste em `tmp/lote-38`. Uma conversa tinha uma
  resposta do local (1.234 tokens) e uma do Gemini (320 tokens), e o registro de uso tinha as duas.
- **Uso do dia:** "Hoje 320 tokens · total 320", com a dica "Tokens pagos usados hoje e no total; o modelo local não
  conta".
- **Resposta do local:** a linha da rota com "aliado-local", e "1.234 tokens locais" com a nota "Tokens do modelo
  local, neste computador: sem custo e fora do uso do dia".
- **Resposta do Gemini:** "320 tokens", e na dica da rota o motivo "o modelo local não deu conta (pediu ajuda): o
  Gemini Flash respondeu".
- **Console:** sem erros.

### Correções durante a Etapa 2

- **Provedor `ollama`, e não `local`:** o app já usava `provider == "local"` para os avisos respondidos sem modelo.
  Com o mesmo nome, as respostas do modelo local ficariam fora do histórico e sem rota.
- **A web como "fora do alcance":** a busca na web deixou de ser um erro do adapter. Agora vai direto ao Gemini, com
  o motivo na rota.
- **Falhas técnicas:** toda falha técnica do local (conexão, modelo não baixado, recusa do Ollama, SDK ausente) vira
  a mesma mensagem clara, sem chamar o Gemini. O cliente não repete a chamada sozinho.
- **Registro de uso duplicado:** se a escalada falhasse e a conversa subisse um degrau, a resposta do local seria
  gravada duas vezes no registro de uso.

## Etapa 3 — o modelo de verdade

### Instalação

| Item | Resultado |
|---|---|
| Ollama | 0.40.6, instalador oficial do GitHub (`OllamaSetup.exe`, 1,58 GB). O SHA-256 `933794ee…0828` confere com o `sha256sum.txt` da versão |
| Variáveis do serviço, no usuário | `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1` e `OLLAMA_KEEP_ALIVE=10m`. O servidor subiu com elas (linha "server config" do registro) |
| Placa | RTX 3050 de 6 GB, com CUDA 13. A placa integrada da Intel ficou de fora |
| Modelo | `qwen3.5:9b` em Q4_K_M, com 9,0 bilhões de parâmetros: 5,63 GB do modelo e 0,92 GB do leitor de imagens. São 32 camadas, uma em cada quatro com atenção completa, o que deixa o contexto leve |
| `aliado-local` | `tmp/lote-38/Modelfile`: `num_ctx 16384`, `num_gpu 22` e `use_mmap true`. Usa os mesmos arquivos do `qwen3.5:9b` |

A linha oscilou entre cerca de 170 KB/s e 45 MB/s. O instalador e o modelo vieram em minutos, conferidos.

### Memória

| Configuração | Placa | Reserva do processo | Observação |
|---|---|---|---|
| 20 camadas, sem `use_mmap` | 3.653 MiB | 8,6 GB | no Windows com CUDA, o Ollama copia os pesos para a memória (`--load-mode none`) |
| 20 camadas, com `use_mmap` | 3.655 MiB | 6,4 GB | os pesos fora da placa vêm do arquivo no SSD; mesma velocidade |
| 22 camadas, com `use_mmap` | 3.941 a 3.959 MiB | 6,6 GB | a escolhida: abaixo dos 4 GB na placa |

- **Com os programas abertos, não carregou:** havia 1,1 GB livres e 33,9 de 35,2 GB reservados, e o registro deu
  "failed to allocate CPU buffer of size 921684928". Esse é o leitor de imagens, que fica na RAM quando o modelo se
  divide entre a placa e o processador.
- **Depois de o pesquisador fechar programas, carregou:** havia 5 GB livres e 24 GB reservados.
- **Carregado:** a reserva do sistema subiu cerca de 6 GB, e a RAM livre caiu para 0,4 a 0,5 GB.

### Velocidade (22 camadas)

| Medida | Resultado |
|---|---|
| Carga | 41 s na primeira, lendo o SSD; de 9 a 11 s com o arquivo em cache |
| Entrada longa | 4.684 tokens a 714 tokens/s (6,6 s). As 18 mil letras deram 3,8 letras por token; o AL-IAdo conta 3, com folga |
| Saída | de 15 a 16 tokens/s |
| Conta de série com raciocínio | 964 tokens, com 2.353 letras de raciocínio, em 64 s; resposta certa |

### O que a Etapa 2 deixou para o modelo

| Conferência | Resultado |
|---|---|
| `reasoning_effort="none"`, pela API compatível | Desliga o raciocínio: 4 tokens em 0,5 s, contra 372 tokens em 27 s, com 953 letras de raciocínio no campo `reasoning`, que o adapter não mostra. Resposta certa (391) nos dois |
| `json_schema`, pelo adapter | JSON válido no formato pedido, em 5 s. Mas, sem raciocínio, leu "8,9e-6 por hora" como 8.9 |
| Imagem, pelo adapter (uma figura feita aqui) | Lida certa: título, anos e valores. Com letra minúscula, pediu ajuda 3 vezes em cerca de 11 tentativas; é sorteio, porque o modelo usa temperatura 1. Com letra normal, sempre leu |
| "[ESCALAR]" diante do impossível (prova da conjectura de Collatz) | Não pediu ajuda: respondeu que a conjectura não está provada, em 32 s |

### Escalada nas perguntas reais, sem custo

Foram as 16 perguntas da avaliação da busca (`data/avaliacao-busca/perguntas.json`), feitas pela conversa do AL-IAdo:
- com uma cópia da biblioteca, em `tmp/lote-38/medicao`;
- com uma pasta de dados nova;
- com um Gemini falso, que só conta as chamadas.

| Primeiro desfecho | Perguntas |
|---|---|
| Respondidas pelo local | 3: P6 (citou o documento esperado), P8 (citou outro documento, com as citações conferidas) e P7 (sem a biblioteca) |
| Direto ao Gemini: o documento ou as páginas inteiras passam de 4 páginas de PDF | 8: P1, P2, P3, E1, E2, E5, E6 e E8 |
| Refeitas pelo Gemini: o local citou os documentos por extenso, sem as marcas `[K…]` | 3: P4, P5 e E4. A P4 e a E4 depois subiram às páginas inteiras, também no Gemini |
| Pedido de ajuda no meio do texto, que apareceu na tela | 1: E3, corrigido abaixo |
| Sem resposta: o app do Ollama foi fechado às 13:58 ("shutting down ollama server") | 1: E7 |

- **Chamadas que iriam ao Gemini:** 13. Sem o modelo local, iriam todas as 16, mais as subidas de degrau.
- **Tempo:** 105 s por pergunta, em média. As respostas do local levaram de 30 s a 4 min, com raciocínio.
- **O aviso de troca:** nas três refeitas, a conversa mandou o evento `recomeco` ("O modelo local não chegou lá: o
  Gemini Flash vai responder…"), o mesmo que a tela usa para apagar o texto parcial.

### Correção feita depois da medição

- **O defeito:** na E3, o local escreveu "**Resposta ao usuário:** [ESCALAR] Não tenho acesso…". Como o pedido de
  ajuda não veio no começo, ele apareceu na tela.
- **A correção:** o adapter guarda os primeiros 160 caracteres antes de mostrar e reconhece o "[ESCALAR]" em
  qualquer ponto deles. Na resposta inteira, ele o reconhece em qualquer ponto. O que vier depois do começo, a
  conversa refaz pelo Gemini.
- **Testes:** `test_help_request_after_a_label_still_hands_over` e
  `test_local_answer_that_asks_for_help_midway_is_redone_by_gemini_flash`.

### Bateria depois da correção

| Conferência | Resultado |
|---|---|
| `pytest`, arquivo por arquivo | 804 testes passaram nos 45 arquivos, nenhum falhou, em 232 s (os 802 da Etapa 2 e os 2 da correção) |
| `ruff check .` | sem apontamentos |
| `git diff --check` | sem apontamentos |
| Os testes novos sem a correção | falhariam: na resposta inteira e no fluxo, o rótulo antes do "[ESCALAR]" deixava passar o texto |

## O que não foi conferido

- **O `qwen3.5:4b`:** a autorização foi para o 9B.
- **A qualidade das respostas em si:** foi conferida só a citação do documento esperado.
- **O aviso de troca no navegador:** foi conferido pelo fluxo da conversa, na medição e em `test_web.py`.
- **O modelo local no `.env` do pesquisador:** não foi ligado. O AL-IAdo dele segue pelo Gemini até ele decidir.
