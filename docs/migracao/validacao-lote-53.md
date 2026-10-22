# Validação do lote 53 — o mestrado da rodada ao chat em pastas

Data: 22/10/2026. Escopo na [spec 0053](../specs/0053-mestrado-da-rodada-ao-chat.md). Commits locais autorizados pelo
pesquisador no plano de 21/10; o push e a tag ficam com ele.

## Os dois commits

| Commit | O que fez | Bateria completa |
|---|---|---|
| ff65950 (mudança de lugar) | os 7 arquivos restantes do mestrado nas pastas novas, com as importações no lugar novo | 837 testes passando, 198,3 s, 18 treinos |
| o seguinte (divisão) | `rodada/` (5 arquivos), `resultados/` (2); os apelidos antigos trocados; o teste do contrato | 838 testes passando, 196,0 s, 18 treinos |

**O Git seguiu os 7 arquivos**, com 94% a 100% de semelhança.

## Conferências

| Conferência | Resultado |
|---|---|
| Equivalência contra a referência do lote 49 | 28 de 28 arquivos iguais |
| O contrato do experimento: os 14 atributos em `rodada/experimento.py` | teste novo passando |
| Toda importação de `aliado…` resolve | sim |
| Pastas vazias ou só com `__pycache__` | nenhuma |
| Caminhos antigos fora dos registros | nenhum |
| Os comandos e o PDF do experimento, numa cópia dos resultados | saída 0 |
| O wheel de uma cópia limpa | 144 arquivos `.py` presentes; 142 módulos importados do próprio wheel, sem erro |
| O pacote do mestrado, o terminal e a interface abrem sem numpy nem PyTorch | sim |
| NUC-01, NUC-02, NUC-04 e Ruff | passando |

## O que a conferência pegou no caminho

- **O apelido sozinho:** usos como `(autoencoders,)`, `experiment is autoencoders`, `getattr(summary, ...)` e
  `monkeypatch.setattr(digest, ...)` foram trocados à mão. Renomear às cegas trocaria também variáveis locais com o
  mesmo nome.
- **O código de teste num processo separado:** o reescritor trocou `digest.build_digest` dentro do texto do teste sem
  numpy, mas a importação no mesmo texto ainda dizia `as digest`. O subprocesso falharia. A importação do texto foi
  corrigida antes da bateria, que passou.

## A reorganização das pastas está completa

Os lotes 49 a 53 levaram a ciência geral e o mestrado para pastas com nomes em português, uma por etapa. Nenhum
número mudou: a equivalência no GPVS sintético e os testes com os dados reais passaram depois de cada commit.
