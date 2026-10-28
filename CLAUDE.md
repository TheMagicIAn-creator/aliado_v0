@AGENTS.md

# AL-IAdo — guia do Claude Code

Este arquivo é lido no início de toda sessão. As regras de custo, dados, Git e autorizações estão no
`AGENTS.md` (importado acima), que vale também para o Codex. Aqui fica só o que é próprio do Claude Code.

## Quem é o pesquisador

- Rodolfo, mestrado na UTFPR, sobre detecção de falhas em inversores fotovoltaicos. O AL-IAdo é a
  ferramenta da pesquisa; o texto da dissertação é escrito por fora.
- Fala português. Quer respostas curtas, em linguagem simples, e decide por perguntas e respostas:
  a resposta dada é a decisão e não precisa ser confirmada de novo.
- Não escreve código. O Claude implementa e explica, em poucas linhas, o que está fazendo.
- Commits, tags, pushes e publicações são do pesquisador. O Claude prepara os arquivos e mostra os comandos.

## Como trabalhar

Todo pedido de desenvolvimento segue o [WORKFLOW.md](WORKFLOW.md). O essencial:

1. Planeje antes de editar e espere a aprovação do plano, a menos que o pedido já autorize a direção (`AGENTS.md`).
   Mudança de mais de um arquivo usa o modo de planejamento.
2. Na falta de uma decisão do pesquisador, pergunte; não adivinhe. Fatos do repositório, procure você mesmo.
3. Verifique antes de dizer que está pronto. Teste simulado não valida o modelo real.
4. Ao terminar, atualize o [ESTADO.md](ESTADO.md) e pergunte qual é o próximo passo.

Uma pergunta simples não precisa de plano.

## Qual workflow usar

| Pedido | Workflow |
|---|---|
| Comportamento novo ou alterado do AL-IAdo | [mudança de comportamento](workflows/mudanca-de-comportamento.md) |
| Algo funciona errado | [correção de defeito](workflows/correcao-de-defeito.md) |
| Medir o modelo local (Ollama) com perguntas de verdade | [bateria do modelo local](workflows/bateria-modelo-local.md) |
| Avaliar, revisar ou levantar pendências, sem mudar código | [diagnóstico](workflows/diagnostico.md) |
| Fechar uma versão | [lançamento](workflows/lancamento.md) |

Um pedido pode juntar mais de um (diagnóstico, depois correção). Se nenhum servir, siga só o
`WORKFLOW.md`; se o mesmo tipo de pedido se repetir, proponha um workflow novo nesta pasta.

## Mapa do repositório

- `src/aliado/` — o núcleo: `agent.py` (monta e confere as respostas), `routing.py` (roteador local),
  `llm/providers/` (gateway, Gemini e Ollama), `memory/` (memória e revisor), `knowledge/` (biblioteca,
  leitura, figuras, reescrita), `interfaces/web/` (servidor e tela), `cli.py`.
- `src/aliado/specializations/mestrado/` — a especialização do mestrado. O núcleo não cita nenhuma.
- `docs/specs/capacidades/` — specs vivas (o que vale hoje); `docs/specs/00NN-*.md` — specs de mudança.
- `docs/roteiro-v0.md` — lotes, specs e decisões; `docs/revisao/` — diagnósticos datados.
- `tests/` — a bateria de testes; `ferramentas/` — a bateria em processos separados, medição e equivalência.
- `data/` e `tmp/` ficam fora do Git: memória, conversas, biblioteca e uso; medições e rascunhos.

## Armadilhas deste ambiente

- Windows. Use `.venv/Scripts/python.exe -m pytest` e `.venv/Scripts/python.exe -m ruff check .`.
- Com o Ollama carregado, rode o pytest e os scripts da bateria com `OPENBLAS_NUM_THREADS=1`.
- O hook de `.claude/settings.json` bloqueia as operações Git perigosas e, na dúvida, o comando que não consegue
  analisar (aspas ou script que atravessam linhas, heredoc). Deixe cada `git` numa linha própria, longe desses scripts.
- Texto com barra invertida (expressões regulares) vai pelo Edit; um heredoc no Bash estraga o `\b`.
- Os arquivos usam CRLF; o aviso de conversão do Git não é erro.
