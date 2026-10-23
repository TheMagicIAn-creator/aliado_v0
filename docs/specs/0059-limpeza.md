# Spec 0059 — a limpeza do disco

Estado: feito em 23/10/2026, sem commit; o commit fica com o pesquisador. Os itens estão na Lixeira do Windows: o
espaço volta quando ele a esvaziar.

## Propósito e decisões

Vem da lista "Depois" do plano de 21/10 e do
[diagnóstico de 21/10](../revisao/2026-10-21-diagnostico-modularizacao.md) (seção 3), que achou cerca de 14 GB de
resíduo fora do Git.

**A decisão (pesquisador, 23/10/2026):** "Apaga tudo para ter mais espaço", sobre a lista de 15 itens mais os
pequenos.

**O método:**
- **Para a Lixeira do Windows, não apagados de vez:** apagar de vez fica com o pesquisador, que esvazia a Lixeira.
- **A capacidade:** a Lixeira do C: comporta 25,8 GB. Ela tinha 1,83 GB e foi a 14,65 GB: tudo coube, sem empurrar
  para fora o que já estava nela.

**O que fica:**
- **`tmp/lote-46/medicao`, com a biblioteca e os resultados copiados:** é a cópia fixa das medições dos lotes 48, 57
  e 58, com o hash do catálogo registrado. Uma medição futura se compara com as anteriores.
- **Os registros das medições:** os JSON e os scripts de cada lote. Saíram só as cópias da biblioteca.

## O que saiu

| Item | Tamanho | Por que saiu |
|---|---:|---|
| `tmp/lote-39`, `40`, `41` (2), `42` e `43` (2): a pasta `biblioteca` de cada medição; `tmp/lote-45/library-snapshot` | 8 × 979 MiB | Cópias da biblioteca feitas para cada medição. Nenhum manifesto guarda hash de arquivo de dentro delas |
| `tmp/lote-29/biblioteca` e `tmp/lote-29/backup` | 2.803 MiB | A cópia e o backup de antes da reindexação de 03/10 (lote 29, versão 0.4.0) |
| `data/models/reranker-bge` | 2.188 MiB | Outro modelo de reordenação. O código o recusa: `reranking.py` confere o hash de uma versão fixa do modelo mMiniLM |
| `data/models/reranker-mmarco` | 130 MiB | Cópia exata de `data/models/reranker`: o modelo e o tokenizador têm os mesmos hashes |
| `data/validacao-lote-32/catalogo-sintetico` | 159 MiB | O catálogo sintético da validação do lote 32, que o script dela refaz. O resultado, `medicao.json`, fica |
| `data/ciencia/erros-33eec42922c0.npz` e `erros-be9e54fa5d21.npz` | 18 MiB | Caches de antes do lote 46. A chave deles não tem os pesos nem as variáveis, então o explorador nunca os lê |
| `tmp/lote-45/results-snapshot`, `tmp/salvaguarda-2026-10-21`, `build/` e `data/validacao-lote-33*` | 21 MiB | Itens pequenos, autorizados com o resto. A salvaguarda era dos commits de 21/10, já publicados |
| `docs/revisao/2026-10-20-diagnostico-arquitetura-complementado.txt` | — | Cópia exata, byte a byte, do `.md` ao lado. Sai do Git no commit do pesquisador |

São 22 itens e 13.151 MiB (12,8 GiB).

## A pasta do reordenador

O reordenador lê a pasta da variável `AL_IADO_RERANKER_DIR`. Sem a variável, lê `data/models/reranker`, que fica. O
`.env.example` traz a variável comentada. O `.env` não foi lido.
- **`reranker-bge`:** nunca funcionaria, com ou sem a variável, porque o hash não confere.
- **`reranker-mmarco`:** só faria falta se o `.env` apontasse a variável para ela. Nesse caso, basta apontar para
  `data/models/reranker` ou tirar a linha, antes de esvaziar a Lixeira.

## No repositório

- `.gitignore`: `.smart-env/` (o índice do Obsidian Smart Connections) e `.codex-remote-attachments/` (os anexos do
  Codex) ficam fora do Git. Nada deles foi apagado.
- A cópia `.txt` do diagnóstico de 20/10 sai.

## Aceitação

- **Cada item conferido:** saiu do lugar e está na Lixeira, que cresceu os 12,8 GiB da lista.
- **O reordenador:** carrega da pasta padrão e ordena certo uma frase relevante e uma sem relação.
- **A bateria rápida:** passando.
- **Os testes com os dados reais:** não rodaram, porque `data/gpvs` e `data/resultados` não foram tocados.
