# Workflow: correção de defeito

**Quando usar:** algo funciona diferente do que a spec viva diz, ou quebra. Segue o
[WORKFLOW.md](../WORKFLOW.md). Se a correção mudar o comportamento descrito na spec, use também a
[mudança de comportamento](mudanca-de-comportamento.md).

## Passos

1. **Reproduza.** Escreva primeiro um teste que falha pelo motivo relatado, sem modelo real e sem os
   dados reais. Se não der para reproduzir, diga isso e mostre o que foi tentado antes de mudar código.
2. **Ache a causa.** Leia o caminho inteiro, não só a linha do erro. Procure todos os chamadores da
   função que vai mudar (`Grep` pelo nome) e os lugares que repetem a mesma regra.
3. **Corrija uma vez,** no ponto compartilhado. Uma regra escrita em dois lugares é um defeito esperando
   para voltar: se não der para unificar agora, registre.
4. **Confira o teste:** o que falhava passa, e os vizinhos continuam passando.
5. **Procure o mesmo defeito em outro lugar.** Exemplo: o lote 70 corrigiu o raciocínio do revisor de
   memória, e as fichas tinham o mesmo problema.

## Verificação

- O teste novo falhava antes da correção e passa depois.
- A bateria inteira e o Ruff.
- Defeito que só aparece com o modelo real: corrija o que dá para provar com teste e proponha a
  [bateria do modelo local](bateria-modelo-local.md) para o resto.

## Saída

A causa em uma frase, a correção, o teste que a prova e o que ficou de fora.
