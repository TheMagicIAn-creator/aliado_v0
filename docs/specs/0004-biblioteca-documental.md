# Lote 04 — biblioteca documental e configuração local

Plano autorizado na conversa; implementação local para revisão em 25/09/2026.

## Entrega

- README com lotes 01–03 e capacidades atuais. `.env` privado preserva os valores
  fornecidos; `.env.example` contém somente exemplos. Chave de API e nome de modelo
  são configurações diferentes. Nenhuma chamada paga integra a validação.
- Provedores rejeitam resposta vazia e saída estruturada que não seja objeto JSON.
- Serviço independente `DocumentLibrary`: adição explícita de PDF, Markdown e JSON,
  originais por SHA-256, versões por título lógico, Markdown extraído e metadados
  JSON por processamento. Duplicatas não repetem indexação; reprocessamento mantém
  os artefatos anteriores. Não restaura o acervo antigo.
- OCR Tesseract local, português/inglês, em páginas sem texto suficiente e sob
  `--forcar-ocr`. Registra página física do PDF, método e confiança do OCR;
  falhas e baixa confiança tornam a extração parcial. Não reescreve textos via LLM.
- SQLite/FTS5 e vetores locais; busca híbrida BM25, similaridade cosseno e fusão
  de posições. Encoder MiniLM multilíngue ONNX, revisão e hashes fixos.
- CLI para adicionar, listar, buscar e verificar. `preparar`/`perguntar` aceitam
  biblioteca explicitamente selecionada e conservam o funcionamento sem biblioteca.
- Contexto documental como dados de consulta, separado das instruções. Citações
  usam identificadores dos trechos recuperados e localizadores reais; identificador
  inventado ou ausente bloqueia a exibição da resposta documental.

## Limites e aceitação

O upload pelo chat pertence à futura interface web. Nesta versão, a entrada é um
arquivo local explícito; não há varredura de diretórios. Cada diretório de biblioteca
representa um projeto. Não há autenticação multiusuário nem serviço publicado.

Indexação e OCR ficam locais; ao usar `perguntar`, os trechos selecionados seguem
para o provedor escolhido. Referência existente não garante interpretação correta:
a checagem de citações valida identidade/localização, não a sustentação semântica
de cada afirmação. Fórmulas, tabelas e OCR exigem conferência no original.

Critérios: preservar bytes/hashes, impedir uso de versão antiga como atual, indicar
falhas, manter isolamento entre bibliotecas, testar busca sem coincidência literal,
não importar memória privada, verificar referências e operação sem biblioteca.
Testes determinísticos usam documentos e provedores sintéticos. Um ensaio local
separado verifica o Tesseract e o encoder reais sem literatura do pesquisador.

Uso e limites de capacidade: [guia documental](../biblioteca/uso.md).
