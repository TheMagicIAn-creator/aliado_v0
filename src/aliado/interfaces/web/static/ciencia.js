"use strict";

/* Aba Ciência (lote 20): resultados, exploradores do GPVS, confiabilidade e FMECA.
   Todo número vem do serviço científico no servidor; aqui só se desenha, em SVG próprio. */

const science = { tab: "resultados", status: null, options: null, timer: null, result: null };
const SCIENCE_TABS = [["resultados", "Resultados"], ["limiar", "Limiar"], ["alarme", "Alarme e detecção"],
  ["confiabilidade", "Confiabilidade"], ["fmeca", "FMECA"]];
const SVGNS = "http://www.w3.org/2000/svg";

/* Formatação */
function num(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 1e-3 || abs >= 1e6)) return value.toExponential(2).replace(".", ",");
  return Number(value).toLocaleString("pt-BR", { maximumSignificantDigits: digits });
}
function pct(value, digits = 3) { return value === null || value === undefined ? "—" : `${num(100 * value, digits)}%`; }
function seconds(ms) { return ms === null || ms === undefined ? "—" : `${num(ms / 1000, 3)} s`; }

/* SVG */
function svg(tag, attrs = {}, ...children) {
  const node = document.createElementNS(SVGNS, tag);
  for (const [key, value] of Object.entries(attrs)) if (value !== undefined && value !== null) node.setAttribute(key, value);
  for (const child of children) if (child !== null && child !== undefined) node.append(child);
  return node;
}

function ticks(min, max, count = 5) {
  if (min === max) return [min];
  const step = (max - min) / (count - 1);
  return Array.from({ length: count }, (_, i) => min + i * step);
}

/* Gráfico de linhas com eixos; faixas verticais, linhas horizontais e marcas são opcionais. */
function chart({ series, xLabel = "", yLabel = "", width = 680, height = 250, yMin, yMax, xMin, xMax,
  bands = [], hLines = [], vLines = [], marks = [], label }) {
  // Com mais de uma série, a legenda ganha uma faixa própria acima da área do gráfico.
  const pad = { left: 56, right: 14, top: series.length > 1 ? 32 : 14, bottom: 38 };
  const xs = series.flatMap((s) => s.points.map((p) => p[0]));
  const ys = series.flatMap((s) => s.points.map((p) => p[1])).concat(hLines.map((h) => h.y));
  const x0 = xMin ?? Math.min(...xs), x1 = xMax ?? Math.max(...xs);
  const y0 = yMin ?? Math.min(0, ...ys), y1 = yMax ?? (Math.max(...ys) * 1.05 || 1);
  const sx = (x) => pad.left + (width - pad.left - pad.right) * (x - x0) / ((x1 - x0) || 1);
  const sy = (y) => height - pad.bottom - (height - pad.top - pad.bottom) * (Math.min(Math.max(y, y0), y1) - y0) / ((y1 - y0) || 1);
  const root = svg("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart", role: "img", "aria-label": label || yLabel });
  for (const band of bands) {
    root.append(svg("rect", { x: sx(band.from), y: pad.top, width: Math.max(1, sx(band.to) - sx(band.from)),
      height: height - pad.top - pad.bottom, class: `chart-band ${band.class || ""}` }, svg("title", {}, band.label || "")));
  }
  for (const value of ticks(y0, y1)) {
    root.append(svg("line", { x1: pad.left, x2: width - pad.right, y1: sy(value), y2: sy(value), class: "chart-grid" }),
      svg("text", { x: pad.left - 6, y: sy(value) + 4, class: "chart-tick", "text-anchor": "end" }, num(value)));
  }
  const whole = xs.every(Number.isInteger);  // janelas e anos inteiros: rótulos sem fração
  for (const raw of ticks(x0, x1)) {
    const value = whole ? Math.round(raw) : raw;
    root.append(svg("text", { x: sx(value), y: height - pad.bottom + 16, class: "chart-tick", "text-anchor": "middle" }, num(value)));
  }
  root.append(svg("text", { x: (pad.left + width - pad.right) / 2, y: height - 4, class: "chart-label", "text-anchor": "middle" }, xLabel),
    svg("text", { x: 12, y: pad.top + (height - pad.top - pad.bottom) / 2, class: "chart-label", "text-anchor": "middle",
      transform: `rotate(-90 12 ${pad.top + (height - pad.top - pad.bottom) / 2})` }, yLabel));
  for (const line of vLines) {
    root.append(svg("line", { x1: sx(line.x), x2: sx(line.x), y1: pad.top, y2: height - pad.bottom, class: `chart-vline ${line.class || ""}` },
      svg("title", {}, line.label || "")));
  }
  for (const item of series) {
    const d = item.points.map((p, i) => `${i ? "L" : "M"}${sx(p[0]).toFixed(1)} ${sy(p[1]).toFixed(1)}`).join("");
    root.append(svg("path", { d, class: "chart-line", style: `stroke: ${item.color || "var(--chart-a)"}` }, svg("title", {}, item.label || "")));
  }
  for (const line of hLines) {
    root.append(svg("line", { x1: pad.left, x2: width - pad.right, y1: sy(line.y), y2: sy(line.y), class: `chart-hline ${line.class || ""}` }),
      svg("text", { x: width - pad.right - 4, y: sy(line.y) - 5, class: "chart-tick", "text-anchor": "end" }, line.label || ""));
  }
  for (const mark of marks) {
    root.append(svg("circle", { cx: sx(mark.x), cy: sy(mark.y), r: mark.r || 3.2, class: `chart-mark ${mark.class || ""}` },
      svg("title", {}, mark.label || "")));
  }
  if (series.length > 1) {
    const legend = svg("g", { class: "chart-legend" });
    series.forEach((item, i) => legend.append(
      svg("rect", { x: pad.left + i * 190, y: 10, width: 14, height: 3, style: `fill: ${item.color}` }),
      svg("text", { x: pad.left + 20 + i * 190, y: 15, class: "chart-tick" }, item.label)));
    root.append(legend);
  }
  return root;
}

/* Barras verticais (erro por variável) ou horizontais (rankings da FMECA). */
function bars({ values, labels, highlight = new Set(), width = 680, height = 190, label, horizontal = false, unit = "" }) {
  const root = svg("svg", { viewBox: `0 0 ${width} ${horizontal ? 34 * values.length + 16 : height}`, class: "chart",
    role: "img", "aria-label": label || "" });
  const max = Math.max(...values, 1e-12);
  if (horizontal) {
    values.forEach((value, i) => {
      const w = (width - 230) * value / max;
      root.append(svg("text", { x: 0, y: 34 * i + 22, class: "chart-tick" }, labels[i]),
        svg("rect", { x: 170, y: 34 * i + 8, width: Math.max(2, w), height: 20, rx: 3, class: highlight.has(i) ? "chart-bar is-hot" : "chart-bar" },
          svg("title", {}, `${labels[i]}: ${num(value)}${unit}`)),
        svg("text", { x: 176 + w, y: 34 * i + 22, class: "chart-tick" }, `${num(value)}${unit}`));
    });
    return root;
  }
  const slot = (width - 20) / values.length;
  values.forEach((value, i) => {
    const h = Math.max(2, (height - 40) * value / max);
    root.append(svg("rect", { x: 10 + i * slot + 2, y: height - 26 - h, width: slot - 4, height: h, rx: 2,
      class: highlight.has(i) ? "chart-bar is-hot" : "chart-bar" }, svg("title", {}, `${labels[i]}: ${num(value)}`)));
  });
  root.append(svg("text", { x: 10, y: height - 8, class: "chart-tick" }, label || ""));
  return root;
}

/* Blocos de interface */
function card(title, value, detail) {
  return el("div", { class: "metric" }, el("p", { text: title }), el("b", { text: value }),
    ...(detail ? [el("span", { class: "muted", text: detail })] : []));
}

function slider(labelText, { min, max, step, value, format = (v) => v }, onInput) {
  const out = el("output", { text: format(value) });
  const input = el("input", { type: "range", min, max, step, value });
  input.addEventListener("input", () => { out.textContent = format(Number(input.value)); onInput(Number(input.value)); });
  return { node: el("label", { class: "control" }, el("span", { text: labelText }), input, out), input, out };
}

function select(labelText, options, value, onChange) {
  const node = el("select", {}, ...options.map(([id, text]) => {
    const option = el("option", { value: String(id), text });
    if (String(id) === String(value)) option.selected = true;
    return option;
  }));
  node.addEventListener("change", () => onChange(node.value));
  return el("label", { class: "control" }, el("span", { text: labelText }), node);
}

function debounce(callback) {
  clearTimeout(science.timer);
  science.timer = setTimeout(callback, 140);
}

function table(headers, rows) {
  return el("div", { class: "table-wrap" }, el("table", { class: "data-table" },
    el("thead", {}, el("tr", {}, ...headers.map((h) => el("th", { text: h })))),
    el("tbody", {}, ...rows.map((row) => el("tr", {}, ...row.map((cell) =>
      cell instanceof Node ? el("td", {}, cell) : el("td", { text: String(cell ?? "—") })))))));
}

/* Navegação da aba */
$("nav-science").addEventListener("click", () => openScience());

async function openScience(tab) {
  showView("science");
  if (tab) science.tab = tab;
  try {
    science.status = await api("/api/ciencia");
  } catch (error) {
    toast(error.message);
  }
  $("science-tabs").replaceChildren(...SCIENCE_TABS.map(([id, text]) => el("button", {
    class: `filter${id === science.tab ? " is-active" : ""}`, type: "button", role: "tab", text,
    "aria-selected": String(id === science.tab), onclick: () => openScience(id) })));
  const body = $("science-body");
  body.replaceChildren(el("p", { class: "muted", text: "Carregando…" }));
  const render = { resultados: renderResults, limiar: renderThreshold, alarme: renderAlarms,
    confiabilidade: renderReliability, fmeca: renderFmeca }[science.tab];
  await render(body);
}

/* GPVS: os exploradores só funcionam com os modelos, a avaliação e os dados no computador. */
async function ensureGpvs(body) {
  const status = science.status?.gpvs;
  if (!status?.disponivel) {
    body.replaceChildren(el("div", { class: "note note-warn",
      text: `Exploradores do GPVS indisponíveis: falta ${(status?.faltando || ["o serviço"]).join("; ")}.` }));
    return false;
  }
  if (status.pronto && status.opcoes?.modelos) { science.options = status.opcoes; return true; }
  body.replaceChildren(el("p", { class: "muted", text: "Preparando os modelos congelados e o erro por variável…" }));
  const job = await api("/api/ciencia/preparar", { method: "POST" });
  for (;;) {
    const state = await api(`/api/ciencia/tarefas/${job.tarefa}`);
    if (state.estado === "falhou") throw new Error(state.erro);
    if (state.estado === "concluido") { science.options = state.resultado; science.status.gpvs.pronto = true; return true; }
    body.firstElementChild.textContent = `Preparando: ${state.etapa} (${state.atual} de ${state.total})…`;
    await new Promise((resolve) => setTimeout(resolve, 600));
  }
}

function gpvsControls(params, rerun, { withConfirmations = false, withTrial = false } = {}) {
  const o = science.options;
  const controls = el("div", { class: "controls" },
    select("Modelo", o.modelos.map((m) => [m.id, m.nome]), params.modelo, (v) => { params.modelo = v; rerun(); }),
    select("Semente", o.sementes.map((s) => [s, s === o.semente_referencia ? `${s} (referência)` : String(s)]), params.semente,
      (v) => { params.semente = Number(v); rerun(); }),
    slider("k (maiores erros)", { min: 1, max: o.variaveis, step: 1, value: params.k }, (v) => { params.k = v; debounce(rerun); }).node,
    slider("Percentil", { min: 90, max: 99.9, step: 0.1, value: params.percentil, format: (v) => num(v, 3) },
      (v) => { params.percentil = v; debounce(rerun); }).node);
  if (withConfirmations) {
    controls.append(slider("m (janelas seguidas)", { min: 1, max: 10, step: 1, value: params.confirmacoes },
      (v) => { params.confirmacoes = v; debounce(rerun); }).node);
  }
  if (withTrial) {
    controls.append(select("Ensaio na linha do tempo", o.ensaios.map((e) => [e, e]), params.ensaio,
      (v) => { params.ensaio = v; rerun(); }));
  }
  return controls;
}

/* Explorador do limiar: só a calibração. */
async function renderThreshold(body) {
  try { if (!(await ensureGpvs(body))) return; } catch (error) { body.replaceChildren(el("p", { class: "muted", text: error.message })); return; }
  const o = science.options;
  const params = science.threshold ||= { modelo: o.modelos[0].id, semente: o.semente_referencia, k: o.k_canonico,
    percentil: o.percentil_canonico, janela: null };
  const output = el("div", { class: "science-output" });
  const rerun = async () => {
    try {
      const data = await api("/api/ciencia/limiar", { method: "POST", json: params });
      drawThreshold(output, data, params, rerun);
    } catch (error) { toast(error.message); }
  };
  body.replaceChildren(el("p", { class: "muted", text: "Usa só os escores de calibração do treino, sem o teste. " +
    `Os valores canônicos são k = ${o.k_canonico} e p${num(o.percentil_canonico)}.` }), gpvsControls(params, rerun), output);
  await rerun();
}

function drawThreshold(output, data, params, rerun) {
  const t = data.limiar;
  const sorted = data.escores_ordenados;
  const cards = el("div", { class: "metrics" },
    card("Limiar", num(t.limiar, 5), `canônico ${num(data.canonico.limiar, 5)} (k = ${data.canonico.k}, p${num(data.canonico.percentil)})`),
    card("Posição na fila", `${t.posicao}ª de ${t.n_calibracao}`, `percentil efetivo ${num(t.percentil_efetivo, 4)}%`),
    card("Janelas de calibração acima", String(t.n_calibracao - t.posicao)),
    card("Falso alarme esperado por janela", pct(t.falso_alarme_esperado_por_janela, 3)));
  const warn = t.maximo_amostral ? el("div", { class: "note note-warn", text: `Com ${t.n_calibracao} janelas, p${num(t.percentil_pedido, 4)} ` +
    `cai no maior escore da calibração: o percentil pedido não se sustenta (seriam precisas ${t.n_minimo_para_o_percentil ?? "infinitas"}).` }) : null;
  const curve = chart({ label: "Escores de calibração ordenados e limiar", xLabel: "janelas de calibração, do menor ao maior escore",
    yLabel: "escore top-k", series: [{ points: sorted.map((v, i) => [i + 1, v]), color: "var(--chart-a)" }],
    hLines: [{ y: t.limiar, label: `limiar ${num(t.limiar, 4)}`, class: "is-threshold" }],
    marks: sorted.map((v, i) => [i + 1, v]).filter(([i]) => i > t.posicao).map(([x, y]) => ({ x, y, class: "is-hot",
      label: `${x}ª janela: ${num(y, 4)}` })) });
  const w = data.janela;
  const windowSlider = slider("Janela de calibração", { min: 0, max: sorted.length - 1, step: 1, value: w.indice,
    format: (v) => `nº ${v + 1}` }, (v) => { params.janela = v; debounce(rerun); });
  const variableBars = bars({ values: w.erros, labels: w.variaveis, highlight: new Set(w.maiores),
    label: `24 variáveis da janela nº ${w.indice + 1} (escore ${num(w.escore, 4)}); as k maiores em destaque` });
  output.replaceChildren(cards, ...(warn ? [warn] : []), el("h3", { class: "science-h", text: "Limiar na calibração" }), curve,
    el("h3", { class: "science-h", text: "Escore top-k de uma janela" }), el("div", { class: "controls" }, windowSlider.node), variableBars,
    el("div", { class: "metrics" }, card("Média das 24 variáveis", num(w.media_todas, 4)),
      card(`Média das ${params.k} maiores`, num(w.media_k, 4)), card("Quanto o top-k amplia", `${num(w.media_k / w.media_todas, 3)}×`)));
}

/* Explorador de alarme e detecção: usa o teste já consultado (M14). */
async function renderAlarms(body) {
  try { if (!(await ensureGpvs(body))) return; } catch (error) { body.replaceChildren(el("p", { class: "muted", text: error.message })); return; }
  const o = science.options;
  const canonical = () => ({ modelo: science.alarms?.modelo || o.modelos[0].id, semente: science.alarms?.semente || o.semente_referencia,
    k: o.k_canonico, percentil: o.percentil_canonico, confirmacoes: o.confirmacoes_canonicas, ensaio: science.alarms?.ensaio || o.ensaios[0] });
  const params = science.alarms ||= canonical();
  const output = el("div", { class: "science-output" });
  const rerun = async () => {
    try {
      drawAlarms(output, await api("/api/ciencia/alarme", { method: "POST", json: params }));
    } catch (error) { toast(error.message); }
  };
  body.replaceChildren(el("div", { class: "note note-warn science-notice", text: "Exploração pós-teste, não canônica (M14): usa o teste " +
      "já consultado e não altera os resultados congelados da avaliação de 27/09/2026." }),
    gpvsControls(params, rerun, { withConfirmations: true, withTrial: true }),
    el("button", { class: "secondary", type: "button", text: `Voltar aos canônicos (k = ${o.k_canonico}, p${num(o.percentil_canonico)}, m = ${o.confirmacoes_canonicas})`,
      onclick: () => { science.alarms = canonical(); openScience("alarme"); } }), output);
  await rerun();
}

function drawAlarms(output, data) {
  const fa = data.falsos_alarmes, c = data.canonico, s = data.resumo;
  const cards = el("div", { class: "metrics" },
    card("Ensaios com falha detectados", `${s.detectados} de ${data.ensaios.length}`, `canônico: ${c.detectados}`),
    card("Atraso mediano", seconds(s.atraso_mediano_ms), `canônico: ${seconds(c.atraso_mediano_ms)}`),
    card("Falsos alarmes no teste saudável", String(fa.teste_saudavel.alarmes),
      `limite superior 95%: ${num(fa.teste_saudavel.limite_superior_por_hora, 4)} por hora · canônico: ${c.alarmes_teste_saudavel}`),
    card("Alarmes no pré-falha", String(fa.pre_falha.alarmes), `canônico: ${c.alarmes_pre_falha}`),
    card("Limiar", num(data.limiar.limiar, 5), `canônico: ${num(c.limiar, 5)}`));
  const same = data.parametros_canonicos ? el("div", { class: "note note-ok", text: "Parâmetros canônicos: estes números " +
    "reproduzem a avaliação de 27/09/2026." }) : null;
  const rows = data.ensaios.map((t) => [t.ensaio, t.falha + (t.fisica ? "" : " (não física)"), t.modo,
    t.detectado ? "sim" : "não", seconds(t.atraso_ms), t.alarmes_pre_falha,
    t.canonico ? `${t.canonico.detectado ? "sim" : "não"} · ${seconds(t.canonico.atraso_ms)}` : "—"]);
  const parts = [cards, ...(same ? [same] : []), table(["Ensaio", "Falha", "Modo", "Detectado", "Atraso", "Alarmes no pré-falha", "Canônico"], rows)];
  const line = data.linha_do_tempo;
  if (line) {
    const bands = [["comissionamento", "Comissionamento", "is-muted"], ["pre_teste", "Pré-falha (teste)", ""],
      ["transicao", "Transição", "is-warn"], ["pos_falha", "Pós-falha", "is-hot"]]
      .filter(([key]) => line[key]).map(([key, label, cls]) => ({ from: line[key][0], to: line[key][1] + 1, label, class: cls }));
    // O pós-falha chega a dezenas de vezes o limiar; a escala para em 4× o limiar, e o excesso fica no topo.
    const top = Math.min(Math.max(...line.escores), 4 * line.limiar);
    const clipped = Math.max(...line.escores) > top;
    parts.push(el("h3", { class: "science-h", text: `Linha do tempo de ${line.ensaio}` }),
      chart({ label: `Escores de ${line.ensaio}`, xLabel: "janelas de um ciclo (20 ms)", yLabel: "escore top-k", bands,
        yMin: 0, yMax: top * 1.02,
        series: [{ points: line.escores.map((v, i) => [i, v]), color: "var(--chart-a)" }],
        hLines: [{ y: line.limiar, label: "limiar", class: "is-threshold" }],
        vLines: [{ x: line.inicio_nominal, label: "início nominal da falha", class: "is-onset" }],
        marks: line.alarmes.map((i) => ({ x: i, y: line.escores[i], class: "is-alarm", label: `alarme na janela ${i}` })) }),
      el("p", { class: "muted", text: "Faixas: comissionamento, pré-falha, transição e pós-falha. Linha vertical: início nominal da " +
        "falha. Pontos: alarmes (a m-ésima janela seguida acima do limiar)." +
        (clipped ? ` A escala vai até 4 vezes o limiar; escores maiores aparecem no topo (máximo ${num(Math.max(...line.escores), 3)}).` : "") }));
  }
  output.replaceChildren(...parts);
}

/* Confiabilidade: explora sem gravar; salvar exige fonte e hipóteses. */
async function renderReliability(body) {
  let presets = [];
  try { presets = await api("/api/ciencia/cenarios"); } catch (error) { toast(error.message); }
  const params = science.reliability ||= { taxa: 8.9e-6, horas_por_ano: 4015, base: "operation", horizonte: 20, nome: "" };
  const output = el("div", { class: "science-output" });
  const rate = el("input", { type: "number", step: "any", min: "0", value: params.taxa });
  const rerun = async () => {
    try {
      drawReliability(output, await api("/api/ciencia/confiabilidade", { method: "POST", json: params }), params);
    } catch (error) { output.replaceChildren(el("p", { class: "muted", text: error.message })); }
  };
  rate.addEventListener("input", () => { params.taxa = Number(rate.value); debounce(rerun); });
  const hours = slider("Horas por ano", { min: 100, max: 8760, step: 5, value: params.horas_por_ano, format: (v) => `${num(v, 4)} h` },
    (v) => { params.horas_por_ano = v; debounce(rerun); });
  const presetOptions = [["", "Escolha um cenário da pesquisa…"], ...presets.map((p, i) => [i, p.cenario.name])];
  const controls = el("div", { class: "controls" },
    select("Ponto de partida", presetOptions, "", (value) => {
      const scenario = presets[Number(value)]?.cenario;
      if (!scenario?.time_base) return;
      Object.assign(params, { taxa: scenario.parameters.rate, horas_por_ano: scenario.time_base.hours_per_year,
        base: scenario.time_base.basis, nome: scenario.name, fontes: scenario.sources, hipoteses: scenario.assumptions });
      openScience("confiabilidade");
    }),
    el("label", { class: "control" }, el("span", { text: "λ (falhas por hora)" }), rate),
    hours.node,
    select("Base", [["operation", "horas de operação"], ["calendar", "horas de calendário"]], params.base, (v) => { params.base = v; rerun(); }),
    slider("Horizonte", { min: 1, max: 40, step: 1, value: params.horizonte, format: (v) => `${v} anos` },
      (v) => { params.horizonte = v; debounce(rerun); }).node);
  body.replaceChildren(el("p", { class: "muted", text: "Vida exponencial, calculada pelo serviço RAM (`time_base`). Explorar não grava nada." }),
    controls, output, saveScenarioForm(params), scenarioJsonForm());
  await rerun();
}

function drawReliability(output, result, params) {
  const rows = result.rows;
  const points = (key) => rows.map((r) => [r.time, r[key]]);
  const marks = rows.filter((r) => Number.isInteger(r.time) && [1, 5, 10, 20, 30, 40].includes(r.time));
  output.replaceChildren(
    el("div", { class: "metrics" }, card("MTTF", `${num(result.summary.mttf, 4)} anos`),
      card("λ em anos da base", `${num(result.summary.rate, 4)} por ano`),
      ...marks.slice(0, 3).map((r) => card(`Chance de falhar em ${r.time} ano(s)`, pct(r.failure_probability)))),
    chart({ label: "R(t) e F(t)", xLabel: "anos", yLabel: "probabilidade", yMin: 0, yMax: 1,
      series: [{ points: points("reliability"), color: "var(--chart-a)", label: "R(t), confiabilidade" },
        { points: points("failure_probability"), color: "var(--chart-b)", label: "F(t), chance de falhar" }] }),
    table(["Anos", "R(t)", "F(t)"], marks.map((r) => [r.time, num(r.reliability, 4), pct(r.failure_probability)])),
    el("p", { class: "muted", text: `Hipóteses: ${result.assumptions.join(" ")} Limitações: ${(result.limitations || []).join(" ")}` }));
  if (params) params.ultimo = result;
}

function scenarioFromControls(params, name, sources, assumptions) {
  const years = Array.from({ length: params.horizonte + 1 }, (_, i) => i);
  return { name, kind: "exponential", time_unit: "year",
    time_base: { rate_unit: "h", hours_per_year: params.horas_por_ano, basis: params.base },
    parameters: { rate: params.taxa }, times: years, sources, assumptions };
}

function lines(text) { return text.split("\n").map((line) => line.trim()).filter(Boolean); }

function saveScenarioForm(params) {
  const name = el("input", { value: params.nome || "", placeholder: "Ex.: IGBT, 4.015 h/ano de operação" });
  const sources = el("textarea", { rows: 3, placeholder: "Uma fonte por linha (autor, ano, tabela e página)" });
  const assumptions = el("textarea", { rows: 3, placeholder: "Uma hipótese por linha" });
  sources.value = (params.fontes || []).join("\n");
  assumptions.value = (params.hipoteses || []).join("\n");
  const status = el("p", { class: "muted" });
  const form = el("form", { class: "science-form" }, el("h3", { class: "science-h", text: "Salvar como cenário" }),
    el("p", { class: "muted", text: "Grava numa pasta nova de resultados. Fonte e hipóteses são obrigatórias." }),
    el("label", { class: "field" }, "Nome", name), el("label", { class: "field" }, "Fontes", sources),
    el("label", { class: "field" }, "Hipóteses", assumptions),
    el("div", { class: "dialog-actions" }, el("button", { class: "primary", type: "submit", text: "Salvar cenário" })), status);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const saved = await api("/api/ciencia/cenarios/salvar", { method: "POST", json: {
        cenario: scenarioFromControls(params, name.value.trim() || "Cenário da aba Ciência", lines(sources.value), lines(assumptions.value)) } });
      status.textContent = `Salvo em ${saved.caminho}.`;
      toast("Cenário salvo.");
    } catch (error) { status.textContent = error.message; }
  });
  return form;
}

function scenarioJsonForm() {
  const text = el("textarea", { rows: 8, class: "mono", placeholder: '{"name": "...", "kind": "weibull", "time_unit": "h", ...}' });
  const output = el("div", { class: "science-output" });
  const send = async (path) => {
    let scenario;
    try { scenario = JSON.parse(text.value); } catch { output.replaceChildren(el("p", { class: "muted", text: "JSON inválido." })); return; }
    try {
      const data = await api(path, { method: "POST", json: { cenario: scenario } });
      if (data.pasta) { output.replaceChildren(el("p", { class: "muted", text: `Salvo em ${data.caminho}.` })); return; }
      if (data.rows?.[0]?.reliability !== undefined && data.rows[0].time !== undefined) drawReliability(output, data);
      else output.replaceChildren(el("pre", { class: "mono science-pre", text: JSON.stringify(data.summary ?? data, null, 2) }));
    } catch (error) { output.replaceChildren(el("p", { class: "muted", text: error.message })); }
  };
  return el("section", { class: "science-form" }, el("h3", { class: "science-h", text: "Qualquer cenário em JSON" }),
    el("p", { class: "muted", text: "Weibull, série, paralelo, mantenabilidade ou disponibilidade, no formato de docs/ciencia." }),
    text, el("div", { class: "dialog-actions" },
      el("button", { class: "secondary", type: "button", text: "Calcular", onclick: () => send("/api/ciencia/cenarios/rodar") }),
      el("button", { class: "primary", type: "button", text: "Salvar", onclick: () => send("/api/ciencia/cenarios/salvar") })), output);
}

/* FMECA: tabela, as duas ordens e o relatório. */
async function renderFmeca(body) {
  let data;
  try { data = await api("/api/ciencia/fmeca"); } catch (error) { body.replaceChildren(el("p", { class: "muted", text: error.message })); return; }
  body.replaceChildren(fmecaView(data), el("div", { class: "dialog-actions" }, el("button", { class: "primary", type: "button",
    text: "Gerar relatório numa pasta nova", onclick: async () => {
      try {
        const saved = await api("/api/ciencia/fmeca", { method: "POST" });
        toast(`FMECA salva em ${saved.caminho}.`);
      } catch (error) { toast(error.message); }
    } })));
}

function fmecaView(data) {
  const items = data.itens;
  const operation = (item) => item.leitura_pelas_taxas.find((r) => r.base === "operation") || item.leitura_pelas_taxas[0];
  const byNpr = [...items].sort((a, b) => a.posicoes.npr - b.posicoes.npr);
  const byRate = [...items].sort((a, b) => a.posicoes.taxa - b.posicoes.taxa);
  return el("div", { class: "science-output" },
    el("p", { class: "muted", text: `${data.criterio} Notas: ${data.fonte_notas}` }),
    table(["Grupo", "S", "O", "D", "NPR", "λ (1/h)", "MTBF em operação", "F(1 ano)", "F(20 anos)"], items.map((item) => {
      const r = operation(item);
      return [item.nome, item.S, item.O, item.D, item.npr, num(item.taxa_por_hora), `${num(r.mtbf_anos, 3)} anos`,
        pct(r.horizontes["1"].chance_de_falhar), pct(r.horizontes["20"].chance_de_falhar)];
    })),
    el("div", { class: "science-pair" },
      el("div", {}, el("h3", { class: "science-h", text: "Ordem pelo NPR (S × O × D)" }),
        bars({ horizontal: true, values: byNpr.map((i) => i.npr), labels: byNpr.map((i) => i.id), label: "NPR" })),
      el("div", {}, el("h3", { class: "science-h", text: "Ordem pela taxa de falha" }),
        bars({ horizontal: true, values: byRate.map((i) => i.taxa_por_hora * 1e6), labels: byRate.map((i) => i.id),
          unit: "e-6/h", label: "taxa" }))),
    el("p", { class: "muted", text: "As duas ordens ficam separadas, sem nota agregada (decisão de 27/09/2026)." }),
    ...(data.pares_discordantes_O_taxa?.length ? [el("h3", { class: "science-h", text: "Pares em que a ocorrência O e a taxa discordam" }),
      table(["Maior O", "Menor O", "O", "Taxas (1/h)"], data.pares_discordantes_O_taxa.map((p) => [p.maior_O, p.menor_O,
        p.O.join(" × "), p.taxas.map((t) => num(t)).join(" × ")]))] : []),
    el("h3", { class: "science-h", text: "Ressalvas e limites" }),
    el("ul", { class: "science-list" }, ...[...(data.ressalvas || []), ...(data.limites || [])].map((text) => el("li", { text }))));
}

/* Resultados gravados */
async function renderResults(body) {
  let items = [];
  try { items = await api("/api/ciencia/resultados"); } catch (error) { toast(error.message); }
  if (!items.length) { body.replaceChildren(el("p", { class: "muted", text: "Nenhum resultado gravado ainda." })); return; }
  const viewer = el("article", { class: "doc-viewer" }, el("p", { class: "muted", text: "Escolha um resultado." }));
  const list = el("ul", { class: "doc-list" }, ...items.map((item) => el("li", {}, el("button", { class: "doc-item", type: "button",
    "data-result": item.id, onclick: () => showResult(item, viewer) },
    el("span", { class: "doc-title", text: item.titulo }), el("span", { class: "doc-ref", text: item.rotulo }),
    el("span", { class: "doc-meta" }, el("span", { text: item.id }))))));
  body.replaceChildren(el("div", { class: "library-body" }, list, viewer));
  const chosen = items.find((item) => item.id === science.result) || null;
  if (chosen) showResult(chosen, viewer);
}

async function showResult(item, viewer) {
  science.result = item.id;
  document.querySelectorAll("[data-result]").forEach((b) => b.classList.toggle("is-current", b.dataset.result === item.id));
  viewer.replaceChildren(el("p", { class: "muted", text: "Carregando…" }));
  let data;
  try { data = await api(`/api/ciencia/resultados/${item.id.split("/").map(encodeURIComponent).join("/")}`); }
  catch (error) { viewer.replaceChildren(el("p", { class: "muted", text: error.message })); return; }
  const parts = [el("div", { class: "doc-viewer-head" }, el("span", { class: "muted", text: `${data.rotulo} · ${data.caminho}` }))];
  if (data.curvas?.linhas?.length) {
    parts.push(chart({ label: "R(t) e F(t)", xLabel: data.curvas.unidade === "year" ? "anos" : data.curvas.unidade, yLabel: "probabilidade",
      yMin: 0, yMax: 1, series: [{ points: data.curvas.linhas.map((r) => [r.time, r.reliability]), color: "var(--chart-a)", label: "R(t)" },
        { points: data.curvas.linhas.map((r) => [r.time, r.failure_probability]), color: "var(--chart-b)", label: "F(t)" }] }));
  }
  if (data.fmeca) parts.push(fmecaView(data.fmeca));
  if (data.calibracao) {
    for (const [kind, curve] of Object.entries(data.calibracao.modelos)) {
      parts.push(el("h3", { class: "science-h", text: `${kind === "lstm" ? "AE-LSTM" : "Denso"}: calibração da semente ${data.calibracao.semente} ` +
        `(k = ${data.calibracao.k}, p${num(data.calibracao.percentil)})` }),
        chart({ label: "Escores de calibração", xLabel: "janelas, do menor ao maior escore", yLabel: "escore",
          series: [{ points: curve.escores_ordenados.map((v, i) => [i + 1, v]), color: "var(--chart-a)" }],
          hLines: [{ y: curve.limiar, label: `limiar ${num(curve.limiar, 5)}`, class: "is-threshold" }] }));
    }
  }
  if (data.ensaios) {
    parts.push(el("h3", { class: "science-h", text: `Ensaios, semente ${data.ensaios.semente}` }),
      table(["Modelo", "Ensaio", "Detectado", "Atraso", "Alarmes no pré-falha"], data.ensaios.linhas.map((r) => [
        r.modelo === "lstm" ? "AE-LSTM" : "Denso", r.ensaio, r.detectado === "True" ? "sim" : "não",
        r.atraso_ms ? seconds(Number(r.atraso_ms)) : "—", r.alarmes_pre_falha])));
  }
  if (data.busca?.resumo) {
    const r = data.busca.resumo;
    parts.push(el("div", { class: "metrics" }, card("Acertos", `${r.acertos} de ${r.perguntas}`), card("MRR", num(r.mrr, 3)),
      card("Documentos distintos", num(r.documentos_distintos_medio, 3))));
  }
  if (data.html) {
    const report = el("div", { class: "answer" });
    report.innerHTML = data.html; // Markdown do relatório renderizado no servidor, sem HTML bruto
    renderMath(report);
    parts.push(report);
  }
  viewer.replaceChildren(...parts);
}
