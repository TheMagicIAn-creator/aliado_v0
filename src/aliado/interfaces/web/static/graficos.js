"use strict";

/* Gráficos da aba Ciência (lotes 23 e 24), em D3 v7 (copiado do mestrado-utfpr, licença ISC).
   Cada gráfico mora num "quadro": título, nota, botões de exportação e uma área que se redesenha
   quando muda de largura, de tema ou de fonte. As cores e a fonte vêm de variáveis CSS lidas do
   próprio contêiner, e o SVG leva tudo resolvido: por isso a exportação sai em fundo branco, com
   as cores do tema claro, sem depender da página. Os números vêm prontos do servidor. */

const BR = d3.formatLocale({ decimal: ",", thousands: ".", grouping: [3], currency: ["R$", ""] });
const GRAFICOS = new Set();

/* Formatação em português */
function num(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 1e-3 || abs >= 1e6)) return value.toExponential(2).replace(".", ",");
  return Number(value).toLocaleString("pt-BR", { maximumSignificantDigits: digits });
}
function pct(value, digits = 3) { return value === null || value === undefined ? "—" : `${num(100 * value, digits)}%`; }
function seconds(ms) { return ms === null || ms === undefined ? "—" : `${num(ms / 1000, 3)} s`; }

/* Glossário: uma nota em linguagem simples para cada índice e indicador da aba. */
const GLOSSARIO = {
  sensibilidade: "Das janelas depois do início da falha, a fração que o modelo marcou como anormais (acima do limiar). 1 = marcou todas.",
  especificidade: "Das janelas saudáveis antes da falha, a fração que o modelo deixou abaixo do limiar. 1 = nenhum falso positivo.",
  precisao: "Das janelas que o modelo marcou como anormais, a fração que era mesmo de falha. Depende da proporção entre janelas saudáveis e com falha.",
  f1: "Média harmônica entre precisão e sensibilidade, de 0 a 1. Só é alta quando as duas são.",
  acuracia_balanceada: "Média entre sensibilidade e especificidade. 0,5 equivale a sortear.",
  mcc: "Coeficiente de Matthews: resume a matriz de confusão num número de −1 a 1. 0 equivale a sortear e 1 é perfeito. Engana-se menos quando uma classe é bem maior que a outra.",
  auc_roc: "Área sob a curva ROC: a chance de uma janela com falha ter escore maior que uma saudável, sem depender do limiar. 0,5 = sorteio; 1 = separação perfeita.",
  auc_pr: "Área sob a curva de precisão por sensibilidade, sem depender do limiar. O valor de sorteio é a fração de janelas com falha, cerca de 2/3 aqui.",
  fpr: "Taxa de falso positivo: 1 − especificidade. A fração das janelas saudáveis que o modelo marcou como anormais.",
  vp: "Verdadeiro positivo: janela com falha que o modelo marcou como anormal.",
  fn: "Falso negativo: janela com falha que ficou abaixo do limiar; nessa janela, a falha passou despercebida.",
  fp: "Falso positivo: janela saudável que o modelo marcou como anormal.",
  vn: "Verdadeiro negativo: janela saudável que ficou abaixo do limiar.",
  matriz: "Conta as janelas de 20 ms dos ensaios com falha: as saudáveis, antes da falha, e as com falha, depois do início. As de comissionamento e a de transição ficam de fora. Cada linha soma 100% da classe real.",
  detectados: "Ensaios com falha em que houve alarme a partir do início da falha, de 14.",
  atraso: "Tempo do início nominal da falha (o meio do registro) até o alarme, no fim da janela que o confirma. O atraso mediano usa só os ensaios detectados.",
  alarme: "Um alarme dispara quando 3 janelas seguidas ficam acima do limiar. Enquanto o escore continua acima, é o mesmo alarme.",
  alarmes_hora: "Alarmes falsos vistos em toda a operação saudável fora do treino e da calibração: o teste saudável (5 s) e o trecho antes da falha dos 14 ensaios (47 s), divididos por esses 52 s, em horas.",
  limite_superior: "Limite superior de 95% (Poisson) para os alarmes falsos por hora. Com pouco tempo de observação, mesmo sem nenhum alarme o limite fica alto: é falta de tempo, não excesso de alarmes.",
  alarmes_estimados: "Estimativa dos alarmes falsos por hora pelo encadeamento das janelas acima do limiar nos 52 s saudáveis: uma cadeia de Markov de dois estados (Brook e Evans, 1972). As sequências de 1 e de 2 janelas acima do limiar, que aparecem nos dados, dão a chance de 3 seguidas, que disparam o alarme. O intervalo de 95% sorteia os 16 trechos saudáveis.",
  janelas_acima: "Fração das janelas saudáveis acima do limiar, sem a regra das 3 seguidas. Pelo limiar p99, o esperado é cerca de 1%.",
  faixa_limiar: "Quanto a fração esperada de janelas acima do limiar pode variar só por o limiar vir de poucas janelas de calibração: com o limiar na posição r de n, ela segue uma distribuição Beta(n + 1 − r, r) (Vovk, 2012).",
  alarmes_antes: "Alarmes nas janelas saudáveis antes da falha, somando os 14 ensaios: são alarmes falsos.",
  limiar: "Valor do escore acima do qual a janela é considerada anormal: o percentil 99 dos escores de calibração, dados saudáveis separados só para isso.",
  percentil: "Posição do limiar entre os escores saudáveis de calibração. p99 = só 1% dessas janelas fica acima dele.",
  k: "O escore de uma janela é a média dos k maiores erros de reconstrução entre as 24 variáveis. Com k pequeno, poucas variáveis fora do normal já elevam o escore.",
  confirmacoes: "Quantas janelas seguidas acima do limiar disparam um alarme. Mais janelas: menos alarmes falsos e um pouco mais de atraso.",
  escore: "Erro de reconstrução do autoencoder na janela: quanto o sinal se afasta do que o modelo aprendeu como saudável.",
  razao: "Escore dividido pelo limiar do modelo, em escala logarítmica. Acima de 1, a janela é anormal. Assim os dois modelos ficam na mesma escala.",
  fases: "Comissionamento: começo do registro, fora da avaliação. Antes da falha: janelas saudáveis, usadas como negativas. Transição: a janela do início. Depois: janelas com falha.",
  inicio: "Início nominal: o meio do registro. Os arquivos do GPVS não marcam o disparo, e o conjunto diz só que a falha foi introduzida manualmente, na metade do experimento. É o início da avaliação de 27/09.",
  mudanca: "Mudança observada: o primeiro instante, depois do comissionamento, em que a média das 24 variáveis do ensaio muda de patamar. Vem de um detector de mudança sobre os sinais, sem os autoencoders.",
  detector_mudanca: "PELT (Killick, Fearnhead e Eckley, 2012): divide o registro nos trechos de média constante que melhor o explicam, pagando uma penalidade por trecho novo. A penalidade usada é a menor que não acha mudança nenhuma nos dois ensaios saudáveis.",
  classe_mudanca: "Clara: a mesma mudança aparece mesmo com penalidades até 7,5 vezes maiores, e o ensaio passa a usá-la. Fraca: some quando a penalidade cresce, pode ser variação do ambiente, e o ensaio fica no meio do registro. Nenhuma: as variáveis não mudam.",
  trecho_incerto: "Entre o meio do registro e a mudança observada pode haver falha ainda invisível. Essas janelas ficam fora da sensibilidade e da especificidade; um alarme nelas conta como detecção.",
  atraso_mudanca: "Tempo da mudança observada até o alarme. Pode ser negativo, se o alarme vier antes de a mudança ficar clara. Com 3 janelas seguidas de confirmação, o menor atraso é de 40 a 60 ms.",
  clara_oito: "Só os 8 ensaios de mudança clara, com o início no meio e com a mudança: separa o efeito do início do efeito de escolher esses 8.",
  modos: "L = IPPT: o inversor com a potência limitada. M = MPPT: o inversor buscando a potência máxima.",
  treinos: "O treino foi repetido 5 vezes, cada uma partindo de um ponto aleatório diferente, dado por um número (a semente). Os números mostrados são os do treino de referência; a faixa mostra o menor e o maior valor entre as 5 repetições.",
  ic95: "Intervalo de 95% da diferença entre os modelos, reamostrando os ensaios. Se ele inclui o zero, não há diferença clara.",
  diferenca: "Denso menos AE-LSTM, ensaio a ensaio, na média dos 14 ensaios.",
  fisica: "Falha física: um componente se danifica (IGBT, arranjo aberto). As demais são falhas de operação ou de controle.",
  teste_saudavel: "Trecho final dos registros sem falha, separado do treino e da calibração. Mede os alarmes falsos.",
  lambda: "λ, a taxa de falha: falhas esperadas por hora (ou por ano) de um componente, suposta constante.",
  horas_ano: "Quantas horas por ano contam para a taxa: 4.015 h de operação (a premissa de Baschel et al.) ou 8.760 h de calendário.",
  base_tempo: "Horas de operação: só enquanto o inversor funciona. Horas de calendário: o ano inteiro. A mesma taxa por hora dá riscos anuais diferentes.",
  mttf: "Tempo médio até a falha. Com taxa constante, é 1/λ.",
  mtbf: "Tempo médio entre falhas. Com taxa constante e reparo imediato, é 1/λ.",
  r_t: "R(t), a confiabilidade: a chance de o componente ainda não ter falhado no tempo t.",
  f_t: "F(t) = 1 − R(t): a chance de o componente já ter falhado até o tempo t.",
  severidade: "S, a severidade: nota de 1 a 10 para o efeito da falha. Aqui, pelo percentual de energia perdida.",
  ocorrencia: "O, a ocorrência: nota de 1 a 10 para a frequência da falha. Aqui, pelo percentual de chamados de manutenção.",
  deteccao: "D, a detecção: nota de 1 a 10 para a dificuldade de perceber a falha antes do efeito. 10 = quase impossível de detectar.",
  npr: "Número de prioridade de risco: S × O × D. Quanto maior, mais prioritário. As notas vêm de Cristaldi et al. (2017).",
};

/* Nota: um "i" que abre um balão ao passar o mouse, ao focar pelo teclado ou ao tocar. */
const balao = el("div", { class: "nota-balao", id: "nota-balao", role: "tooltip", hidden: true });
document.body.append(balao);
let notaFixa = null;

function abrirNota(botao) {
  balao.textContent = botao.dataset.texto;
  balao.hidden = false;
  const caixa = botao.getBoundingClientRect();
  const largura = Math.min(320, window.innerWidth - 24);
  balao.style.maxWidth = `${largura}px`;
  const esquerda = Math.min(Math.max(12, caixa.left - 12), window.innerWidth - largura - 12);
  const cabe = caixa.bottom + balao.offsetHeight + 12 < window.innerHeight;
  balao.style.left = `${esquerda}px`;
  balao.style.top = `${cabe ? caixa.bottom + 6 : caixa.top - balao.offsetHeight - 6}px`;
  botao.setAttribute("aria-describedby", "nota-balao");
}
function fecharNota(botao) {
  if (notaFixa && notaFixa !== botao) return;
  balao.hidden = true;
  botao?.removeAttribute("aria-describedby");
}

function nota(chave, extra = "") {
  const texto = [GLOSSARIO[chave] || chave, extra].filter(Boolean).join(" ");
  const botao = el("button", { class: "nota", type: "button", "aria-label": `O que é: ${texto.slice(0, 60)}`, text: "i" });
  botao.dataset.texto = texto;
  botao.addEventListener("pointerenter", () => { if (!notaFixa) abrirNota(botao); });
  botao.addEventListener("pointerleave", () => { if (!notaFixa) fecharNota(botao); });
  botao.addEventListener("focus", () => abrirNota(botao));
  botao.addEventListener("blur", () => { notaFixa = null; fecharNota(botao); });
  botao.addEventListener("click", (event) => {
    event.stopPropagation();
    notaFixa = notaFixa === botao ? null : botao;
    if (notaFixa) abrirNota(botao); else fecharNota(botao);
  });
  return botao;
}
document.addEventListener("click", () => { if (notaFixa) { const b = notaFixa; notaFixa = null; fecharNota(b); } });
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !balao.hidden) { notaFixa = null; balao.hidden = true; } });

/* Rótulo com nota ao lado. */
function comNota(texto, chave, extra) { return el("span", { class: "com-nota" }, texto, nota(chave, extra)); }

/* Dica dos gráficos: o valor exato sob o mouse. */
const dica = el("div", { class: "grafico-dica", hidden: true });
document.body.append(dica);
function mostrarDica(event, linhas) {
  dica.replaceChildren(...linhas.map((linha) => el("span", { text: linha })));
  dica.hidden = false;
  const x = Math.min(event.clientX + 14, window.innerWidth - dica.offsetWidth - 8);
  const y = Math.max(8, event.clientY - dica.offsetHeight - 10);
  dica.style.left = `${x}px`;
  dica.style.top = `${y}px`;
}
function esconderDica() { dica.hidden = true; }

/* Cores e fonte resolvidas a partir do contêiner (o tema dele, ou o claro, na exportação). */
function coresDe(node) {
  const style = getComputedStyle(node);
  const v = (name) => style.getPropertyValue(name).trim();
  return {
    denso: v("--g-denso"), lstm: v("--g-lstm"), texto: v("--g-texto"), suave: v("--g-suave"), grade: v("--g-grade"),
    eixo: v("--g-eixo"), fundo: v("--g-fundo"), limiar: v("--g-limiar"), inicio: v("--g-inicio"), vazio: v("--g-vazio"),
    mudanca: v("--g-mudanca"),
    fases: { comissionamento: v("--g-fase-comissionamento"), pre_teste: v("--g-fase-antes"),
      transicao: v("--g-fase-transicao"), pos_falha: v("--g-fase-depois") },
    fonte: style.fontFamily,
  };
}
const MODELO_COR = (cores, modelo) => (modelo === "lstm" ? cores.lstm : cores.denso);

/* Base de todo gráfico: SVG com título, descrição, fonte e fundo. */
function base(area, largura, altura, cores, { titulo = "", descricao = "", margem }) {
  const svgNode = d3.create("svg").attr("xmlns", "http://www.w3.org/2000/svg").attr("viewBox", `0 0 ${largura} ${altura}`)
    .attr("width", largura).attr("height", altura).attr("role", "img").attr("style", `max-width: ${largura}px`)
    .attr("font-family", cores.fonte).attr("font-size", 12).attr("fill", cores.texto);
  svgNode.append("title").text(titulo);
  svgNode.append("desc").text(descricao || titulo);
  svgNode.append("rect").attr("class", "fundo").attr("width", largura).attr("height", altura).attr("fill", cores.fundo);
  const m = { top: 14, right: 16, bottom: 42, left: 58, ...margem };
  const g = svgNode.append("g").attr("transform", `translate(${m.left},${m.top})`);
  area.replaceChildren(svgNode.node());
  return { svg: svgNode, g, largura: largura - m.left - m.right, altura: altura - m.top - m.bottom, m };
}

function eixos(b, x, y, cores, { xRotulo = "", yRotulo = "", xFormato, yFormato, yTicks = 5, xTicks, yValores } = {}) {
  const ticksY = (axis) => (yValores ? axis.tickValues(yValores) : axis.ticks(yTicks));
  const grade = b.g.append("g").call(ticksY(d3.axisLeft(y)).tickSize(-b.largura).tickFormat(""));
  grade.selectAll("line").attr("stroke", cores.grade);
  grade.select(".domain").remove();
  const eixoX = b.g.append("g").attr("transform", `translate(0,${b.altura})`)
    .call(d3.axisBottom(x).ticks(xTicks ?? (b.largura < 360 ? 4 : 7)).tickFormat(xFormato || BR.format("~g")));
  const eixoY = b.g.append("g").call(ticksY(d3.axisLeft(y)).tickFormat(yFormato || BR.format("~g")));
  for (const eixo of [eixoX, eixoY]) {
    eixo.selectAll("line,path").attr("stroke", cores.eixo);
    eixo.selectAll("text").attr("fill", cores.suave).attr("font-size", 11).attr("font-family", cores.fonte);
  }
  if (xRotulo) {
    b.g.append("text").attr("x", b.largura / 2).attr("y", b.altura + 34).attr("text-anchor", "middle")
      .attr("font-size", 12).attr("fill", cores.suave).text(xRotulo);
  }
  if (yRotulo) {
    b.g.append("text").attr("transform", `translate(${-44},${b.altura / 2}) rotate(-90)`).attr("text-anchor", "middle")
      .attr("font-size", 12).attr("fill", cores.suave).text(yRotulo);
  }
  return { eixoX, eixoY };
}

/* Linhas: séries, escala log opcional, faixas, linhas de referência e marcas. */
function graficoLinhas(area, largura, cores, o) {
  // Proporção pela largura, com altura mínima para continuar legível em tela estreita.
  const altura = o.altura || Math.max(o.alturaMinima ?? 200, Math.round(largura * (o.proporcao || 0.42)));
  const b = base(area, largura, altura, cores, { titulo: o.titulo, descricao: o.descricao,
    margem: { top: o.legenda ? 30 : 14, left: o.margemEsquerda || 58 } });
  const xs = o.series.flatMap((s) => s.pontos.map((p) => p[0]));
  const ys = o.series.flatMap((s) => s.pontos.map((p) => p[1])).filter((v) => Number.isFinite(v));
  const x = d3.scaleLinear().domain(o.xDominio || d3.extent(xs)).range([0, b.largura]);
  let y;
  if (o.log) {
    const lo = o.yDominio?.[0] ?? Math.max(1e-3, d3.min(ys) / 1.5);
    const hi = o.yDominio?.[1] ?? d3.max(ys) * 1.5;
    y = d3.scaleLog().domain([lo, hi]).range([b.altura, 0]).clamp(true);
  } else {
    y = d3.scaleLinear().domain(o.yDominio || [Math.min(0, d3.min(ys)), d3.max(ys) * 1.05 || 1]).nice().range([b.altura, 0]);
  }
  for (const faixa of o.faixas || []) {
    b.g.append("rect").attr("x", x(faixa.de)).attr("width", Math.max(1, x(faixa.ate) - x(faixa.de))).attr("y", 0)
      .attr("height", b.altura).attr("fill", faixa.cor).attr("opacity", faixa.opacidade ?? 0.18);
  }
  // Na escala log, grade e rótulos só nas potências de 10; de 10⁴ para cima e abaixo de 0,01, como 10ⁿ.
  const decadas = o.log ? d3.range(Math.ceil(Math.log10(y.domain()[0])), Math.floor(Math.log10(y.domain()[1])) + 1) : null;
  const passo = decadas && decadas.length > 7 ? Math.ceil(decadas.length / 7) : 1;
  const sobrescrito = (n) => String(n).replace(/-/g, "⁻").replace(/\d/g, (c) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[c]);
  const yFormatoLog = (v) => { const e = Math.round(Math.log10(v)); return e >= 4 || e <= -3 ? `10${sobrescrito(e)}` : BR.format("~g")(v); };
  eixos(b, x, y, cores, { xRotulo: o.xRotulo, yRotulo: o.yRotulo, xFormato: o.xFormato,
    yFormato: o.yFormato || (o.log ? yFormatoLog : undefined),
    yValores: decadas ? decadas.filter((e) => e % passo === 0 || e === 0).map((e) => 10 ** e) : undefined });
  for (const linha of o.linhasV || []) {
    b.g.append("line").attr("x1", x(linha.x)).attr("x2", x(linha.x)).attr("y1", 0).attr("y2", b.altura)
      .attr("stroke", linha.cor).attr("stroke-width", linha.espessura || 1.4).attr("stroke-dasharray", linha.traco || "5 4");
  }
  for (const linha of o.linhasH || []) {
    b.g.append("line").attr("x1", 0).attr("x2", b.largura).attr("y1", y(linha.y)).attr("y2", y(linha.y))
      .attr("stroke", linha.cor).attr("stroke-width", 1.4).attr("stroke-dasharray", "6 4");
    if (linha.rotulo) {
      b.g.append("text").attr("x", b.largura - 4).attr("y", y(linha.y) - 5).attr("text-anchor", "end")
        .attr("font-size", 11).attr("fill", linha.cor).text(linha.rotulo);
    }
  }
  const caminho = d3.line().defined((p) => Number.isFinite(p[1])).x((p) => x(p[0])).y((p) => y(p[1]));
  for (const serie of o.series) {
    b.g.append("path").datum(serie.pontos).attr("fill", "none").attr("stroke", serie.cor)
      .attr("stroke-width", serie.espessura || 1.6).attr("stroke-opacity", serie.opacidade ?? 0.95).attr("d", caminho);
  }
  const simbolo = { triangulo: d3.symbolTriangle, xis: d3.symbolCross, circulo: d3.symbolCircle, losango: d3.symbolDiamond };
  for (const marca of o.marcas || []) {
    b.g.append("path").attr("transform", `translate(${x(marca.x)},${y(marca.y)})${marca.forma === "xis" ? " rotate(45)" : ""}`)
      .attr("d", d3.symbol(simbolo[marca.forma] || d3.symbolCircle, marca.tamanho || 64)())
      .attr("fill", marca.cor).attr("stroke", cores.fundo).attr("stroke-width", 1).attr("tabindex", 0)
      .on("pointerenter focus", (event) => mostrarDica(event.type === "focus" ? posicao(event.target) : event, marca.dica))
      .on("pointerleave blur", esconderDica);
  }
  if (o.legenda) legenda(b, o.series.filter((s) => s.nome), cores);
  // Guia vertical: o valor de cada série no ponto mais próximo do mouse.
  const guia = b.g.append("line").attr("y1", 0).attr("y2", b.altura).attr("stroke", cores.suave).attr("opacity", 0);
  const perto = d3.bisector((p) => p[0]).center;
  b.g.append("rect").attr("width", b.largura).attr("height", b.altura).attr("fill", "transparent")
    .on("pointermove", (event) => {
      const [px] = d3.pointer(event);
      const alvo = x.invert(px);
      const linhas = [o.dicaX ? o.dicaX(alvo) : num(alvo)];
      for (const serie of o.series) {
        const p = serie.pontos[perto(serie.pontos, alvo)];
        if (p) linhas.push(`${serie.nome || ""}: ${o.dicaY ? o.dicaY(p[1]) : num(p[1])}`);
      }
      guia.attr("x1", px).attr("x2", px).attr("opacity", 0.6);
      mostrarDica(event, linhas);
    })
    .on("pointerleave", () => { guia.attr("opacity", 0); esconderDica(); });
  b.svg.selectAll("path[tabindex]").raise();
  return b.svg.node();
}

function posicao(node) { const r = node.getBoundingClientRect(); return { clientX: r.right, clientY: r.top }; }

function legenda(b, series, cores) {
  const g = b.svg.append("g").attr("transform", `translate(${b.m.left},12)`);
  let deslocamento = 0;
  for (const serie of series) {
    g.append("rect").attr("x", deslocamento).attr("y", -5).attr("width", 16).attr("height", 3).attr("fill", serie.cor);
    const texto = g.append("text").attr("x", deslocamento + 22).attr("y", 0).attr("font-size", 12).attr("fill", cores.texto)
      .text(serie.nome);
    deslocamento += 34 + (texto.node().getComputedTextLength?.() || serie.nome.length * 7);
  }
}

/* Mapa de calor: linhas × colunas, com o valor em cada célula. */
function mapaDeCalor(area, largura, cores, o) {
  const alturaLinha = o.alturaLinha || 30;
  const altura = 34 + alturaLinha * o.linhas.length + 28;
  const b = base(area, largura, altura, cores, { titulo: o.titulo, descricao: o.descricao,
    margem: { top: 30, left: o.margemEsquerda || 150, bottom: 28, right: 12 } });
  const x = d3.scaleBand().domain(o.colunas.map((c) => c.id)).range([0, b.largura]).padding(0.06);
  const y = d3.scaleBand().domain(o.linhas.map((l) => l.id)).range([0, b.altura]).padding(0.08);
  const escala = o.escala || d3.scaleSequential(d3.interpolateViridis).domain(o.dominio || [0, 1]);
  for (const coluna of o.colunas) {
    b.g.append("text").attr("x", x(coluna.id) + x.bandwidth() / 2).attr("y", -10).attr("text-anchor", "middle")
      .attr("font-size", 12).attr("fill", cores.texto).text(coluna.rotulo);
  }
  for (const linha of o.linhas) {
    b.g.append("text").attr("x", -8).attr("y", y(linha.id) + y.bandwidth() / 2 + 4).attr("text-anchor", "end")
      .attr("font-size", 12).attr("fill", cores.texto).text(linha.rotulo);
    for (const coluna of o.colunas) {
      const valor = o.valor(linha, coluna);
      const cor = valor === null || valor === undefined ? cores.vazio : escala(valor);
      const claro = valor !== null && valor !== undefined && d3.hsl(cor).l < 0.55;
      b.g.append("rect").attr("x", x(coluna.id)).attr("y", y(linha.id)).attr("width", x.bandwidth())
        .attr("height", y.bandwidth()).attr("rx", 3).attr("fill", cor).attr("tabindex", 0)
        .on("pointerenter focus", (event) => mostrarDica(event.type === "focus" ? posicao(event.target) : event, o.dica(linha, coluna, valor)))
        .on("pointerleave blur", esconderDica);
      b.g.append("text").attr("x", x(coluna.id) + x.bandwidth() / 2).attr("y", y(linha.id) + y.bandwidth() / 2 + 4)
        .attr("text-anchor", "middle").attr("font-size", 12).attr("pointer-events", "none")
        .attr("fill", claro ? "#ffffff" : "#0b0b0b").text(o.formato(valor));
    }
  }
  return b.svg.node();
}

/* Matriz de confusão 2×2, normalizada por classe real, em azuis, como a figura antiga. */
function matrizDeConfusao(area, largura, cores, o) {
  const lado = Math.min(largura, 420);
  const b = base(area, lado, Math.round(lado * 0.78), cores, { titulo: o.titulo, descricao: o.descricao,
    margem: { top: 34, left: 96, bottom: 16, right: 12 } });
  const { vp, fn, fp, vn } = o.contagens;
  const celulas = [
    { real: "Saudável", prevista: "Saudável", n: vn, total: vn + fp, chave: "vn", sigla: "VN" },
    { real: "Saudável", prevista: "Falha", n: fp, total: vn + fp, chave: "fp", sigla: "FP" },
    { real: "Falha", prevista: "Saudável", n: fn, total: fn + vp, chave: "fn", sigla: "FN" },
    { real: "Falha", prevista: "Falha", n: vp, total: fn + vp, chave: "vp", sigla: "VP" },
  ];
  const x = d3.scaleBand().domain(["Saudável", "Falha"]).range([0, b.largura]).padding(0.04);
  const y = d3.scaleBand().domain(["Saudável", "Falha"]).range([0, b.altura]).padding(0.04);
  b.g.append("text").attr("x", b.largura / 2).attr("y", -22).attr("text-anchor", "middle").attr("font-size", 12)
    .attr("fill", cores.suave).text("Classe predita");
  b.g.append("text").attr("transform", `translate(-80,${b.altura / 2}) rotate(-90)`).attr("text-anchor", "middle")
    .attr("font-size", 12).attr("fill", cores.suave).text("Classe real");
  for (const rotulo of ["Saudável", "Falha"]) {
    b.g.append("text").attr("x", x(rotulo) + x.bandwidth() / 2).attr("y", -6).attr("text-anchor", "middle")
      .attr("font-size", 12).attr("fill", cores.texto).text(rotulo);
    b.g.append("text").attr("x", -8).attr("y", y(rotulo) + y.bandwidth() / 2 + 4).attr("text-anchor", "end")
      .attr("font-size", 12).attr("fill", cores.texto).text(rotulo);
  }
  for (const c of celulas) {
    const fracao = c.total ? c.n / c.total : 0;
    const cor = d3.interpolateBlues(0.08 + 0.87 * fracao);
    b.g.append("rect").attr("x", x(c.prevista)).attr("y", y(c.real)).attr("width", x.bandwidth())
      .attr("height", y.bandwidth()).attr("rx", 4).attr("fill", cor).attr("tabindex", 0)
      .on("pointerenter focus", (event) => mostrarDica(event.type === "focus" ? posicao(event.target) : event,
        [`${c.sigla}: ${BR.format(",")(c.n)} janelas (${pct(fracao)} da classe real)`, GLOSSARIO[c.chave]]))
      .on("pointerleave blur", esconderDica);
    const texto = b.g.append("text").attr("text-anchor", "middle").attr("pointer-events", "none")
      .attr("fill", fracao > 0.55 ? "#ffffff" : "#0b0b0b");
    const cx = x(c.prevista) + x.bandwidth() / 2, cy = y(c.real) + y.bandwidth() / 2;
    texto.append("tspan").attr("x", cx).attr("y", cy - 4).attr("font-size", 17).attr("font-weight", 600)
      .text(BR.format(",")(c.n));
    texto.append("tspan").attr("x", cx).attr("y", cy + 16).attr("font-size", 12).text(`${pct(fracao)} · ${c.sigla}`);
  }
  return b.svg.node();
}

/* Barras agrupadas (verticais): um grupo por categoria, uma barra por série. */
function barrasAgrupadas(area, largura, cores, o) {
  const altura = o.altura || 280;
  const b = base(area, largura, altura, cores, { titulo: o.titulo, descricao: o.descricao,
    margem: { top: o.series.length > 1 ? 30 : 14, bottom: o.rotulosInclinados ? 86 : 42 } });
  const x = d3.scaleBand().domain(o.grupos.map((g) => g.id)).range([0, b.largura]).padding(0.22);
  const dentro = d3.scaleBand().domain(o.series.map((s) => s.id)).range([0, x.bandwidth()]).padding(0.08);
  const valores = o.grupos.flatMap((g) => o.series.map((s) => o.valor(g, s))).filter((v) => Number.isFinite(v));
  const y = d3.scaleLinear().domain(o.dominio || [0, d3.max(valores) * 1.08 || 1]).nice().range([b.altura, 0]);
  const { eixoX } = eixos(b, x, y, cores, { yRotulo: o.yRotulo, yFormato: o.yFormato,
    xFormato: (id) => o.grupos.find((g) => g.id === id)?.rotulo ?? id });
  if (o.rotulosInclinados) {
    eixoX.selectAll("text").attr("transform", "rotate(-45)").attr("text-anchor", "end").attr("dx", "-0.5em").attr("dy", "0.2em");
  }
  for (const grupo of o.grupos) {
    for (const serie of o.series) {
      const valor = o.valor(grupo, serie);
      if (!Number.isFinite(valor)) continue;
      const cor = typeof serie.cor === "function" ? serie.cor(grupo) : serie.cor;
      b.g.append("rect").attr("x", x(grupo.id) + dentro(serie.id)).attr("width", dentro.bandwidth())
        .attr("y", y(Math.max(0, valor))).attr("height", Math.abs(y(valor) - y(0))).attr("rx", 2)
        .attr("fill", cor).attr("tabindex", 0)
        .on("pointerenter focus", (event) => mostrarDica(event.type === "focus" ? posicao(event.target) : event, o.dica(grupo, serie, valor)))
        .on("pointerleave blur", esconderDica);
    }
  }
  if (o.series.length > 1) legenda(b, o.series, cores);
  return b.svg.node();
}

/* Barras horizontais: um item por linha, com o valor escrito ao lado. */
function barrasHorizontais(area, largura, cores, o) {
  const altura = 16 + 34 * o.itens.length;
  const b = base(area, largura, altura, cores, { titulo: o.titulo, descricao: o.descricao,
    margem: { top: 8, left: o.margemEsquerda || 190, bottom: 8, right: 70 } });
  const y = d3.scaleBand().domain(o.itens.map((i) => i.id)).range([0, b.altura]).padding(0.22);
  const x = d3.scaleLinear().domain([0, d3.max(o.itens, (i) => i.valor) || 1]).range([0, b.largura]);
  for (const item of o.itens) {
    b.g.append("text").attr("x", -8).attr("y", y(item.id) + y.bandwidth() / 2 + 4).attr("text-anchor", "end")
      .attr("font-size", 12).attr("fill", cores.texto).text(item.rotulo);
    b.g.append("rect").attr("x", 0).attr("y", y(item.id)).attr("width", Math.max(2, x(item.valor)))
      .attr("height", y.bandwidth()).attr("rx", 3).attr("fill", item.cor || cores.denso);
    b.g.append("text").attr("x", x(item.valor) + 6).attr("y", y(item.id) + y.bandwidth() / 2 + 4)
      .attr("font-size", 12).attr("fill", cores.texto).text(o.formato(item.valor));
  }
  return b.svg.node();
}

/* Ponto com faixa: uma linha por métrica, um ponto por modelo e a faixa dos treinamentos. */
function pontoComFaixa(area, largura, cores, o) {
  const altura = 40 + 42 * o.itens.length;
  const b = base(area, largura, altura, cores, { titulo: o.titulo, descricao: o.descricao,
    margem: { top: 30, left: o.margemEsquerda || 170, bottom: 36, right: 16 } });
  const y = d3.scaleBand().domain(o.itens.map((i) => i.id)).range([0, b.altura]).padding(0.3);
  const x = d3.scaleLinear().domain(o.dominio || [0, 1]).range([0, b.largura]);
  const grade = b.g.append("g").call(d3.axisBottom(x).ticks(5).tickSize(b.altura).tickFormat(""));
  grade.selectAll("line").attr("stroke", cores.grade);
  grade.select(".domain").remove();
  const eixoX = b.g.append("g").attr("transform", `translate(0,${b.altura})`)
    .call(d3.axisBottom(x).ticks(5).tickFormat(BR.format("~g")));
  eixoX.selectAll("line,path").attr("stroke", cores.eixo);
  eixoX.selectAll("text").attr("fill", cores.suave).attr("font-size", 11).attr("font-family", cores.fonte);
  if (o.xRotulo) {
    b.g.append("text").attr("x", b.largura / 2).attr("y", b.altura + 32).attr("text-anchor", "middle")
      .attr("font-size", 12).attr("fill", cores.suave).text(o.xRotulo);
  }
  const passo = y.bandwidth() / (o.series.length + 1);
  for (const item of o.itens) {
    b.g.append("text").attr("x", -10).attr("y", y(item.id) + y.bandwidth() / 2 + 4).attr("text-anchor", "end")
      .attr("font-size", 12).attr("fill", cores.texto).text(item.rotulo);
    o.series.forEach((serie, indice) => {
      const dado = o.valor(item, serie);
      if (!dado) return;
      const cy = y(item.id) + passo * (indice + 1);
      const cor = serie.cor;
      b.g.append("line").attr("x1", x(dado.faixa[0])).attr("x2", x(dado.faixa[1])).attr("y1", cy).attr("y2", cy)
        .attr("stroke", cor).attr("stroke-width", 3).attr("stroke-linecap", "round").attr("opacity", 0.5);
      b.g.append("path").attr("transform", `translate(${x(dado.valor)},${cy})`)
        .attr("d", d3.symbol(indice ? d3.symbolDiamond : d3.symbolCircle, 70)()).attr("fill", cor)
        .attr("stroke", cores.fundo).attr("tabindex", 0)
        .on("pointerenter focus", (event) => mostrarDica(event.type === "focus" ? posicao(event.target) : event, [
          `${serie.nome} · ${item.rotulo}: ${num(dado.valor)}`, `Nos 5 treinamentos: de ${num(dado.faixa[0])} a ${num(dado.faixa[1])}`]))
        .on("pointerleave blur", esconderDica);
    });
  }
  legenda(b, o.series, cores);
  return b.svg.node();
}

/* Linha do tempo por item: um trilho opcional, uma ligação entre dois valores e marcas com forma e cor. */
function linhaDoTempo(area, largura, cores, o) {
  const alturaLinha = o.alturaLinha || 30;
  const esquerda = o.margemEsquerda || 170;
  // A legenda quebra em linhas quando não cabe (largura estimada pelo número de letras).
  const posicoes = [];
  let coluna = 0, linha = 0;
  for (const item of o.legenda || []) {
    const ocupa = 30 + item.nome.length * 6.6;
    if (coluna && coluna + ocupa > largura - esquerda - 16) { coluna = 0; linha += 1; }
    posicoes.push([coluna, linha * 18]);
    coluna += ocupa;
  }
  const extra = 18 * linha;
  const altura = 44 + extra + alturaLinha * o.itens.length + 40;
  const b = base(area, largura, altura, cores, { titulo: o.titulo, descricao: o.descricao,
    margem: { top: 34 + extra, left: esquerda, bottom: 40, right: 16 } });
  const y = d3.scaleBand().domain(o.itens.map((i) => i.id)).range([0, b.altura]).padding(0.2);
  const x = d3.scaleLinear().domain(o.dominio).range([0, b.largura]);
  const ticks = b.largura < 360 ? 4 : 8;
  const grade = b.g.append("g").call(d3.axisBottom(x).ticks(ticks).tickSize(b.altura).tickFormat(""));
  grade.selectAll("line").attr("stroke", cores.grade);
  grade.select(".domain").remove();
  const eixoX = b.g.append("g").attr("transform", `translate(0,${b.altura})`)
    .call(d3.axisBottom(x).ticks(ticks).tickFormat(o.xFormato || BR.format("~g")));
  eixoX.selectAll("line,path").attr("stroke", cores.eixo);
  eixoX.selectAll("text").attr("fill", cores.suave).attr("font-size", 11).attr("font-family", cores.fonte);
  if (o.xRotulo) {
    b.g.append("text").attr("x", b.largura / 2).attr("y", b.altura + 34).attr("text-anchor", "middle")
      .attr("font-size", 12).attr("fill", cores.suave).text(o.xRotulo);
  }
  const simbolo = { circulo: d3.symbolCircle, losango: d3.symbolDiamond, quadrado: d3.symbolSquare };
  for (const item of o.itens) {
    const cy = y(item.id) + y.bandwidth() / 2;
    b.g.append("text").attr("x", -10).attr("y", cy + 4).attr("text-anchor", "end").attr("font-size", 12)
      .attr("fill", cores.texto).text(item.rotulo);
    if (item.trilho) {
      b.g.append("rect").attr("x", x(item.trilho[0])).attr("width", Math.max(1, x(item.trilho[1]) - x(item.trilho[0])))
        .attr("y", cy - 5).attr("height", 10).attr("rx", 5).attr("fill", cores.vazio);
    }
    if (item.ligar) {
      b.g.append("line").attr("x1", x(item.ligar[0])).attr("x2", x(item.ligar[1])).attr("y1", cy).attr("y2", cy)
        .attr("stroke", item.corLigacao || cores.suave).attr("stroke-width", 2.5).attr("stroke-linecap", "round");
    }
    for (const ponto of item.pontos) {
      b.g.append("path").attr("transform", `translate(${x(ponto.x)},${cy})`)
        .attr("d", d3.symbol(simbolo[ponto.forma] || d3.symbolCircle, ponto.tamanho || 80)())
        .attr("fill", ponto.vazado ? cores.fundo : ponto.cor).attr("stroke", ponto.cor).attr("stroke-width", 1.6)
        .attr("tabindex", 0)
        .on("pointerenter focus", (event) => mostrarDica(event.type === "focus" ? posicao(event.target) : event, ponto.dica))
        .on("pointerleave blur", esconderDica);
    }
  }
  const g = b.svg.append("g").attr("transform", `translate(${b.m.left},14)`);
  (o.legenda || []).forEach((item, i) => {
    const [dx, dy] = posicoes[i];
    g.append("path").attr("transform", `translate(${dx + 6},${dy - 4})`)
      .attr("d", d3.symbol(simbolo[item.forma] || d3.symbolCircle, 60)())
      .attr("fill", item.vazado ? cores.fundo : item.cor).attr("stroke", item.cor).attr("stroke-width", 1.6);
    g.append("text").attr("x", dx + 16).attr("y", dy).attr("font-size", 12).attr("fill", cores.texto).text(item.nome);
  });
  return b.svg.node();
}

/* Quadro: título, nota, exportação e redesenho por largura, tema e fonte. */
function quadro({ titulo, chave, extra, arquivo, desenhar, csv, preguicoso = false, classe = "" }) {
  const area = el("div", { class: "quadro-area" });
  const acoes = el("span", { class: "quadro-acoes" });
  const figura = el("figure", { class: `quadro ${classe}` },
    el("figcaption", { class: "quadro-titulo" }, el("span", {}, titulo, ...(chave ? [nota(chave, extra)] : [])), acoes), area);
  const registro = { area, desenhar, largura: 0, visivel: !preguicoso, titulo };
  const redesenhar = () => {
    if (!registro.visivel || !area.isConnected) return;
    const largura = Math.floor(area.clientWidth);
    if (!largura) return;
    registro.largura = largura;
    desenhar(area, largura, coresDe(area));
  };
  registro.redesenhar = redesenhar;
  if (arquivo) {
    acoes.append(el("button", { class: "link", type: "button", text: "SVG", title: "Baixar como SVG (fundo branco)",
      onclick: () => exportar(registro, arquivo, "svg") }),
    el("button", { class: "link", type: "button", text: "PNG", title: "Baixar como PNG, 300 dpi (fundo branco)",
      onclick: () => exportar(registro, arquivo, "png") }));
  }
  if (csv) {
    acoes.append(el("button", { class: "link", type: "button", text: "CSV", title: "Baixar os dados em CSV",
      onclick: () => baixarCSV(csv(), `${arquivo || "dados"}.csv`) }));
  }
  let pendente = 0;
  new ResizeObserver(() => {
    if (Math.floor(area.clientWidth) === registro.largura) return;
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(redesenhar);
  }).observe(area);
  if (preguicoso) {
    const observador = new IntersectionObserver((entradas) => {
      if (entradas.some((e) => e.isIntersecting)) { registro.visivel = true; observador.disconnect(); redesenhar(); }
    }, { rootMargin: "300px" });
    observador.observe(figura);
  }
  GRAFICOS.add(registro);
  requestAnimationFrame(redesenhar);
  return figura;
}

/* Tema e fonte: redesenha os gráficos visíveis. */
new MutationObserver(() => {
  for (const registro of GRAFICOS) {
    if (!registro.area.isConnected) GRAFICOS.delete(registro);
    else registro.redesenhar();
  }
}).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "data-font"] });

/* Exportação: redesenha fora da tela, em fundo branco e com as cores do tema claro. */
async function exportar(registro, arquivo, formato) {
  const largura = 1000;
  const fora = el("div", { class: "grafico-claro grafico-exportacao" });
  fora.style.width = `${largura}px`;
  document.body.append(fora);
  try {
    const svgNode = registro.desenhar(fora, largura, coresDe(fora));
    const texto = new XMLSerializer().serializeToString(svgNode);
    if (formato === "svg") {
      baixar(new Blob([texto], { type: "image/svg+xml;charset=utf-8" }), `${arquivo}.svg`);
      return;
    }
    const imagem = new Image();
    imagem.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(texto)}`;
    await imagem.decode();
    const escala = 300 / 96;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(svgNode.width.baseVal.value * escala);
    canvas.height = Math.round(svgNode.height.baseVal.value * escala);
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.scale(escala, escala);
    ctx.drawImage(imagem, 0, 0);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    baixar(blob, `${arquivo}.png`);
  } catch (error) {
    toast(`Não foi possível exportar: ${error.message || error}`);
  } finally {
    fora.remove();
  }
}

function baixar(blob, nome) {
  const link = el("a", { href: URL.createObjectURL(blob), download: nome });
  document.body.append(link);
  link.click();
  setTimeout(() => { URL.revokeObjectURL(link.href); link.remove(); }, 1000);
}

/* CSV com ponto e vírgula e vírgula decimal, que o Excel em português abre direto. */
function baixarCSV(linhas, nome) {
  const celula = (valor) => {
    if (valor === null || valor === undefined) return "";
    const texto = typeof valor === "number" ? String(valor).replace(".", ",") : String(valor);
    return /[;"\n]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
  };
  const corpo = linhas.map((linha) => linha.map(celula).join(";")).join("\r\n");
  baixar(new Blob(["﻿" + corpo], { type: "text/csv;charset=utf-8" }), nome);
}
