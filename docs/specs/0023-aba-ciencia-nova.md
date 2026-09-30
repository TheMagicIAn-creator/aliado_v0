# Lote 23 — aba Ciência nova, parte 1 (resultados do GPVS)

Lote autorizado em 30/09/2026, depois do lote 22 (`cdcd141`), dentro do roteiro da 0.3.0. O pesquisador
achou a aba Ciência confusa, com gráficos ruins, e sentiu falta das visões do projeto antigo: os escores
divididos por ensaio, a matriz de confusão e as métricas para comparar.

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Organização | Pelas perguntas: o resultado primeiro e as ferramentas no fim. |
| Gráficos | D3 v7, copiado do `mestrado-utfpr`. |
| "Métricas entre componentes" | Por tipo de falha do GPVS (F1–F7); a FMECA não se liga ao GPVS. |
| Escores | As duas visões juntas, num contêiner por ensaio. Depois de ver os prints, o pesquisador pediu um **carrossel**: um gráfico por vez, todos do mesmo tamanho, na ordem Denso → AE-LSTM → Ambos, para a página encurtar e os gráficos crescerem. |
| Exploradores | Continuam, no fim da aba. |
| Linguagem | Telas só com dados, sem códigos internos, "semente", "canônica" ou pasta sem explicação, e com uma nota em cada índice. |

## Escopo implementado

- **Navegação:** Resumo · Escores por ensaio · Métricas por falha · Confiabilidade · FMECA · Explorar · Rodar e arquivos.
- **Resumo** (`GET /api/ciencia/resumo`):
  - em cima, a comparação por objetivo, com a diferença Denso − AE-LSTM, o intervalo de 95% e a leitura;
  - embaixo, uma coluna por modelo com os indicadores (ensaios detectados, atraso mediano, alarmes falsos por hora e o limite, alarmes antes da falha, sensibilidade, especificidade, F1, MCC e AUC) e a matriz de confusão;
  - a matriz é normalizada por classe real, em azuis, como a figura antiga, com um filtro por falha e por ensaio.
- **Escores por ensaio** (`GET /api/ciencia/escores`):
  - um contêiner por ensaio, com o índice de F1 a F7 e o teste saudável;
  - em cada contêiner, um carrossel com o Denso, o AE-LSTM e os dois sobrepostos, nessa ordem, no mesmo tamanho e na mesma escala;
  - dá para passar pelas setas, pelos nomes, pelas setas do teclado ou deslizando o dedo; depois do último, volta ao primeiro;
  - "Mostrar em todos" põe o mesmo gráfico em todos os ensaios de uma vez;
  - escore ÷ limiar em escala logarítmica, fases sombreadas, início nominal e alarmes;
  - os alarmes seguem a regra da avaliação: os de antes da falha contados só nesse trecho, e a detecção como o primeiro alarme a partir do início;
  - os gráficos só são desenhados quando o contêiner aparece na tela.
- **Métricas por falha** (`GET /api/ciencia/metricas`):
  - em cima, as barras agrupadas por tipo de falha (L e M somados; as contagens de janelas somadas e as métricas recalculadas, e AUC e atraso como média);
  - embaixo, um mapa de calor por modelo (F1–F7 por L e M);
  - por fim, as métricas gerais com a faixa dos 5 treinamentos repetidos.
- **Explorar:** os exploradores de limiar e de alarme, com o treino de referência (sem seletor de semente), com as métricas por janela e a matriz de confusão dos valores escolhidos.
- **Rodar e arquivos:**
  - a execução do GPVS e os resultados gravados, em linguagem simples ("ajustes originais" ou "exploração");
  - o histórico de avaliações fica recolhido.
- **Confiabilidade e FMECA:** os mesmos cálculos, agora com D3, notas e exportação. O redesenho delas é o lote 24.
- **Gráficos** (`static/graficos.js`, D3 v7.9.0 em `static/vendor/d3/` com a licença ISC):
  - linhas (com escala log, faixas, referências, marcas e guia), mapa de calor, matriz de confusão, barras agrupadas, barras horizontais e ponto com faixa;
  - largura pelo contêiner, redesenho ao trocar o tema ou a fonte do texto, dica com o valor exato e marcas focáveis pelo teclado;
  - cores das figuras antigas: Denso `#2a78d6` e AE-LSTM `#1baf7a`.
- **Exportação:** SVG e PNG de 300 dpi, sempre em fundo branco com as cores do tema claro, e CSV com ponto e vírgula e vírgula decimal. Tudo no navegador.
- **Notas:** um glossário único (`GLOSSARIO`) e a função `nota`, com balão ao passar o mouse, ao focar e ao tocar.
- **Backend:**
  - `science/detection/summary.py`, só com numpy e sem carregar os modelos;
  - o aviso dos exploradores em palavras;
  - `Explorer.alarms` passa a repassar as métricas por janela e as contagens.

## Critérios de aceitação

- **Testes sem rede:**
  - as contagens dão as mesmas métricas das fórmulas por janela;
  - o resumo usa só o treino de referência e não traz termos internos;
  - o agrupamento por falha e a faixa dos treinamentos;
  - as rotas e o erro claro sem dados;
  - a página carrega o D3 e os gráficos antes da aba.
- **Com os dados reais:**
  - o resumo repete o relatório;
  - as matrizes repetem as contagens de cada ensaio;
  - os painéis têm o comprimento de `escores.npz`;
  - as marcas de alarme repetem a detecção, o atraso em janelas e os alarmes antes da falha da avaliação oficial.
- **No navegador:** cada seção, as notas, a exportação, os temas claro e escuro e a tela estreita.
- A suíte completa e o Ruff passam.

## Fora do escopo

- Uma curva de confiabilidade por componente, a FMECA nova e a disponibilidade (lote 24).
- O início real das falhas, que as figuras de escores tornam visível (lote 25).
