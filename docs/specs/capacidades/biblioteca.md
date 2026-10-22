# Capacidade: biblioteca

Spec viva: diz o que vale **hoje** para a leitura das páginas dos documentos da biblioteca e para a conferência
das citações deles. Um lote que mudar esta capacidade atualiza este arquivo e cita na própria spec de mudança os
requisitos que acrescenta, altera ou retira. Cada requisito é citado por pelo menos um teste (`tests/test_specs.py`).

Criada no lote 37 (18/10/2026), pela [spec 0037](../0037-paginas-sem-leitura.md), só com os requisitos da leitura
das páginas. A indexação, a busca e as fichas seguem descritas nas specs 0004, 0019, 0029, 0030 e 0032. O lote 46,
pela [spec 0046](../0046-correcoes-do-relatorio.md), acrescentou o BIB-05.

## Requisitos

**BIB-01. Página em branco.** Uma página sem texto que está em branco não é pendência de leitura: o documento não
fica "parcial" por causa dela. Ela é reconhecida no computador, pela imagem: a 100 dpi, menos de 0,1% de pontos
visíveis no miolo, longe das margens onde a digitalização deixa a dobra e a borda do vidro.
*Cenário:* dada a página 2 do guia de MCC da NASA, em branco, quando o documento é reindexado, então o aviso "sem
texto utilizável" sai; uma página sem texto, mas com um desenho, continua com o aviso.

**BIB-02. Página descrita pelo modelo.** Uma página com OCR de baixa confiança, ou sem texto, que o modelo já
descreveu (figura ou tabela) não é mais pendência de leitura: o conteúdo dela está na busca, como descrição
automática, marcada para conferir no original.
*Cenário:* dada a página 64 do manual do Lafraia, um gráfico já descrito, quando o documento é reindexado, então o
aviso "OCR com baixa confiança" sai; uma página com OCR fraco e sem descrição continua com o aviso.

**BIB-03. OCR fraco entra na descrição.** Uma página digitalizada com OCR de baixa confiança (média abaixo de 50)
entra na lista da descrição de figuras e tabelas, mesmo sem a legenda lida: costuma ser figura, desenho ou tabela
impressa de lado. A descrição continua só por pedido do pesquisador, com o custo antes.
*Cenário:* dadas as páginas 63, 126, 273, 365 e 366 do manual do Lafraia, quando o documento é reindexado, então a
ficha mostra "Descrever figuras e tabelas (5 páginas)", e nada é enviado ao modelo até o clique.

**BIB-04. OCR página por página.** Na entrada de um PDF, cada página tem a sua camada de texto extraída. Só a
página com menos de 20 caracteres úteis, ou com caracteres corrompidos, passa por OCR, e só ela. O texto de cada
página fica gravado com o número dela e com a origem (`native` ou `ocr`, esta com a confiança). O limite foi
conferido na biblioteca real no lote 41.
*Cenário:* dado um PDF todo digital, nenhuma página passa por OCR; todo escaneado, todas passam; misto (capa em
imagem ou folha de aprovação escaneada), só essas páginas; o número da página fica certo nos três casos.

**BIB-05. Marca que aponta um só trecho.** Na conferência das citações de uma resposta, a marca que não é um
identificador enviado, mas aponta sem ambiguidade um único trecho enviado, vale como esse trecho e é reescrita com o
identificador dele. São só duas formas, as do lote 45:
- o identificador do trecho com a página dele colada no fim (`p11`);
- o documento e a página, no formato das páginas, quando um único trecho enviado é daquele documento e daquela
  página.

O formato das regras escrito como citação (`[K...]`, `[K…]` ou `[K]`) sai do texto. Qualquer outra marca fora do
que foi enviado continua reprovando a resposta (identificador truncado, copiado de um exemplo, página que não é a
do trecho, ou dois trechos da mesma página). Não há comparação aproximada.
*Cenário:* dadas as marcas das 4 respostas locais descartadas no lote 45, quando a resposta é conferida, então a da
P8 (trecho com a página dele) e a da E8 (documento e página de um trecho enviado) valem como os trechos, e o
`[K...]` sai. As da P5 (truncada) e da E7 (o exemplo das regras) continuam reprovando.
