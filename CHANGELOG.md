# Registro de mudanças

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). As versões
seguem o [versionamento semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

Lote 18, a partir dos apontamentos do pesquisador no uso real. A versão 0.2.0 sai com a aba
Ciência (lote 20), depois da busca (lote 19). Detalhes na [spec 0018](docs/specs/0018-biblioteca-memoria-anexos.md).

### Adicionado

- **Perfil na memória:** o que você conta sobre si (nome, instituição, pesquisa) vale em todas as conversas. O revisor guarda até 8 anotações por troca.
- **Memória de conversas:** cada troca fica guardada no computador, e até 3 trocas de outras conversas, parecidas com o assunto, entram como contexto. As conversas que já existiam são indexadas na primeira abertura.
- **Catálogo no modo biblioteca:** o agente recebe a lista dos documentos e responde sobre o acervo.
- **Busca com contexto:** mensagens curtas, como "tente novamente", buscam junto com a pergunta anterior.

### Alterado

- **Resposta sem citação** no modo biblioteca: aparece com o aviso "Esta resposta não cita trechos dos seus documentos" e entra no histórico. Citação inventada continua bloqueada.
- **Fontes e memória** abrem numa janela sobre a resposta, que fecha com Esc ou com um clique fora. O painel lateral saiu.
- **Anexos:** fila de até 3 cartões com contador; os que dão certo somem em 6 s.
- **Conversa apagada** deixa de ser lembrada. As anotações que saíram dela continuam.
- Sem anotação sobre algo, o agente diz que não tem isso anotado, e não que não tem memória.

### Corrigido

- Anotações e trocas com mais de 128 tokens ficavam sem vetor e nunca eram achadas por semelhança. As que faltam são preenchidas na abertura.
- O navegador guardava versões antigas da interface depois de uma atualização.

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
