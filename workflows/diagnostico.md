# Workflow: diagnóstico

**Quando usar:** o pesquisador pede para avaliar, revisar, levantar pendências ou procurar
inconsistências, sem pedir mudança de código. Segue o [WORKFLOW.md](../WORKFLOW.md).

## Passos

1. **Delimite.** Quais áreas, desde quando (último commit, último lote), e o que já foi analisado antes
   (`docs/revisao/`, `ESTADO.md`).
2. **Levante em paralelo.** Investigações independentes podem ir a subagentes de leitura, uma por área.
   O resultado deles é pista, não prova.
3. **Confira no código** cada achado antes de apresentá-lo. Descarte o falso alarme e diga por quê.
4. **Classifique** cada item:
   - implementado e testado;
   - implementado, sem medição com o modelo real;
   - medido e não registrado;
   - não implementado;
   - decisão pendente com o pesquisador.
5. **Escreva o relatório** `docs/revisao/AAAA-MM-DD-<assunto>.md`: o que foi visto, as evidências
   (arquivo e linha), a prioridade e a proposta de próximo passo para cada item.

## Limites

- Diagnóstico não muda código. Se o pesquisador pedir as correções no mesmo pedido, elas seguem a
  [correção de defeito](correcao-de-defeito.md) ou a [mudança de comportamento](mudanca-de-comportamento.md),
  depois do relatório.
- Ler dados reais (`data/`) só para responder ao que foi perguntado, sem copiar o conteúdo para o relatório.
- Nenhuma chamada a modelo real.

## Saída

O relatório datado e, na conversa, um resumo com as decisões que o pesquisador precisa tomar.
