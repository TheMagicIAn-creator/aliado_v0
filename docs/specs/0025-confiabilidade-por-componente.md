# Lote 25 — confiabilidade por componente, matriz de criticidade e disponibilidade

Lote autorizado em 30/09/2026, depois do lote 24 (`0cc8f78`). Na revisão da 0.2.0, o pesquisador achou a
curva de confiabilidade "muito esquisita": um único gráfico, com um λ digitado. Ele pediu uma curva para
cada componente. A disponibilidade nunca tinha sido calculada, por falta de fonte de tempo de reparo
(decisão de 27/09).

## Decisões do pesquisador (30/09)

| Tema | Decisão |
|---|---|
| Tempo de reparo | Dois cenários, com a faixa entre eles. O reparo ativo do IEEE 493 dá a disponibilidade inerente, e a parada de campo de Baschel et al. (2018), a disponibilidade com logística. |
| Contatores | O mesmo tempo do inversor (26 h no IEEE 493), com o reparo no nível do inversor. A linha de partidas de motor da norma fica só como ressalva. |
| Base de tempo | "Una ambos": as duas bases no gráfico, cheia para a operação (4.015 h/ano) e tracejada para o calendário (8.760 h/ano), e um seletor para ver as duas, só a operação ou só o calendário. |
| FMECA | Entra a matriz de criticidade S × O. Barras de S, O e D, a ordem pela indisponibilidade e os 4 grupos em série ficam de fora. |

## Fontes conferidas nas páginas (30/09)

- **IEEE Std 493-2007, Tabela 10-4 (continuação), p. 290 do PDF:** "Inverters, all types" (E25-000), com 414,8 unidades-ano, 2 falhas, 0,00482 falha/ano, MTBF de 1.817.016 h e **MTTR de 26 h**. Os dados são do TM 5-698-5 do Exército dos EUA (2006).
- **IEEE Std 493-2007, Tabela 10-2, p. 283 do PDF:** partidas de motor com contato de 0 a 600 V, média de 65,1 h e mediana de 24,5 h por falha. Não foi usada, por decisão do pesquisador.
- **Baschel et al. (2018), Figura 7, p. 12:** inversor com **MTTD de 1 dia e MTTR de 5 dias** (parada de 6 dias), pela experiência de campo em grandes usinas fotovoltaicas. A figura é imagem; o valor foi conferido com a página renderizada.
- Nenhuma fonte da biblioteca traz o tempo de reparo de IGBT, placa de controle, contatores ou ventiladores. Por isso, o tempo é o do inversor inteiro.

## Escopo implementado

- **`docs/pesquisa-inversores/reparos.json`:** os dois cenários, cada um com fontes (tabela e página), hipóteses e ressalvas.
- **`science/components.py`** (sem dependências externas):
  - `validate_repairs` e `load_repairs`;
  - `component_view`, que dá, para cada grupo e base:
    - λ por hora e por ano, MTBF, falhas esperadas, F(1) e F(20);
    - as curvas R(t) e F(t) em 41 pontos, pelo serviço RAM;
    - a disponibilidade por cenário de reparo: MTBF em horas de calendário = 8.760 / (λ · horas por ano), A pelo `availability_inherent` do serviço RAM e horas paradas por ano = falhas por ano × parada.
- **Rota:** `GET /api/ciencia/componentes`, com 404 claro sem `reparos.json`.
- **Seção Confiabilidade:**
  - o seletor de base;
  - a confiabilidade dos quatro grupos num gráfico;
  - um painel por grupo, com R(t) e F(t) e os cartões: λ, MTBF, F(1), F(20), falhas esperadas, disponibilidade e horas paradas por ano;
  - a disponibilidade de cada grupo nos dois cenários (gráfico de faixa e tabela), com as fontes e as ressalvas;
  - o explorador de um cenário qualquer, no fim.
- **FMECA:**
  - a matriz de criticidade S × O, com o fundo pelo produto S × O, sem faixas de risco, porque não há fonte para os limites;
  - os pares em que O e a taxa discordam, mostrados pelo nome dos grupos.
- **Gráficos:**
  - séries tracejadas, com a legenda que desenha o tracejado;
  - legenda que quebra linha e usa um rótulo próprio;
  - 4 cores de grupo nos temas claro, escuro e de exportação.
- **Glossário:** MTTR, parada por falha, disponibilidade, disponibilidade inerente e com logística, horas paradas, falhas esperadas, cenário de reparo e matriz de criticidade, e a base de tempo revista.
- **Textos atualizados:**
  - o limite da FMECA passa a apontar para a disponibilidade, sem nome de arquivo;
  - a skill do mestrado 0.2.1 descreve os dois cenários de reparo.
- **Linguagem na tela:**
  - os 8 cenários trocaram "Horizonte de 20 anos (M12)" por "o das diretrizes da pesquisa";
  - uma ressalva da FMECA deixou de citar commit e caminho do projeto anterior.

## Critérios de aceitação

- **Testes sem rede:**
  - um bloco por grupo, com as duas bases;
  - os números do IGBT e da CCB conferidos pelas fórmulas;
  - a disponibilidade igual à do serviço RAM;
  - tabelas de reparo inválidas recusadas;
  - as fontes com tabela e página;
  - a FMECA e a skill atualizadas;
  - a rota, com 200, 404 e sem termos internos.
- **No navegador:**
  - o seletor nas 3 posições, o tema escuro e a tela de 360 px sem rolagem lateral;
  - a exportação SVG e PNG dos gráficos novos;
  - nenhum termo interno nem nome de arquivo nas seções da aba.

## Fora do escopo

- Tempo de reparo por componente, que nenhuma fonte traz.
- Distribuição do tempo de reparo e disponibilidade operacional completa, com preventiva.
- A skill e os resultados no chat, que ficam no lote 26.
