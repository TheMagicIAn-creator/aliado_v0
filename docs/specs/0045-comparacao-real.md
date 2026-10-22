# Spec 0045 — comparação real dos fluxos local e Gemini

Estado: ensaio real executado em 20/10/2026; aguarda revisão do pesquisador.

## Propósito e autorização

Medir as 16 perguntas aprovadas nos fluxos reais Ollama com escaladas normais e Gemini direto, com 32 respostas. O pesquisador autorizou até 96 chamadas, no máximo 64 ao Gemini, 1,2 milhão de tokens totais e 600 mil pagos, incluindo reescritas e escaladas. Os limites de confirmação das leituras continuaram ativos.

## Requisitos vivos

Nenhum requisito é acrescentado, alterado ou retirado. Trata-se de validação adicional dos provedores e do fluxo de perguntas já entregue, incluindo a escalada do requisito PRV-02. Os manifestos e registros anteriores permanecem preservados.

## Execução e aceitação

- SDKs e servidor HTTP reais, sem respostas substituídas; mesmas perguntas e cópias fixas da biblioteca e dos resultados, com memória nova por caso.
- Medir primeiro texto, primeiro texto aceito e conclusão; contar chamadas e tokens auxiliares, tentativas e escaladas, respeitando o orçamento.
- Preservar falhas e retomadas; apagar os arquivos enviados pelo ensaio e conferir a lista remota.
- Registrar o consumo real uma vez no uso do aplicativo, para preservar o controle diário.
- Apresentar médias, medianas e tempos por pergunta, com as limitações de cache, carga inicial, roteamento e ausência de revisão científica integral.

Resultados no [relatório](../migracao/validacao-lote-45.md) e no [manifesto](../migracao/lote-45.json). Nenhuma alteração do produto, download, reindexação, commit ou publicação.
