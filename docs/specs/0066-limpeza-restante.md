# Spec 0066 — o resto da limpeza: indexações antigas, `transformers` e OpenAI

Estado: feito em 24/10/2026, sem commit; o commit fica com o pesquisador.

## Propósito e decisões

**A origem:** os itens que o lote 65 deixou abertos no
[levantamento de 24/10](../revisao/2026-10-24-levantamento-exclusoes.md): as indexações antigas da biblioteca, o pacote
`transformers` e o provedor da OpenAI.

**A decisão (pesquisador, 24/10/2026):** "Sim, aplique o lote 66 como planejado."

## O que muda

**As indexações antigas (BIB-06, novo):**
- **O comando:** `aliado biblioteca limpar-versoes --biblioteca …`.
  - **Sem `--executar`:** mostra quantas indexações nenhum documento usa, os trechos delas e o espaço das pastas. Não
    muda nada.
  - **Com `--executar`:** apaga essas indexações, os trechos e as pastas delas e compacta o catálogo.
- **O que fica:** a indexação ativa de cada documento, as versões dos documentos, os originais, as figuras descritas
  e as fichas.
- **Na cópia fixa da biblioteca do lote 46** (`tmp/lote-46/medicao/biblioteca`, igual à real nesse ponto), a contagem
  deu 25 indexações, 13.800 trechos e 182.101.140 bytes (174 MiB) em pastas, como no levantamento. O catálogo não
  mudou: o hash foi o mesmo antes e depois.
- **A biblioteca real não foi tocada.** O pesquisador roda o comando quando quiser.

**O pacote `transformers`:**
- **O que saiu do `.venv`:** `transformers` (100 MB) e os três pacotes que só ele usava, `safetensors`, `regex` e
  `typer`. Nenhum era importado pelo AL-IAdo nem estava no `pyproject.toml` ou no `requirements-dev.lock`.
- **A conferência:** `pip check` sem problemas. A busca e o reordenador importam normalmente, porque `tokenizers` e
  `huggingface-hub` ficaram.

**O provedor da OpenAI:**
- **Nunca foi usado:** das 1.569 chamadas registradas, nenhuma foi para ele, e os modelos dele estavam vazios no
  `.env`.
- **O que saiu:**
  - `src/aliado/llm/providers/openai.py`;
  - os modelos luna, terra e sol no gateway;
  - a opção `--provider openai` do comando `perguntar`;
  - as linhas dele no `.env.example` e no README.
- **Nos testes:**
  - saíram os 6 testes só do adaptador da OpenAI;
  - os testes compartilhados ficaram só com o Gemini;
  - os testes do comando `perguntar` e do gateway padrão passaram a usar o Gemini.
- **O que fica:** o pacote `openai`, que é o cliente do Ollama.
- **A chave no `.env`:** o `.env` não foi lido nem mudado. Cabe ao pesquisador tirar a `OPENAI_API_KEY` e revogá-la.

**Junto:** o commit do lote 65 (7f58d37) fica registrado no roteiro e na spec 0065.

## Requisitos vivos

- **BIB-06 (novo), em `biblioteca.md`:** as indexações antigas saem por pedido.

## Aceitação

- **O teste do BIB-06:**
  - sem `execute`, nada muda, nem o catálogo;
  - com `execute`, sai só a indexação antiga;
  - a busca segue achando os dois documentos.
- **A bateria completa,** com os testes com os dados reais: 853 passando, nenhum falhou nem foi ignorado; 36 grupos;
  18 treinos; 229,7 s. O registro fica em `tmp/lote-66/bateria.log`.
  - **Por que são 18 a menos que os 871 da 0.9.2:** saíram 6 testes só da OpenAI e 13 casos da OpenAI nos testes de
    saída estruturada, e entrou 1, o do BIB-06.
- **O Ruff:** sem apontamentos.
- **Fica de fora:** as miudezas do grupo C do levantamento.
