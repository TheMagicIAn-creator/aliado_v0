# Workflow: lançamento de versão

**Quando usar:** o pesquisador pede para fechar uma versão. Segue o [WORKFLOW.md](../WORKFLOW.md).
O último exemplo completo é a [spec 0064](../docs/specs/0064-lancamento-0-9-2.md) (0.9.2).

## Decisões a perguntar

- **O número da versão.** Pelo versionamento semântico, uma função nova pede a versão do meio (0.10.0);
  só correção, a última (0.9.3). Apresente a sugestão e o motivo; quem escolhe é o pesquisador.
- **O que entra:** os commits desde a última tag. Trabalho sem commit não entra sem ser commitado antes.

## Passos

1. **Spec do lançamento** `docs/specs/00NN-lancamento-X-Y-Z.md`: o pedido, o que entra, a versão escolhida.
2. **Versão** em `pyproject.toml`; reinstale o pacote sem downloads.
3. **CHANGELOG:** a seção não lançada vira a seção da versão. **README:** versão e o que mudou para quem usa.
   **Roteiro:** a linha do lote.
4. **Pacote:** monte o wheel numa cópia limpa dos arquivos versionados, pelo bloco do README, em
   `dist/vX.Y.Z/`; anote o tamanho e o SHA-256.
5. **Notas da versão** em `tmp/releases/vX.Y.Z.md`.

## Verificação

- A bateria completa, com os testes dos dados reais (`ferramentas/bateria.py`).
- A equivalência da ciência sem diferença (`ferramentas/equivalencia.py`).
- O Ruff, as importações fora de `src` e o conteúdo do wheel.

## Entrega — com o pesquisador

O commit, a tag, o push e a release no GitHub são do pesquisador (o hook bloqueia o push do assistente).
Mostre os comandos, um por linha, com a mensagem de commit e o hash do wheel para conferir na release.
