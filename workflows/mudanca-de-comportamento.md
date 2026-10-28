# Workflow: mudança de comportamento

**Quando usar:** o AL-IAdo deve passar a fazer algo novo, ou fazer de outro jeito. Segue o
[WORKFLOW.md](../WORKFLOW.md); aqui estão os passos próprios deste tipo de pedido.

## Entradas

- O pedido e as decisões do pesquisador na conversa.
- A spec viva da capacidade (`docs/specs/capacidades/<capacidade>.md`) e os requisitos que mudam.
- O código e os testes que o pedido toca.

## Passos

1. **Ache o requisito.** Procure nas specs vivas o requisito atual (por exemplo, NUC-05). Se nenhum cobre
   o pedido, a mudança cria um requisito novo, com o próximo número livre da capacidade.
2. **Escreva a spec de mudança** `docs/specs/00NN-<assunto>.md`, com o próximo número livre:
   - propósito e decisões (quem decidiu e quando);
   - o que muda e o que fica igual;
   - os requisitos vivos acrescentados, alterados ou retirados;
   - aceitação: os testes e, se houver modelo real, a medição a fazer.
3. **Implemente** a menor mudança que cumpre a spec, no padrão do código ao redor.
4. **Teste:** pelo menos um teste por requisito novo ou alterado, citando o código dele (`NUC-05`) num
   comentário ou na docstring; `tests/test_specs.py` cobra a citação.
5. **Atualize a spec viva** com o texto novo do requisito e um cenário ("dado …, então …").
6. **Registre no roteiro** (`docs/roteiro-v0.md`): uma linha do lote, com a spec e o resultado.

## Verificação

- Os testes do que mudou, a bateria inteira e o Ruff.
- `tests/test_specs.py` e `tests/test_isolation.py` passam: requisito citado e núcleo sem nome de especialização.
- Se a mudança depende da resposta do modelo, diga que não foi medida e proponha a
  [bateria do modelo local](bateria-modelo-local.md).

## Saída

Spec de mudança, spec viva, código, testes e roteiro atualizados; resumo e comandos de commit.
