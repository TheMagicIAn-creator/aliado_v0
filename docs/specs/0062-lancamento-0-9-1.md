# Spec 0062 — o lançamento da 0.9.1

Estado: feito em 23/10/2026. O commit, a tag `v0.9.1`, o push e a release foram autorizados pelo pesquisador.

## Propósito e decisões

**O pedido:** "Faça. Não deixe nada pendente."

**O que entra:** o lote 61 (6cc1001), a forma abreviada do intervalo de páginas nas citações (BIB-05). Era a única
mudança fora de uma versão publicada.
- **A versão:** é uma correção que não muda nenhuma interface, então, pelo versionamento semântico, vira 0.9.1.
- **O método:** o mesmo do fechamento da 0.9.0 (lote 60).

**O que muda:**
- `pyproject.toml` passa a 0.9.1, e o pacote é reinstalado sem downloads;
- o CHANGELOG ganha a seção 0.9.1;
- o README e o roteiro são atualizados.

**Nenhum requisito muda.**

## O pacote

- **O arquivo:** `dist/v0.9.1/aliado-0.9.1-py3-none-any.whl`, com 899.427 bytes.
- **SHA-256:** `3d546b1fb17905f0c73ee9579f5b39764b8144a845b29df56b9528a460bd0485`.
- **Como foi montado:** numa cópia limpa dos arquivos versionados (`tmp/verificar.py`).
- **O conteúdo:** 197 arquivos, com os 156 módulos `.py`. Importado fora de `src`, sem erro.
- **As notas da versão:** `tmp/releases/v0.9.1.md`.

## Aceitação

- **A bateria completa,** com os testes com os dados reais.
- **A equivalência da ciência, sem diferença.**
- **As conferências extras:** as importações, as pastas, os comandos e o wheel.
- **A seleção rápida do pedido de 22/10 e o Ruff.**
- **A publicação:** a tag e a release no GitHub, com o mesmo hash do wheel.

Os números estão na [validação](../migracao/validacao-lote-62.md).
