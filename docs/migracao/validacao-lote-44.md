# Validação do lote 44 - revisão e fechamento da 0.8.0

Data: 20/10/2026. Escopo na [spec 0044](../specs/0044-revisao-fechamento.md). Validado localmente; aguardando revisão
e commit do pesquisador. Nenhuma chamada a modelos de linguagem reais, download ou reindexação da biblioteca real.

## Regressões

Antes das correções, os cinco testes pytest novos falharam: o teste JavaScript encontrou as sete falhas de
concorrência iniciais; dois casos mostraram o modelo menor repetido na escalada e dois mostraram tentativa
indevida ou motivo ausente na falta/falha do Flash. Após as correções, os cinco passaram na bateria completa.
Na revisão adicional, três cenários passaram a cobrir o histórico durante a abertura e as alterações de fixados
durante o primeiro PATCH. O teste integrado da biblioteca foi ajustado para usar uma descrição distinta por página,
sem confundir a deduplicação correta da busca com perda da descrição.

## Registros anteriores preservados

Os registros 35/36 foram recolocados exatamente como no commit `77fb76d`. Os adendos posteriores feitos no trabalho
anterior de Claude são preservados aqui como histórico; seus números não substituem a conferência atual.

- Em 18/10, seis PDFs anexados e a mensagem "Opa" deixaram só um fixado; os outros terminaram na biblioteca sem
  conversa. O servidor passou a fixar o anexo no destino do envio, a apresentação passou a criar a conversa,
  o painel passou a mostrar envios novos primeiro e os avisos deixaram de pedir a chave "Usar biblioteca".
  O relato anterior registra conferência por interface, fixação única, conversa apagada e envio pelo painel.
- Em 18/10, o pesquisador criou uma rodada com separação de 22 janelas, a sexta consulta ao teste. Quatro testes
  dependiam da rodada atual ao conferir números de 27/09. A fixture `official_results` passou a usar uma cópia
  só da avaliação, treino e reanálise históricos; a rodada real foi preservada.
- A entrega original do lote 36 registra 786 testes em 195,1 s e wheel com 111 arquivos, SHA-256
  `b920d7d67a8605063316d6df87b453afec062502aa8c4ca6615f1a77678d9edb`.
- O adendo posterior de Claude registra 787 testes em 185,9 s e wheel reconstruído com SHA-256
  `7c00478ccdc13a1f6f62952f3f1fb161ac7c6fb5502c6c48eeff4753154c6ea0`. Este é um relato posterior, não o hash da entrega original.
- As medições dos lotes 38 a 43 usaram o modelo local real e Gemini simulado, em cópias da biblioteca. As contagens
  de encaminhamentos ao Gemini nessas medições não representam chamadas pagas nem avaliação das respostas dele.

## Conferência final

A bateria completa foi executada em processos separados por arquivo para limitar a memória.

| Conferência | Resultado |
|---|---|
| Pytest, 46 arquivos | **814 passaram, 0 falharam, 0 ignorados**, em 242.59 s |
| JavaScript real, com I/O simulado | **13 cenários passaram**, incluídos no teste de interface do pytest |
| Ruff, sem reescrita | sem apontamentos |
| `git diff --check` e sintaxe do JavaScript | sem apontamentos |
| Specs vivas e isolamento do núcleo | testes aprovados na bateria completa |
| Registros originais 35/36 | quatro arquivos idênticos ao commit `77fb76d` |
| Wheel de fontes limpos | 112 arquivos, 107 do pacote; conteúdo idêntico aos fontes |
| Importação do wheel fora de `src` | skills, CLI especializado, interface web e provedor local aprovados |

Os testes registram o aviso de descontinuação de `anyio.abc.BlockingPortal`, vindo do Starlette instalado.
Ele não é uma falha do lote. Os testes científicos gravam resultados e consultas em pastas temporárias;
os resultados reais do pesquisador são preservados.

A execução e os logs completos estão em `tmp/lote-44/pytest.json` e nos arquivos `.log` ao lado.
O teste JavaScript usa Node nativo, sem instalar dependências. Sem Node, o pytest o marca como ignorado;
nenhum teste foi ignorado nesta conferência.

## Pacote final

- Arquivo: `dist/v0.8.0-fechamento/aliado-0.8.0-py3-none-any.whl` (839,421 bytes).
- SHA-256: `47d1076c09868f9fdaeb1463a225c0d27b3ce3f888947cebe49bb7223c922b20`.
- Cópia limpa usada: `tmp/lote-44/build-881e968b`; montagem com `build --wheel --no-isolation`, sem downloads.
- Conferência de conteúdo e teste de importação: `tmp/lote-44/wheel.json` e `tmp/lote-44/wheel-smoke.log`.
- O wheel anterior em `dist/v0.8.0/` foi preservado e continua com SHA-256
  `5c548dd35421fd25871b997f0bcf5854652f944d9a36d15bcd164a7d08cad821`.

## Arquivos para revisão e commit

A lista explícita está em `tmp/lote-44/arquivos-commit.txt`; os comandos para o pesquisador,
em `tmp/lote-44/comandos-commit.txt`. O manifesto do lote 44 também guarda a lista da entrega.
As configurações locais `.claude/launch.json`, `.claude/settings.local.json` e `.smart-env/` ficam fora dela.
Nenhum arquivo foi colocado no stage; nenhum commit, push, PR ou publicação foi executado.

## Limites da conferência

A correção foi validada com I/O simulado e documentos sintéticos; a interface usa as funções JavaScript reais em Node.
Não houve nova sessão visual no navegador nem nova avaliação das respostas do modelo local. As medições reais
anteriores continuam sendo as dos lotes 38 a 43. A reindexação da biblioteca real continua por pedido do pesquisador.
