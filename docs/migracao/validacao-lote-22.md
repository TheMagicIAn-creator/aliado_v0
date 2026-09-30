# Validação do lote 22 — correções de confiança

Verificação local em **30/09/2026**, sobre o commit `50c4a63` (0.2.0). O assistente não fez push nem tag.

**Chamadas pagas:** as da consulta reescrita, decidida no mesmo dia depois do caso da MCC:
- 34 ao modelo mais barato: duas vezes o caso real e as 16 perguntas de referência;
- no aceite pelo chat, 2 respostas do Flash, 2 consultas e 2 revisões de memória.

## Testes

Há 8 testes novos, sem rede:
- `tests/test_library_delete.py`, com 5 testes:
  - apagar remove todas as versões, as extrações, os trechos, a ficha e o original, e `verify()` continua limpa;
  - um original compartilhado com outro título fica;
  - um documento desconhecido é recusado;
  - só as deduções do documento apagado são revogadas;
  - a rota exige o cabeçalho local, responde 404 para um documento desconhecido e 409 durante um envio, e depois apaga e revoga. O original apagado abre uma página curta.
- `tests/test_research_skill.py`, com 3 testes:
  - o texto de M09 a M14 confere com o hash do commit `50c4a63`;
  - o contexto da skill não tem mais as frases desatualizadas;
  - a skill registra onde está cada taxa;
  - a FMECA e os 8 cenários citam tabela e página.
- `tests/test_query_rewrite.py`, com 7 testes:
  - a reescrita usa as 4 últimas mensagens e corta as longas;
  - uma consulta vazia ou longa demais é recusada;
  - a busca usa a consulta e, sem trechos, volta à regra antiga;
  - a medição aceita a consulta reescrita;
  - no chat, a chamada só acontece com a biblioteca ligada, entra no registro de uso, fica guardada na resposta e, se falhar, não derruba a resposta.
- `tests/test_fmeca.py` passou a esperar a ressalva conferida da CCB, no lugar de "reconferir".

**384 testes passaram** (369 da 0.2.0 e 15 novos), o Ruff não apontou problemas e `app.js` passou na
checagem de sintaxe, no Python 3.12.14.

## A busca nas continuações da conversa

**O caso**, na conversa real do pesquisador em 30/09:
1. Primeiro ele perguntou: "Tragra o conceito de MCC conforme uma literatura ao menos."
2. Depois pediu: "Traga a definição com base na literatura. Uma citação direta."
3. A resposta disse que nenhum trecho trazia a definição. Os trechos eram definições de dicionário, a contracapa do Lafraia e o escopo de uma norma.

**A causa:**
- A continuação tinha 9 palavras, e só as de até 6 somavam a pergunta anterior. A busca procurou só "definição, literatura, citação direta".
- Somar a pergunta anterior não teria bastado: testado, isso trouxe 0 dos 6 trechos com definição, porque "MCC" aparecia só como sigla.

**A definição estava na biblioteca:**
- IEEE 493 (2007), p. 134: "Reliability centered maintenance (RCM) is a logical, structured framework…";
- Lafraia (2001), p. 181 e p. 256;
- Muqauwim et al., p. 1 e 2;
- o guia da NASA (2008), p. 19.

**Com a consulta reescrita pelo modelo mais barato**, a partir da conversa real:
- A consulta foi: "Manutenção Centrada na Confiabilidade (MCC) Reliability-Centered Maintenance (RCM) definição citação direta literatura Lafraia", com 767 tokens.
- A busca trouxe Lafraia p. 181, IEEE 493 p. 134 e NASA p. 19 entre os 6 trechos.

**Perguntas de referência**, na biblioteca real, antes e depois da reescrita:

| | Acertos | MRR | Outro idioma | Mesmo idioma |
|---|---|---|---|---|
| Sem reescrita (`busca-depois-lote-22`) | 13 de 16 | 0,781 | 7 de 10 | 6 de 6 |
| Com reescrita (`busca-lote-22-reescrita`) | **15 de 16** | **0,906** | 9 de 10 | 6 de 6 (MRR 1,0) |

- P4 e E8 passaram a acertar, e E1 subiu da 2ª para a 1ª posição.
- **Só P8 ainda erra**, e nenhuma pergunta piorou.
- A média de documentos distintos caiu de 3,75 para 3,38. Autores e normas citados na consulta levam mais trechos do mesmo documento.
- O texto da instrução foi fixado antes da medição, e as perguntas não foram alteradas por causa dela.

**Segunda medição**, com a consulta mantendo só os autores e as normas que o pesquisador citou (`busca-lote-22-reescrita-2`):
- **16 de 16**, MRR **0,969**, com média de 3,62 documentos distintos.
- A P8 passou a acertar em 1º lugar, e nenhuma pergunta piorou.
- No caso da MCC, com 10 trechos, a busca trouxe 6 documentos: NASA (p. 19 e 28), Muqauwim (p. 1 e 6), IEEE 493 (p. 134 e 135), Lafraia (p. 181 e 269), o FMEA do Cap. 5 e Marangis.
- **Cuidado:** são só 16 perguntas, e a instrução foi ajustada depois da primeira medição.

**Aceite pelo chat**, numa conversa nova na cópia, com a biblioteca ligada:
- **A primeira pergunta** foi reescrita como "Manutenção Centrada na Confiabilidade (MCC) Reliability-Centered Maintenance (RCM) conceito definição literatura". A resposta citou o IEEE 493 p. 134, a NASA p. 19, Muqauwim p. 1 e Lafraia p. 6, com as citações conferidas.
- **A continuação** foi reescrita como "…(MCC ou Reliability-Centered Maintenance - RCM) definição literatura citação direta norma IEEE 493-2007". A resposta trouxe a **citação direta** do IEEE 493, p. 134, igual ao trecho, com a tradução ao lado.
- **A janela de fontes** mostrou "Buscou na biblioteca: …".
- **Tokens:** as consultas custaram 243 e 467 tokens, e as respostas do Flash, cerca de 11,4 mil e 10,2 mil.
- Esse aceite foi feito antes dos 10 trechos e do ajuste da consulta, que foram medidos pela busca, sem nova resposta do Flash.

## Fonte do texto

Interface de teste em `127.0.0.1:8771`:
- as 8 opções aparecem no seletor, cada uma escrita na própria letra;
- Times New Roman trocou a letra do corpo e dos títulos da resposta;
- a escolha continuou depois de recarregar a página;
- com 360 px e com 1280 px de largura, a barra do topo não rolou para os lados. Em 360 px, o "Aa" some e o seletor encolhe.

## Conferência nos PDFs

As páginas foram vistas como imagem, renderizadas dos originais da biblioteca, e não só no texto extraído.

| Fonte | Página | O que confere |
|---|---|---|
| Sarquis Filho et al. (2020), Tab. III | p. 3 | Contactor 8,31×10⁻⁶ [3]; Ctrl & Communication board 63,7×10⁻⁶ [3] e 26,7×10⁻⁶ [9]; Cooling fan 26,7×10⁻⁶ [9]; IGBT module 16,6×10⁻⁶ [3] e 8,9×10⁻⁶ [9]. [3] é Gallardo-Saavedra et al. (2019), e [9] é Baschel et al. (2018), p. 5 da lista de referências. |
| Baschel et al. (2018), Tab. 1 | p. 5 | IGBT module 11,4 (negrito, [30]) e 8,9 ([−]), por 10⁶ h; MTBF de 28 anos com 4.015 h de operação por ano. |
| Baschel et al. (2018), Tab. 1 (cont.) | p. 6 | Cooling fan 26,7 ([−]), MTBF de 9,3 anos. |
| Cristaldi et al. (2017), Tab. 6 | p. 6 | IGBT 3/3/7 (63), AC/DC contactors 6/5/5 (150), Cooling fans 4/3/4 (48), PCB 7/4/6 (168). |

**Os valores escolhidos pelo pesquisador conferem.** Um achado a registrar: na Tab. 1 de Baschel, [−] marca
valores extrapolados dos relatórios de O&M da juwi, e os valores em negrito são os que o estudo usa. O 8,9e-6/h do
IGBT e o 26,7e-6/h do ventilador são [−]. Para o IGBT, o valor usado por Baschel é 11,4e-6/h.

## Aceite no navegador

Interface de teste em `127.0.0.1:8771`, com cópias de `data/bibliotecas/principal` e de `data/memoria` em
`tmp/lote-22`.

| Etapa | Resultado |
|---|---|
| Apagar o "Adobe Scan" pela interface | A janela disse: "9 anotações inferidas tiradas dele são revogadas… Não tem volta". O aviso final foi: "«Adobe Scan 11 de jan. de 2024.pdf» foi apagado; 9 anotações revogadas". O documento saiu da lista. |
| Apagar o capítulo 7 pela rota | 1 versão, 65 trechos e 7 anotações revogadas, sem arquivos sobrando. A biblioteca ficou com 25 documentos, e só o manual completo do Lafraia. |
| Original de um documento apagado | Status 404 com a página "Este documento não está na biblioteca: ele pode ter sido apagado". |
| Tela estreita (360 px) | Sem rolagem lateral. O botão Apagar desce para a linha de baixo, depois de um ajuste no cabeçalho do visualizador. |
| Console | O único erro foi o 404 pedido de propósito. |

## Biblioteca real

- **Apagados sem cópia**, com as mesmas funções da rota:

| Documento | Versões | Trechos | Anotações revogadas |
|---|---|---|---|
| `7_cap_confiabilidade_sistemas.pdf` | 1 | 65 | 7 |
| `Adobe Scan 11 de jan. de 2024.pdf` | 1 | 29 | 9 |

- **Resultado:** a biblioteca foi de 27 para 25 documentos, e as anotações revogadas, de 0 para 16. Nenhum arquivo sobrou.
- **`verificar`** aponta só as 2 extrações parciais que já existiam antes, por OCR de baixa confiança em algumas páginas: o manual de Lafraia e o guia da NASA.
- **Perguntas de referência:**
  - P7 e E8 aceitavam o recorte ou o manual. Passaram a esperar só o manual, com a nota no campo "onde".
  - A medição (`data/resultados/busca-depois-lote-22`) deu **13 de 16, MRR 0,781**, igual ao lote 19, sem nenhuma pergunta mudar.
  - Continuam errando P4, P8 e E8, todas com o documento em outro idioma.

## Estado final

- `.claude/launch.json` ganhou a entrada `aliado-web-lote-22`.
- `tmp/lote-22` guarda as cópias usadas no aceite e pode ser apagada depois da revisão.
- O commit do lote 22 foi feito pelo assistente, com a autorização do pesquisador ("aplique"), sem push.
