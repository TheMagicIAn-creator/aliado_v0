# Validação do lote 17 — lançamento v0.1.0

Verificação local em **27/09/2026**. Nenhum commit, push, PR ou tag.

## Instalação do zero

| Etapa | Resultado |
|---|---|
| Clone simulado | 184 arquivos (os não ignorados pelo `.gitignore`) copiados para `tmp/lote-17/repo`. |
| Python | 3.14.6, o do PATH, com `python -m venv .venv` como no README. |
| `pip install -r requirements-dev.lock` e `pip install --no-deps -e .` | Sem erros. Todos os pacotes fixados têm versão para 3.14; torch 2.12.0+cpu, numpy 2.5.3 e onnxruntime 1.30.0. Download de cerca de 170 MB, cujo maior arquivo é o torch para 3.14 (123 MB). |
| `aliado biblioteca preparar-modelo` com cache vazio | 14 min 37 s pela rede. `model_quint8_avx2.onnx` e `tokenizer.json` saíram com os mesmos SHA-256 do encoder existente. |
| pytest | **331 passaram**, com os dados do GPVS ligados por atalho de pasta. Os modelos da origem são reproduzidos **bit a bit também no Python 3.14**. |
| Ruff | Sem problemas. |

**Defeito encontrado e corrigido.** Na primeira rodada, 3 testes falharam porque os arquivos
de `tests/data/` não estavam na lista do Git: a regra `data/` do `.gitignore` valia para
qualquer pasta `data`. A regra passou a `/data/`, e os arquivos de referência passam a
entrar no commit.

## Aceite com chamadas reais

Interface da instalação limpa em `127.0.0.1:8766`, modelo `gemini-3.5-flash-lite`.

| Critério | Resultado |
|---|---|
| 2. PDF enviado, com citação de página | Um PDF sintético de 2 páginas foi enviado pela rota do clipe (`/api/biblioteca`), porque o navegador do app não abre o seletor de arquivos; saíram 2 trechos e uma ficha com 4 anotações. A resposta dá "45.000 horas a 40 °C, página 2", e o painel mostra "página PDF 2 · p. 2" com o trecho. |
| 3. Memória entre conversas | "Lembre que prefiro respostas com no máximo duas frases" gerou 1 anotação nova. Numa conversa nova, a resposta veio em duas frases, usando a preferência. Na correção para quatro frases, a anotação antiga ficou **superada e preservada**, com o link para a origem, e a resposta seguinte teve quatro frases. |
| 4. Web com fonte | "Versão estável mais recente do Python": 2 buscas, 2 fontes de python.org no painel e a preferência de memória aplicada. |
| Uso | 13 chamadas, 34.428 tokens de entrada e 853 de saída, e 2 buscas na web. O custo segue a tabela do Google. |

**Defeito encontrado e corrigido.** Na primeira resposta sobre o PDF, o modelo escreveu
identificadores internos (`[6452e6b8, K435b627e…]`). O contexto de memória levava o `id` de
cada anotação, e o modelo o copiou junto de uma citação.
- O `id` saiu do contexto: as anotações usadas já chegam à interface pelos metadados.
- A regra da biblioteca pede um identificador por colchete.
- Refeita a pergunta, a resposta veio limpa, com citações [1] e a página 2.

## Pacote

`dist/v0.1.0/aliado-0.1.0-py3-none-any.whl`, gerado de novo depois da correção: 75 arquivos,
480 kB, SHA-256 `4f52f2033b42d8842b932add62feee4211be446e4db8782c19fe8e525d943729`.

- **Conteúdo:** a interface, o KaTeX com licença e 20 fontes, as 3 skills com a referência e os módulos de ciência e detecção. Testes, documentação e dados ficam fora.
- **Teste num ambiente novo:** o pacote, instalado sem modo editável no Python 3.14, rodou `skills`, `preparar`, `ciencia calcular` (com o PNG) e `ciencia fmeca`. A interface respondeu 200 para a página, o `app.js`, o KaTeX e as fontes, e `/api/estado` respondeu.

## Auditoria antes do commit

| Verificação | Resultado |
|---|---|
| Lista do Git | 184 arquivos, 1,5 MB, com `.agents/`, `.claude/`, `docs/`, `src/`, `tests/` e os arquivos da raiz. O maior é o `katex.min.js`, com 271 kB. |
| `.env`, `data/`, `tmp/`, `dist/`, `build/` e `.venv/` | Fora. |
| Segredos | Nenhum padrão de chave Google, OpenAI, Hugging Face ou GitHub, nem de chave privada ou atribuição de segredo. |
| Caminho pessoal | Só em `docs/migracao/lote-10.json`, que registra o caminho local do repositório de origem, com o nome de usuário do Windows. O manifesto foi preservado como registro, e a decisão é do pesquisador. |

## Suíte final

No ambiente de trabalho (Python 3.12) e no limpo (Python 3.14): **331 testes passaram** e o
Ruff não apontou problemas.
