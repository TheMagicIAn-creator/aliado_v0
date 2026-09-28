# Registro de mudanças

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). As versões
seguem o [versionamento semântico](https://semver.org/lang/pt-BR/).

## [0.1.0] — 2026-09-27

Primeira versão do AL-IAdo retrabalhado a partir do repositório `mestrado-utfpr`: um agente
local, de uso individual, com a pesquisa em inversores fotovoltaicos como primeira
especialização. O detalhe de cada lote está nas [specs](docs/specs/) e no
[mapa de migração](docs/migracao/README.md).

### Núcleo e provedores

- **Contratos e gateway** para OpenAI e Gemini, com aliases configurados no `.env`, sem modelo presumido.
- **Registro local de uso:** data, modelo, tokens (inclusive de raciocínio) e número de buscas, nunca o texto.
- **Skills do AL-IAdo:** `pesquisa-inversores` 0.1.5, `confiabilidade` e `engenharia`, com as decisões M01–M16.

### Interface local

- **Navegador em `127.0.0.1`**, sem login: conversas com histórico e lixeira, respostas em fluxo com botão de parar, escolha de skill e modelo, e tokens por resposta.
- **Envio de PDF, Markdown e JSON pelo chat**, com progresso por página, ficha de leitura e citações com trecho e página.
- **Fórmulas** com KaTeX incluído no pacote, sem CDN.

### Biblioteca, memória e web

- **Biblioteca:** OCR em português e inglês, versão Markdown de cada documento e busca híbrida com encoder local de revisão fixa.
- **Memória persistente por origem:**
  - o feedback do pesquisador vale na hora, e as inferências ficam marcadas;
  - conflitos ficam para decisão do pesquisador, e correções nunca apagam o histórico;
  - apagar uma conversa não apaga a memória.
- **Busca na web** pelo Gemini, com fontes numeradas e separadas dos documentos, e "Conferir na web" para as anotações.

### Ciência

- **Cálculos RAM** por cenário explícito: confiabilidade exponencial e Weibull, sistemas em série e em paralelo, mantenabilidade e disponibilidade inerente. Taxas horárias são convertidas pelo serviço (`time_base`).
- **8 cenários dos quatro grupos** da FMECA, em duas bases temporais.
- **FMECA:** NPR calculado das notas da fonte e, separada, a leitura pelas taxas (MTBF, chance de falhar e falhas esperadas).

### Experimento de detecção (GPVS)

- **Protocolo M14 executável:** divisão 50/15/15/20 com 11 janelas de separação, normalização só no treino e verificação de autocorrelação.
- **Autoencoders Denso e AE-LSTM** (PyTorch 2.12.0, CPU):
  - parada pela validação e limiar p99 na calibração;
  - 5 sementes e configuração congelada com hashes;
  - com a configuração da origem, reproduzem os modelos antigos bit a bit.
- **Avaliação M13:**
  - alarme com 3 janelas seguidas;
  - falsos alarmes por hora com limite superior, detecção e atraso por ensaio;
  - bootstrap em blocos e comparação pareada por objetivo, sem vencedor geral.

### Não incluído

- Site com domínio e vários usuários, MCP, roteador de modelos e importação das memórias antigas, previstos para a v1.
- Disponibilidade dos inversores, por falta de fonte de tempo de reparo.
