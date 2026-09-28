# Lote 18 — biblioteca, memória, anexos e fontes

Primeiro lote depois da v0.1.0, autorizado em 28/09/2026. Parte dos apontamentos do pesquisador
no uso real da interface, e as decisões foram tomadas em perguntas e respostas. A versão 0.2.0
sai com a aba Ciência.

Depois do lote, o pesquisador pôs a busca da biblioteca antes da aba Ciência: a busca passou a
ser o lote 19, e a aba Ciência, o lote 20. As menções ao "lote 19" na tabela de decisões
registram a decisão como foi tomada.

## Apontamentos e diagnóstico

| Apontamento | Causa encontrada |
|---|---|
| Com 4 PDFs enviados, "Quais arquivos você tem acesso?" não foi exibida, e "tente novamente" não achou nada. | O agente não recebia o catálogo, e a lista de arquivos não está em trecho nenhum. A resposta sem citação era escondida e saía do histórico. A busca usava só a mensagem atual: "tente novamente" era buscado literalmente. |
| O agente deveria guardar tudo, não só o que se pede. | O revisor aceitava 4 tipos e até 3 anotações por troca, e fato exige citação. O que o pesquisador conta sobre si não tinha onde ficar. |
| "Qual o meu nome?" teve como resposta "não possuo memória persistente". | A instrução geral dizia que a memória só existe quando indicada no pedido. |
| Os cartões de anexo ficam no chat, sem tempo nem limite. | Cada cartão só saía pelo ×. |
| O painel lateral de fontes é grande demais. | Coluna fixa à direita da conversa. |
| A aba Ciência está inacessível. | Botão "em breve" desde o lote 10. Fica para o lote 20. |
| As memórias poderiam ir para o Git? | Não: `/data/` está no `.gitignore`, e o commit v0.1.0 não tem arquivo de `data/`. |

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| A. Resposta sem citação no modo biblioteca | **Mostrar com aviso** e manter no histórico. Citação inventada continua bloqueada. |
| B1. "Salvar tudo" | **Perfil**, um tipo novo de anotação, **e memória de conversas**. |
| B2. Conversa apagada | **Deixa de ser lembrada.** As anotações que saíram dela ficam, como no lote 11. |
| C. Aba Ciência | Fazer tudo pela interface, com gráficos, tabelas e exploradores interativos com os dados reais. |
| C1. Explorador de alarme e detecção | Pode usar o teste e os ensaios com falha, com o rótulo "exploração pós-teste, não canônica (M14)". |
| C2. Divisão | Dois lotes: o 18 (A, B e D) e o 19 (a aba Ciência). |
| D. Cartão de anexo que deu certo | Some em **6 s**. |
| Versão | A 0.2.0 sai no fim do lote 19. Ao fim do lote 18, o pesquisador pode fazer o commit, sem tag. |

## Escopo implementado

### A. Modo biblioteca (`agent.py`)

- **Catálogo:** com a biblioteca ligada, o pedido leva a lista dos documentos (título, versão e estado; até 200) como dados de consulta. Perguntas sobre o acervo são respondidas pelo catálogo, sem `[K]`.
- **Busca com contexto:**
  - mensagens de até 6 palavras buscam junto com a pergunta anterior;
  - se a pergunta não acha trecho, a busca é refeita com a anterior;
  - a consulta usada fica nos metadados (`search_query`).
- **Sem trecho recuperado,** o modelo é chamado assim mesmo, com o aviso de que nada foi encontrado. A resposta local "Não encontrei trechos suficientes" deixou de existir.
- **Resposta sem nenhuma citação:** estado `uncited`. Aparece com a faixa "Esta resposta não cita trechos dos seus documentos" e entra no histórico enviado ao modelo. Com a web e fontes, continua `web_grounded`.
- **Citação inventada**, com identificador fora dos trechos recuperados, continua bloqueando a resposta.
- `[K1, K2]` é separado em `[K1][K2]` antes da conferência.

### B. Memória (`memory/store.py`, `memory/reviewer.py`, `agent.py`)

- **Perfil:**
  - guarda quem é o usuário e o seu contexto: nome, formação, instituição, orientador, prazos e situação da pesquisa;
  - vale em todas as skills e entra sempre no contexto (até 15), antes das preferências;
  - o revisor é instruído a anotar o que o usuário conta sobre si e passa a propor até 8 anotações por troca (antes, 3);
  - "Lembrar…" e a aba Memória ganham o tipo.
- **Memória de conversas:**
  - tabela `exchanges` no SQLite de `data/memoria/`;
  - cada troca exibida que entra no histórico é guardada: pergunta até 500 caracteres e resposta até 1.500;
  - o vetor soma pergunta e resposta com o mesmo peso, para uma resposta longa não apagar o assunto;
  - a cada pergunta, até 3 trocas de **outras** conversas, com semelhança de pelo menos 0,40, entram como dados, com a data. As regras dizem que elas não são decisões aprovadas e podem estar superadas pelas anotações;
  - a resposta mostra "lembrou N conversas", com um link para abrir cada uma.
- **Conversas anteriores:** ao abrir, o servidor indexa uma vez, em segundo plano, as conversas que já existem e calcula os vetores que faltam (`fill_missing_vectors`).
- **Apagar uma conversa** marca as trocas dela como esquecidas (`forgotten`). As anotações ficam, e o aviso de confirmação diz isso.
- **Instrução geral:** o agente tem memória persistente. Sem anotação sobre algo, ele diz que não tem isso anotado.

### D. Interface (`app.js`, `app.css`, `index.html`, `app.py`)

- **Janela de fontes e memória:**
  - os links no fim da resposta (fontes, buscas na web, conversas lembradas, memórias usadas e anotações novas) e os números `[n]` abrem uma janela sobre a resposta, perto do link;
  - a janela cabe na tela, com rolagem interna, e fecha com Esc, com um clique fora ou pelo ×;
  - o painel lateral saiu, e a conversa ocupa a largura.
- **Fila de anexos:**
  - até 3 cartões à vista, com o mais recente no topo;
  - contador "X de N indexados", com as falhas;
  - o sucesso some em 6 s; a falha fica até ser fechada; um tipo não aceito gera só o aviso.
- **Cache:** a página e os arquivos estáticos saem com `Cache-Control: no-cache`, e uma atualização aparece sem limpar o navegador.

### Correção encontrada no aceite

O encoder local recusa textos com mais de 128 tokens, e o erro era engolido. Anotações e trocas
longas ficavam **sem vetor** e nunca eram achadas por semelhança. Agora o texto é dividido pelo
`split` do encoder e os vetores das partes são somados. Na memória real do pesquisador, 18 das
236 anotações estão nessa situação e ganham vetor na próxima abertura.

## Critérios de aceitação

- **Testes sem rede:**
  - catálogo, busca de continuação e citação agrupada;
  - resposta sem citação exibida e mantida no histórico;
  - perfil global e sempre lembrado, e o revisor com 8 anotações;
  - memória de conversas lembrada e esquecida ao apagar, e a indexação única das conversas existentes;
  - vetores de textos longos e o preenchimento dos que faltam;
  - o cabeçalho de cache.
- **Aceite com chamadas reais ao Flash-Lite:**
  - "Quais arquivos você tem acesso?" lista o acervo com o aviso, e uma continuação curta segue a pergunta anterior;
  - o pesquisador se apresenta e, noutra conversa, o agente diz o nome dele;
  - um assunto é lembrado noutra conversa e deixa de ser depois que a conversa é apagada.
- **Interface:** a fila de anexos e a janela de fontes conferidas.
- A suíte completa e o Ruff passam.

## Fora do escopo

- A aba Ciência, no lote 20.
- **A qualidade da busca da biblioteca**, no lote 19:
  - perguntas em português puxam sobretudo documentos em português;
  - o catálogo mostra o nome do arquivo, sem autor nem ano.
- Cópia de segurança ou exportação da memória: proposta, sem decisão.
- O wheel e a tag, que saem com a 0.2.0.
