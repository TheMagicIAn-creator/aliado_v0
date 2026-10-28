# Workflow do desenvolvimento

O caminho de todo pedido de desenvolvimento do AL-IAdo, do Claude Code ou do Codex. O pesquisador
diz o resultado que quer; o assistente conduz as etapas, mantém specs e registros e entrega o
resultado verificado. O pesquisador não cria nem administra lotes.

As regras de custo, dados e Git estão no [AGENTS.md](AGENTS.md). Os passos próprios de cada tipo de
pedido estão em [workflows/](workflows/), conforme a tabela do [CLAUDE.md](CLAUDE.md).

## 1. Entender

- Leia o pedido e o [ESTADO.md](ESTADO.md). Veja `git status --short` e as diferenças dos arquivos que
  vai tocar: o que já estava alterado é trabalho anterior, a preservar.
- Leia as specs vivas da capacidade envolvida (`docs/specs/capacidades/`) e o código que o pedido toca.
- Defina o resultado observável: o que o pesquisador vai ver quando estiver pronto.

## 2. Planejar — e esperar a aprovação

- Apresente um plano curto: objetivo, arquivos, como verificar. Mudança de mais de um arquivo usa o
  modo de planejamento do Claude Code.
- Pergunte só o que é decisão do pesquisador: comportamento esperado, prioridade, custo, dados reais.
  Cada pergunta curta, com o efeito de cada resposta. A resposta dada é a decisão.
- Enquanto espera, avance só no que não depende da resposta. Sem aprovação, nada é editado; se o pedido já
  autoriza a direção, siga dentro dele e pergunte só o que faltar.

## 3. Implementar

- A menor mudança que cumpre o pedido, no padrão do código ao redor. Nada de extra "para depois".
- Comportamento novo ou alterado ganha spec de mudança, spec viva e teste
  ([mudança de comportamento](workflows/mudanca-de-comportamento.md)). Mudança só nas instruções dos
  assistentes não ganha spec de produto.
- Investigação larga pode ir a um subagente de leitura; quem escreve num arquivo é um só por vez.

## 4. Verificar

- Rode os testes do que mudou e, no fim, a bateria e o Ruff:
  `.venv/Scripts/python.exe -m pytest` e `.venv/Scripts/python.exe -m ruff check .`.
- Registre comando e resultado. Separe falha antiga de regressão nova, com evidência.
- Falhou: corrija dentro do pedido e verifique de novo. Se a correção pedir outra decisão, pare e pergunte.
  Nunca enfraqueça um teste para ele passar.
- Teste simulado não valida o modelo real; medir o modelo real é a
  [bateria do modelo local](workflows/bateria-modelo-local.md), com autorização.

## 5. Revisar

- Peça ao subagente `revisor` (só leitura) que confronte o diff com o pedido, as specs e os testes.
- Avalie cada apontamento; corrija o que for defeito e mande o trecho corrigido de volta para conferência.
- Sem subagente disponível, diga na entrega que não houve revisão independente.

## 6. Entregar

- Atualize specs, roteiro e o [ESTADO.md](ESTADO.md).
- Apresente em poucas linhas: o que mudou e onde, o que foi verificado e o resultado, o que ficou de fora.
- Mostre os comandos de commit com os caminhos deste pedido, sem incluir trabalho anterior de outro pedido.
  O commit é do pesquisador.
- Pergunte qual é o próximo passo. Não escolha outro objetivo por conta própria.

## Retomar

- O [ESTADO.md](ESTADO.md) diz o que estava em andamento e a próxima ação. Confira com os arquivos e o Git
  antes de continuar: o estado é um registro, não uma prova nem uma autorização.
- Uma autorização citada no estado (modelo real, dados, Git) vale só se estiver na conversa atual;
  se não estiver, pergunte.
- Antes de reescrever o estado de outro pedido, leve o que importa dele para a spec, o roteiro ou o relatório.

## Melhorar o workflow

Quando algo der errado ou o pesquisador corrigir o rumo, ajuste o workflow que falhou, no mesmo pedido,
e diga na entrega o que mudou. Tipo de pedido que se repete ganha um arquivo novo em `workflows/`.

## Erros que já aconteceram aqui

- Uma medição rodou e não foi registrada: a spec continuou dizendo que ela não tinha rodado (lote 70).
- Um teste simulado foi tratado como validação do modelo real.
- Uma instrução nova no prompt causou regressão, e a correção não foi medida de novo (lote 67).
- Um registro de estado foi sobrescrito sem guardar o anterior (26/10).
- Um comando Git foi junto com um script de várias linhas, e o hook, sem conseguir analisá-lo, bloqueou.

## Origem

Inspirado em [How to Build an AI Agent with Claude Code](https://www.youtube.com/watch?v=bcM9dP_uXJU)
(AI Master): o `CLAUDE.md` como peça central, planejar antes de agir e um workflow em arquivo para cada
tarefa que se repete, melhorado a cada uso. Foram consultados o título, a descrição e os capítulos; a
transcrição e o material do autor não estavam acessíveis, então os detalhes são adaptações ao AL-IAdo.
