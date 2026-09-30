# Validação do lote 21 — GPVS pela interface e 0.2.0

Verificação local em **28/09/2026**, sobre o commit `4d38e19` (lote 20). **Nenhuma chamada paga.**
O assistente não fez commit do lote 21, push nem tag.

## Testes

`tests/test_gpvs_runs.py` traz 7 testes novos, sem rede. O executor do subprocesso é trocado
por um falso, que cria a pasta que o comando criaria:
- **Registro:** semeado com a consulta canônica de 27/09, sem gravar ao ler; recusa sem a frase; numera, só acrescenta eventos e recusa um estado final inválido.
- **Pastas:** sempre novas e numeradas (`gpvs-modelos-003` depois da 002).
- **Preparo e treino:** argumentos do terminal, `execucao.json`, a rodada canônica e a exploratória (sementes diferentes), e a recusa de sementes repetidas, separação fracionada e teto zero.
- **Avaliação:** frase ausente ou errada e treino inexistente recusados, sem gravar no registro; com a frase, recebe a consulta 2, `consulta.json` e a faixa de não canônica nos Resultados.
- **Uma etapa por vez e o cancelamento:** uma segunda etapa recebe 409. Cancelada, a avaliação fica "cancelada" no registro.
- **Resultados:** a avaliação canônica é identificada.
- **Com os dados reais:** o preparo pela interface, em subprocesso de verdade, gera o mesmo `relatorio.json` que o comando.

**369 testes passaram** (362 do lote 20 e 7 novos), o Ruff não apontou problemas e `app.js` e
`ciencia.js` passaram na checagem de sintaxe, no Python 3.12.14.

**Falha intermitente, não resolvida.** Numa das 5 rodadas completas da suíte, 1 teste falhou.
Aquela rodada não listava os nomes das falhas, e o teste não foi identificado. A falha não se
repetiu em 3 rodadas completas seguidas, com a lista de falhas ligada, nem em 15 rodadas dos testes
dos lotes 20 e 21. O candidato mais provável é um teste com prazo curto sob carga, como o envio de
documento em `tests/test_web.py`, que espera no máximo 2,5 s. Nenhum teste foi alterado sem
evidência; se a falha voltar, o nome deve ser registrado.

## Aceite no navegador

Interface de teste em `127.0.0.1:8770`:
- os resultados numa **cópia** de `data/resultados`, em `tmp/lote-21/resultados`;
- os dados reais do GPVS, só para leitura.

| Etapa | Resultado |
|---|---|
| Abertura | Cartões com a configuração canônica (separação 11, sementes 13,29,42,71,101, teto 2.000) e o selo "configuração canônica". As rodadas 001 (exploratória) e 002 (canônica) aparecem, e o registro mostra a consulta 1 de 27/09 sem ter gravado o arquivo. |
| Preparar | `gpvs-preparo-001` em 0,7 s, com o link para os Resultados. |
| Cancelar | Um treino cancelado aos 6 s ficou "cancelado". A pasta não foi criada, e nenhum processo de treino ficou vivo no Windows. |
| Treinar | `gpvs-modelos-003` em 107 s, com as 10 linhas de progresso. O hash da configuração é igual ao de `gpvs-modelos-002`, e **os 10 arquivos de pesos e os limiares são idênticos bit a bit**. `execucao.json` marca a configuração como canônica. |
| Avaliar | A janela do M14 anunciou a consulta nº 2 e só liberou o botão com a frase completa. Levou 5,2 s. **`metricas_por_ensaio.csv`, `relatorio.json` e os 480 vetores de escores são idênticos aos da `gpvs-avaliacao-001`**, e o hash da configuração da avaliação também. |
| Registro | Na cópia, 3 eventos: a consulta 1 (canônica, semeada), a 2 "iniciada" e a 2 "concluída", não canônica. A pasta ganhou `consulta.json`. |
| Resultados | A 002 aparece como "não canônica, consulta nº 2" e a 001 como canônica. A 003 aparece como "treino com a configuração canônica" e a 001 dos modelos como exploratória. O preparo é reconhecido, e as rodadas pela interface mostram início e fim. |
| Tela estreita | Com 319 px, nenhuma das 6 seções rola para os lados, depois da correção abaixo. |
| Console | Sem erros, e o servidor não registrou erros. |

**Os resultados reais não mudaram.** Comparada com `data/resultados`, a cópia só tem a mais as três
pastas do aceite e o registro. O registro real não foi criado.

## Defeitos encontrados e corrigidos

1. **Rolagem lateral em telas estreitas**, que vinha do lote 20.
   - Os cartões da seção Rodar pediam 240 px, e os gráficos lado a lado da FMECA, 300 px.
   - As grades passaram a `minmax(min(…, 100%), 1fr)`, e as saídas da aba, a uma coluna `minmax(0, 1fr)`, para as tabelas rolarem dentro da própria caixa.
2. **Estados sem acento na tela** ("concluida" e "concluido"). Passaram a "concluída" e "concluído".

## Pacote 0.2.0

- **Arquivo:** `dist/v0.2.0/aliado-0.2.0-py3-none-any.whl`, 83 arquivos, 524 kB, SHA-256 `175d7d8c57bd6256480c1547111ff8d71a4c818b3b591fd39c1711fff7915933`.
- **Conteúdo:**
  - todos os módulos novos dos lotes 18 a 21 (`ciencia.js`, `gpvs_runs.py`, `science.py`, `explorer.py`, `registry.py`, `metadata.py`, `stopwords.py` e `knowledge/evaluation.py`);
  - nada de testes, documentação ou dados;
  - nenhuma sobra de build antigo.
- **Teste fora do projeto:** instalado com `--target` numa pasta separada e usado a partir de outra pasta. O código carregado veio do pacote, e a versão lida foi 0.2.0.
  - `aliado skills` listou as 3 skills, e `aliado ciencia fmeca` gerou o relatório.
  - A interface respondeu 200 em `/`, `app.js`, `ciencia.js`, `app.css`, `/api/ciencia`, `/api/ciencia/gpvs` e `/api/ciencia/fmeca`.

## Estado final

- `.claude/launch.json` ganhou a entrada `aliado-web-lote-21` para o servidor de teste.
- `tmp/lote-21` guarda a cópia dos resultados, o aceite e o pacote extraído, e pode ser apagada depois da revisão.
- **Com o pesquisador:** o commit do lote 21, a tag `v0.2.0` e o push.
