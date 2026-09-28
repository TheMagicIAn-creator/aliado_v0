# Lote 19 — qualidade da busca da biblioteca

Lote autorizado em 28/09/2026, depois do diagnóstico da [validação do lote 18](../migracao/validacao-lote-18.md).
O pesquisador pôs a busca antes da aba Ciência, que passou ao lote 20. A versão 0.2.0 sai com
a aba Ciência.

## Problema

- Perguntas em português puxavam sobretudo documentos em português. A busca por palavras
  juntava todas as palavras com OU, inclusive "de", "dos" e "segundo".
- O catálogo só tinha o nome do arquivo, sem autor nem ano, e "segundo Baschel" não achava
  `energies-11-01579.pdf`.
- Não havia limite de trechos por documento, e o manual de Lafraia chegava a ocupar os 6 resultados.

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Ordem | A busca antes da aba Ciência: lote 19 (busca) e lote 20 (Ciência). |
| Correções | Palavras vazias ignoradas e mais peso ao significado; ficha do documento; limite por documento. |
| Tradução da pergunta | Fica de fora, e só volta a ser considerada depois da medição. |
| Medição | Perguntas de referência propostas pelo assistente e revisadas pelo pesquisador, medidas antes e depois. |
| Fichas da biblioteca real | Preenchidas no aceite, depois de uma cópia de segurança do catálogo. |

## Parâmetros fixados antes de medir

Para a medição não servir de ajuste, os valores foram fixados no plano, antes de rodar a busca
nova com as perguntas:

| Parâmetro | Valor |
|---|---|
| Palavras vazias | Lista fixa de português e inglês (`knowledge/stopwords.py`), sem palavras tiradas das perguntas de referência |
| Pesos na fusão (RRF, constante 60) | significado 1; palavras 0,5; documento citado 1 |
| Limite por documento | 2 dos 6 resultados; 4 para um documento citado na pergunta |

## Escopo implementado

- **Medição** (`knowledge/evaluation.py` e `aliado biblioteca avaliar`):
  - lê as perguntas de `data/avaliacao-busca/perguntas.json`, fora do Git;
  - dá acertos entre os 6 resultados, MRR e documentos distintos, por idioma, por tipo de pergunta (autor ou conteúdo) e por cruzamento de idioma;
  - grava o relatório numa pasta nova, com os parâmetros da busca, e nunca sobrescreve outro.
- **Busca** (`knowledge/library.py`):
  - palavras vazias fora da parte por palavras;
  - pesos novos e uma terceira lista com os trechos do documento citado;
  - limite por documento, passado só quando faltam candidatos de outros documentos;
  - cada trecho traz a `referencia` curta da ficha.
- **Ficha do documento** (`knowledge/metadata.py`):
  - o Flash-Lite lê até 6.000 caracteres do começo do texto extraído e devolve título, autores, ano e DOI em saída estruturada;
  - o código confere cada campo no texto: título e sobrenomes precisam aparecer nele, o DOI precisa ter o formato certo e o ano deve estar entre 1900 e o ano seguinte;
  - sequências `/gid00030…`, glifos sem texto de alguns PDFs, são removidas antes do envio;
  - `reference()` forma "Baschel et al., 2018", "Colli, 2015" ou "IEEE, 2007".
- **Catálogo** (`catalog.sqlite3`): a tabela `document_cards` é só acrescentada, por documento lógico, com a ficha inferida e a editada em colunas separadas. Um catálogo anterior, sem a tabela, continua funcionando.
- **Agente** (`agent.py`):
  - o catálogo enviado ao modelo leva obra, autores, ano, DOI e referência;
  - os trechos levam a referência;
  - a regra da biblioteca pede para nomear o documento pela ficha.
- **Interface:**
  - a ficha é criada ao indexar um documento novo;
  - o botão **Completar fichas (N)**, na aba Biblioteca, pede confirmação com o número de chamadas e mostra o progresso;
  - cada documento mostra a referência na lista e a ficha no visualizador, marcada "inferida" ou "sua", com edição;
  - as fontes da resposta mostram "Baschel et al., 2018 · energies-11-01579.pdf".
- **Uso:** cada ficha entra no registro como `biblioteca-ficha`.

## Critérios de aceitação

- **Testes sem rede:**
  - palavras vazias e limite por documento;
  - documento citado pelo autor;
  - conferência da ficha no texto e referência curta;
  - edição sobre a inferida, catálogo sem a tabela, catálogo e contexto do agente;
  - medição e comando `avaliar`;
  - rotas da ficha na interface.
- **Medição antes e depois** com as 16 perguntas aprovadas, relatada como saiu.
- **Aceite com o Flash-Lite:**
  - fichas dos 27 documentos da biblioteca real;
  - "segundo Baschel" citando o artigo certo;
  - uma pergunta em português respondida por um artigo em inglês;
  - uma pergunta sobre o acervo respondida pelas fichas.
- A verificação da biblioteca real não muda, e a suíte completa e o Ruff passam.

## Fora do escopo

- A tradução da pergunta para o inglês, a decidir com a medição.
- A aba Ciência, no lote 20.
