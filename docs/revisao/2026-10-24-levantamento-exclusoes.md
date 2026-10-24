# Levantamento do que pode sair do AL-IAdo (24/10/2026)

Pedido do pesquisador: "um levantamento pormenorizado do que pode ser excluído do aliado, seja pasta, arquivo ou
código". Nada foi apagado. Cada item foi conferido no disco, no Git ou no código. Os tamanhos são os tamanhos dos
arquivos. Feito depois da 0.9.2.

**Como ler:** os itens vão do mais seguro ao que pede decisão sua.
- **Grupo A:** sai sem perda nenhuma, porque o AL-IAdo ou o Python refazem sozinhos, ou porque há cópia no GitHub.
- **Grupo B:** pede uma capacidade nova no AL-IAdo.
- **Grupo C:** pede decisão sua.
- **Grupo D:** o que eu **não** recomendo apagar.

## Resumo

| Grupo | O quê | Espaço | Risco |
|---|---|---:|---|
| A1 | Arquivos compilados de módulos que já não existem | 1,2 MB | nenhum |
| A2 | Sobras de montagem e de conferência em `tmp/` | 43 MB | nenhum |
| A3 | Pacotes antigos em `dist/` que já estão nas releases do GitHub | cerca de 7 MB | baixo |
| A4 | 10 configurações quebradas do servidor de teste | — | nenhum |
| A5 | Código que nada chama (cerca de 70 linhas) | — | baixo |
| B1 | As 25 versões antigas da indexação da biblioteca | cerca de 300 MB | baixo, com um comando novo |
| C1 | O pacote `transformers`, instalado sem uso | 100 MB | baixo |
| C2 | O provedor da OpenAI, nunca usado | cerca de 150 linhas e testes | baixo; envolve uma chave secreta |
| C3 | Itens pequenos de configuração e campos sem leitor | — | baixo |
| D | A medição fixa do lote 46, os registros, os dados da pesquisa | cerca de 1,2 GB | não recomendo |

O código está enxuto: todo módulo de `src/` é importado por outro, e só um punhado de funções está sem uso. O espaço
que dá para recuperar com segurança é de cerca de 450 MB. Os demais 2,8 GB entre `data/` e `tmp/` são dados da pesquisa
ou registros guardados de propósito.

---

## A. Sai sem perda

### A1. Arquivos compilados órfãos (1,2 MB)

São 43 arquivos `.pyc`, compilados de módulos renomeados ou movidos nos lotes 49 a 56.
- **Onde ficam:** em `src/aliado/science/`, `src/aliado/science/deteccao/`, `src/aliado/specializations/mestrado/`,
  `src/aliado/interfaces/web/` e `tests/`.
- **Exemplos:** `science/__pycache__/fmeca.cpython-312.pyc` e `mestrado/__pycache__/routing.cpython-312.pyc`.
- **Por que saem:** o Python nunca os lê, porque o `.py` de origem não existe mais.
- **O mesmo vale para os caches de ferramentas:** `.pytest_cache` (91 kB), `.ruff_cache` (32 kB) e todas as pastas
  `__pycache__`, que o Python refaz.

### A2. Sobras em `tmp/` (43 MB)

| Pasta | Tamanho | O que é |
|---|---:|---|
| `tmp/verificacao` | 24 MB | A cópia dos resultados que `tmp/verificar.py` faz a cada fechamento; ele a refaz |
| `tmp/pacote-85a785…` | 5,7 MB | A cópia limpa dos fontes usada para montar o pacote da 0.9.2 |
| `tmp/v070-build`, `tmp/v080-build` | 7,9 MB | As montagens dos pacotes da 0.7.0 e da 0.8.0, já publicados |
| `tmp/v070-check`, `tmp/v080-check` | 4,9 MB | As conferências desses pacotes, já registradas nas validações |
| `tmp/lote-64/baixado` | 0,9 MB | O pacote da 0.9.2 baixado do GitHub só para conferir o hash |

### A3. Pacotes antigos em `dist/` (cerca de 7 MB)

O GitHub guarda o pacote de cada release, da v0.1.0 à v0.9.2. As cópias locais de `dist/v0.1.0` a `dist/v0.7.0` são
redundantes.
- **Antes de apagar:** conferir o hash de cada uma contra a release.
- **Ficam:**
  - **`dist/v0.4.1`:** não tem release no GitHub.
  - **`dist/v0.8.0-fechamento`:** é o pacote publicado da 0.8.0. A pasta `dist/v0.8.0` é a montagem anterior a ele e
    pode sair.
  - **As três da 0.9:** são as versões atuais.
- **`dist/lote-08`, `dist/lotes-04-06` e o `aliado-0.1.0-py3-none-any.whl` solto:** são as entregas de antes da 0.1.0.
  São registros das entregas originais e só saem se você quiser.

### A4. Configurações quebradas do servidor de teste

Em `.claude/launch.json`, 10 configurações apontam para pastas que a limpeza de 23/10 já tirou: as dos lotes 12 e 19
a 27.
- **Erro a mais:** as dos lotes 20 a 27 usam a opção `--gpvs`, que o comando `aliado web` não tem mais.
- **O que acontece hoje:** nenhuma delas abre.
- **Os lotes 29 a 35:** outras 7 configurações chamam scripts antigos em `tmp/lote-NN/`. Os scripts existem, mas não
  testei se ainda rodam com o código de hoje.

### A5. Código que nada chama (cerca de 70 linhas)

Procurei, em `src/`, `tests/` e `ferramentas/`, toda função, classe e constante de nível de módulo cujo nome não
aparece em nenhum outro lugar.

| Onde | O quê | Linhas | Situação |
|---|---|---:|---|
| `src/aliado/llm/contracts.py:142-189` | `texto_resultado_llm` e as 4 funções auxiliares dela | 48 | Ninguém chama, nem os testes. Era para "SDKs legados" |
| `src/aliado/llm/contracts.py:10` | A enumeração `TaskType` | 10 | Só um teste a usa; o código passa o tipo da tarefa como texto |
| `src/aliado/knowledge/library.py:120` | `_join` | 4 | Só um teste a usa (`tests/test_passages.py:63`); a indexação não a chama |
| `src/aliado/llm/providers/gateway.py:200-202` | Os nomes antigos `AL_IADO_GEMINI_MODEL_FUNDO`, `_AUDITOR` e `AL_IADO_GEMINI_MODEL` | 3 | Nem o `.env`, nem o `.env.example`, nem o README os usam |
| `src/aliado/llm/contracts.py:88,129` | O campo `request_id` do pedido e do resultado | 2 | Ninguém preenche nem lê |

---

## B. Pede uma capacidade nova

### B1. As versões antigas da indexação da biblioteca (cerca de 300 MB)

Quando um documento é reindexado, a versão anterior fica guardada. A biblioteca tem 31 documentos e 56 indexações:
25 delas são antigas e não são usadas por nenhuma busca.
- **Os arquivos delas:** 174 MB em `data/bibliotecas/principal/extracted/`.
- **No catálogo:** 13.800 trechos, de 33.991, com 126 MB de texto e vetores.
- **O catálogo:** tem 355 MB e encolheria depois de compactado.

**Como sairiam:** um comando novo no próprio AL-IAdo, por exemplo `aliado biblioteca limpar-versoes`. Ele mostraria
quanto sai e só apagaria com confirmação. Pela regra combinada, a biblioteca real é mexida pelo AL-IAdo, não por
mim à mão.

---

## C. Pede decisão sua

### C1. O pacote `transformers` (100 MB em `.venv`)

- **O que é:** um pacote instalado no ambiente do AL-IAdo.
- **Por que pode sair:** nada no código o importa, nenhum outro pacote depende dele, e ele não está no `pyproject.toml`
  nem no `requirements-dev.lock`.
- **Origem provável:** um teste antigo dos modelos de busca. A busca usa o formato ONNX, sem ele.
- **Como sairia:** `pip uninstall transformers`.

### C2. O provedor da OpenAI (cerca de 150 linhas, mais os testes)

- **O que é:** o código para usar os modelos da OpenAI no lugar do Gemini.
- **Nunca foi usado:** o registro de uso tem 1.569 chamadas (1.548 do Gemini e 21 do modelo local) e nenhuma da OpenAI.
- **Não funcionaria hoje:** os modelos dele (`AL_IADO_OPENAI_MODEL_LUNA`, `_TERRA` e `_SOL`) estão vazios no `.env`.
- **O que sairia:**
  - `src/aliado/llm/providers/openai.py` (142 linhas);
  - o registro dos três modelos no gateway;
  - a opção `--provider openai` do comando `perguntar`;
  - os trechos dos testes que o usam, em 5 arquivos.
- **O que fica:** o pacote `openai` continua instalado, porque é ele que conversa com o Ollama.
- **Atenção à chave:** o `.env` tem uma `OPENAI_API_KEY` preenchida, sem uso. É uma chave secreta guardada à toa.
  Recomendo tirá-la do `.env` e, se não for usá-la em outro lugar, revogá-la no site da OpenAI.

### C3. Itens pequenos

- **A skill `grill-me`** (`.claude/skills/grill-me/`): só manda chamar a `grilling`, que fica ao lado. É um atalho
  repetido.
- **O campo "risco metodológico" dos pedidos ao modelo:** o código preenche e confere, mas nenhum provedor o lê. São
  cerca de 20 linhas em `contracts.py` e uma em `agent.py`.
- **O estado "experimental" dos modelos:** nenhum modelo real é registrado assim, e só um teste o usa. São cerca de 5
  linhas.
- **Pastas vazias em `data/`:** `data/ciencia` e `data/uploads-temporarios`. A segunda é usada pelos envios e deve
  ficar.

---

## D. Não recomendo apagar

| Item | Tamanho | Por quê |
|---|---:|---|
| `tmp/lote-46/medicao` | 993 MB | É a cópia fixa da biblioteca para comparar medições. Você decidiu mantê-la na limpeza de 23/10 |
| Os registros dos lotes em `tmp/lote-NN/` | cerca de 100 MB | As validações dos lotes citam esses arquivos (bateria, equivalência, medições) |
| `tmp/equivalencia/referencia` | 2,9 MB | A referência contra a qual cada versão confere que os números da ciência não mudaram |
| `data/gpvs`, `data/models`, `data/tools/tesseract` | 824 MB | Os dados dos ensaios, os modelos de busca e o leitor de páginas escaneadas: todos em uso |
| `data/resultados`: 9 rodadas que nada cita | cerca de 6 MB | Por exemplo, `gpvs-avaliacao-003` e `004` e as três `fmeca-20261001-…`. São o histórico da pesquisa |
| `docs/specs` 0001 a 0033, os manifestos e as validações em `docs/migracao` | — | São registros que as regras do projeto mandam preservar |
| As skills repetidas em `.agents/skills` e `.claude/skills` | — | São as mesmas três skills, uma cópia para o Codex e outra para o Claude Code |
| `.obsidian`, `.smart-env`, `.codex-remote-attachments`, `.idea` | 7,3 MB | São das suas ferramentas, fora do Git |

## Como foi feito

- **Espaço:** medido com `du`, por pasta.
- **O catálogo da biblioteca:** lido só em modo leitura.
- **Os pacotes do GitHub:** listados com `gh release view`.
- **O código sem uso:** um script percorreu as definições de nível de módulo e os métodos e contou os usos de cada
  nome em `src/`, `tests/`, `ferramentas/` e nos arquivos da tela. Cada achado foi conferido à mão.
- **O registro de uso:** contado por provedor.
- **Não foram lidos:** o `.env`, além dos nomes das variáveis e de estarem vazias ou preenchidas.
