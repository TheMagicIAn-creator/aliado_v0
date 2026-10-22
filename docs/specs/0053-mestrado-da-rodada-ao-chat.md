# Spec 0053 — o mestrado da rodada ao chat em pastas

Estado: feito em 22/10/2026, com commits locais autorizados pelo pesquisador no plano de 21/10; push e tag ficam com
ele.

## Propósito e decisões

A última parte do mestrado em pastas com nomes em português:
- `rodada/`: o experimento;
- `resultados/`: a rodada atual e os painéis;
- `resumo_para_o_chat/`: os blocos [R1]…[R8];
- `exploradores/`, `tela/`, `roteamento/` e `glossario/`.

Com ela, nenhum arquivo de código fica solto na raiz do mestrado: só o `__init__.py`, que é o contrato com o núcleo.

**Decisões do plano de 21/10 e da revisão:**
- **A rodada:**
  - `declaracao.py` guarda as constantes, para quem precisa delas não importar a rodada inteira e para evitar a
    importação circular com os resultados;
  - `experimento.py` é o módulo que o núcleo lê: os 14 atributos do contrato, reunidos dos arquivos da pasta.
- **A pasta oficial:** o experimento e os resultados passaram a ler o nome dela de `avaliacao/oficial.py`. É o único
  lugar onde está escrito.
- **A tela:** continua despachando os painéis pelo nome da função, agora em `resultados/paineis.py`.

## Requisitos vivos

- **EXP-01:** o texto não muda. O "Onde está" de `experimentos.md` passa a citar `rodada/`, e um teste novo exige os
  14 atributos do contrato.

## Implementação

**Dois commits, para o Git seguir o histórico:**
1. **A mudança de lugar** (ff65950):
   - `autoencoders.py` → `rodada/experimento.py`;
   - `summary.py` → `resultados/paineis.py`;
   - `digest.py` → `resumo_para_o_chat/blocos.py`;
   - `explorer.py` → `exploradores/explorador.py`;
   - `web.py` → `tela/rotas.py`;
   - `routing.py` → `roteamento/frases.py`;
   - `notes.py` → `glossario/notas.py`.
2. **A divisão:**

| Pasta | Arquivos | O que tem |
|---|---|---|
| `rodada/` | `declaracao.py` | a chave, o título, a base, a descrição, os parâmetros da tela, as etapas e a avaliação oficial |
| `rodada/` | `execucao.py` | `missing`, `consultations`, `interrupted` e `run` |
| `rodada/` | `consolidacao.py` | `legacy`, `collect`, `numbers`, `command` e `parameter_texts` |
| `rodada/` | `apresentacao.py` | `report` (os blocos do PDF) |
| `rodada/` | `experimento.py` | o contrato: os 14 atributos |
| `resultados/` | `rodada_atual.py` | `Run`, `current` e `label` |
| `resultados/` | `paineis.py` | `overview`, `per_fault`, `score_panels` e `onsets` |

**As chamadas:** os apelidos antigos (`autoencoders`, `summary` e `digest`) viraram os nomes dos módulos novos.

**Correções:**
- a explicação do explorador, que ainda falava do explorador de confiabilidade (ele está no núcleo);
- o código de teste que roda num processo separado, sem numpy, que importava o resumo pelo nome antigo.

## Aceitação

- A bateria completa passando, com os testes com os dados reais.
- A equivalência sem nenhuma diferença contra a referência do lote 49.
- NUC-01, NUC-02, NUC-04 e Ruff.
- O pacote do mestrado, o terminal e a interface abrindo sem numpy nem PyTorch.
- As conferências extras: importações, pastas, caminhos antigos, comandos e wheel.
