# Capacidade: experimentos

Spec viva: diz o que vale **hoje** para os experimentos. Um lote que mudar esta capacidade atualiza este
arquivo e cita na própria spec de mudança os requisitos que acrescenta, altera ou retira. Cada requisito
é citado por pelo menos um teste (`tests/test_specs.py`).

Criada no lote 34 (17/10/2026), pela [spec 0034](../0034-experimentos.md).

## O que é

Um experimento é uma pesquisa que roda de ponta a ponta sobre uma base de dados e produz números. Ele é
declarado por uma especialização. Hoje existe um: **AE Denso × AE-LSTM**, na base de dados **GPVS**,
declarado pela especialização do mestrado. O núcleo cuida do que é igual para todos: a pasta de cada
rodada, a rodada atual, o resultado em JSON e Markdown, o PDF e a comparação.

## Requisitos

**EXP-01. Descoberta.** O núcleo acha os experimentos das especializações instaladas sem conhecê-las pelo nome.
*Cenário:* dada uma especialização com `EXPERIMENTS`, quando a aba pede a lista, então o experimento aparece, e
nenhum arquivo do núcleo cita o nome da especialização.

**EXP-02. Rodada do zero.** "Rodar experimento" roda o experimento inteiro, num processo só, numa pasta nova
`<resultados>/<chave>/rodada-NNN/` que nunca é reaproveitada.
*Cenário:* dado um experimento com rodadas 001 e 002 (a 002 incompleta), quando ele roda de novo, então a rodada
nova é a 003, e as outras pastas ficam como estão.

**EXP-03. Rodada completa.** Só conta a rodada com `resultado.json` legível. Uma rodada interrompida não aparece.
*Cenário:* dada uma rodada cancelada no meio do treino, quando a aba abre, então ela mostra a rodada anterior.

**EXP-04. Rodada atual.** A aba Ciência, o chat e o PDF mostram só a rodada completa mais nova; sem nenhuma, a
avaliação oficial de 27/09/2026. As pastas antigas ficam no disco e não são listadas na aba.
*Cenário:* dada uma rodada nova completa, quando a aba abre, então o resumo, as métricas, os escores, o início
das falhas e os exploradores passam a ser os dela.

**EXP-05. Mesmos parâmetros.** Com os parâmetros da rodada mostrada, "Rodar experimento" fica desativado, com o
motivo na tela, e o servidor recusa o pedido (409). O mesmo valor escrito de outro jeito conta como igual.
*Cenário:* dada a rodada de 27/09 com as repetições 13, 29, 42, 71 e 101, quando a tela tem "101, 71, 42, 29, 13",
então o botão fica desativado; quando a separação muda para 2, então ele fica ativo.

**EXP-06. Consulta ao teste.** Uma rodada que usa os dados de teste exige a frase "consultar o teste". A janela de
confirmação diz quantas vezes eles já foram usados. A consulta é aberta logo antes de pontuar o teste e fechada no
fim; se o processo parar antes, o servidor a fecha como cancelada ou falha.
*Cenário:* dado um pedido sem a frase, então nada roda (400); dada uma rodada cancelada depois de abrir a consulta,
então o registro a mostra cancelada.

**EXP-07. Uma por vez.** Só uma rodada anda de cada vez; Cancelar encerra o processo.
*Cenário:* dada uma rodada em andamento, quando outra é pedida, então o servidor recusa (409).

**EXP-08. Resultados em JSON e Markdown.** Cada rodada grava `resultado.json`, por último e de uma vez, e
`resultado.md`, além dos relatórios de cada etapa.
*Cenário:* dada uma rodada completa, então os dois arquivos existem e o JSON traz parâmetros, hashes, indicadores
e as visões da aba.

**EXP-09. PDF por pedido.** O PDF só é montado quando pedido e não fica gravado. Ele é técnico e formal: capa,
sumário, seções numeradas, tabelas com legenda e notas, cabeçalho e rodapé com "página n de N", e o
`resultado.json` anexado.
*Cenário:* quando "Baixar PDF" é clicado, então o navegador recebe o arquivo, e nenhuma pasta de resultados muda.

**EXP-10. Comparar.** Um PDF exportado (pelo anexo) ou um `resultado.json` aparece ao lado da rodada atual,
indicador por indicador, com a diferença, e os parâmetros dele podem ser reaplicados no formulário. Um arquivo
ruim vira aviso (400, ou 413 acima de 5 MB), nunca um erro do servidor.
*Cenário:* dado o PDF da própria rodada atual, quando ele é comparado, então todos os indicadores são iguais.

**EXP-11. Rótulos.** "Oficial" é só a avaliação de 27/09/2026. Uma rodada nova aparece como "Rodada de
DD/MM/AAAA · Nª vez que os dados de teste foram usados", na aba, no chat e no PDF.
*Cenário:* sem rodada nova, a aba diz "Avaliação oficial de 27/09/2026".

**EXP-12. Protocolo fixo.** O experimento AE Denso × AE-LSTM segue sempre o protocolo de 27/09/2026:
- os 24 atributos, na ordem, por janela de 200 amostras (um ciclo de 50 Hz a 10 kHz);
- a normalização robusta pela linha de base do treino (mediana e IQR, com piso de 10% do IQR);
- a divisão 50/15/15/20, com separação padrão de 11 janelas;
- o escore pela média dos 5 maiores erros e o limiar no percentil 99 da calibração;
- o alarme com 3 janelas seguidas e sequências de 8 janelas no AE-LSTM.

A tela muda só a separação, as repetições e o teto de épocas. Mudar qualquer outro valor é mudar o método e pede
spec própria.
*Cenário:* dado o código do mestrado, quando os testes leem os valores do protocolo, então eles são os de
27/09/2026.

## Onde está

- Núcleo: `src/aliado/experiments/` (rodadas, resultado, PDF, comparação), `src/aliado/interfaces/web/experiments.py`
  (rotas `/api/experimentos/*` e o executor) e o comando `aliado experimento listar|rodar|pdf`.
- Especialização: `src/aliado/specializations/mestrado/rodada/` (o experimento AE Denso × AE-LSTM): `experimento.py`
  reúne os 14 atributos do contrato; `declaracao.py`, `execucao.py`, `consolidacao.py` e `apresentacao.py` os
  definem.
