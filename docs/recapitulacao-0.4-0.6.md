# Recapitulação das versões 0.4.0, 0.5.0 e 0.6.0

Escrita em 17/10/2026. Diz o que cada versão trouxe e onde está cada uma. Os detalhes estão no
[CHANGELOG](../CHANGELOG.md) e nas specs de cada lote.

## O que cada versão trouxe

| Versão | Lotes | Em poucas palavras |
|---|---|---|
| 0.4.0 (03/10) | 27–29 | **Envios:** aviso no canto da tela, com as etapas de cada documento. **Respostas com várias fontes.** **Obsidian:** espelho das conversas e documentos para ver no grafo. **Indexação:** figuras e tabelas descritas pelo modelo, com os trechos cortados por frase. |
| 0.5.0 (04/10) | 30–31 | **Leitura:** páginas e documentos inteiros. **Documentos fixados na conversa.** **Escolha automática:** um roteador local escolhe modelo, skill e leitura antes de gastar. **Limites:** pergunta acima de 30 mil tokens e aviso diário em 300 mil. |
| 0.6.0 (17/10) | 32–33 | **Busca:** em memória (de 3,3 s para 0,08 s) e com reordenação local das páginas. **Revisor de memória seletivo.** **Reescrita:** só quando precisa. **Plano por partes.** **Aprendizado com o uso**, local e sem tokens. **Resultados:** perguntas reconhecidas em 9 de 10. |

A 0.4.1 foi preparada no lote 30 e não foi lançada: o padrão dela lia até 400 mil tokens por pergunta.

## Onde está cada uma

| Versão | Commit | No GitHub | Tag | Release | Pacote |
|---|---|---|---|---|---|
| 0.4.0 | `85dce50` | sim | `v0.4.0` (sem descrição) | **falta** | `dist/v0.4.0` |
| 0.5.0 | `98be273` | **falta o push** | **falta** | **falta** | `dist/v0.5.0`, igual ao commit |
| 0.6.0 | **falta o commit** | **falta o push** | **falta** | **falta** | `dist/v0.6.0` |

- **Os commits da 0.4.0 e da 0.5.0 estão com a sua identidade no Git.** As sessões anteriores deixaram os comandos de
  tag e de push com o botão "Run", e é provável que tenham sido executados por ele.
- **O pacote da 0.5.0 foi conferido em 17/10:** ele foi refeito a partir do commit `98be273` e tem o mesmo conteúdo
  de `dist/v0.5.0`, salvo as quebras de linha.
- **As notas de cada release** estão em `tmp/releases/v0.4.0.md`, `v0.5.0.md` e `v0.6.0.md`.

## Pendências antigas

- A conferência do espelho no Obsidian (lote 28).
- As pastas `tmp/lote-28` a `tmp/lote-33` e `dist/v0.4.1` só saem com o seu OK.
- O `.claude/launch.json` tem uma entrada para o servidor de teste do lote 33.
