# Validação do lote 45 — comparação real de respostas

Data: 2026-10-20. Escopo na [spec 0045](../specs/0045-comparacao-real.md). **32 respostas reais concluídas**, sem respostas substituídas. O Gemini direto reduziu o tempo médio em 80,3% neste conjunto e foi mais rápido nos 16 pares.

## Tempos observados

| Medida | Ollama com escaladas normais | Gemini direto |
|---|---:|---:|
| Tempo médio até a resposta concluída | 111,7 s | 22,0 s |
| Mediana até a resposta concluída | 83,8 s | 19,0 s |
| Percentil 90 | 224,8 s | 44,4 s |
| Primeiro texto visível, média | 83,7 s | 17,1 s |
| Primeiro texto da resposta aceita, média | 95,6 s | 17,1 s |

Nota: o tempo começa no envio HTTP da pergunta e termina no evento de resposta concluída. Inclui busca, reescrita, envio de PDFs, raciocínio, geração, escaladas e validação. O primeiro texto pode ser de uma resposta local depois descartada; a linha da resposta aceita considera esse reinício. O percentil 90 é o valor de ordem ceil(0,90 × 16), sem interpolação.

| Pergunta | Fluxo local (s) | Gemini direto (s) | Provedor final no fluxo local | Leitura: local / direto |
|---|---:|---:|---|---|
| P1 | 22,8 | 15,4 | Gemini | documento inteiro / documento inteiro |
| P2 | 90,4 | 26,5 | local | documento inteiro / documento inteiro |
| P3 | 188,7 | 53,8 | local | páginas inteiras / páginas inteiras |
| P4 | 38,8 | 11,2 | local | trechos / trechos |
| P5 | 77,1 | 16,5 | Gemini | trechos / trechos |
| P6 | 111,0 | 22,1 | local | trechos / trechos |
| P7 | 181,5 | 13,6 | local | sem a biblioteca / sem a biblioteca |
| P8 | 71,6 | 14,9 | Gemini | trechos / trechos |
| E1 | 29,2 | 23,1 | Gemini | documento inteiro / documento inteiro |
| E2 | 141,9 | 21,5 | local | documento inteiro / documento inteiro |
| E3 | 55,5 | 6,6 | local | sem a biblioteca / sem a biblioteca |
| E4 | 40,6 | 4,8 | local | trechos / trechos |
| E5 | 231,6 | 25,1 | local | páginas inteiras / páginas inteiras |
| E6 | 224,8 | 37,3 | local | páginas inteiras / páginas inteiras |
| E7 | 72,4 | 15,4 | Gemini | trechos / trechos |
| E8 | 209,2 | 44,4 | Gemini | páginas inteiras / páginas inteiras |

As perguntas e notas de avaliação vêm de `data/avaliacao-busca/perguntas.json`, aprovadas em 28/09/2026. A identificação P/E indica apenas a linha desse arquivo.

## Chamadas e consumo

No fluxo com preferência local, 10 das 16 respostas terminaram no Ollama e 6 no Gemini. Houve quatro escaladas após resposta local (P5, P8, E7 e E8) e dois encaminhamentos por limite de contexto (P1 e E1); E1 ainda teve reescrita local. O aplicativo escolheu Flash ou Flash Lite normalmente no modo direto; a escalada após reprovação local usou Flash.

| Medida | Fluxo local | Gemini direto |
|---|---:|---:|
| Chamadas aos SDKs, incluindo auxiliares e falhas | 29 | 23 |
| Chamadas ao Gemini | 6 | 23 |
| Tokens pagos informados pelo SDK | 88427 | 205989 |
| Tokens informados, locais e pagos | 297109 | 205989 |
| Chamadas sem tokens informados | 2 | 0 |

Nota: tokens são unidades de texto usadas na contagem dos modelos; os pagos incluem entrada, saída e raciocínio, com os tokens de cache ainda contados. Não foi calculado valor monetário. Nas chamadas sem medição, 78790 tokens permaneceram reservados conservadoramente para controlar o orçamento; não são consumo comprovado.

O pesquisador autorizou até 96 chamadas (64 ao Gemini), 1,2 milhão de tokens no total e até 600 mil pagos. O controle contabilizou 52 chamadas, 29 ao Gemini, 581888 tokens com reservas e 294416 pagos. Os registros do aplicativo e do SDK coincidem no consumo pago. O consumo real foi incorporado uma vez ao registro de uso, para manter o aviso diário correto.

## Método e incidentes

Foram usadas a biblioteca real com 31 documentos e uma cópia dos resultados existentes, sem reindexação, treinos ou execução de experimentos. Biblioteca e resultados foram copiados uma vez; cada pergunta/modo ganhou conversa e memória novas. As chamadas passaram pelo servidor HTTP real do aplicativo, em sequência. A ordem alternou entre os modos; a retomada pulou respostas concluídas. Foram preservados contexto, modelos, roteamento, limites de confirmação e pedidos originais. Nenhuma figura nova foi descrita.

O Ollama foi `aliado-local`, baseado em Qwen3.5 9B Q4_K_M, contexto 32768 e 32 camadas na GPU RTX 3050 de 6 GB. Os modelos pagos configurados foram `gemini-3.8-flash` e `gemini-3.5-flash-lite`.

Houve duas falhas antes de completar a P2 local: erro de alocação CUDA e erro de reserva interna de memória. Elas ficaram no orçamento e nas evidências, fora das médias das 32 respostas concluídas. O pesquisador autorizou fechar aplicativos por estar fora de casa; Firefox e VS Code foram encerrados normalmente. A carga local funcionou após isso, sem alterar o modelo. O servidor do projeto que rodava no terminal do editor fechou junto e foi restaurado ao final.

A conferência inicial de exclusão por GET esperava 404, mas o Google devolveu 403 também para arquivos apagados. A lista autenticada confirmou zero arquivos, e passou a ser usada nas limpezas seguintes. Ao final, todos os registros de uploads do ensaio estavam vazios e a lista remota retornou zero arquivos. Somente arquivos registrados nas pastas deste teste foram enviados para exclusão.

## Qualidade e limites da comparação

A fonte esperada apareceu em 13/16 respostas no fluxo local e 13/16 no direto. Esse indicador mede presença do documento indicado nas notas de avaliação; não mede correção científica. P7 e E3 foram roteadas sem biblioteca. P8 consultou trechos, mas os dois modos não citaram a fonte esperada.

Na P3 local, a resposta expandiu ECP como `Eliminated Conductive Parts`; a fonte efetivamente enviada, página 15, diz `exposed conductive part`. O estado de citação válida apenas conferiu o identificador, sem impedir o erro de conteúdo. Em E3, os dois modos seguiram a rota de resultados do projeto para uma pergunta sobre um TCC: o direto absteve-se; o local apresentou Denso e AE-LSTM com a ressalva de que não comprovava a ligação à UFSC.

Há uma execução por pergunta e configuração, sem intervalo de confiança. Temperatura, reescritas e validações reais podem alterar tamanho e conteúdo das respostas. O cache implícito do Gemini apareceu em algumas chamadas; não foi desligado. As primeiras três respostas precederam a liberação de memória e houve pausas para diagnóstico e limpeza; carregamento inicial e cache também afetam os tempos. Portanto, este é um comparativo dos fluxos completos nessas consultas, não uma medição isolada da capacidade dos modelos. Não houve revisão científica integral.

## Evidências e continuidade

O [manifesto](lote-45.json) contém medidas por pergunta, orçamento, hashes e conferências operacionais. As respostas, eventos, chamadas e scripts finais ficam em `tmp/lote-45/`, fora do Git. Os scripts de medição evoluíram na retomada apenas para registrar tentativas, liberar objetos encerrados e conferir limpeza; os pedidos e respostas dos modelos não foram substituídos.

Nenhum comportamento do produto, requisito vivo ou versão foi alterado neste lote. O pacote e o manifesto do lote 44 foram preservados. Correções de conteúdo, roteamento ou desempenho precisam de um próximo lote combinado com o pesquisador. Não houve commit ou publicação.
