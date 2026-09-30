# Validação do lote 23 — aba Ciência nova, parte 1

Verificação local em **30/09/2026**, sobre o commit `cdcd141` (lote 22). **Nenhuma chamada paga.** O
assistente não fez push nem tag.

## Testes

`tests/test_science_views.py` traz 8 testes novos:
- **Métricas:** as contagens de janelas dão as mesmas métricas das fórmulas de `window_metrics`.
- **Resumo** (dados sintéticos com 2 treinamentos):
  - usa só o treino de referência;
  - as matrizes somam certo no total, por falha e por ensaio;
  - a resposta não traz "semente", "canônica" nem códigos M.
- **Métricas por falha:**
  - recalculadas das contagens somadas de L e M, com AUC e atraso em média;
  - com a faixa dos treinamentos e em quantos treinamentos o ensaio foi detectado.
- **Erros:** sem a avaliação oficial ou sem os dados do GPVS, a mensagem diz o que falta.
- **Rotas e página:**
  - as rotas `/api/ciencia/resumo`, `/metricas` e `/escores` respondem, com 404 claro sem dados;
  - a página carrega o D3 v7.9.0 e `graficos.js` antes de `ciencia.js`, e a licença do D3 está lá.
- **Com os dados reais:**
  - o resumo repete o relatório de 27/09 (detectados, alarmes por hora e janelas antes da falha);
  - as matrizes repetem as contagens de cada ensaio, e as métricas refeitas das contagens batem com as do relatório;
  - os painéis têm o comprimento de `escores.npz`, com a razão pelo limiar certo e o início igual ao da avaliação;
  - nos 14 ensaios e nos 2 modelos, as marcas de alarme repetem a detecção, o atraso em janelas e os alarmes antes da falha.

**392 testes passaram** (384 do lote 22 e 8 novos). O Ruff não apontou problemas, e `graficos.js`,
`ciencia.js` e `app.js` passaram na checagem de sintaxe, no Python 3.12.14.

## Aceite no navegador

Interface de teste em `127.0.0.1:8772`, com uma cópia de `data/resultados` em `tmp/lote-23`. Os dados do
GPVS foram só lidos.

| Seção | Resultado |
|---|---|
| Resumo | A comparação por objetivo, as colunas do Denso e do AE-LSTM com 34 notas e as matrizes de confusão. O Denso tem 2.293 VN, 55 FP, 2.747 FN e 1.937 VP, normalizados por classe real, em azuis. |
| Escores por ensaio | 16 contêineres (14 ensaios e 2 trechos do teste saudável). Só os visíveis são desenhados: 3 de 48 ao abrir. Os gráficos mostram os modelos sobrepostos, as fases, o limiar, o início nominal e os alarmes. O eixo log marca 0,01, 1, 100, 10⁴ e 10⁶. |
| Métricas por falha | As barras agrupadas por falha, os mapas de calor (viridis) e o gráfico de pontos com a faixa dos 5 treinamentos. |
| Explorar | Com os valores oficiais, o alarme repete 10 de 14 ensaios, 2,04 s de atraso mediano, 0 alarme falso e o limiar de 3,7338, e avisa que os números são os oficiais. Não há seletor de semente. |
| Rodar e arquivos | Os três cartões em linguagem simples, e o histórico recolhido. A avaliação de 27/09 aparece como "Avaliação oficial", e o treino como "Treino com os ajustes originais". |
| Termos internos | Varredura do texto das 7 seções: sobravam "(M09)" e "(M11)" numa ressalva da FMECA e "sementes" num rótulo. Foram corrigidos (ver abaixo). |
| Notas | Abrem ao passar o mouse, com `aria-describedby`, fecham ao sair, abrem e fecham ao tocar, e fecham com Esc. |
| Exportação | SVG em fundo branco e sem variáveis de CSS; PNG de 3.125 px de largura (300 dpi); CSV com ponto e vírgula e vírgula decimal. O PNG de um ensaio, aberto de volta, mostrou fundo branco com as cores do tema claro. |
| Tema e fonte | Ao trocar para o tema escuro e para Times New Roman, os gráficos se redesenharam com o fundo e a fonte novos. |
| Tela estreita (360 px) | A página não rola para os lados em nenhuma seção. Nos escores, os painéis por modelo passam para baixo do gráfico conjunto, com altura mínima. |
| Console e servidor | Sem erros do aplicativo. |

## Defeitos encontrados e corrigidos no aceite

1. **Gráficos minúsculos e letras com contorno:** a regra global de `svg`, feita para os ícones, fixava 18 px e punha contorno. Os gráficos ganharam uma regra própria.
2. **A matriz esticada até a largura toda:** cada gráfico passou a ficar no seu tamanho natural.
3. **O eixo log mostrava "1e+6" e linhas de grade demais:** agora marca só as potências de 10, e usa a forma 10ⁿ de 10⁴ para cima.
4. **Termos internos na tela:**
   - a ressalva da FMECA perdeu os códigos, com o mesmo sentido, em `fmeca.json`;
   - o rótulo das repetições do treino perdeu a palavra "sementes", que ficou explicada na nota.
5. **Tela estreita:** o gráfico conjunto ficava com 100 px de altura. Os gráficos de linha ganharam altura mínima, e os painéis por modelo passam para uma coluna.

## Carrossel dos escores (pedido depois dos prints)

O pesquisador viu os prints da aba e pediu que os escores de cada ensaio virassem um carrossel: um gráfico
por vez, do mesmo tamanho, na ordem Denso → AE-LSTM → Ambos.

- **Controles:** as setas ‹ ›, os botões com o nome, as setas do teclado com o carrossel em foco e o deslizar do dedo, com encaixe em cada gráfico.
- **No navegador:**
  - começou no Denso; a seta levou ao AE-LSTM, o teclado a Ambos, e o passo seguinte voltou ao Denso;
  - os três gráficos saíram com o mesmo tamanho (391 × 240 px no painel estreito);
  - "Mostrar em todos: AE-LSTM" passou os 16 carrosséis de uma vez;
  - sem rolagem lateral da página.
- **Tamanho da página:** em 1280 px, a seção caiu de cerca de 5.400 px para cerca de 4.400 px. Cada gráfico passou a ter a largura toda do contêiner.

## Observação para o lote 25

Os escores por ensaio mostram claramente que a mudança do sinal vem segundos depois do início nominal da
falha. No F1L, por exemplo, o início nominal é em 6,4 s e o salto dos escores, em cerca de 8,7 s. É o tema
do lote 25.

## Estado final

- `.claude/launch.json` ganhou a entrada `aliado-web-lote-23`.
- `tmp/lote-23` guarda a cópia dos resultados e pode ser apagada depois da revisão.
- O commit do lote 23 foi feito pelo assistente, com a autorização do pesquisador (30/09), sem push.
