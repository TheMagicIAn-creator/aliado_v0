# Spec 0038 — o modelo local como principal, com o Gemini Flash na escalada

Estado: Etapas 2 e 3 feitas e validadas localmente em 18/10/2026. Na Etapa 2, o código foi conferido com testes
simulados. Na Etapa 3, o Ollama foi instalado, o modelo baixado e medido, e o defeito do "[ESCALAR]" foi corrigido.
Aguarda a revisão e o commit do pesquisador. O modelo local não foi ligado no `.env` dele. Spec de mudança: os
requisitos vivos estão na spec nova [capacidades/provedores.md](capacidades/provedores.md) (PRV-01 a PRV-05, novos).

## Propósito

O pesquisador quer o AL-IAdo rodando com um modelo aberto, quantizado e local como principal, sem custo por uso:
"estou com limite de grana". O Gemini Flash só entra quando o modelo local esbarra no limite do raciocínio, e não
no de tokens. Nada científico muda, nada da v1.

## Decisões do pesquisador (18/10/2026)

- Etapa 1, só diagnóstico; Etapa 2, o provedor local com testes simulados, sem baixar nada, parando para a revisão
  dele antes da Etapa 3.
- Os modelos locais são os principais. Atingidos os limites do pensamento e do raciocínio deles ("não de
  tokenização, mas por não irem além"), entra o Gemini Flash, sem um caminho de troca entre provedores.
- Com o Ollama fora do ar: erro claro, sem gastar. O Gemini não entra sozinho por falha técnica.
- Mecanismos de quantização para aproveitar melhor os parâmetros dos modelos.
- Memória: placa de vídeo até 4 GB; o SSD como complemento, até 6 GB no uso normal e 20 GB no pico; a RAM com o que
  estiver livre. A conferência está no README (seção "Modelo local"): a ordem que funciona é placa > RAM > SSD; o
  arquivo de paginação do Windows é configuração do sistema e fica com ele.

## O que muda

- **Novo `src/aliado/llm/providers/local.py`:** o adapter do Ollama (provedor `ollama`, apelido `local`), pela API
  compatível com a OpenAI e com o SDK `openai` já instalado (sem dependência nova).
  - As instruções vão num `system` só, com a regra do pedido de ajuda: responder só "[ESCALAR]" quando não
    conseguir.
  - A imagem vai em base64, e o PDF, como imagens das páginas (até 4, com 1.024 px no lado maior).
  - A saída estruturada vai em `json_schema`. O raciocínio do modelo desliga quando o roteador pede raciocínio baixo
    (`reasoning_effort="none"`, conferido na Etapa 3).
  - No fluxo, os primeiros 160 caracteres ficam guardados, e o "[ESCALAR]" é reconhecido em qualquer ponto deles. Na
    Etapa 3, o pedido de ajuda veio depois de um rótulo. O que vier depois disso, a conversa refaz pelo Gemini.
  - O contexto (`AL_IADO_LOCAL_CONTEXT`, padrão 16.384) é conferido antes de enviar, porque o Ollama corta em
    silêncio o que passa dele.
  - Três situações: `LocalLimit` (o limite do raciocínio), `LocalOutOfReach` (o pedido fora do alcance) e
    `LocalUnavailable` (falha técnica, com a mensagem do que conferir). O cliente não repete a chamada sozinho.
- **`providers/base.py`:** recebe de `gemini.py`, sem mudar o comportamento, os tipos de imagem e de documento e a
  leitura do PDF do pedido, para os dois adapters usarem.
- **`providers/gateway.py`:**
  - registra o provedor `ollama` e o modelo de `AL_IADO_LOCAL_MODEL`, desligado sem a variável;
  - `execute` e `stream` ganham `local=True`, e o local vem primeiro;
  - `LocalLimit` passa a vez a `google/flash` (`escalation_used` e `route_reason`; no fluxo, `fallback_used`);
  - `LocalOutOfReach` vai direto ao provedor pedido, com o motivo na rota;
  - `LocalUnavailable` sobe como erro.
- **`agent.py`:**
  - `stream_answer(..., local=True)` repassa a escolha ao gateway;
  - a resposta guarda quem respondeu de fato e o motivo da troca.
- **`interfaces/web/app.py`:**
  - a escalada da conversa: a resposta do local que não cita o que a busca trouxe, cita o que não foi enviado ou
    traz números que não conferem é refeita uma vez pelo Gemini Flash, com o aviso `recomeco`;
  - o motivo da troca entra na rota;
  - a mensagem do Ollama no lugar de "O Gemini não respondeu";
  - o uso do dia sem as linhas do local, com o teto e o aviso diário sobre os tokens pagos;
  - a confirmação da descrição de figuras nomeia o modelo local.
- **Terminal (`cli.py`):** a linha "Rota:" quando o local passa a vez, e a mensagem do Ollama no erro.
- **Tela:**
  - os tokens do local aparecem como "tokens locais", com a nota "sem custo";
  - a dica do uso do dia diz que conta só os tokens pagos.
- **`.env.example`:** `AL_IADO_LOCAL_MODEL`, `AL_IADO_LOCAL_BASE_URL` e `AL_IADO_LOCAL_CONTEXT`, comentados.

## Por que o nome `ollama`, e não `local`

O app já usa `provider == "local"` para os avisos respondidos sem modelo: eles ficam fora do histórico, sem rota e
sem "Ler mais fundo". As respostas do modelo local são respostas de verdade, então o provedor dele se chama `ollama`.

## Desvio do plano aprovado

O plano punha o modelo local na lista de modelos da tela. Ficou de fora: a lista guia o roteador (Flash-Lite ou
Flash), e o local responde por baixo de qualquer escolha. Sem o Gemini configurado, a tela segue avisando que falta o
modelo, porque o local precisa do Flash para a escalada.

## Testes

- **`tests/test_local_provider.py` (novo, 13 testes, com um cliente falso; o 13º, da Etapa 3, é o "[ESCALAR]" depois
  de um rótulo):**
  - o adapter: o `system` com o pedido de ajuda, o raciocínio baixo, a imagem e as páginas em base64, o `json_schema`;
  - os limites: o pedido de ajuda, o JSON inválido e a resposta vazia, enquanto a resposta cortada não escala;
  - o fluxo que reconhece o "[ESCALAR]" antes da tela, o que fica fora do alcance e as mensagens do Ollama;
  - a cascata do gateway: o local responde, escala para o Flash, vai direto ao modelo pedido e, fora do ar, não
    chama o Gemini;
  - o agente guarda quem respondeu.
- **`tests/test_web.py` (três novos):**
  - a resposta do local sem citação é refeita uma vez pelo Gemini Flash, e o uso do dia soma só o Gemini;
  - com o Ollama fechado, a mensagem diz o que conferir, e nada é refeito;
  - da Etapa 3: o "[ESCALAR]" no meio de uma resposta já mostrada também é refeito.
- **`tests/test_results_chat.py`:** o gateway falso aceita a opção nova.

## Resultado da Etapa 3 (18/10/2026)

- **Instalado:**
  - o Ollama 0.40.6, com o SHA-256 conferido;
  - o `qwen3.5:9b` em 4 bits (6,6 GB);
  - o `aliado-local`, com `num_ctx 16384`, `num_gpu 22` e `use_mmap true`.
- **Memória:**
  - **placa:** 3,9 GB;
  - **reserva do modelo:** 6,6 GB com `use_mmap`; sem ele, o Ollama copia os pesos e reserva 8,6 GB;
  - **limite da máquina:** com os programas do dia abertos, o modelo não carrega.
- **Velocidade:**
  - entrada de 714 tokens/s e saída de 15 a 16 tokens/s;
  - com raciocínio, de 1 a 4 minutos por resposta da biblioteca.
- **Escalada nas 16 perguntas reais, sem custo:**
  - 3 respondidas pelo local;
  - 8 direto ao Gemini, porque o documento ou as páginas inteiras passam de 4 páginas de PDF;
  - 3 refeitas pelo Gemini, porque o local citou por extenso, sem as marcas `[K…]`;
  - 1 com o pedido de ajuda no meio do texto, corrigido;
  - 1 sem resposta, porque o Ollama foi fechado.
- **Testes novos:**
  - `test_help_request_after_a_label_still_hands_over`;
  - `test_local_answer_that_asks_for_help_midway_is_redone_by_gemini_flash`.

Os números estão na [validação do lote 38](../migracao/validacao-lote-38.md).

## Fora deste lote (para o pesquisador escolher o próximo)

- **Ler o documento ou as páginas inteiras como texto no local:** é o que tirou 8 das 16 perguntas do local.
- **As marcas de citação no local:** 3 das 16 foram refeitas pelo Gemini.
- **O raciocínio do local nos trechos:** hoje uma resposta leva de 1 a 4 minutos.
- **O roteador:** mandou a E3, uma pergunta da biblioteca em inglês, para "sem a biblioteca".
- **Ligar o modelo local no `.env` dele.**
- **O `qwen3.5:4b`:** a autorização foi para o 9B.
- **Sem data:** OCR e descrição de figuras locais na indexação, leitura ampla no local e busca na web local.
