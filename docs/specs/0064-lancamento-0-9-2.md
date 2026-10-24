# Spec 0064 — o lançamento da 0.9.2

Estado: feito em 24/10/2026. O commit, a tag `v0.9.2`, o push e a release foram autorizados pelo pesquisador.

## Propósito e decisões

**O pedido:** "lançar a 0.9.2 com o modo sem internet".

**O que entra:** o lote 63 (f920740 e 18eb983), o modo sem internet (PRV-08 e INT-02). Era a única mudança fora de
uma versão publicada.
- **A versão:** pelo versionamento semântico, uma função nova pediria 0.10.0. Perguntado, o pesquisador escolheu
  0.9.2: o modo só liga por pedido, e nada do que existia muda.
- **O método:** o mesmo da 0.9.1 (lote 62).
- **O push:** fica com o pesquisador, porque o hook do projeto bloqueia o do assistente.

**O que muda:**
- `pyproject.toml` passa a 0.9.2, e o pacote é reinstalado sem downloads;
- o CHANGELOG ganha a seção 0.9.2;
- o README e o roteiro são atualizados.

**Nenhum requisito muda.**

## O pacote

- **O arquivo:** `dist/v0.9.2/aliado-0.9.2-py3-none-any.whl`, com 900.524 bytes.
- **SHA-256:** `824e3b53a6113b8e801ebff9c8de87787293e523283c734a727b2830773c867a`.
- **Como foi montado:** numa cópia limpa dos arquivos versionados, pelo bloco do README.
- **O conteúdo:** 197 arquivos, com os 156 módulos `.py`. Importado fora de `src`, sem erro.
- **As notas da versão:** `tmp/releases/v0.9.2.md`.

## Aceitação

- **A bateria completa,** com os testes com os dados reais.
- **A equivalência da ciência, sem diferença.**
- **As conferências extras:** as importações, as pastas, os comandos e o wheel.
- **O Ruff.**
- **A publicação:** a tag e a release no GitHub, com o mesmo hash do wheel.

Os números estão na [validação](../migracao/validacao-lote-64.md).
