"use strict";

/* Aba Ciência (lotes 20, 23 e 24), organizada pelas perguntas: o resultado primeiro e as ferramentas
   no fim. Todo número vem do servidor; aqui só se desenha, com os gráficos de graficos.js. As telas
   mostram dados em palavras: a avaliação oficial é a de 27/09/2026, e os números são os do treino de
   referência dela. Os controles internos do protocolo ficam no servidor e nos arquivos. */

const science = { tab: "resumo", status: null, options: null, timer: null, result: null, cache: {} };
const SCIENCE_TABS = [["resumo", "Resumo"], ["escores", "Escores por ensaio"], ["metricas", "Métricas por falha"],
  ["inicio", "Início das falhas"], ["confiabilidade", "Confiabilidade"], ["fmeca", "FMECA"], ["explorar", "Explorar"], ["rodar", "Rodar e arquivos"]];
const MODELOS = [["denso", "Denso"], ["lstm", "AE-LSTM"]];
const NOME_MODELO = Object.fromEntries(MODELOS);
const METRICAS = { sensibilidade: "Sensibilidade", especificidade: "Especificidade", precisao: "Precisão", f1: "F1",
  acuracia_balanceada: "Acurácia balanceada", mcc: "MCC", auc_roc: "AUC-ROC", auc_pr: "AUC-PR" };

/* Blocos de interface */
function card(title, value, detail, chave, extra) {
  return el("div", { class: "metric" }, el("p", {}, title, ...(chave ? [nota(chave, extra)] : [])), el("b", { text: value }),
    ...(detail ? [typeof detail === "string" ? el("span", { class: "muted", text: detail }) : detail] : []));
}

function slider(labelText, { min, max, step, value, format = (v) => v }, onInput, chave) {
  const out = el("output", { text: format(value) });
  const input = el("input", { type: "range", min, max, step, value });
  input.addEventListener("input", () => { out.textContent = format(Number(input.value)); onInput(Number(input.value)); });
  const label = el("span", {}, labelText, ...(chave ? [nota(chave)] : []));
  return { node: el("label", { class: "control" }, label, input, out), input, out };
}

function select(labelText, options, value, onChange, chave) {
  const node = el("select", {}, ...options.map(([id, text]) => {
    const option = el("option", { value: String(id), text });
    if (String(id) === String(value)) option.selected = true;
    return option;
  }));
  node.addEventListener("change", () => onChange(node.value));
  return el("label", { class: "control" }, el("span", {}, labelText, ...(chave ? [nota(chave)] : [])), node);
}

function debounce(callback) {
  clearTimeout(science.timer);
  science.timer = setTimeout(callback, 140);
}

function table(headers, rows) {
  return el("div", { class: "table-wrap" }, el("table", { class: "data-table" },
    el("thead", {}, el("tr", {}, ...headers.map((h) => (h instanceof Node ? el("th", {}, h) : el("th", { text: h }))))),
    el("tbody", {}, ...rows.map((row) => el("tr", {}, ...row.map((cell) =>
      cell instanceof Node ? el("td", {}, cell) : el("td", { text: String(cell ?? "—") })))))));
}

/* Tabela com título, nota e o botão de CSV. */
function tabelaComCSV(titulo, chave, headers, rows, arquivo, csvRows) {
  return el("section", { class: "science-output" },
    el("h3", { class: "science-h subtitulo-secao" }, titulo, ...(chave ? [nota(chave)] : []),
      el("button", { class: "link", type: "button", text: "CSV", title: "Baixar em CSV",
        onclick: () => baixarCSV(csvRows, `${arquivo}.csv`) })),
    table(headers, rows));
}

function faixaTexto(faixa, formato = num) {
  return faixa ? `Nos 5 treinamentos repetidos, variou de ${formato(faixa[0])} a ${formato(faixa[1])}.` : "";
}

function aviso(body, message) { body.replaceChildren(el("div", { class: "note note-warn", text: message })); }
function day(iso) { return iso ? String(iso).slice(0, 10).split("-").reverse().join("/") : "—"; }
function dec(value, digits = 2) { return value === null || value === undefined ? "—" : BR.format(`.${digits}f`)(value); }
function ms(value) { return value === null || value === undefined ? "—" : `${num(value, 3)} ms`; }

async function carregar(chave, caminho) {
  if (!science.cache[chave]) science.cache[chave] = await api(caminho);
  return science.cache[chave];
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
  const render = { resumo: renderSummary, escores: renderScores, metricas: renderMetrics, inicio: renderOnsets,
    confiabilidade: renderReliability,
    fmeca: renderFmeca, explorar: renderExplore, rodar: renderRunsAndFiles }[science.tab];
  await render(body);
}

/* 1. Resumo: qual modelo detecta mais falhas com menos alarmes falsos? */
async function renderSummary(body) {
  let d;
  try { d = await carregar("resumo", "/api/ciencia/resumo"); } catch (error) { aviso(body, error.message); return; }
  const favor = (row) => (row.maior_e_melhor ? "Positivo favorece o Denso." : "Negativo favorece o Denso.");
  const comparison = tabelaComCSV("Comparação por objetivo", "diferenca",
    ["Objetivo", "Métrica", comNota("Diferença (Denso − AE-LSTM)", "diferenca"), comNota("Intervalo de 95%", "ic95"), "Leitura"],
    d.comparacao.map((row) => [row.objetivo, row.metrica,
      el("span", { class: "com-nota" }, num(row.diferenca), nota(favor(row))),
      `${num(row.ic95[0])} a ${num(row.ic95[1])}`, row.leitura]),
    "comparacao-por-objetivo",
    [["Objetivo", "Métrica", "Diferença (Denso − AE-LSTM)", "IC 95% inferior", "IC 95% superior", "Ensaios", "Leitura"],
      ...d.comparacao.map((row) => [row.objetivo, row.metrica, row.diferenca, row.ic95[0], row.ic95[1], row.ensaios, row.leitura])]);
  const filtro = science.matriz ||= "total";
  const filterOptions = [["total", "Todos os 14 ensaios"],
    ...[1, 2, 3, 4, 5, 6, 7].map((f) => [`F${f}`, `F${f} · ${d.ensaios.find((t) => t.falha === `F${f}`).nome} (L e M)`]),
    ...d.ensaios.map((t) => [t.id, `${t.id} · ${t.nome} · ${t.modo_nome}`])];
  const columns = el("div", { class: "par-modelos" }, ...MODELOS.map(([kind]) => modelColumn(d, kind, filtro)));
  body.replaceChildren(
    el("p", { class: "muted" }, `Avaliação oficial de ${day(d.data)}: os 14 ensaios com falha e o teste saudável, `,
      "em janelas de 20 ms. Os números são os do treino de referência ", nota("treinos"), "."),
    comparison,
    el("div", { class: "controls" }, select("Matriz de confusão de", filterOptions, filtro, (value) => {
      science.matriz = value;
      openScience("resumo");
    }, "matriz")),
    columns);
}

function modelColumn(d, kind, filtro) {
  const m = d.modelos[kind];
  const f = m.faixa;
  const counts = filtro === "total" ? m.matrizes.total : m.matrizes.por_falha[filtro] || m.matrizes.por_ensaio[filtro];
  const healthy = m.teste_saudavel;
  const s = m.saudavel;
  const trecho = (part) => {
    const item = s.trechos[part];
    return `${pct(item.fracao)}${item.ic95 ? ` (intervalo de 95%: ${pct(item.ic95[0])} a ${pct(item.ic95[1])})` : ""}`;
  };
  const est = m.alarmes_estimados;
  const faixa = m.limiar_faixa;
  const cards = el("div", { class: "metrics" },
    card("Ensaios detectados", `${m.detectados} de ${m.ensaios}`, null, "detectados", faixaTexto(f.detectados)),
    card("Atraso mediano", seconds(m.atraso_mediano_ms), null, "atraso", faixaTexto(f.atraso_mediano_ms, seconds)),
    card("Alarmes falsos por hora", num(s.alarmes_por_hora),
      el("span", { class: "muted com-nota" }, `limite superior: ${num(s.limite_superior_por_hora)} por hora`, nota("limite_superior")),
      "alarmes_hora", `${s.alarmes} alarme(s) em ${num(s.duracao_s)} s saudáveis: ${healthy.alarmes} no teste saudável e ` +
      `${m.antes_da_falha.alarmes} antes da falha.`),
    ...(est ? [card("Alarmes falsos por hora, estimados", num(est.alarmes_por_hora),
      `intervalo de 95%: ${num(est.ic95[0])} a ${num(est.ic95[1])}`, "alarmes_estimados",
      `Conferência: a cadeia previa ${num(est.previsto.sequencias_de_2)} sequências de 2 janelas e houve ` +
      `${est.observado.sequencias_de_2}; previa ${num(est.previsto.alarmes)} alarme(s) e houve ${est.observado.alarmes}.`)] : []),
    card("Janelas saudáveis acima do limiar", pct(s.janelas_acima / s.janelas),
      faixa ? `esperado pelo limiar: ${pct(faixa.ic95[0])} a ${pct(faixa.ic95[1])}` : null, "janelas_acima",
      `${s.janelas_acima} de ${s.janelas} janelas. No teste saudável: ${trecho("teste_saudavel")}. Antes da falha: ` +
      `${trecho("pre_falha")}.${faixa ? ` ${GLOSSARIO.faixa_limiar} Aqui, o limiar é o ${faixa.posicao}º de ${faixa.n}.` : ""}`),
    card("Alarmes antes da falha", String(m.antes_da_falha.alarmes), null, "alarmes_antes", faixaTexto(f.alarmes_pre_falha)),
    ...["sensibilidade", "especificidade", "f1", "mcc", "auc_roc", "auc_pr"].map((key) =>
      card(METRICAS[key], dec(m.metricas[key]), null, key, `Média dos 14 ensaios. ${faixaTexto(f[key], (v) => dec(v))}`)));
  const label = filtro === "total" ? "todos os ensaios" : filtro;
  return el("section", { class: "coluna-modelo" },
    el("h3", { class: "science-h" }, el("span", { class: `marca-modelo is-${kind}` }), m.nome),
    cards,
    quadro({ titulo: `Matriz de confusão · ${m.nome} · ${label}`, chave: "matriz", arquivo: `matriz-confusao-${kind}-${filtro}`,
      desenhar: (area, largura, cores) => matrizDeConfusao(area, largura, cores, { contagens: counts,
        titulo: `Matriz de confusão do ${m.nome} (${label})`, descricao: "Janelas de 20 ms por classe real e classe predita." }),
      csv: () => [["", "Predita saudável", "Predita falha"], ["Real saudável", counts.vn, counts.fp], ["Real falha", counts.fn, counts.vp]] }));
}

/* 2. Escores por ensaio: os "escores divididos", um contêiner por ensaio. */
async function renderScores(body) {
  body.replaceChildren(el("p", { class: "muted", text: "Carregando os escores dos 14 ensaios…" }));
  let d;
  try { d = await carregar("escores", "/api/ciencia/escores"); } catch (error) { aviso(body, error.message); return; }
  const swatch = (text, color) => el("span", {}, el("i", { style: `background: ${color}` }), text);
  const legend = el("div", { class: "legenda-fases" },
    swatch("Denso", "var(--g-denso)"), swatch("AE-LSTM", "var(--g-lstm)"),
    el("span", { class: "com-nota" }, "Escore ÷ limiar", nota("razao")),
    swatch("Comissionamento", "color-mix(in srgb, var(--g-fase-comissionamento) 35%, transparent)"),
    swatch("Antes da falha", "color-mix(in srgb, var(--g-fase-antes) 35%, transparent)"),
    swatch("Transição", "color-mix(in srgb, var(--g-fase-transicao) 45%, transparent)"),
    swatch("Depois do início", "color-mix(in srgb, var(--g-fase-depois) 35%, transparent)"), nota("fases"),
    el("span", { class: "com-nota" }, "Linha tracejada vertical: início nominal", nota("inicio")),
    ...(d.reanalise ? [el("span", { class: "com-nota" }, swatch("", "var(--g-mudanca)"), "Linha pontilhada: mudança observada nos sinais",
      nota("mudanca"))] : []),
    el("span", { class: "com-nota" }, "▲ alarme que detectou · ✕ alarme antes da falha", nota("alarme")));
  const index = el("nav", { class: "indice", "aria-label": "Ir para o ensaio" },
    ...[1, 2, 3, 4, 5, 6, 7].map((f) => el("button", { class: "filter", type: "button", text: `F${f}`,
      onclick: () => $(`ensaio-F${f}L`)?.scrollIntoView({ behavior: "smooth" }) })),
    el("button", { class: "filter", type: "button", text: "Teste saudável",
      onclick: () => $("ensaio-F0L")?.scrollIntoView({ behavior: "smooth" }) }));
  // Passa todos os carrosséis para o mesmo gráfico de uma vez, para comparar os ensaios.
  CARROSSEIS.clear();
  const all = el("div", { class: "indice" }, el("span", { class: "muted", text: "Mostrar em todos:" }),
    ...["Denso", "AE-LSTM", "Ambos"].map((name, i) => el("button", { class: "filter", type: "button", text: name,
      onclick: () => CARROSSEIS.forEach((c) => c.isConnected && c.ir(i, false)) })));
  body.replaceChildren(
    el("p", { class: "muted" }, "Cada ensaio mostra um gráfico por vez: Denso, AE-LSTM e os dois juntos, no mesmo tamanho e ",
      "na mesma escala. Passe pelas setas, pelos nomes ou deslizando. Janelas de 20 ms; ",
      `alarme com ${d.confirmacoes} janelas seguidas acima do limiar `, nota("confirmacoes"), "."),
    legend, index, all,
    el("div", { class: "escores-grade" }, ...d.ensaios.map((p) => trialBox(p, d)), ...d.teste_saudavel.map((p) => trialBox(p, d))));
}

function trialBox(p, d) {
  const time = (i) => i * d.janela_s;
  const kinds = MODELOS.map(([kind]) => kind);
  const ratios = kinds.flatMap((kind) => p.modelos[kind].razao);
  const domain = [Math.max(1e-3, d3.min(ratios) / 1.5), d3.max(ratios) * 1.5];
  const healthy = !p.fases;
  // Os três gráficos do carrossel têm o mesmo tamanho e a mesma escala, para comparar ao passar de um ao outro.
  const panel = (shown) => (area, largura, cores) => graficoLinhas(area, largura, cores, {
    titulo: `${p.id}: escore ÷ limiar (${shown.map((k) => NOME_MODELO[k]).join(" e ")})`,
    descricao: `${p.nome}, ${p.modo_nome}. Escore de cada janela de 20 ms dividido pelo limiar do modelo.`,
    proporcao: 0.5, alturaMinima: 240, log: true, yDominio: domain, legenda: true,
    xRotulo: "tempo (s)", yRotulo: "escore ÷ limiar",
    dicaX: (x) => `${num(x)} s`, dicaY: (v) => num(v),
    series: shown.map((kind) => ({ nome: NOME_MODELO[kind], cor: MODELO_COR(cores, kind),
      pontos: p.modelos[kind].razao.map((v, i) => [time(i), v]) })),
    faixas: healthy ? [] : Object.entries(p.fases).filter(([, span]) => span).map(([phase, [a, b]]) =>
      ({ de: time(a), ate: time(b + 1), cor: cores.fases[phase], opacidade: phase === "transicao" ? 0.3 : 0.12 })),
    linhasH: [{ y: 1, cor: cores.limiar, rotulo: "limiar" }],
    linhasV: healthy ? [] : [{ x: time(p.inicio), cor: cores.inicio },
      ...(p.inicio_observado === null || p.inicio_observado === undefined ? []
        : [{ x: time(p.inicio_observado), cor: cores.mudanca, traco: "2 3", espessura: 2 }])],
    marcas: shown.flatMap((kind) => {
      const m = p.modelos[kind];
      const color = MODELO_COR(cores, kind);
      const falsos = m.alarmes_antes.map((i) => ({ x: time(i), y: m.razao[i], cor: color, forma: "xis", tamanho: 70,
        dica: [`${NOME_MODELO[kind]}: alarme ${healthy ? "falso no teste saudável" : "antes da falha (falso)"}`, `${num(time(i))} s`] }));
      const hit = m.alarme_deteccao === null ? [] : [{ x: time(m.alarme_deteccao), y: m.razao[m.alarme_deteccao], cor: color,
        forma: "triangulo", tamanho: 90, dica: [`${NOME_MODELO[kind]}: alarme que detectou a falha`, `atraso de ${seconds(m.atraso_ms)}`] }];
      return [...falsos, ...hit];
    }),
  });
  const phaseOf = (i) => (healthy ? "teste saudável" : Object.entries(p.fases).find(([, s]) => s && i >= s[0] && i <= s[1])?.[0] ?? "");
  const csv = () => [["janela", "tempo_s", "fase", "denso_escore_sobre_limiar", "lstm_escore_sobre_limiar"],
    ...p.modelos.denso.razao.map((v, i) => [i, time(i), phaseOf(i), v, p.modelos.lstm.razao[i]])];
  const title = healthy ? `${p.id} · Teste saudável` : `${p.id} · ${p.nome}`;
  const detail = healthy ? nota("teste_saudavel")
    : nota(`${p.descricao}. ${p.fisica ? "Falha física." : "Falha de operação ou de controle."}`);
  const footer = kinds.map((kind) => {
    const m = p.modelos[kind];
    const since = m.atraso_mudanca_ms === null || m.atraso_mudanca_ms === undefined ? ""
      : ` e ${ms(m.atraso_mudanca_ms)} depois da mudança`;
    const found = since ? `detectou ${seconds(m.atraso_ms)} depois do meio${since}` : `detectou em ${seconds(m.atraso_ms)}`;
    const text = healthy ? `${m.alarmes_antes.length} alarme(s) falso(s)`
      : `${m.detectado ? found : "não detectou"} · ${m.alarmes_pre_falha} alarme(s) antes da falha`;
    return el("span", { class: "com-nota" }, el("span", { class: `marca-modelo is-${kind}` }), `${NOME_MODELO[kind]}: ${text}`);
  });
  return el("section", { class: "ensaio", id: `ensaio-${p.id}` },
    el("h3", { class: "ensaio-titulo" }, title, detail, el("span", { class: "muted", text: `· ${p.modo_nome}` }), nota("modos")),
    carrossel(`Escores de ${p.id}`, [
      { nome: "Denso", node: quadro({ titulo: `${p.id} · Denso`, chave: "razao", arquivo: `escores-${p.id}-denso`,
        desenhar: panel(["denso"]), csv, preguicoso: true }) },
      { nome: "AE-LSTM", node: quadro({ titulo: `${p.id} · AE-LSTM`, chave: "razao", arquivo: `escores-${p.id}-lstm`,
        desenhar: panel(["lstm"]), csv, preguicoso: true }) },
      { nome: "Ambos", node: quadro({ titulo: `${p.id} · Denso e AE-LSTM`, chave: "razao", arquivo: `escores-${p.id}`,
        desenhar: panel(kinds), csv, preguicoso: true }) },
    ]),
    el("div", { class: "ensaio-rodape" }, ...footer));
}

/* Carrossel: um gráfico por vez, todos do mesmo tamanho; setas, nomes, teclado ou deslizar o dedo. */
const CARROSSEIS = new Set();

function carrossel(rotulo, slides) {
  const track = el("div", { class: "carrossel-trilho", tabindex: 0, role: "region", "aria-roledescription": "carrossel",
    "aria-label": `${rotulo}: use as setas do teclado para passar` },
  ...slides.map((slide, i) => el("div", { class: "carrossel-slide", role: "group", "aria-roledescription": "slide",
    "aria-label": `${i + 1} de ${slides.length}: ${slide.nome}` }, slide.node)));
  const current = () => Math.round(track.scrollLeft / Math.max(1, track.clientWidth));
  const go = (index, smooth = true) => {
    const target = (index + slides.length) % slides.length;
    track.scrollTo({ left: target * track.clientWidth, behavior: smooth ? "smooth" : "auto" });
  };
  const pills = slides.map((slide, i) => el("button", { class: "filter", type: "button", text: slide.nome, onclick: () => go(i) }));
  const mark = () => pills.forEach((pill, i) => {
    pill.classList.toggle("is-active", i === current());
    pill.setAttribute("aria-pressed", String(i === current()));
  });
  track.addEventListener("scroll", () => requestAnimationFrame(mark), { passive: true });
  track.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") { event.preventDefault(); go(current() + 1); }
    if (event.key === "ArrowLeft") { event.preventDefault(); go(current() - 1); }
  });
  const node = el("div", { class: "carrossel" },
    el("div", { class: "carrossel-controles" },
      el("button", { class: "carrossel-seta", type: "button", "aria-label": "Gráfico anterior", text: "‹", onclick: () => go(current() - 1) }),
      ...pills,
      el("button", { class: "carrossel-seta", type: "button", "aria-label": "Próximo gráfico", text: "›", onclick: () => go(current() + 1) })),
    track);
  node.ir = go;
  CARROSSEIS.add(node);
  requestAnimationFrame(mark);
  return node;
}

/* 3. Métricas por falha: em que falhas cada modelo vai melhor? */
const METRIC_CHOICES = [["sensibilidade", "Sensibilidade"], ["especificidade", "Especificidade"], ["precisao", "Precisão"],
  ["f1", "F1"], ["mcc", "MCC"], ["auc_roc", "AUC-ROC"], ["auc_pr", "AUC-PR"], ["atraso_ms", "Atraso (s)"]];

async function renderMetrics(body) {
  let d;
  try { d = await carregar("metricas", "/api/ciencia/metricas"); } catch (error) { aviso(body, error.message); return; }
  const metric = science.metrica ||= "sensibilidade";
  const isDelay = metric === "atraso_ms";
  const value = (item) => (item?.[metric] === null || item?.[metric] === undefined ? null : isDelay ? item[metric] / 1000 : item[metric]);
  const format = (v) => (v === null ? (isDelay ? "não detectou" : "—") : isDelay ? `${dec(v)} s` : dec(v));
  const label = Object.fromEntries(METRIC_CHOICES)[metric];
  const glossKey = isDelay ? "atraso" : metric;
  const faults = d.falhas;
  const grouped = quadro({ titulo: `${label} por tipo de falha (L e M somados)`, chave: glossKey,
    extra: isDelay ? "Média dos modos detectados." : ["auc_roc", "auc_pr"].includes(metric) ? "Média dos modos L e M."
      : "Recalculada das janelas dos dois modos.",
    arquivo: `metrica-${metric}-por-falha`,
    desenhar: (area, largura, cores) => barrasAgrupadas(area, largura, cores, {
      titulo: `${label} por tipo de falha`, altura: 300, yRotulo: label,
      dominio: isDelay ? undefined : [Math.min(0, ...MODELOS.flatMap(([k]) => faults.map((f) => value(d.modelos[k].por_falha[f.id]) ?? 0))), 1],
      grupos: faults.map((f) => ({ id: f.id, rotulo: f.id, nome: f.nome })),
      series: MODELOS.map(([kind, name]) => ({ id: kind, nome: name, cor: MODELO_COR(cores, kind) })),
      valor: (g, s) => value(d.modelos[s.id].por_falha[g.id]),
      dica: (g, s, v) => [`${g.id} · ${g.nome}`, `${s.nome}: ${format(v)}`,
        `detectou ${d.modelos[s.id].por_falha[g.id].detectados} de 2 modos`],
    }),
    csv: () => [["falha", "nome", ...MODELOS.map(([, n]) => `${label} ${n}`)],
      ...faults.map((f) => [f.id, f.nome, ...MODELOS.map(([k]) => value(d.modelos[k].por_falha[f.id]))])] });
  const heatmaps = el("div", { class: "par-modelos" }, ...MODELOS.map(([kind, name]) => quadro({
    titulo: `${label} por ensaio · ${name}`, chave: glossKey, arquivo: `metrica-${metric}-${kind}`,
    desenhar: (area, largura, cores) => mapaDeCalor(area, largura, cores, {
      titulo: `${label} por ensaio (${name})`, margemEsquerda: Math.min(190, largura * 0.42),
      linhas: faults.map((f) => ({ id: f.id, rotulo: `${f.id} · ${f.nome}` })),
      colunas: [{ id: "L", rotulo: "L (IPPT)" }, { id: "M", rotulo: "M (MPPT)" }],
      escala: isDelay
        ? d3.scaleSequential(d3.interpolateViridis).domain([d3.max(Object.values(d.modelos[kind].por_ensaio), (t) => value(t)) || 1, 0])
        : d3.scaleSequential(d3.interpolateViridis).domain([0, 1]).clamp(true),
      valor: (l, c) => value(d.modelos[kind].por_ensaio[`${l.id}${c.id}`]),
      formato: format,
      dica: (l, c, v) => {
        const t = d.modelos[kind].por_ensaio[`${l.id}${c.id}`];
        const spread = t.faixa?.[metric];
        return [`${l.id}${c.id} · ${l.rotulo.split(" · ")[1]} · ${c.rotulo}`, `${name}: ${format(v)}`,
          ...(spread ? [`Nos 5 treinamentos: de ${format(isDelay ? spread[0] / 1000 : spread[0])} a ${format(isDelay ? spread[1] / 1000 : spread[1])}`] : []),
          `detectou em ${t.detectado_em} de ${t.treinamentos} treinamentos`];
      },
    }),
    csv: () => [["ensaio", "falha", "modo", label],
      ...faults.flatMap((f) => ["L", "M"].map((mode) => [`${f.id}${mode}`, f.nome, mode, value(d.modelos[kind].por_ensaio[`${f.id}${mode}`])]))],
  })));
  const general = [["sensibilidade", "Sensibilidade"], ["f1", "F1"], ["precisao", "Precisão"], ["auc_roc", "AUC-ROC"],
    ["auc_pr", "AUC-PR"], ["fpr", "Taxa de falso positivo"]];
  const summary = quadro({ titulo: "Métricas gerais: média dos 14 ensaios, com a faixa dos 5 treinamentos", chave: "treinos",
    arquivo: "metricas-gerais",
    desenhar: (area, largura, cores) => pontoComFaixa(area, largura, cores, {
      titulo: "Métricas gerais dos dois modelos", xRotulo: "média por ensaio", margemEsquerda: 170,
      itens: general.map(([id, rotulo]) => ({ id, rotulo })),
      series: MODELOS.map(([kind, name]) => ({ id: kind, nome: name, cor: MODELO_COR(cores, kind) })),
      valor: (item, serie) => {
        const g = d.modelos[serie.id].gerais;
        if (item.id !== "fpr") return g[item.id];
        return { valor: 1 - g.especificidade.valor, faixa: [1 - g.especificidade.faixa[1], 1 - g.especificidade.faixa[0]] };
      },
    }),
    csv: () => [["métrica", ...MODELOS.flatMap(([, n]) => [`${n}`, `${n} mínimo`, `${n} máximo`])],
      ...general.map(([id, rotulo]) => [rotulo, ...MODELOS.flatMap(([k]) => {
        const g = d.modelos[k].gerais;
        const item = id === "fpr" ? { valor: 1 - g.especificidade.valor, faixa: [1 - g.especificidade.faixa[1], 1 - g.especificidade.faixa[0]] } : g[id];
        return [item.valor, item.faixa[0], item.faixa[1]];
      })])] });
  body.replaceChildren(
    el("div", { class: "controls" }, select("Métrica", METRIC_CHOICES, metric, (v) => { science.metrica = v; openScience("metricas"); }, glossKey)),
    grouped, heatmaps, summary);
}

/* 4. Início das falhas: quando cada falha aparece nos sinais e o que muda nos indicadores (lote 24). */
const CLASSES_MUDANCA = { clara: "clara", fraca: "fraca (não usada)", nenhuma: "nenhuma" };
const INDICADORES_INICIO = [["detectados", "Ensaios detectados"], ["atraso_mediano_ms", "Atraso mediano"],
  ["sensibilidade", "Sensibilidade"], ["especificidade", "Especificidade"], ["precisao", "Precisão"], ["f1", "F1"],
  ["mcc", "MCC"], ["auc_roc", "AUC-ROC"], ["auc_pr", "AUC-PR"]];
const COLUNAS_INICIO = [["meio", "14 ensaios · meio", "inicio"], ["mudanca", "14 ensaios · mudança", "mudanca"],
  ["clara_meio", "8 de mudança clara · meio", "clara_oito"], ["clara_mudanca", "8 de mudança clara · mudança", "clara_oito"]];

function sinal(value) { return `${value > 0 ? "+" : ""}${dec(value)}`; }
/* Em tela estreita, só o ensaio (F1L); o nome da falha fica na dica. */
function rotuloEnsaio(t, largura) { return largura < 480 ? t.id : `${t.id} · ${t.nome}`; }

async function renderOnsets(body) {
  let d;
  try { d = await carregar("inicio", "/api/ciencia/inicio"); } catch (error) { aviso(body, error.message); return; }
  const longest = Math.ceil(d3.max(d.ensaios, (t) => t.duracao_s));
  const timeline = quadro({ titulo: "Quando cada falha aparece nos sinais", chave: "mudanca", extra: GLOSSARIO.classe_mudanca,
    arquivo: "inicio-das-falhas",
    desenhar: (area, largura, cores) => linhaDoTempo(area, largura, cores, {
      titulo: "Início nominal e mudança observada em cada ensaio",
      descricao: "Para cada ensaio, o registro inteiro, o meio (início nominal) e a mudança observada nos sinais.",
      dominio: [0, longest], xRotulo: "tempo no registro (s)", margemEsquerda: largura < 480 ? 48 : Math.min(230, largura * 0.42),
      legenda: [{ nome: "meio do registro", forma: "circulo", cor: cores.inicio, vazado: true },
        { nome: "mudança clara", forma: "losango", cor: cores.mudanca },
        { nome: "mudança fraca (não usada)", forma: "losango", cor: cores.suave, vazado: true }],
      itens: d.ensaios.map((t) => ({ id: t.id, rotulo: rotuloEnsaio(t, largura), trilho: [0, t.duracao_s],
        ligar: t.classe === "clara" ? [t.nominal_s, t.observado_s] : null, corLigacao: cores.mudanca,
        pontos: [{ x: t.nominal_s, forma: "circulo", cor: cores.inicio, vazado: true,
          dica: [`${t.id} · ${t.nome} · meio do registro`, `${dec(t.nominal_s)} s de ${dec(t.duracao_s)} s`] },
        ...(t.observado_s === null ? [] : [{ x: t.observado_s, forma: "losango", vazado: t.classe !== "clara",
          cor: t.classe === "clara" ? cores.mudanca : cores.suave,
          dica: [`${t.id} · ${t.nome} · mudança ${CLASSES_MUDANCA[t.classe]}`, `${dec(t.observado_s)} s (${sinal(t.observado_s - t.nominal_s)} s em relação ao meio)`] }])] })),
    }),
    csv: () => [["ensaio", "falha", "modo", "meio_s", "mudanca_s", "diferenca_s", "classe", "duracao_s"],
      ...d.ensaios.map((t) => [t.id, t.nome, t.modo, t.nominal_s, t.observado_s,
        t.observado_s === null ? null : t.observado_s - t.nominal_s, t.classe, t.duracao_s])] });
  const format = (key, value, n) => (key === "detectados" ? `${value} de ${n}` : key === "atraso_mediano_ms" ? seconds(value) : dec(value, 3));
  const indicators = MODELOS.map(([kind]) => {
    const m = d.modelos[kind];
    return tabelaComCSV(`Indicadores com cada início · ${m.nome}`, "trecho_incerto",
      ["Indicador", ...COLUNAS_INICIO.map(([, label, chave]) => comNota(label, chave))],
      INDICADORES_INICIO.map(([key, label]) => [
        comNota(label, key === "atraso_mediano_ms" ? "atraso_mudanca" : key === "detectados" ? "detectados" : key,
          key === "atraso_mediano_ms" ? "Nas colunas do meio, contado do meio do registro." : ""),
        ...COLUNAS_INICIO.map(([column]) => format(key, m[column][key], m[column].ensaios))]),
      `indicadores-inicio-${kind}`,
      [["indicador", ...COLUNAS_INICIO.map(([, label]) => label)],
        ...INDICADORES_INICIO.map(([key, label]) => [label, ...COLUNAS_INICIO.map(([column]) => m[column][key])])]);
  });
  const sensitivity = el("div", { class: "par-modelos" }, ...MODELOS.map(([kind, name]) => quadro({
    titulo: `Sensibilidade por ensaio · ${name}`, chave: "sensibilidade", extra: GLOSSARIO.trecho_incerto,
    arquivo: `sensibilidade-inicio-${kind}`,
    desenhar: (area, largura, cores) => {
      const color = MODELO_COR(cores, kind);
      return linhaDoTempo(area, largura, cores, {
        titulo: `Sensibilidade por ensaio com cada início (${name})`, dominio: [0, 1], xRotulo: "sensibilidade",
        margemEsquerda: largura < 480 ? 48 : Math.min(190, largura * 0.42), alturaLinha: 26,
        legenda: [{ nome: "meio do registro", forma: "circulo", cor: color, vazado: true }, { nome: "mudança observada", forma: "losango", cor: color }],
        itens: d.ensaios.map((t) => {
          const r = d.por_ensaio[kind][t.id];
          return { id: t.id, rotulo: rotuloEnsaio(t, largura), ligar: [r.sensibilidade_meio, r.sensibilidade_mudanca], corLigacao: color,
            pontos: [{ x: r.sensibilidade_meio, forma: "circulo", cor: color, vazado: true, tamanho: 60,
              dica: [`${t.id} · ${name}`, `com o meio: ${dec(r.sensibilidade_meio, 3)}`] },
            { x: r.sensibilidade_mudanca, forma: "losango", cor: color, tamanho: 60,
              dica: [`${t.id} · ${name}`, `com a mudança: ${dec(r.sensibilidade_mudanca, 3)}`, `mudança ${CLASSES_MUDANCA[t.classe]}`] }] };
        }),
      });
    },
    csv: () => [["ensaio", "classe", "sensibilidade_meio", "sensibilidade_mudanca"],
      ...d.ensaios.map((t) => [t.id, t.classe, d.por_ensaio[kind][t.id].sensibilidade_meio, d.por_ensaio[kind][t.id].sensibilidade_mudanca])],
  })));
  const delays = tabelaComCSV("Atraso por ensaio", "atraso_mudanca",
    ["Ensaio", comNota("Mudança", "classe_mudanca"), ...MODELOS.flatMap(([, name]) => [comNota(`${name}: do meio`, "atraso"),
      comNota(`${name}: da mudança`, "atraso_mudanca")])],
    d.ensaios.map((t) => [`${t.id} · ${t.nome}`, CLASSES_MUDANCA[t.classe], ...MODELOS.flatMap(([kind]) => {
      const r = d.por_ensaio[kind][t.id];
      if (!r.detectado) return ["não detectou", "—"];
      return [seconds(r.atraso_meio_ms), t.classe === "clara" ? ms(r.atraso_mudanca_ms) : "—"];
    })]),
    "atraso-por-ensaio",
    [["ensaio", "classe", ...MODELOS.flatMap(([, name]) => [`${name} do meio (ms)`, `${name} da mudança (ms)`])],
      ...d.ensaios.map((t) => [t.id, t.classe, ...MODELOS.flatMap(([kind]) => {
        const r = d.por_ensaio[kind][t.id];
        return [r.atraso_meio_ms, t.classe === "clara" ? r.atraso_mudanca_ms : null];
      })])]);
  const pair = (row) => (row.diferenca === null ? "—" : `${num(row.diferenca)} (${num(row.ic95[0])} a ${num(row.ic95[1])})`);
  const comparison = tabelaComCSV("Comparação por objetivo com a mudança observada", "diferenca",
    ["Objetivo", "Métrica", comNota("14 ensaios: diferença (intervalo de 95%)", "ic95"), "Leitura",
      comNota("8 de mudança clara: diferença (intervalo de 95%)", "clara_oito"), "Leitura"],
    d.comparacao.mudanca.map((row, i) => [row.objetivo, row.metrica, pair(row), row.leitura, pair(d.comparacao.clara[i]),
      d.comparacao.clara[i].leitura]),
    "comparacao-inicio-observado",
    [["objetivo", "métrica", "14: diferença", "14: IC inferior", "14: IC superior", "14: leitura", "8: diferença", "8: IC inferior",
      "8: IC superior", "8: leitura"],
      ...d.comparacao.mudanca.map((row, i) => {
        const clear = d.comparacao.clara[i];
        return [row.objetivo, row.metrica, row.diferenca, row.ic95?.[0], row.ic95?.[1], row.leitura, clear.diferenca, clear.ic95?.[0],
          clear.ic95?.[1], clear.leitura];
      })]);
  body.replaceChildren(
    el("p", { class: "muted" }, "Os arquivos do GPVS não marcam quando cada falha foi disparada; o conjunto diz só que ela foi ",
      "introduzida manualmente, na metade do experimento. A avaliação oficial usou o meio do registro ", nota("inicio"),
      ". Aqui, um detector de mudança sobre as 24 variáveis, sem os autoencoders, mostra quando a falha aparece de fato nos sinais ",
      nota("detector_mudanca"), `. Nos dois ensaios saudáveis, ele não acha mudança nenhuma. Os números reaproveitam os escores `,
      `da avaliação de ${day(d.data_oficial)}, sem rodar os modelos de novo, e ela continua sendo a oficial.`),
    timeline,
    el("div", { class: "tabela-inicios" }, ...indicators),
    sensitivity, delays, comparison,
    el("div", { class: "note" }, "O que isto não resolve: F4 (sombreamento parcial) não muda as 24 variáveis, e F6 e F7 (ajustes do ",
      "controlador PI) mudam pouco. Para eles não há início confiável, e a falta de detecção é, em boa parte, das variáveis, não só ",
      "dos modelos. Como a mudança e os modelos olham as mesmas variáveis, a sensibilidade de 1 nos 8 ensaios de mudança clara ",
      "mostra que os modelos veem logo o que aparece nelas; ela não mede falhas que não aparecem."));
}

/* 5. Explorar: e se o limiar fosse outro? Usa o treino de referência. */
async function renderExplore(body) {
  const sub = science.explorar ||= "limiar";
  const inner = el("div", { class: "science-output" });
  body.replaceChildren(
    el("div", { class: "indice" }, ...[["limiar", "Limiar"], ["alarme", "Alarme e detecção"]].map(([id, text]) =>
      el("button", { class: `filter${id === sub ? " is-active" : ""}`, type: "button", text,
        onclick: () => { science.explorar = id; openScience("explorar"); } }))),
    inner);
  try { if (!(await ensureGpvs(inner))) return; } catch (error) { aviso(inner, error.message); return; }
  if (sub === "limiar") await renderThreshold(inner); else await renderAlarms(inner);
}

/* Os exploradores precisam dos modelos, da avaliação e dos dados no computador. */
async function ensureGpvs(body) {
  const status = science.status?.gpvs;
  if (!status?.disponivel) {
    aviso(body, `Os exploradores não estão disponíveis: falta ${(status?.faltando || ["o serviço"]).join("; ")}.`);
    return false;
  }
  if (status.pronto && status.opcoes?.modelos) { science.options = status.opcoes; return true; }
  body.replaceChildren(el("p", { class: "muted", text: "Carregando os modelos e o erro de cada variável…" }));
  const job = await api("/api/ciencia/preparar", { method: "POST" });
  for (;;) {
    const state = await api(`/api/ciencia/tarefas/${job.tarefa}`);
    if (state.estado === "falhou") throw new Error(state.erro);
    if (state.estado === "concluido") { science.options = state.resultado; science.status.gpvs.pronto = true; return true; }
    body.firstElementChild.textContent = `Carregando: ${state.etapa} (${state.atual} de ${state.total})…`;
    await new Promise((resolve) => setTimeout(resolve, 600));
  }
}

function gpvsControls(params, rerun, { withConfirmations = false, withTrial = false } = {}) {
  const o = science.options;
  const controls = el("div", { class: "controls" },
    select("Modelo", o.modelos.map((m) => [m.id, NOME_MODELO[m.id] || m.nome]), params.modelo, (v) => { params.modelo = v; rerun(); }),
    slider("k (maiores erros)", { min: 1, max: o.variaveis, step: 1, value: params.k }, (v) => { params.k = v; debounce(rerun); }, "k").node,
    slider("Percentil do limiar", { min: 90, max: 99.9, step: 0.1, value: params.percentil, format: (v) => num(v, 3) },
      (v) => { params.percentil = v; debounce(rerun); }, "percentil").node);
  if (withConfirmations) {
    controls.append(slider("Janelas seguidas para o alarme", { min: 1, max: 10, step: 1, value: params.confirmacoes },
      (v) => { params.confirmacoes = v; debounce(rerun); }, "confirmacoes").node);
  }
  if (withTrial) {
    controls.append(select("Ensaio na linha do tempo", o.ensaios.map((e) => [e, e]), params.ensaio,
      (v) => { params.ensaio = v; rerun(); }));
  }
  return controls;
}

/* Limiar: só a calibração, sem os ensaios de teste. */
async function renderThreshold(body) {
  const o = science.options;
  const params = science.threshold ||= { modelo: o.modelos[0].id, semente: o.semente_referencia, k: o.k_canonico,
    percentil: o.percentil_canonico, janela: null };
  const output = el("div", { class: "science-output" });
  const rerun = async () => {
    try { drawThreshold(output, await api("/api/ciencia/limiar", { method: "POST", json: params }), params, rerun); }
    catch (error) { toast(error.message); }
  };
  body.replaceChildren(el("p", { class: "muted", text: "Usa só os escores de calibração do treino, sem os ensaios de teste. " +
    `Os valores oficiais são k = ${o.k_canonico} e percentil ${num(o.percentil_canonico)}.` }), gpvsControls(params, rerun), output);
  await rerun();
}

function drawThreshold(output, data, params, rerun) {
  const t = data.limiar;
  const sorted = data.escores_ordenados;
  const cards = el("div", { class: "metrics" },
    card("Limiar", num(t.limiar, 5), `oficial: ${num(data.canonico.limiar, 5)} (k = ${data.canonico.k}, p${num(data.canonico.percentil)})`, "limiar"),
    card("Posição do limiar", `${t.posicao}ª de ${t.n_calibracao}`, `percentil efetivo ${num(t.percentil_efetivo, 4)}%`, "percentil"),
    card("Janelas de calibração acima", String(t.n_calibracao - t.posicao), null, "fpr"),
    card("Falso alarme esperado por janela", pct(t.falso_alarme_esperado_por_janela, 3), null, "fpr"));
  const warn = t.maximo_amostral ? el("div", { class: "note note-warn", text: `Com ${t.n_calibracao} janelas, o percentil ` +
    `${num(t.percentil_pedido, 4)} cai no maior escore da calibração: ele não se sustenta com tão poucas janelas ` +
    `(seriam precisas ${t.n_minimo_para_o_percentil ?? "infinitas"}).` }) : null;
  const curve = quadro({ titulo: "Escores de calibração, do menor ao maior, e o limiar", chave: "limiar", arquivo: `limiar-${params.modelo}`,
    desenhar: (area, largura, cores) => graficoLinhas(area, largura, cores, { titulo: "Escores de calibração ordenados",
      proporcao: 0.38, xRotulo: "janelas de calibração, do menor ao maior escore", yRotulo: "escore",
      series: [{ nome: "escore", cor: MODELO_COR(cores, params.modelo), pontos: sorted.map((v, i) => [i + 1, v]) }],
      linhasH: [{ y: t.limiar, cor: cores.limiar, rotulo: `limiar ${num(t.limiar, 4)}` }],
      marcas: sorted.map((v, i) => [i + 1, v]).filter(([i]) => i > t.posicao).map(([x, y]) => ({ x, y, cor: cores.limiar,
        dica: [`${x}ª janela: escore ${num(y, 4)}`, "acima do limiar"] })) }),
    csv: () => [["posicao", "escore"], ...sorted.map((v, i) => [i + 1, v])] });
  const w = data.janela;
  const windowSlider = slider("Janela de calibração", { min: 0, max: sorted.length - 1, step: 1, value: w.indice,
    format: (v) => `nº ${v + 1}` }, (v) => { params.janela = v; debounce(rerun); });
  const top = new Set(w.maiores);
  const variables = quadro({ titulo: `Erro das 24 variáveis na janela nº ${w.indice + 1}; as ${params.k} maiores em destaque`,
    chave: "k", arquivo: `variaveis-janela-${w.indice + 1}`,
    desenhar: (area, largura, cores) => barrasAgrupadas(area, largura, cores, { titulo: "Erro por variável", altura: 300,
      rotulosInclinados: true, yRotulo: "erro",
      grupos: w.variaveis.map((name, i) => ({ id: name, rotulo: name, indice: i })),
      series: [{ id: "erro", nome: "erro", cor: (g) => (top.has(g.indice) ? cores.limiar : cores.eixo) }],
      valor: (g) => w.erros[g.indice], dica: (g, s, v) => [g.rotulo, `erro ${num(v, 4)}`, top.has(g.indice) ? "entre as k maiores" : ""] }),
    csv: () => [["variavel", "erro", "entre_as_k_maiores"], ...w.variaveis.map((name, i) => [name, w.erros[i], top.has(i) ? "sim" : "não"])] });
  output.replaceChildren(cards, ...(warn ? [warn] : []), curve, el("div", { class: "controls" }, windowSlider.node), variables,
    el("div", { class: "metrics" }, card("Média das 24 variáveis", num(w.media_todas, 4)),
      card(`Média das ${params.k} maiores (o escore)`, num(w.media_k, 4), null, "escore"),
      card("Quanto o escore amplia a média", `${num(w.media_k / w.media_todas, 3)}×`, null, "k")));
}

/* Alarme e detecção: reusa os ensaios de teste. */
async function renderAlarms(body) {
  const o = science.options;
  const official = () => ({ modelo: science.alarms?.modelo || o.modelos[0].id, semente: o.semente_referencia,
    k: o.k_canonico, percentil: o.percentil_canonico, confirmacoes: o.confirmacoes_canonicas, ensaio: science.alarms?.ensaio || o.ensaios[0] });
  const params = science.alarms ||= official();
  const output = el("div", { class: "science-output" });
  const rerun = async () => {
    try { drawAlarms(output, await api("/api/ciencia/alarme", { method: "POST", json: params })); }
    catch (error) { toast(error.message); }
  };
  body.replaceChildren(el("div", { class: "note note-warn science-notice", text: "Estes controles reusam os ensaios de teste. " +
      "Servem para explorar; os números oficiais continuam os da avaliação de 27/09/2026." }),
    gpvsControls(params, rerun, { withConfirmations: true, withTrial: true }),
    el("button", { class: "secondary", type: "button",
      text: `Voltar aos valores oficiais (k = ${o.k_canonico}, p${num(o.percentil_canonico)}, ${o.confirmacoes_canonicas} janelas)`,
      onclick: () => { science.alarms = official(); openScience("explorar"); } }), output);
  await rerun();
}

function drawAlarms(output, data) {
  const fa = data.falsos_alarmes, c = data.canonico, s = data.resumo;
  const cards = el("div", { class: "metrics" },
    card("Ensaios detectados", `${s.detectados} de ${data.ensaios.length}`, `oficial: ${c.detectados}`, "detectados"),
    card("Atraso mediano", seconds(s.atraso_mediano_ms), `oficial: ${seconds(c.atraso_mediano_ms)}`, "atraso"),
    card("Alarmes falsos no teste saudável", String(fa.teste_saudavel.alarmes),
      `limite superior: ${num(fa.teste_saudavel.limite_superior_por_hora, 4)} por hora · oficial: ${c.alarmes_teste_saudavel}`, "limite_superior"),
    card("Alarmes antes da falha", String(fa.pre_falha.alarmes), `oficial: ${c.alarmes_pre_falha}`, "alarmes_antes"),
    card("Limiar", num(data.limiar.limiar, 5), `oficial: ${num(c.limiar, 5)}`, "limiar"),
    ...["sensibilidade", "especificidade", "f1", "mcc"].map((key) => card(METRICAS[key], dec(s[`${key}_media`]), null, key, "Média dos 14 ensaios.")));
  const same = data.parametros_canonicos ? el("div", { class: "note note-ok", text: "Com estes valores, os números são os oficiais de 27/09/2026." }) : null;
  const counts = ["vp", "fn", "fp", "vn"].reduce((acc, key) => ({ ...acc, [key]: data.ensaios.reduce((sum, t) => sum + (t[key] || 0), 0) }), {});
  const matrix = quadro({ titulo: `Matriz de confusão · ${NOME_MODELO[data.modelo]} · valores escolhidos`, chave: "matriz",
    arquivo: `matriz-exploracao-${data.modelo}`,
    desenhar: (area, largura, cores) => matrizDeConfusao(area, largura, cores, { contagens: counts, titulo: "Matriz de confusão (exploração)" }),
    csv: () => [["", "Predita saudável", "Predita falha"], ["Real saudável", counts.vn, counts.fp], ["Real falha", counts.fn, counts.vp]] });
  const rows = data.ensaios.map((t) => [t.ensaio, t.falha + (t.fisica ? "" : " (não física)"), t.modo,
    t.detectado ? "sim" : "não", seconds(t.atraso_ms), t.alarmes_pre_falha, dec(t.sensibilidade), dec(t.especificidade),
    t.canonico ? `${t.canonico.detectado ? "sim" : "não"} · ${seconds(t.canonico.atraso_ms)}` : "—"]);
  const parts = [cards, ...(same ? [same] : []), matrix,
    table(["Ensaio", "Falha", "Modo", comNota("Detectou", "detectados"), comNota("Atraso", "atraso"), comNota("Alarmes antes", "alarmes_antes"),
      comNota("Sensibilidade", "sensibilidade"), comNota("Especificidade", "especificidade"), "Oficial"], rows)];
  const line = data.linha_do_tempo;
  if (line) {
    const phases = { comissionamento: line.comissionamento, pre_teste: line.pre_teste, transicao: line.transicao, pos_falha: line.pos_falha };
    const ratios = line.escores.map((v) => v / line.limiar);
    parts.push(quadro({ titulo: `Linha do tempo de ${line.ensaio}: escore ÷ limiar`, chave: "razao", arquivo: `linha-do-tempo-${line.ensaio}`,
      desenhar: (area, largura, cores) => graficoLinhas(area, largura, cores, { titulo: `Escores de ${line.ensaio}`, proporcao: 0.36,
        log: true, xRotulo: "tempo (s)", yRotulo: "escore ÷ limiar", dicaX: (x) => `${num(x)} s`,
        series: [{ nome: NOME_MODELO[data.modelo], cor: MODELO_COR(cores, data.modelo), pontos: ratios.map((v, i) => [i * 0.02, v]) }],
        faixas: Object.entries(phases).filter(([, span]) => span).map(([phase, [a, b]]) =>
          ({ de: a * 0.02, ate: (b + 1) * 0.02, cor: cores.fases[phase], opacidade: phase === "transicao" ? 0.3 : 0.12 })),
        linhasH: [{ y: 1, cor: cores.limiar, rotulo: "limiar" }], linhasV: [{ x: line.inicio_nominal * 0.02, cor: cores.inicio }],
        marcas: line.alarmes.map((i) => ({ x: i * 0.02, y: ratios[i], cor: cores.limiar, forma: "triangulo", dica: [`alarme em ${num(i * 0.02)} s`] })) }),
      csv: () => [["janela", "tempo_s", "escore", "escore_sobre_limiar"], ...line.escores.map((v, i) => [i, i * 0.02, v, ratios[i]])] }));
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
    (v) => { params.horas_por_ano = v; debounce(rerun); }, "horas_ano");
  const presetOptions = [["", "Escolha um cenário da pesquisa…"], ...presets.map((p, i) => [i, p.cenario.name])];
  const controls = el("div", { class: "controls" },
    select("Ponto de partida", presetOptions, "", (value) => {
      const scenario = presets[Number(value)]?.cenario;
      if (!scenario?.time_base) return;
      Object.assign(params, { taxa: scenario.parameters.rate, horas_por_ano: scenario.time_base.hours_per_year,
        base: scenario.time_base.basis, nome: scenario.name, fontes: scenario.sources, hipoteses: scenario.assumptions });
      openScience("confiabilidade");
    }),
    el("label", { class: "control" }, el("span", {}, "λ (falhas por hora)", nota("lambda")), rate),
    hours.node,
    select("Base de tempo", [["operation", "horas de operação"], ["calendar", "horas de calendário"]], params.base,
      (v) => { params.base = v; rerun(); }, "base_tempo"),
    slider("Horizonte", { min: 1, max: 40, step: 1, value: params.horizonte, format: (v) => `${v} anos` },
      (v) => { params.horizonte = v; debounce(rerun); }).node);
  body.replaceChildren(el("p", { class: "muted", text: "Vida exponencial (taxa constante), calculada pelo serviço de confiabilidade. Explorar não grava nada." }),
    controls, output, saveScenarioForm(params), scenarioJsonForm());
  await rerun();
}

function reliabilityChart(rows, unit = "anos") {
  return quadro({ titulo: "R(t) e F(t)", chave: "r_t", extra: GLOSSARIO.f_t, arquivo: "confiabilidade",
    desenhar: (area, largura, cores) => graficoLinhas(area, largura, cores, { titulo: "Confiabilidade e chance de falhar",
      proporcao: 0.4, legenda: true, yDominio: [0, 1], xRotulo: unit, yRotulo: "probabilidade", dicaX: (x) => `${num(x)} ${unit}`,
      dicaY: (v) => pct(v),
      series: [{ nome: "R(t), confiabilidade", cor: cores.denso, pontos: rows.map((r) => [r.time, r.reliability]) },
        { nome: "F(t), chance de falhar", cor: cores.limiar, pontos: rows.map((r) => [r.time, r.failure_probability]) }] }),
    csv: () => [["tempo", "R(t)", "F(t)"], ...rows.map((r) => [r.time, r.reliability, r.failure_probability])] });
}

function drawReliability(output, result, params) {
  const rows = result.rows;
  const marks = rows.filter((r) => Number.isInteger(r.time) && [1, 5, 10, 20, 30, 40].includes(r.time));
  output.replaceChildren(
    el("div", { class: "metrics" }, card("MTTF", `${num(result.summary.mttf, 4)} anos`, null, "mttf"),
      card("λ por ano, na base escolhida", `${num(result.summary.rate, 4)} por ano`, null, "lambda"),
      ...marks.slice(0, 3).map((r) => card(`Chance de falhar em ${r.time} ano(s)`, pct(r.failure_probability), null, "f_t"))),
    reliabilityChart(rows),
    table(["Anos", comNota("R(t)", "r_t"), comNota("F(t)", "f_t")], marks.map((r) => [r.time, num(r.reliability, 4), pct(r.failure_probability)])),
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
  try { data = await api("/api/ciencia/fmeca"); } catch (error) { aviso(body, error.message); return; }
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
  const ranking = (titulo, chave, list, value, format, arquivo) => quadro({ titulo, chave, arquivo,
    desenhar: (area, largura, cores) => barrasHorizontais(area, largura, cores, { titulo, formato: format,
      margemEsquerda: Math.min(230, largura * 0.45),
      itens: list.map((item) => ({ id: item.id, rotulo: item.nome, valor: value(item), cor: cores.denso })) }),
    csv: () => [["grupo", titulo], ...list.map((item) => [item.nome, value(item)])] });
  return el("div", { class: "science-output" },
    el("p", { class: "muted", text: `${data.criterio} Notas: ${data.fonte_notas}` }),
    table(["Grupo", comNota("S", "severidade"), comNota("O", "ocorrencia"), comNota("D", "deteccao"), comNota("NPR", "npr"),
      comNota("λ (1/h)", "lambda"), comNota("MTBF em operação", "mtbf"), comNota("F(1 ano)", "f_t"), comNota("F(20 anos)", "f_t")],
    items.map((item) => {
      const r = operation(item);
      return [item.nome, item.S, item.O, item.D, item.npr, num(item.taxa_por_hora), `${num(r.mtbf_anos, 3)} anos`,
        pct(r.horizontes["1"].chance_de_falhar), pct(r.horizontes["20"].chance_de_falhar)];
    })),
    el("div", { class: "science-pair" },
      ranking("Ordem pelo NPR (S × O × D)", "npr", byNpr, (i) => i.npr, (v) => String(v), "fmeca-npr"),
      ranking("Ordem pela taxa de falha (×10⁻⁶ por hora)", "lambda", byRate, (i) => i.taxa_por_hora * 1e6, (v) => dec(v), "fmeca-taxa")),
    el("p", { class: "muted", text: "As duas ordens ficam separadas, sem nota agregada (decisão de 27/09/2026)." }),
    ...(data.pares_discordantes_O_taxa?.length ? [el("h3", { class: "science-h", text: "Pares em que a ocorrência O e a taxa discordam" }),
      table(["Maior O", "Menor O", "O", "Taxas (1/h)"], data.pares_discordantes_O_taxa.map((p) => [p.maior_O, p.menor_O,
        p.O.join(" × "), p.taxas.map((t) => num(t)).join(" × ")]))] : []),
    el("h3", { class: "science-h", text: "Ressalvas e limites" }),
    el("ul", { class: "science-list" }, ...[...(data.ressalvas || []), ...(data.limites || [])].map((text) => el("li", { text }))));
}

/* 6. Rodar e arquivos: preparar, treinar e avaliar pelos próprios comandos, e os resultados gravados. */
const STEP_NAMES = { preparar: "Preparo", treinar: "Treino", avaliar: "Avaliação" };
const JOB_STATES = { processando: "em andamento", concluido: "concluído", falhou: "falhou", cancelado: "cancelado" };
const CONSULTATION_STATES = { iniciada: "iniciada", concluida: "concluída", falhou: "falhou", cancelada: "cancelada" };

async function renderRunsAndFiles(body) {
  const runs = el("div", { class: "science-output" });
  const files = el("div", { class: "science-output" });
  body.replaceChildren(el("h3", { class: "science-h", text: "Rodar" }), runs,
    el("h3", { class: "science-h", text: "Arquivos de resultados" }), files);
  await Promise.all([renderRuns(runs), renderResults(files)]);
}

async function renderRuns(body) {
  let info;
  try { info = await api("/api/ciencia/gpvs"); } catch (error) { aviso(body, error.message); return; }
  if (!info.disponivel) { aviso(body, `Não dá para rodar agora: falta ${info.faltando.join("; ")}.`); return; }
  const c = info.canonica;
  const progress = el("div", { class: "science-output" });
  const prep = { separacao: c.separacao };
  const train = science.train ||= { separacao: c.separacao, sementes: c.sementes.join(","), teto_epocas: c.teto_epocas };
  const badge = el("span", { class: "badge" });
  const updateBadge = () => {
    const seeds = String(train.sementes).split(",").map((s) => Number(s.trim())).join(",");
    const same = Number(train.separacao) === c.separacao && seeds === c.sementes.join(",") && Number(train.teto_epocas) === c.teto_epocas;
    badge.className = `badge ${same ? "badge-ok" : "badge-warn"}`;
    badge.textContent = same ? "ajustes originais" : "ajustes diferentes (exploração)";
  };
  const field = (label, key, target, attrs = {}, chave) => {
    const input = el("input", { value: target[key], ...attrs });
    input.addEventListener("input", () => { target[key] = input.value; updateBadge(); });
    return el("label", { class: "control" }, el("span", {}, label, ...(chave ? [nota(chave)] : [])), input);
  };
  const trainingSelect = el("select", {}, ...info.treinos.map((item) => {
    const option = el("option", { value: item.pasta, text: `${item.pasta} (${item.canonica ? "ajustes originais" : "exploração"})` });
    if (item.pasta === c.treino) option.selected = true;
    return option;
  }));
  const cards = el("div", { class: "run-grid" },
    el("section", { class: "run-card" }, el("h3", { class: "science-h", text: "1. Preparar" }),
      el("p", { class: "muted", text: "Divide os dados (50/15/15/20), normaliza só com o treino e confere a autocorrelação. Não usa modelos nem os ensaios de teste." }),
      field("Separação entre blocos (janelas)", "separacao", prep, { type: "number", min: 0, max: 200 }),
      el("button", { class: "primary", type: "button", text: "Preparar", onclick: () => launch("/api/ciencia/gpvs/preparar", prep, progress) })),
    el("section", { class: "run-card" }, el("h3", { class: "science-h", text: "2. Treinar" }),
      el("p", { class: "muted", text: "Treina o Denso e o AE-LSTM em cada repetição, para pela validação e põe o limiar no percentil 99 da calibração." }),
      field("Separação entre blocos (janelas)", "separacao", train, { type: "number", min: 0, max: 200 }),
      field("Repetições do treino (um número por repetição, separados por vírgula)", "sementes", train, {}, "treinos"),
      field("Teto de épocas (só de segurança)", "teto_epocas", train, { type: "number", min: 1 }),
      badge,
      el("button", { class: "primary", type: "button", text: "Treinar (cerca de 2 min)", onclick: () => launch("/api/ciencia/gpvs/treinar", train, progress) })),
    el("section", { class: "run-card" }, el("h3", { class: "science-h", text: "3. Avaliar" }),
      el("p", { class: "muted", text: "Pontua de novo o teste saudável e os 14 ensaios com falha. Fica registrada como exploração; a avaliação oficial continua a de 27/09." }),
      el("label", { class: "control" }, el("span", { text: "Rodada de treino (pasta)" }), trainingSelect),
      el("button", { class: "primary", type: "button", text: "Avaliar…", disabled: info.treinos.length ? null : true,
        onclick: () => confirmEvaluation(trainingSelect.value, info.frase, progress) })));
  updateBadge();
  const history = el("details", { class: "historico" }, el("summary", { text: "Histórico de avaliações" }),
    table(["Nº", "Data", "Treino (pasta)", "Resultado (pasta)", "Estado", "Tipo"], info.consultas.map((item) => [
      item.numero, day(item.data), item.treino?.pasta, item.saida, CONSULTATION_STATES[item.estado] || item.estado,
      item.tipo === "reanalise" ? "reanálise com o início observado (mesmos escores)" : item.canonica ? "oficial" : "exploração"])));
  body.replaceChildren(el("p", { class: "muted", text: "Cada etapa roda o mesmo comando do terminal e grava numa pasta nova de resultados, uma por vez." }),
    progress, cards, history);
  if (info.tarefa) watch(info.tarefa.id, progress);
}

function confirmEvaluation(training, phrase, progress) {
  const input = el("input", { autocomplete: "off", placeholder: phrase });
  const go = el("button", { class: "primary", type: "button", text: "Avaliar", disabled: true });
  input.addEventListener("input", () => { go.disabled = input.value.trim().toLowerCase() !== phrase; });
  const dialog = el("dialog", { class: "dialog", "aria-labelledby": "consulta-titulo" },
    el("h2", { id: "consulta-titulo", text: "Avaliar de novo" }),
    el("p", { class: "muted", text: `Avaliar ${training} pontua de novo o teste saudável e os 14 ensaios com falha, os mesmos da ` +
      "avaliação oficial de 27/09. O resultado fica registrado como exploração e não substitui o oficial. " +
      "Não use esse resultado para escolher ajustes: os ensaios de teste deixariam de ser um teste independente." }),
    el("label", { class: "field" }, `Digite "${phrase}" para confirmar`, input),
    el("div", { class: "dialog-actions" }, el("button", { class: "secondary", type: "button", text: "Cancelar", onclick: () => dialog.close() }), go));
  go.addEventListener("click", () => { dialog.close(); launch("/api/ciencia/gpvs/avaliar", { treino: training, frase: input.value }, progress); });
  dialog.addEventListener("close", () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
  input.focus();
}

async function launch(path, payload, progress) {
  try {
    const job = await api(path, { method: "POST", json: payload });
    watch(job.tarefa, progress);
  } catch (error) { toast(error.message); }
}

async function watch(id, box) {
  for (;;) {
    let job;
    try { job = await api(`/api/ciencia/tarefas/${id}`); } catch (error) { box.replaceChildren(el("p", { class: "muted", text: error.message })); return; }
    if (!box.isConnected) return;  // a seção foi trocada; a etapa continua no servidor
    const running = job.estado === "processando";
    const elapsed = running ? (Date.now() - Date.parse(job.iniciado_em)) / 1000 : job.decorrido_s;
    const title = `${STEP_NAMES[job.etapa] || job.etapa} → ${job.pasta}: ${JOB_STATES[job.estado] || job.estado}, ${num(elapsed, 3)} s`;
    const actions = el("div", { class: "dialog-actions" });
    if (running) {
      actions.append(el("button", { class: "secondary", type: "button", text: "Cancelar etapa", onclick: async () => {
        try { await api("/api/ciencia/gpvs/cancelar", { method: "POST" }); } catch (error) { toast(error.message); }
      } }));
    } else if (job.resultado?.pasta) {
      actions.append(el("button", { class: "primary", type: "button", text: "Abrir o resultado",
        onclick: () => { science.result = job.resultado.pasta; openScience("rodar"); } }));
    }
    const tone = job.estado === "falhou" ? "note-warn" : job.estado === "concluido" ? "note-ok" : "";
    box.replaceChildren(el("div", { class: `note ${tone} run-status`, text: title }),
      ...(job.erro ? [el("p", { class: "muted", text: job.erro })] : []),
      ...(job.linhas?.length ? [el("pre", { class: "run-log", text: job.linhas.slice(-12).join("\n") })] : []), actions);
    if (!running) {
      if (job.estado === "concluido" && !science.refreshed?.has(id)) {
        (science.refreshed ||= new Set()).add(id);
        if (science.tab === "rodar") openScience("rodar");  // atualiza as rodadas e o histórico
      }
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

/* Resultados gravados: pelo nome e pela data; a pasta aparece como detalhe. */
async function renderResults(body) {
  let items = [];
  try { items = await api("/api/ciencia/resultados"); } catch (error) { toast(error.message); }
  if (!items.length) { body.replaceChildren(el("p", { class: "muted", text: "Nenhum resultado gravado ainda." })); return; }
  const viewer = el("article", { class: "doc-viewer" }, el("p", { class: "muted", text: "Escolha um resultado." }));
  const list = el("ul", { class: "doc-list" }, ...items.map((item) => el("li", {}, el("button", { class: "doc-item", type: "button",
    "data-result": item.id, onclick: () => showResult(item, viewer) },
    el("span", { class: "doc-title", text: item.titulo }), el("span", { class: "doc-ref", text: item.rotulo }),
    el("span", { class: "doc-meta" }, el("span", { text: item.modificado ? new Date(item.modificado).toLocaleString("pt-BR") : "" }))))));
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
  const parts = [el("div", { class: "doc-viewer-head" }, el("span", { class: "muted", text: `${data.rotulo} · pasta: ${data.caminho}` }))];
  if (data.consulta) {
    parts.push(el("div", { class: `note ${data.consulta.canonica ? "note-ok" : "note-warn"}`, text: data.consulta.canonica
      ? "Avaliação oficial, de 27/09/2026."
      : `Avaliação feita depois da oficial, em ${day(data.consulta.data)}: é exploração. Os números oficiais continuam os de 27/09.` }));
  }
  if (data.tipo === "gpvs-reanalise") {
    parts.push(el("div", { class: "note note-ok", text: "Reanálise dos mesmos escores da avaliação oficial de 27/09, com o início " +
      "observado das falhas. Não pontua o teste de novo, e a avaliação oficial continua a de 27/09." }));
  }
  if (data.configuracao_canonica !== undefined) {
    parts.push(el("div", { class: `note ${data.configuracao_canonica ? "note-ok" : "note-warn"}`, text: data.configuracao_canonica
      ? "Treino com os ajustes originais." : "Treino com ajustes diferentes dos originais (exploração)." }));
  }
  if (data.execucao) {
    parts.push(el("p", { class: "muted", text: `Feita pela interface (${JOB_STATES[data.execucao.estado] || data.execucao.estado}): ` +
      `${new Date(data.execucao.iniciado_em).toLocaleString("pt-BR")} a ${new Date(data.execucao.terminado_em).toLocaleString("pt-BR")}.` }));
  }
  if (data.curvas?.linhas?.length) parts.push(reliabilityChart(data.curvas.linhas, data.curvas.unidade === "year" ? "anos" : data.curvas.unidade));
  if (data.fmeca) parts.push(fmecaView(data.fmeca));
  if (data.calibracao) {
    for (const [kind, curve] of Object.entries(data.calibracao.modelos)) {
      parts.push(quadro({ titulo: `${NOME_MODELO[kind] || kind}: escores de calibração do treino de referência ` +
        `(k = ${data.calibracao.k}, percentil ${num(data.calibracao.percentil)})`, chave: "limiar", arquivo: `calibracao-${kind}`,
      desenhar: (area, largura, cores) => graficoLinhas(area, largura, cores, { titulo: "Escores de calibração", proporcao: 0.36,
        xRotulo: "janelas, do menor ao maior escore", yRotulo: "escore",
        series: [{ nome: "escore", cor: MODELO_COR(cores, kind), pontos: curve.escores_ordenados.map((v, i) => [i + 1, v]) }],
        linhasH: [{ y: curve.limiar, cor: cores.limiar, rotulo: `limiar ${num(curve.limiar, 5)}` }] }) }));
    }
  }
  if (data.ensaios) {
    parts.push(el("h3", { class: "science-h", text: "Ensaios (treino de referência)" }),
      table(["Modelo", "Ensaio", comNota("Detectou", "detectados"), comNota("Atraso", "atraso"), comNota("Alarmes antes da falha", "alarmes_antes")],
        data.ensaios.linhas.map((r) => [NOME_MODELO[r.modelo] || r.modelo, r.ensaio, r.detectado === "True" ? "sim" : "não",
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
