# Roteiro para o AL-IAdo v0.1.0

Meta definida pelo pesquisador em 26/09/2026. A redação da dissertação fica fora
deste roteiro. Cada lote continua sendo combinado antes de começar, conforme `AGENTS.md`.

## O que é a v0

Um agente **local e de uso individual** que o pesquisador usa no dia a dia da
pesquisa: conversa pelo navegador, recebe referências pelo chat, lembra do que
aprendeu nas conversas e se corrige, calcula confiabilidade e executa o experimento
de detecção de forma reproduzível.

**Critérios de pronto**

1. Instala do zero seguindo o README.
2. Responde pelo Gemini citando páginas de PDFs enviados pelo chat.
3. Lembra, em outra conversa, de um feedback dado antes e corrige uma anotação
   superada, sem apagar o histórico.
4. Consulta a web quando necessário e cita a fonte.
5. Executa o cálculo de confiabilidade e o experimento Denso × AE-LSTM no GPVS,
   de forma reproduzível e com relatório.
6. Testes e Ruff passam.
7. O pesquisador faz os commits e cria a tag `v0.1.0`. Pela decisão dele, nenhum
   commit é feito antes de a v0 estar concluída.

## Situação dos critérios — 27/09/2026

Os critérios 1 a 6 foram conferidos no lote 17, numa instalação do zero com Python 3.14:
- **1:** instalação pelo README e download do encoder pela rede.
- **2, 3 e 4:** chamadas reais ao Flash-Lite na interface, com PDF citado pela página, memória
  lembrada e corrigida sem apagar e busca na web com fonte.
- **5:** reprodução bit a bit, com os relatórios dos lotes 13–16.
- **6:** 331 testes e o Ruff.

O critério 7 fica com o pesquisador: os commits e a tag `v0.1.0`. Veja a
[validação do lote 17](migracao/validacao-lote-17.md).

## Lotes e progresso

| Lote | Entrega | Peso | Situação |
|---|---|---:|---|
| 01–08 | Transferência, modularização e adequações | 45% | Concluído |
| 09 | Gemini em uso real: identificadores de modelo no `.env` e primeira chamada barata, com custo registrado | 5% | Concluído |
| 10 | Interface web local: chat, escolha da skill, envio de PDF que vai para a biblioteca (com versão Markdown) e citações clicáveis | 10% | Concluído |
| 11 | Memória persistente de conversa, com autocorreção por anotações superadas e histórico preservado | 8% | Concluído |
| 12 | Busca na web pelo Gemini, com fontes citadas, integrada à autocorreção | 4% | Concluído |
| 13 | Dados GPVS e protocolo M14 executável: janelas, partição 50/15/15/20 com intervalos de separação, normalizador ajustado só no treino | 6% | Concluído |
| 14 | Autoencoders Denso e AE-LSTM: treino com parada pela validação, limiar p99 na calibração, configuração versionada e sementes fixas | 8% | Concluído |
| 15 | Avaliação M13: falsos alarmes no teste saudável, detecção nos ensaios com falha, relatório comparativo | 6% | Concluído |
| 16 | FMECA: revisão do NPR e, se desejado, tempos de reparo e disponibilidade | 4% | Concluído |
| 17 | Lançamento: instalação do zero num ambiente limpo, guia de uso, registro de mudanças, wheel | 4% | Concluído |

Progresso atual: **100%**. A soma dos pesos dos lotes concluídos dá o percentual.

## Decisões de escopo — 26/09/2026

- O experimento de detecção entra na v0.
- A interface é web **local**, sem login. Um site com domínio próprio fica para a v1.
- Só o Gemini será usado, por ser a API disponível. OpenAI continua configurável.
- As referências entram pelo chat. A biblioteca gera o Markdown, e o agente cria
  notas próprias citando a página.
- **Memória por origem:** o que vem do feedback explícito do pesquisador vale na
  hora. O que o agente deduz sozinho, de PDF, web ou conclusão própria, também vale,
  mas fica marcado como "inferido" e visível para ser revogado. Nada é apagado:
  anotações corrigidas ficam como superadas. Nenhuma anotação passa por cima de
  M01–M16 ou das skills, e texto de PDF ou web é dado, não instrução.
- A busca na web entra na v0, pelo Gemini, com possível custo por consulta.
- Apagar uma conversa não apaga a memória gerada a partir dela. A conversa vai para
  a lixeira local, e a memória guarda o próprio conteúdo e a referência à origem.
- A ordem prioriza o chat e a memória antes do experimento.

## Decisões do experimento — 27/09/2026

- Separação canônica de 11 janelas entre blocos, pela verificação de autocorrelação do
  lote 13; 2 janelas só para conferir a reprodução da origem.
- Escore top-5 e limiar p99 na calibração; sensibilidade de k ∈ {5, 10, 20} fixada
  antes da avaliação e só relatada.
- Modelos, hiperparâmetros e sementes da origem, com PyTorch 2.12.0 só CPU.
- A validação decide a parada do treino (paciência 20, teto só de segurança); o teto de
  150 épocas da origem cortava 8 dos 10 treinos.
- Avaliação (lote 15):
  - O alarme exige 3 janelas seguidas; a grade {1, 2, 3, 5} é só relatada.
  - Os falsos alarmes são contados no teste saudável e no pré-falha, separados.
  - As métricas principais são as físicas (falsos alarmes por hora com limite superior, ensaios
    detectados, atraso em ms, sensibilidade e especificidade); as da origem ficam como secundárias.
  - A incerteza vem de bootstrap em blocos de 12 janelas.
  - A semente 42 é a referência, com a faixa das 5 ao lado.
  - A comparação é pareada por ensaio e por objetivo, sem vencedor geral.

## Decisões da FMECA — 27/09/2026

- O NPR usa as notas de Cristaldi et al. (2017), Tab. 6, com a CCB herdando o item "PCB" (a reconferir
  no PDF). S e D são os da fonte, e os detectores não os alteram (M09).
- A ocorrência O não é recalculada pelas taxas. O ranking pelas taxas fica numa leitura separada, sem
  nota agregada, e a divergência é relatada.
- A partir das taxas entram MTBF e falhas esperadas em 1 e 20 anos. A disponibilidade espera uma
  fonte de tempo de reparo.

## Fica para a v1

Site com domínio e acesso de vários usuários com convite, MCP (M15), roteador de
modelos com fallback e observabilidade, e importação das memórias antigas.

## Entradas necessárias do pesquisador

| Lote | Entrada |
|---|---|
| 09 | Atendido: `gemini-3.8-flash` (flash) e `gemini-3.5-flash-lite` (flash_lite) |
| 10–11 | As referências, enviadas pelo chat quando ele estiver pronto |
| 13 | Local dos dados do GPVS e versão do repositório antigo usada como referência do pipeline |
| 16 | Decisões sobre NPR e reparos, em perguntas e respostas |
