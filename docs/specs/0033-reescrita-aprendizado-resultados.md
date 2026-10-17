# Lote 33 — reescrita seletiva, plano por partes, aprendizado com o uso e vocabulário dos resultados

Proposto em 17/10/2026, com as decisões do pesquisador nas perguntas e respostas de 16 e 17/10/2026, e aprovado
por ele no mesmo dia ("Aprovo a spec 0033. Pode começar a implementação do lote 33.").
Continua a 0.5.0, sobre o lote 32, que ainda não tem commit. O que ficou fora do lote 32 entra aqui,
junto com o plano por partes que foi acrescentado ao código em 05/10, depois da validação do lote 32,
sem spec nem testes.

## Ponto de partida (medido em 16/10/2026, sem tokens)

- **Plano por partes de 05/10** (`knowledge/coverage.py` e trechos de `rewrite.py`, `agent.py`, `app.py` e
  `app.js`): divide o pedido em partes, busca cada uma, confere se cada parte recebeu citação e faz uma
  segunda chamada para as que ficaram sem. Responde a uma falha real de 05/10: "uma fonte para cada um"
  (MCC, FMEA e FMECA) saiu só com a MCC, por uma página de uma resposta antiga, sem nova busca.
  Problemas: pede o plano a toda pergunta à biblioteca (até 2.048 tokens de saída, contra 512); impõe um
  título por parte a toda resposta da biblioteca; desfez o atalho das trilhas do lote 31; sobe outra vez
  no mesmo degrau quando uma pergunta simples, já lida por páginas, sai sem citação; não tem testes.
  A suíte tem 737 testes que passam e 2 que falham por causa dele (trilha e texto da rota na página).
- **Roteador:** de 10 perguntas sobre os resultados escritas de outro jeito, reconheceu 5. "Qual componente
  tem a maior criticidade?" foi tratada como conversa, sem os resultados. Nas 58 mensagens reais, três
  conversas soltas depois de uma resposta da biblioteca foram à biblioteca com o modelo maior
  ("Cara, como você tá tão sabido assim? kkkkk").
- **Reescrita:** cerca de 580 tokens por pergunta à biblioteca, no modelo menor, contra 5 a 16 mil da
  resposta (4% a 10%). Dispensá-la poupa pouco; o risco é perder o assunto da conversa.

## Decisões do pesquisador

1. O plano por partes de 05/10 é adotado e corrigido neste lote.
2. A segunda chamada para as partes sem citação é automática, só dentro do teto de 30 mil tokens e antes
   do aviso diário de 300 mil; a tela mostra. Fora disso, pede confirmação, como hoje.
3. O aprendizado usa dois sinais: as escolhas feitas na tela e as perguntas refeitas ou reclamações.
   Não haverá uma lista nova para revisar o que foi aprendido.
4. Teste pago no fim do lote: até 8 chamadas e 80 mil tokens de entrada, contados antes de cada chamada.

## Escopo

1. **Reescrita seletiva**, decidida localmente antes de qualquer chamada:
   - sem reescrita quando a mensagem já diz o assunto: tem ao menos dois termos de assunto (sem as palavras
     do pedido, como "traga", "literatura", "fonte") e não depende da conversa;
   - reescrita simples, como antes do plano, quando depende da conversa ("isso", "outra fonte",
     "e o segundo?", mensagem curta depois de uma resposta da biblioteca);
   - plano por partes só quando há partes: lista ("MCC, FMEA e FMECA"), comparação ou "cada um"/"os dois".
   - A busca e a reordenação locais usam a pergunta original quando não há reescrita.
2. **Plano por partes corrigido:**
   - busca por parte e conferência por parte continuam;
   - a regra de um título por parte só vai ao modelo quando há duas partes ou mais;
   - a segunda chamada só acontece se houver algo novo a ler: partes sem citação que tiveram candidatos
     na busca e não foram enviadas; uma pergunta de uma só parte sobe só a partir dos trechos, como no
     lote 31; uma parte sem nenhum candidato na busca não gera segunda chamada;
   - o botão "Completar pesquisa" fica só para quando a segunda chamada pedir confirmação.
3. **Trilhas do lote 31 de volta, com um limite:** a pergunta muito parecida com uma já respondida volta a
   partir das páginas daquela resposta, sem nova busca, só quando tem uma parte e a resposta anterior ficou
   completa. Com mais partes, as páginas da trilha só apoiam a nova busca. O texto da rota volta a dizer
   "partiu de uma resposta anterior" quando houve o atalho.
4. **Aprendizado com o uso, local e sem tokens:**
   - **Escolhas na tela:** quando o pesquisador fixa o modelo, a leitura ou a skill e a escolha difere da
     automática, ou clica em "Ler mais fundo", a mensagem e a escolha ficam guardadas em `data/memoria/`.
     Uma mensagem nova muito parecida com uma guardada recebe a mesma escolha, dentro dos limites de tokens,
     e a rota diz "aprendido com uma escolha sua de dd/mm".
   - **Pergunta refeita ou reclamação** ("você não conseguiu", "faltou", "não é isso"): a trilha daquela
     resposta perde força (não serve de atalho) e a mensagem anterior fica guardada com o degrau seguinte.
     A reclamação é tratada como pedido de leitura mais funda da pergunta anterior.
   - **Conversa solta** depois de uma resposta da biblioteca só volta à biblioteca se tiver termos de assunto
     ou referência à resposta ("isso", "a segunda fonte").
5. **Vocabulário dos resultados:** os nomes que o roteador reconhece como resultados da pesquisa vêm dos
   próprios resultados montados para o chat (modelos, métricas, falhas, componentes, grupos e FMECA),
   além de frases de exemplo novas. Sem os resultados na pasta, valem as palavras de hoje.

## Arquivos

- `routing.py` e `routing_examples.py`: vocabulário dos resultados, conversa solta, reclamação e escolhas
  aprendidas.
- `knowledge/rewrite.py` e `knowledge/coverage.py`: decisão local da reescrita e plano só com partes.
- `agent.py` e `interfaces/web/app.py`: regra de títulos, segunda chamada, trilhas e registro das escolhas.
- `memory/store.py` (ou módulo novo ao lado): escolhas aprendidas e trilhas enfraquecidas.
- `interfaces/web/static/app.js`: texto da rota e nota do aprendizado.
- Testes novos (`test_coverage.py`, `test_routing.py`, `test_web.py`), changelog, roteiro, AGENTS.md e novo
  registro em `docs/migracao/`. Os mapas de arquitetura de 05/10 ficam como estão.

## Validação e limites

- Testes sem rede para o plano, a reescrita seletiva, a segunda chamada, as trilhas e o aprendizado; os dois
  testes que hoje falham voltam a passar. Suíte completa e Ruff.
- Medições sem tokens, com perguntas escritas antes da mudança:
  - 10 perguntas novas sobre os resultados, escritas de outro jeito: meta de 9 ou mais reconhecidas;
  - as 58 mensagens reais: nenhuma conversa solta enviada à biblioteca, e as rotas de hoje mantidas nas demais;
  - perguntas reais que dispensam a reescrita: a busca local pela pergunta traz o documento que a consulta
    reescrita trazia;
  - o pedido de 05/10 ("MCC, FMEA e FMECA" e depois "uma fonte para cada um") sai com três partes.
- Teste pago: até 8 chamadas e 80 mil tokens de entrada, com o plano por partes, a continuação "cada um",
  a segunda chamada e uma pergunta sem reescrita. O roteiro conta antes de cada chamada e para no limite.
  Sem leitura ampla nem envio ao serviço de arquivos do Google.
- Os limites de 30 mil por leitura e o aviso em 300 mil por dia não mudam. A leitura ampla continua só
  por escolha na tela.
- O aprendizado só usa dados locais; não há treino de rede nem envio das mensagens a um serviço.
- Sem commit, push, publicação ou alteração dos manifestos anteriores. Como os lotes 32 e 33 tocam os
  mesmos arquivos, o commit sugerido é um só para os dois. A versão continua 0.5.0.
