# Spec 0065 — a limpeza sem perda

Estado: feito em 24/10/2026, sem commit; o commit fica com o pesquisador. Os arquivos estão na Lixeira do Windows: o
espaço volta quando ele a esvaziar.

## Propósito e decisões

**A origem:** o [levantamento de 24/10](../revisao/2026-10-24-levantamento-exclusoes.md), pedido pelo pesquisador, do
que pode sair do AL-IAdo. Este lote faz o grupo A, o que sai sem perda.

**A decisão (pesquisador, 24/10/2026):** "Comece pelo grupo A (sem perda) como lote 65: me mostre a lista final antes
de apagar". Depois, sobre a lista: "Sim, aplique a lista do lote 65 como mostrada."

**O método:** o mesmo da limpeza do lote 59. Os arquivos vão para a Lixeira do Windows, e apagar de vez fica com o
pesquisador. As mudanças no código ficam no Git.

**Duas mudanças em relação ao levantamento:**
- **Os pacotes da v0.7.0 e da v0.8.0 em `dist/` ficam.** Comparados com os das releases, são diferentes; só os da v0.1.0
  à v0.6.0 são idênticos.
- **A função `_join` da biblioteca fica.** Cerca de 15 testes a usam para conferir a regra de encaixe dos trechos;
  tirá-la obrigaria a reescrevê-los sem ganho.

## O que saiu

| Item | Tamanho | Por que saiu |
|---|---:|---|
| 43 arquivos `.pyc` de módulos renomeados nos lotes 49 a 56 | 1,1 MiB | O Python nunca os lê: o `.py` de origem não existe |
| `.pytest_cache` e `.ruff_cache` | 0,1 MiB | As ferramentas refazem |
| `tmp/verificacao` | 23,2 MiB | A cópia dos resultados que `tmp/verificar.py` refaz a cada fechamento |
| `tmp/pacote-85a785…` | 5,6 MiB | A cópia limpa dos fontes usada para montar o pacote da 0.9.2 |
| `tmp/v070-build` e `tmp/v080-build` | 7,8 MiB | Cópias do código da 0.7.0 e da 0.8.0, que as tags guardam |
| `tmp/v070-check/pacote` e `tmp/v080-check/pacote` | cerca de 5 MiB | Os pacotes abertos para a conferência. Os scripts `conferir_pacote.py` ficam, porque a validação do lote 36 os cita |
| `tmp/lote-64/baixado` e `tmp/lote-65/releases` | cerca de 6 MiB | Pacotes baixados do GitHub só para conferir o hash |
| `dist/v0.1.0` a `dist/v0.6.0` | 3,9 MiB | Idênticos, byte a byte, aos das releases no GitHub |

São 43 arquivos e 16 pastas, 52,8 MiB. A lista item a item, com o tamanho, está em `tmp/lote-65/lixeira.txt`.

**Na configuração e no código:**
- **`.claude/launch.json`:** saem 10 das 19 configurações do servidor de teste, as dos lotes 12 e 19 a 27. Elas
  apontavam para pastas que a limpeza do lote 59 já tirou, e 7 delas usavam a opção `--gpvs`, que o `aliado web` não
  tem mais.
- **`src/aliado/llm/contracts.py`:** saem `texto_resultado_llm`, com as 4 funções auxiliares, a enumeração `TaskType`
  e o campo `request_id` do pedido e do resultado. Nenhum código os usava.
- **`src/aliado/llm/providers/gateway.py`:** saem os nomes antigos `AL_IADO_GEMINI_MODEL_FUNDO`,
  `AL_IADO_GEMINI_MODEL_AUDITOR` e `AL_IADO_GEMINI_MODEL`. Ficam só `AL_IADO_GEMINI_MODEL_FLASH_LITE` e
  `AL_IADO_GEMINI_MODEL_FLASH`, os do `.env` e do `.env.example`.
- **`tests/test_contracts.py`:** usa o texto `"scientific_reasoning"` no lugar de `TaskType`, e confere o mesmo.

**Nenhum requisito muda.**

## Fica para depois

Do levantamento:
- as versões antigas da indexação da biblioteca;
- o pacote `transformers`;
- o provedor da OpenAI e a chave dele no `.env`;
- os itens pequenos do grupo C.

## Aceitação

- **Cada item:** saiu do lugar e está na Lixeira.
- **A bateria completa,** com os testes com os dados reais: 871 passando, nenhum falhou nem foi ignorado; 36 grupos;
  18 treinos; 221,1 s; pico de 559,0 MiB. O registro fica em `tmp/lote-65/bateria.log`.
- **O Ruff:** sem apontamentos.
