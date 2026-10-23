# Spec 0060 — o fechamento da 0.9.0

Estado: feito em 23/10/2026, sem commit; o commit, a tag `v0.9.0` e o push ficam com o pesquisador.

## Propósito e decisões

O pesquisador pediu "Finaliza" depois do lote 59 e aprovou o plano do fechamento em 23/10/2026. A aprovação valeu
como o OK para a bateria com os dados reais.

**A 0.9.0 reúne o que veio depois da tag `v0.8.0`** (6770061, de 21/10): os lotes 45 a 59 e este fechamento.
- **Lotes 45 a 48:** as correções do relatório de eficiência, o roteador e o raciocínio desligado nas leituras.
- **Lotes 49 a 53:** a ciência e o mestrado em pastas.
- **Lotes 54 e 55:** o contrato da rodada e a evidência espectral.
- **Lotes 56 a 59:** as duplicatas, as regras sem o exemplo, o cache q4_0 e a limpeza.

**O que muda:**
- `pyproject.toml`: de 0.8.0 para 0.9.0. O pacote foi reinstalado, sem baixar nada, e as rodadas novas gravam 0.9.0.
- **O CHANGELOG:**
  - a seção 0.9.0, datada de 23/10, com a abertura;
  - a 0.8.0 passa a ter a data do commit da tag (21/10), no lugar de "em fechamento local";
  - as linhas de estado dos lotes 58 e 59 passam a citar os commits deles.
- **O README:** a versão, a 0.9.0 na história das versões e o comando do pacote, que passa a gravar em
  `dist/v0.9.0`.
- **O roteiro:** a linha, as decisões e a spec do lote.
- **`ferramentas/equivalencia.py`:** passa a esconder também a data curta entre parênteses (`meio (22/10)`), com dia e
  mês válidos.
  - **A falha que ela tinha:** foi a primeira comparação feita em outro dia que não o da referência. A data curta da
    rodada, no relatório do início das falhas, aparecia como diferença.
  - **O que ela continua mostrando:** frações como `(13/16)` e `103/104` e a data fixa `27/09`.

**Nenhum requisito muda.**

## O pacote

- **O arquivo:** `dist/v0.9.0/aliado-0.9.0-py3-none-any.whl`, com 899.358 bytes.
- **SHA-256:** `ab2025b1eb978dad2c8a46c4c480408a09b9479d01c431df7bfea214aabcee2d`.
- **Como foi montado:** numa cópia limpa dos arquivos versionados (`tmp/verificar.py`), com
  `build --wheel --no-isolation`, sem downloads.
- **O conteúdo:** 197 arquivos, com os 156 módulos `.py` do pacote. Importado fora de `src`, sem erro.
- **As notas da versão:** `tmp/releases/v0.9.0.md`, com os links para a tag.

## Aceitação

- **A bateria completa,** com os testes com os dados reais.
- **A equivalência sem diferença,** e o autoteste da ferramenta, depois do ajuste.
- **As conferências extras:** as importações, as pastas, os comandos e o wheel.
- **A seleção rápida do pedido de 22/10, o Ruff e o `git diff --check`.**
- **A versão instalada:** 0.9.0.

Os números estão na [validação](../migracao/validacao-lote-60.md).
