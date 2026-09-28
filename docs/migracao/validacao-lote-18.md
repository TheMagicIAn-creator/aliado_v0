# Validação do lote 18 — biblioteca, memória, anexos e fontes

Verificação local em **28/09/2026**. Nenhum commit, push, PR ou tag.

## Testes

| Arquivo | Mudança |
|---|---|
| `tests/test_knowledge.py` | 2 testes novos. O que exigia não chamar o provedor com a busca vazia foi reescrito: agora a resposta sai pelo catálogo, com o aviso. |
| `tests/test_memory.py` | 6 novos: perfil, revisor com 8 anotações, memória de conversas, contexto do agente, vetores de textos longos e preenchimento dos que faltam. |
| `tests/test_web.py` | 4 novos: lembrar e esquecer conversas, indexação única das existentes, resposta sem citação no histórico e cabeçalho de cache. |
| `tests/test_web_search.py` | 2 asserções ajustadas: sem citação e sem fonte da web, a resposta agora aparece como `uncited`. |

**343 testes passaram** (331 da v0.1.0 e 12 novos) e o Ruff não apontou problemas, no Python 3.12.14.

## Aceite com chamadas reais

Interface de teste em `127.0.0.1:8768`, com dados temporários em `tmp/lote-18/dados` e a biblioteca
real `data/bibliotecas/principal` (27 documentos) só para consulta. A memória e as conversas reais
do pesquisador não foram usadas. Modelo `gemini-3.5-flash-lite`.

| Critério | Resultado |
|---|---|
| Acervo | "Quais arquivos você tem acesso?" listou os 27 documentos pelo catálogo, com os 2 em estado parcial, e a faixa "Esta resposta não cita trechos dos seus documentos". Antes, essa resposta era escondida. |
| Continuação | "E do módulo IGBT?", depois de uma pergunta sobre os ventiladores, buscou junto com a pergunta anterior e respondeu no mesmo assunto. |
| Perfil | A apresentação gerou 1 anotação de perfil, "sua" e sem skill. Numa conversa nova, "Qual o meu nome?" teve como resposta "Você se chama Rodolfo". |
| Memória de conversas | Depois da correção abaixo, numa conversa nova, "O que eu te perguntei antes sobre os ventiladores de refrigeração?" mostrou "lembrou 2 conversas", e a resposta repetiu a pergunta anterior e a taxa. |
| Esquecer | Com a conversa de origem apagada, as 3 trocas dela ficaram esquecidas, e ela foi para a lixeira. A pergunta seguinte, sobre o IGBT, lembrou só a conversa de apresentação. |
| Janela de fontes | Aberta por "lembrou 2 conversas", mostrou as conversas, com "Abrir conversa", e a anotação de perfil usada. Numa janela de 650 × 698 px ela ficou com o topo em 64 px e rolagem interna, e fecha com Esc. |
| Fila de anexos | Numa biblioteca temporária, 6 notas Markdown sintéticas e um `.txt`. O `.txt` só gerou o aviso. O contador foi de "0 de 6 indexados" a "5 de 6", nunca houve mais de 3 cartões à vista, cada sucesso sumiu cerca de 6 s depois, e a fila terminou vazia. |
| Uso | **30 chamadas** ao Flash-Lite: 7 respostas, 7 revisões de memória e 16 fichas de leitura das notas sintéticas. Foram 53.488 tokens de entrada e 3.896 de saída, sem busca na web. |

A primeira tentativa de apresentação teve "O Gemini não respondeu". O registro do servidor não
mostrou erro, e a segunda tentativa funcionou: foi uma falha passageira do provedor.

## Defeitos encontrados e corrigidos

1. **Textos longos sem vetor.** Na primeira pergunta sobre os ventiladores, a conversa anterior não foi lembrada. 4 das 5 trocas guardadas estavam sem vetor, porque o encoder recusa mais de 128 tokens ("Trecho ou consulta excede 128 tokens") e o erro era engolido.
   - A correção divide o texto pelo `split` do encoder e soma os vetores das partes.
   - A abertura do servidor preenche os vetores que faltam.
   - O defeito vinha do lote 11 e também afeta anotações: **18 das 236 anotações** da memória real estão sem vetor. A leitura foi só de consulta, e elas serão preenchidas quando o pesquisador reiniciar o AL-IAdo.
2. **Versões antigas da interface.** Depois de uma atualização, o navegador usava o `app.css` guardado, e a fila de anexos aparecia errada. A página e `/static/` passaram a sair com `Cache-Control: no-cache`.
3. **Janela de fontes fora da tela.** Aberta perto do fim da conversa, ela passava da borda superior (topo em −9 px). A altura passou a se limitar ao espaço disponível.
4. **Lista de conversas em janela estreita.** A constante do modo estreito saiu junto com o painel lateral, mas ainda era usada, e a lista não abria. Ela foi restaurada. O defeito surgiu e foi corrigido dentro do lote.

## Achado para decisão: a qualidade da busca

Diagnóstico só de leitura, feito no índice real (27 documentos e 13.946 trechos):

- **A busca por palavras** junta todas as palavras da pergunta com OU, inclusive "de", "dos" e "segundo". "de" aparece em 2.203 trechos. Assim, os documentos em português vencem a parte por palavras de qualquer pergunta em português, e a fusão dá a ela o mesmo peso da parte por significado.
- **A busca por significado** usa um encoder multilíngue e cruza os idiomas. Para "detecção de anomalias em usinas fotovoltaicas com aprendizado de máquina", os 6 trechos mais próximos são de artigos em inglês, mas o resultado final pôs um documento em português ("Aprendizado de máquina aplicado à predição de falhas em inversores de frequência") em 4 das 6 posições.
- **Autor e ano não estão no catálogo**, que só tem o nome do arquivo. "Baschel" aparece num único trecho do próprio artigo (`energies-11-01579.pdf`) e em outros 5 documentos que o citam. Para "Qual é a taxa de falha dos ventiladores de refrigeração segundo Baschel et al. (2018)?", os 6 trechos foram do manual de Lafraia, e a resposta veio da skill.
- **Não há diversidade:** os 4 maiores documentos somam 71% dos trechos, e os 6 resultados podem sair todos de um só.

O pesquisador decidiu tratar isso no lote 19, antes da aba Ciência, que passa ao lote 20. Entram
três correções: ignorar palavras vazias e dar mais peso ao significado, a ficha de cada documento
(título, autores, ano e DOI) e um limite de trechos por documento. A medição usa perguntas de
referência, antes e depois da mudança.

## Estado final

- O `git status` mostra modificados só os 11 arquivos de código e testes deste lote, e a documentação listada no [manifesto](lote-18.json). Nenhum outro arquivo difere do commit `eac1a36`.
- `git ls-files data` não lista nenhum arquivo.
- A pasta `tmp/lote-18`, fora do Git, guarda só os dados do aceite e pode ser apagada.
