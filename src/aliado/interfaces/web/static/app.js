"use strict";

const $ = (id) => document.getElementById(id);
// A tela inicial sai do DOM quando há mensagens; a referência permite recolocá-la.
const WELCOME = $("welcome");
const state ={ conversation: null, models: [], skills: [], documents: 0, busy: false, sourcesOf: null,
  infoAnchor: null };
const SKILL_LABELS = {
  "pesquisa-inversores": "Pesquisa · inversores",
  "engenharia": "Engenharia",
  "confiabilidade": "Confiabilidade",
  "nenhuma": "Sem especialização",
};
const SUGGESTIONS = [
  "Quais taxas de falha foram decididas para a FMECA?",
  "Resuma o protocolo de partição e calibração dos detectores",
  "Como converter uma taxa por hora em probabilidade em 20 anos?",
];

const store = {
  get(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* armazenamento opcional */ } },
};

async function api(path, options = {}) {
  const headers = { "x-aliado": "1", ...(options.headers || {}) };
  if (options.json !== undefined) {
    headers["content-type"] = "application/json";
    options.body = JSON.stringify(options.json);
  }
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.erro || "Algo deu errado. Tente de novo.");
  return data;
}

// Resposta em fluxo: linhas JSON {tipo: texto|erro|fim|memoria}. "fim" chega antes do revisor
// de memória, então a resposta aparece sem esperar as anotações novas.
async function streamMessage(cid, body, handlers, signal) {
  const response = await fetch(`/api/conversas/${cid}/mensagens`, {
    method: "POST", signal, body: JSON.stringify(body),
    headers: { "x-aliado": "1", "content-type": "application/json" },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.erro || "Algo deu errado. Tente de novo.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let final = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let index;
    while ((index = buffer.indexOf("\n")) >= 0) {
      const raw = buffer.slice(0, index);
      buffer = buffer.slice(index + 1);
      if (!raw.trim()) continue;
      const event = JSON.parse(raw);
      if (event.tipo === "texto") handlers.onText(event.texto);
      else if (event.tipo === "erro") {
        if (!final) throw new Error(event.erro);
      } else if (event.tipo === "fim") { final = event; handlers.onFinal(event); }
      else if (event.tipo === "memoria") handlers.onMemory?.(event);
    }
  }
  if (!final) throw new Error("A resposta foi interrompida. Tente de novo.");
  return final;
}

function toast(text) {
  const el = $("toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.hidden = true; }, 4200);
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null && value !== false) node.setAttribute(key, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

function formatTokens(value) { return Number(value || 0).toLocaleString("pt-BR"); }

function relativeDate(iso) {
  const date = new Date(iso);
  const days = Math.floor((Date.now() - date) / 86400000);
  if (days < 1) return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  if (days < 7) return `${days} d atrás`;
  return date.toLocaleDateString("pt-BR");
}

function renderMath(node) {
  if (!window.renderMathInElement) return;
  window.renderMathInElement(node, {
    delimiters: [
      { left: "$$", right: "$$", display: true }, { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false }, { left: "$", right: "$", display: false },
    ],
    throwOnError: false,
  });
}

/* Tema */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  store.set("aliado.theme", theme);
}
$("theme").addEventListener("click", () =>
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
applyTheme(store.get("aliado.theme",
  window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));

/* Fonte do texto (lote 22): a escolha fica neste navegador. */
const FONTS = [
  ["padrao", "Padrão", ""], ["arial", "Arial", "Arial, sans-serif"], ["calibri", "Calibri", "Calibri, sans-serif"],
  ["verdana", "Verdana", "Verdana, sans-serif"], ["georgia", "Georgia", "Georgia, serif"],
  ["cambria", "Cambria", "Cambria, serif"], ["times", "Times New Roman", "'Times New Roman', serif"],
  ["mono", "Monoespaçada", "Consolas, monospace"],
];
function applyFont(font) {
  const known = FONTS.some(([key]) => key === font) ? font : "padrao";
  if (known === "padrao") delete document.documentElement.dataset.font;
  else document.documentElement.dataset.font = known;
  $("font").value = known;
  store.set("aliado.font", known);
}
$("font").replaceChildren(...FONTS.map(([key, label, family]) =>
  el("option", { value: key, text: label, ...(family ? { style: `font-family: ${family}` } : {}) })));
$("font").addEventListener("change", (event) => applyFont(event.target.value));
applyFont(store.get("aliado.font", "padrao"));

/* Estado geral */
async function loadState() {
  const data = await api("/api/estado");
  state.skills = data.skills;
  state.models = data.modelos;
  state.documents = data.biblioteca.documentos;
  const skill = $("skill");
  skill.replaceChildren(...[...data.skills.map((s) => s.name).filter((n) => n !== "confiabilidade"),
    "confiabilidade", "nenhuma"].map((name) => el("option", { value: name, text: SKILL_LABELS[name] || name })));
  skill.value = store.get("aliado.skill", "pesquisa-inversores");
  if (!skill.value) skill.value = "pesquisa-inversores";
  const model = $("model");
  model.replaceChildren(...data.modelos.map((m) => el("option", { value: m.alias, text: m.model_id })));
  if (!data.modelos.length) {
    model.replaceChildren(el("option", { value: "", text: "nenhum modelo" }));
    toast("Nenhum modelo Gemini configurado. Confira o .env e reinicie.");
  }
  const savedModel = store.get("aliado.model", "flash");
  if (data.modelos.some((m) => m.alias === savedModel)) model.value = savedModel;
  $("support").setAttribute("aria-pressed", store.get("aliado.support", "false"));
  $("use-library").checked = store.get("aliado.library", "false") === "true";
  $("use-web").checked = store.get("aliado.web", "false") === "true";
  state.results = data.resultados || { disponivel: false };
  updateResultsSwitch();
  updateSupportVisibility();
  updateLibraryLabel();
  showUsage(data.uso);
}

function showUsage(uso) {
  $("usage").textContent = `Hoje ${formatTokens(uso.hoje)} tokens · total ${formatTokens(uso.total)}`;
}

function updateSupportVisibility() {
  const skill = $("skill").value;
  // A pesquisa já carrega confiabilidade; o apoio só faz sentido para as demais.
  $("support").hidden = skill === "pesquisa-inversores" || skill === "confiabilidade";
}

/* Resultados da pesquisa no chat (lote 26): ligado por padrão só na skill do mestrado; a escolha fica por skill. */
function updateResultsSwitch() {
  const skill = $("skill").value;
  $("results-switch").hidden = !state.results?.disponivel;
  $("use-results").checked = store.get(`aliado.results.${skill}`, String(skill === state.results?.skill)) === "true";
}

function updateLibraryLabel() {
  const count = state.documents;
  $("library-label").textContent = count ? `Usar biblioteca (${count})` : "Usar biblioteca";
}

$("skill").addEventListener("change", () => {
  store.set("aliado.skill", $("skill").value);
  updateSupportVisibility();
  updateResultsSwitch();
});
$("use-results").addEventListener("change", () =>
  store.set(`aliado.results.${$("skill").value}`, String($("use-results").checked)));
$("model").addEventListener("change", () => store.set("aliado.model", $("model").value));
$("support").addEventListener("click", () => {
  const next = $("support").getAttribute("aria-pressed") !== "true";
  $("support").setAttribute("aria-pressed", String(next));
  store.set("aliado.support", String(next));
});
$("use-library").addEventListener("change", () => store.set("aliado.library", String($("use-library").checked)));
$("use-web").addEventListener("change", () => store.set("aliado.web", String($("use-web").checked)));

/* Conversas */
async function loadConversations() {
  // Uma primeira pergunta interrompida deixa a conversa vazia; como a página abre sempre na apresentação
  // (lote 27), ela não seria reaberta. Conversas sem mensagens ficam fora da lista, menos a que está aberta.
  const items = (await api("/api/conversas")).filter((item) => item.messages || item.id === state.conversation?.id);
  const list = $("chat-list");
  list.replaceChildren(...items.map((item) => el("li", { class: item.id === state.conversation?.id ? "is-current" : "" },
    el("button", { class: "chat-open", type: "button", title: "Duplo clique para renomear",
      onclick: () => { openConversation(item.id); $("app").classList.remove("drawer-open-small"); },
      ondblclick: () => renameConversation(item) },
    el("span", { class: "chat-title", text: item.title }),
    el("span", { class: "chat-date", text: `${relativeDate(item.updated_at)} · ${item.messages} mensagens` })),
    el("button", { class: "chat-delete", type: "button", "aria-label": `Apagar conversa ${item.title}`,
      title: "Apagar conversa", onclick: () => deleteConversation(item) }, trashIcon()))));
  if (!items.length) list.replaceChildren(el("li", { class: "muted", text: "Suas conversas aparecem aqui." }));
}

function trashIcon() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6");
  svg.append(path);
  return svg;
}

async function deleteConversation(item) {
  const ok = window.confirm(`Apagar a conversa “${item.title}”?\n\nEla sai da lista e vai para a lixeira local ` +
    "(data/conversas/lixeira) e deixa de ser lembrada em outras conversas. As anotações geradas a partir dela "
    + "continuam valendo.");
  if (!ok) return;
  if (state.busy && state.conversation?.id === item.id) state.controller?.abort();
  try {
    await api(`/api/conversas/${item.id}`, { method: "DELETE" });
    if (state.conversation?.id === item.id) {
      state.conversation = null;
      showChat();
      showWelcome();
    }
    await loadConversations();
    toast("Conversa apagada.");
  } catch (error) { toast(error.message); }
}

async function renameConversation(item) {
  const title = window.prompt("Novo título da conversa", item.title);
  if (!title || !title.trim()) return;
  try {
    await api(`/api/conversas/${item.id}`, { method: "PATCH", json: { title } });
    await loadConversations();
  } catch (error) { toast(error.message); }
}

async function openConversation(id) {
  try {
    state.conversation = await api(`/api/conversas/${id}`);
  } catch {
    state.conversation = null;
    return showWelcome();
  }
  showChat();
  const messages = $("messages");
  messages.replaceChildren();
  for (const message of state.conversation.messages) messages.append(renderMessage(message));
  if (!state.conversation.messages.length) showWelcome();
  messages.scrollTop = messages.scrollHeight;
  loadConversations();
}

function showWelcome() {
  WELCOME.hidden = false;
  $("messages").replaceChildren(WELCOME);
  $("suggestions").replaceChildren(...SUGGESTIONS.map((text) =>
    el("button", { class: "suggestion", type: "button", text, onclick: () => { $("question").value = text; autosize(); $("question").focus(); } })));
  closeInfo();
}

$("new-chat").addEventListener("click", () => {
  state.conversation = null;
  showChat();
  showWelcome();
  loadConversations();
  $("question").focus();
});

/* Mensagens */
function renderMessage(message) {
  if (message.role === "user") {
    return el("div", { class: "msg-user" }, el("div", { class: "bubble", text: message.content }));
  }
  const answer = el("div", { class: "answer" });
  answer.innerHTML = message.html; // HTML gerado no servidor, com HTML do modelo escapado
  renderMath(answer);
  answer.querySelectorAll(".cite").forEach((button) =>
    button.addEventListener("click", () => openInfo(message, button, button.dataset.web
      ? { number: button.dataset.web, kind: "web" }
      : button.dataset.result ? { number: button.dataset.result, kind: "result" }
        : { number: button.dataset.cite, kind: "source" })));
  const node = el("article", { class: "msg-assistant", "data-message": message.id }, answer);
  if (message.validation_status === "insufficient_evidence" || message.validation_status === "invalid_citations") {
    node.append(el("div", { class: "note note-warn",
      text: "Resposta local: a biblioteca não sustentou uma resposta com citações. Ela não entra no histórico enviado ao modelo." }));
  }
  if (message.validation_status === "invalid_result_refs") {
    node.append(el("div", { class: "note note-warn",
      text: "Resposta local: o modelo citou um resultado que não recebeu. Ela não entra no histórico enviado ao modelo." }));
  }
  if (message.results_status === "numeros_nao_conferidos") {
    node.append(el("div", { class: "note note-warn",
      text: `Estes números não vieram dos resultados citados: ${(message.numeros_nao_conferidos || []).join("; ")}. ` +
        "Confira na aba Ciência. A resposta não entra no histórico enviado ao modelo." }));
  }
  if (message.numeros_sem_marca && message.results_status !== "numeros_nao_conferidos") {
    const n = message.numeros_sem_marca;
    node.append(el("div", { class: "note note-uncited",
      text: `${n === 1 ? "Há 1 número" : `Há ${n} números`} nesta resposta sem a marca de um resultado e que ` +
        "não aparecem nos resultados enviados: não foram conferidos." }));
  }
  if (message.cortada) {
    // Lote 27: o modelo parou no teto de tamanho; a resposta fica fora do histórico.
    node.append(el("div", { class: "note note-warn",
      text: "A resposta foi interrompida pelo limite de tamanho e pode estar incompleta. Peça de novo ou restrinja a pergunta. "
        + "Ela não entra no histórico enviado ao modelo." }));
  }
  if (message.resultados_faltando?.length) {
    node.append(el("div", { class: "note note-uncited",
      text: `Não entraram nesta resposta: ${message.resultados_faltando.join("; ")}.` }));
  }
  if (message.validation_status === "uncited" && !message.result_sources?.length) {
    node.append(el("div", { class: "note note-uncited", text: "Esta resposta não cita trechos dos seus documentos." }));
  }
  const usage = message.usage || {};
  const meta = el("div", { class: "meta" });
  if (message.model && message.provider !== "local") meta.append(el("span", { text: message.model }));
  if (usage.total_tokens) meta.append(el("span", { text: `${formatTokens(usage.total_tokens)} tokens` }));
  if (usage.reasoning_tokens) meta.append(el("span", { text: `${formatTokens(usage.reasoning_tokens)} de raciocínio` }));
  const info = (event) => openInfo(message, event.currentTarget);
  if (message.result_sources?.length) {
    meta.append(el("button", { class: "link result-link", type: "button",
      text: `${message.result_sources.length} resultado(s)`, onclick: info }));
  }
  if (message.sources?.length) {
    meta.append(el("button", { class: "link", type: "button", text: `${message.sources.length} fonte(s)`,
      onclick: info }));
  }
  // Lote 27: quantos dos documentos que a busca trouxe a resposta citou; os outros ficam na janela de fontes.
  const cited = new Set((message.sources || []).map((source) => source.title));
  const brought = new Set([...cited, ...(message.recuperados || []).map((source) => source.title)]);
  if (brought.size > cited.size) {
    meta.append(el("button", { class: "link retrieved-link", type: "button",
      onclick: (event) => openInfo(message, event.currentTarget, { kind: "retrieved" }),
      title: "A busca na biblioteca traz os trechos mais parecidos com a pergunta; nem todos tratam do assunto. Clique para ver os que a resposta não usou.",
      text: cited.size ? `citou ${cited.size} dos ${brought.size} documentos que a busca trouxe`
        : `a busca na biblioteca trouxe ${brought.size} ${brought.size === 1 ? "documento" : "documentos"}` }));
  }
  if (message.web_sources?.length || message.web_queries?.length) {
    const searches = message.web_queries?.length || 0;
    meta.append(el("button", { class: "link web-link", type: "button",
      text: `${searches} ${searches === 1 ? "busca" : "buscas"} na web · ${message.web_sources?.length || 0} fonte(s)`,
      onclick: info }));
  }
  const recalled = message.conversas_lembradas?.length || 0;
  if (recalled) meta.append(el("button", { class: "link memory-link", type: "button",
    text: `lembrou ${recalled} ${recalled === 1 ? "conversa" : "conversas"}`, onclick: info }));
  const used = message.memorias_usadas?.length || 0;
  const created = message.memorias_criadas?.length || 0;
  if (used) meta.append(el("button", { class: "link memory-link", type: "button",
    text: `usou ${used} ${used === 1 ? "memória" : "memórias"}`, onclick: info }));
  if (created) meta.append(el("button", { class: "link memory-link is-new", type: "button",
    text: `${created} ${created === 1 ? "anotação nova" : "anotações novas"}`, onclick: info }));
  if (message.id && message.provider !== "local") {
    meta.append(el("button", { class: "link", type: "button", text: "Lembrar…",
      onclick: () => openRemember() }));
  }
  if (meta.childElementCount) node.append(meta);
  return node;
}

/* Memória */
const KIND_LABELS = { perfil: "Perfil", preferencia: "Preferência", correcao: "Correção", fato: "Fato",
  decisao: "Decisão" };
const ORIGIN_LABELS = { feedback: "sua", comando: "sua", inferido: "inferida" };
const STATUS_LABELS = { ativa: "ativa", conflito: "em conflito", superada: "superada", revogada: "revogada" };

function memorySource(memory) {
  const source = memory.source || {};
  if (source.title) return `${source.title}${source.page ? `, p. ${source.page}` : ""}${source.ficha ? " · ficha de leitura" : ""}`;
  if (source.conversation_title) return `Conversa “${source.conversation_title}”`;
  if (source.manual) return "Criada por você";
  return "";
}

function memoryChip(memory) {
  return el("li", { class: "memory-chip" },
    el("span", { class: `badge ${memory.origin === "inferido" ? "badge-warn" : "badge-ok"}`,
      text: `${KIND_LABELS[memory.kind] || memory.kind} · ${ORIGIN_LABELS[memory.origin] || memory.origin}` }),
    el("span", { class: "memory-chip-text", text: memory.text }));
}

function renderMemoryPanel(message) {
  const panel = $("memory-panel");
  const used = message?.memorias_usadas || [];
  const created = message?.memorias_criadas || [];
  const recalled = message?.conversas_lembradas || [];
  if (!used.length && !created.length && !recalled.length) { panel.replaceChildren(); return; }
  const parts = [el("h2", { class: "panel-title panel-title-spaced", text: "Memória nesta resposta" })];
  if (recalled.length) {
    parts.push(el("p", { class: "muted", text: "Conversas lembradas:" }), el("ul", { class: "memory-chips" },
      ...recalled.map((item) => el("li", { class: "recall-item" },
        el("span", { class: "muted", text: relativeDate(item.created_at) }),
        el("span", { class: "memory-chip-text", text: item.question }),
        el("button", { class: "link", type: "button", text: "Abrir conversa",
          onclick: () => { closeInfo(); openConversation(item.conversation_id); } })))));
  }
  if (used.length) parts.push(el("p", { class: "muted", text: "Usadas:" }), el("ul", { class: "memory-chips" }, ...used.map(memoryChip)));
  if (created.length) parts.push(el("p", { class: "muted", text: "Anotações novas:" }), el("ul", { class: "memory-chips" }, ...created.map(memoryChip)));
  parts.push(el("button", { class: "link", type: "button", text: "Abrir a aba Memória", onclick: () => openMemory() }));
  panel.replaceChildren(...parts);
}

async function refreshMemoryBadge() {
  try {
    const data = await api("/api/memoria?estado=conflito");
    const count = data.contagem.conflito;
    $("memory-badge").hidden = !count;
    $("memory-badge").textContent = String(count);
    $("memory-badge").title = `${count} conflito(s) para decidir`;
  } catch { /* memória opcional */ }
}

function openRemember(memory) {
  const dialog = $("remember-dialog");
  state.editing = memory || null;
  $("remember-title").textContent = memory ? "Editar anotação" : "Lembrar";
  $("remember-hint").textContent = memory
    ? "A edição cria uma versão nova, com origem sua; a anterior fica no histórico."
    : "A anotação vale na hora, como uma decisão sua.";
  $("remember-kind").value = memory?.kind || "preferencia";
  $("remember-kind").disabled = Boolean(memory);
  $("remember-text").value = memory?.text || "";
  $("remember-error").hidden = true;
  dialog.showModal();
  $("remember-text").focus();
}

$("remember-cancel").addEventListener("click", () => $("remember-dialog").close());
$("remember-text").addEventListener("input", () => { $("remember-error").hidden = true; });
$("remember-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = $("remember-text").value.trim();
  if (!text) { $("remember-error").hidden = false; return; }
  try {
    if (state.editing) {
      await api(`/api/memoria/${state.editing.id}/editar`, { method: "POST", json: { texto: text } });
      toast("Anotação editada. A versão anterior ficou no histórico.");
    } else {
      const skill = $("skill").value;
      await api("/api/memoria", { method: "POST", json: {
        texto: text, tipo: $("remember-kind").value, skill: skill === "nenhuma" ? null : skill,
        conversa: state.conversation?.id || null } });
      toast("Anotação guardada na memória.");
    }
    $("remember-dialog").close();
    if (!$("memory-view").hidden) loadMemory();
  } catch (error) { toast(error.message); }
});

const MEMORY_FILTERS = [
  ["ativa", "Ativas"], ["inferido", "Inferidas"], ["conflito", "Conflitos"],
  ["superada", "Superadas"], ["revogada", "Revogadas"], ["todas", "Todas"],
];

async function loadMemory(filter = state.memoryFilter || "ativa") {
  state.memoryFilter = filter;
  const query = filter === "todas" ? "" : filter === "inferido" ? "?estado=ativa&origem=inferido" : `?estado=${filter}`;
  let data;
  try { data = await api(`/api/memoria${query}`); } catch (error) { return toast(error.message); }
  $("memory-filters").replaceChildren(...MEMORY_FILTERS.map(([key, label]) => {
    const count = key === "todas" ? null : data.contagem[key];
    return el("button", { class: `filter${key === filter ? " is-active" : ""}`, type: "button", role: "tab",
      "aria-selected": String(key === filter), onclick: () => loadMemory(key) },
      el("span", { text: label }), count !== null ? el("span", { class: "filter-count", text: String(count) }) : null);
  }));
  const list = $("memory-list");
  if (!data.itens.length) {
    list.replaceChildren(el("li", { class: "empty", text: filter === "ativa"
      ? "Ainda não há anotações. Elas surgem das conversas, das fichas de leitura dos PDFs ou do botão “Nova anotação”."
      : "Nenhuma anotação neste filtro." }));
    return;
  }
  list.replaceChildren(...data.itens.map(renderMemoryCard));
  refreshMemoryBadge();
}

function renderMemoryCard(memory) {
  const badges = el("div", { class: "memory-badges" },
    el("span", { class: "badge", text: KIND_LABELS[memory.kind] || memory.kind }),
    el("span", { class: `badge ${memory.origin === "inferido" ? "badge-warn" : "badge-ok"}`,
      text: memory.origin === "inferido" ? "inferida" : "sua" }),
    memory.status !== "ativa" ? el("span", { class: `badge ${memory.status === "conflito" ? "badge-fail" : ""}`,
      text: STATUS_LABELS[memory.status] }) : null,
    memory.diverges_skill ? el("span", { class: "badge badge-fail", title: "Vale sobre a skill até ser incorporada a ela",
      text: "diverge da skill" }) : null,
    memory.skill ? el("span", { class: "badge", text: SKILL_LABELS[memory.skill] || memory.skill }) : null);
  const source = memory.source || {};
  const origin = el("div", { class: "memory-origin" }, el("span", { text: memorySource(memory) }));
  if (source.document_id) {
    origin.append(el("a", { class: "link", target: "_blank", rel: "noopener",
      href: `/api/biblioteca/${source.document_id}/original${source.page ? `#page=${source.page}` : ""}`, text: "Abrir" }));
  } else if (source.conversation_id) {
    origin.append(el("button", { class: "link", type: "button", text: "Ver conversa", onclick: async () => {
      try { await api(`/api/conversas/${source.conversation_id}`); openConversation(source.conversation_id); }
      catch { toast("A conversa foi apagada; a anotação continua valendo."); }
    } }));
  }
  const actions = el("div", { class: "memory-actions" });
  const act = async (path, message, confirmText) => {
    if (confirmText && !window.confirm(confirmText)) return;
    try { await api(`/api/memoria/${memory.id}/${path}`, { method: "POST", json: {} }); toast(message); loadMemory(); }
    catch (error) { toast(error.message); }
  };
  if (memory.status === "conflito") {
    actions.append(
      el("button", { class: "secondary", type: "button", text: "Aceitar a nova",
        onclick: () => act("aceitar", "Nova anotação aceita; a anterior ficou superada.") }),
      el("button", { class: "secondary", type: "button", text: "Manter a minha",
        onclick: () => act("manter", "A sua anotação continua valendo.") }));
  }
  const verdictBox = el("div", { class: "memory-verdict", hidden: true });
  if (memory.status === "ativa" || memory.status === "conflito") {
    const checkButton = el("button", { class: "link", type: "button", text: "Conferir na web" });
    checkButton.addEventListener("click", async () => {
      checkButton.disabled = true;
      checkButton.textContent = "Conferindo…";
      try {
        const result = await api(`/api/memoria/${memory.id}/conferir`, { method: "POST", json: {} });
        renderVerdict(verdictBox, result);
        if (result.criada) {
          toast(result.criada.status === "conflito"
            ? "A web contradiz uma anotação sua: abri um conflito para você decidir."
            : "A web corrigiu esta dedução; a versão anterior ficou no histórico.");
          setTimeout(() => loadMemory(), 2500);
        }
      } catch (error) { toast(error.message); }
      checkButton.disabled = false;
      checkButton.textContent = "Conferir na web";
    });
    actions.append(checkButton);
    actions.append(
      el("button", { class: "link", type: "button", text: "Editar", onclick: () => openRemember(memory) }),
      el("button", { class: "link danger", type: "button", text: "Revogar",
        onclick: () => act("revogar", "Anotação revogada; ela continua no histórico.",
          "Revogar esta anotação? Ela deixa de ser usada, mas fica no histórico.") }));
  }
  const history = el("div", { class: "memory-history", hidden: true });
  if (memory.supersedes || memory.superseded_by) {
    actions.append(el("button", { class: "link", type: "button", text: "Histórico", onclick: async () => {
      if (!history.hidden) { history.hidden = true; return; }
      try {
        const chain = await api(`/api/memoria/${memory.id}/historico`);
        history.replaceChildren(...chain.map((item) => el("div", { class: `history-item${item.id === memory.id ? " is-current" : ""}` },
          el("span", { class: "muted", text: `${new Date(item.created_at).toLocaleString("pt-BR")} · ${STATUS_LABELS[item.status]} · ${ORIGIN_LABELS[item.origin]}` }),
          el("span", { text: item.text }))));
        history.hidden = false;
      } catch (error) { toast(error.message); }
    } }));
  }
  let conflictNote = null;
  if (memory.conflict_with && memory.status === "conflito") {
    conflictNote = el("p", { class: "note note-warn", text: "Esta dedução contradiz uma anotação sua, que continua valendo até você decidir." });
  } else if (memory.conflict_with && memory.status === "ativa") {
    conflictNote = el("p", { class: "note note-warn" }, "Há uma dedução do agente em conflito com esta anotação. ",
      el("button", { class: "link", type: "button", text: "Ver conflitos", onclick: () => loadMemory("conflito") }));
  }
  return el("li", { class: `memory-card is-${memory.status}` }, badges,
    el("p", { class: "memory-text", text: memory.text }), conflictNote, origin, actions, verdictBox, history);
}

const VERDICTS = {
  confirma: ["A web confirma", "badge-ok"], contradiz: ["A web contradiz", "badge-fail"],
  inconclusivo: ["Inconclusivo", "badge-warn"],
};

function renderVerdict(box, result) {
  const [label, badge] = VERDICTS[result.veredito] || VERDICTS.inconclusivo;
  const parts = [el("div", { class: "memory-badges" }, el("span", { class: `badge ${badge}`, text: label }),
    el("span", { class: "muted", text: `${result.buscas} ${result.buscas === 1 ? "busca" : "buscas"}` }))];
  if (result.explicacao) parts.push(el("p", { class: "verdict-text", text: result.explicacao }));
  if (result.correcao) parts.push(el("p", { class: "verdict-text", text: `Correção proposta: ${result.correcao}` }));
  if (result.fontes?.length) {
    parts.push(el("ul", { class: "verdict-sources" }, ...result.fontes.slice(0, 5).map((source) =>
      el("li", {}, el("a", { class: "link", href: source.uri, target: "_blank", rel: "noopener noreferrer",
        text: source.title || source.domain || "Página" })))));
  } else {
    parts.push(el("p", { class: "muted", text: "A busca não trouxe fontes; nada foi alterado." }));
  }
  box.replaceChildren(...parts);
  box.hidden = false;
}

function openMemory() {
  showView("memory");
  loadMemory();
}

$("memory-add").addEventListener("click", () => openRemember());
$("nav-memory").addEventListener("click", () => openMemory());

function showSources(message) {
  state.sourcesOf = message;
  renderMemoryPanel(message);
  const list = $("source-list");
  const sources = message?.sources || [];
  const web = message?.web_sources || [];
  // Lote 22: a consulta que a biblioteca buscou, reescrita a partir da conversa.
  const query = message?.consulta_biblioteca
    ? [el("p", { class: "muted source-queries", text: `Buscou na biblioteca: ${message.consulta_biblioteca}` })] : [];
  const results = message?.result_sources || [];
  const retrieved = message?.recuperados || [];
  if (!sources.length && !web.length && !results.length && !retrieved.length) {
    list.replaceChildren(...query,
      el("p", { class: "muted", text: "Esta resposta não usou resultados da pesquisa, trechos da biblioteca nem a web." }));
    return;
  }
  // Abrir a página no original e ver a extração: valem para o trecho citado e para o só recuperado.
  const sourceActions = (source) => {
    const actions = el("div", { class: "source-actions" });
    if (source.document_id) {
      const page = source.page ? `#page=${source.page}` : "";
      actions.append(
        el("a", { class: "link", href: `/api/biblioteca/${source.document_id}/original${page}`, target: "_blank",
          rel: "noopener", text: "Abrir página" }),
        el("button", { class: "link", type: "button", text: "Ver Markdown",
          onclick: () => openLibrary(source.document_id) }));
    }
    return actions;
  };
  // As quebras de linha do PDF viram espaço; só a linha em branco continua separando parágrafos.
  const flowText = (value) => String(value || "").replace(/([^\n])\n(?!\n)/g, "$1 ");
  const sourceFlags = (source) => {
    const flags = [];
    if (source.method === "ocr") flags.push("OCR: conferir no original");
    if (source.status === "partial") flags.push("extração parcial");
    return flags;
  };
  const parts = [];
  if (results.length) {
    parts.push(el("h3", { class: "source-group", text: "Resultados da pesquisa" }));
    parts.push(...results.map((block) => {
      const table = el("div", { class: "answer result-table" });
      table.innerHTML = block.html || ""; // Markdown gerado por código e renderizado no servidor
      const day = String(block.data || "").split("-").reverse().join("/");
      return el("div", { class: "source-card source-result", "data-result": block.citation_id },
        el("div", { class: "source-head" }, el("span", { class: "cite cite-result", text: block.citation_id }),
          el("span", { class: "source-title", title: block.titulo, text: block.titulo })),
        el("div", { class: "source-loc", text: [block.fonte, day].filter(Boolean).join(" · ") }),
        ...(block.estatuto === "secundaria" ? [el("span", { class: "badge badge-warn",
          text: "Secundária: a oficial continua sendo a de 27/09/2026" })] : []),
        table,
        ...(block.notas?.length ? [el("details", { class: "result-notes" }, el("summary", { text: "O que cada indicador significa" }),
          el("ul", {}, ...block.notas.map((note) => el("li", {}, el("b", { text: `${note.nome}: ` }), note.texto))))] : []),
        el("div", { class: "source-actions" }, el("button", { class: "link", type: "button", text: "Ver na aba Ciência",
          onclick: () => { closeInfo(); openScience(block.secao); } })));
    }));
  }
  parts.push(...query);
  if (sources.length && (web.length || results.length)) parts.push(el("h3", { class: "source-group", text: "Seus documentos" }));
  parts.push(...sources.map((source, index) => {
    const number = index + 1;
    const where = [source.locator, source.page ? `p. ${source.page}` : null].filter(Boolean).join(" · ");
    return el("div", { class: "source-card", "data-source": String(number) },
      el("div", { class: "source-head" }, el("span", { class: "cite", text: String(number) }),
        el("span", { class: "source-title", title: source.title,
          text: source.referencia ? `${source.referencia} · ${source.title}` : source.title })),
      el("div", { class: "source-loc", text: [`v${source.version}`, where, ...sourceFlags(source)].filter(Boolean).join(" · ") }),
      // A passagem enviada ao modelo: o trecho achado pela busca com os vizinhos da mesma página (lote 27).
      el("p", { class: "source-text", text: flowText(source.passagem || source.text) }),
      sourceActions(source));
  }));
  if (retrieved.length) {
    // O que a busca trouxe e a resposta não citou (lote 27): cada passagem abre ao clicar.
    parts.push(el("h3", { class: "source-group source-retrieved",
      text: sources.length ? "A busca também trouxe" : "O que a busca na biblioteca trouxe" }),
      el("p", { class: "muted source-queries",
        text: "Trechos que a busca recuperou e a resposta não citou. Nem todos tratam do assunto da pergunta. "
          + "Clique em um trecho para ler." }));
    parts.push(...retrieved.map((source) => {
      const name = source.referencia || source.title;
      const where = source.page ? `p. ${source.page}` : source.locator;
      return el("details", { class: "source-card source-more" },
        el("summary", {}, el("span", { class: "source-title", title: source.title, text: name }),
          el("span", { class: "source-loc", text: [where, ...sourceFlags(source)].filter(Boolean).join(" · ") }),
          // O começo do trecho achado pela busca distingue dois trechos da mesma página antes de abrir.
          el("span", { class: "source-peek", text: flowText(source.text).replace(/\s+/g, " ").slice(0, 140) })),
        el("p", { class: "source-text", text: flowText(source.passagem || source.text) }),
        sourceActions(source));
    }));
  }
  if (web.length) {
    parts.push(el("h3", { class: "source-group", text: "Na web" }));
    if (message.web_queries?.length) {
      parts.push(el("p", { class: "muted source-queries", text: `Buscou: ${message.web_queries.join(" · ")}` }));
    }
    parts.push(...web.map((source, index) => {
      const number = index + 1;
      const name = source.title || source.domain || "Página";
      return el("div", { class: "source-card source-web", "data-web": String(number) },
        el("div", { class: "source-head" }, el("span", { class: "cite cite-web", text: String(number) }),
          el("span", { class: "source-title", title: name, text: name })),
        el("div", { class: "source-loc", text: source.domain && source.domain !== name ? source.domain : "Fonte externa: confira no original" }),
        el("div", { class: "source-actions" }, el("a", { class: "link", href: source.uri, target: "_blank",
          rel: "noopener noreferrer", text: "Abrir página" })));
    }));
  }
  list.replaceChildren(...parts);
}

const SMALL = window.matchMedia("(max-width: 1100px)");

/* Janela de fontes e memória: abre sobre a resposta, perto do link clicado. */
function openInfo(message, anchor, focus) {
  showSources(message);
  const pop = $("info-popover");
  pop.hidden = false;
  state.infoAnchor = anchor;
  placeInfo(anchor);
  if (focus?.kind === "retrieved") pop.querySelector(".source-retrieved")?.scrollIntoView({ block: "start" });
  else if (focus) highlightSource(focus.number, focus.kind);
  else pop.scrollTop = 0;
}

function placeInfo(anchor) {
  const pop = $("info-popover");
  const area = $("chat-view").getBoundingClientRect();
  const rect = anchor.getBoundingClientRect();
  const width = Math.max(260, Math.min(560, area.width - 24));
  pop.style.width = `${width}px`;
  pop.style.left = `${Math.min(Math.max(rect.left - 24, area.left + 12), area.right - width - 12)}px`;
  // Abre acima do link se couber (ou se houver mais espaço acima); a altura nunca passa da tela.
  const above = rect.top - area.top - 16;
  const below = window.innerHeight - rect.bottom - 16;
  pop.style.maxHeight = "";
  const natural = Math.min(pop.scrollHeight, window.innerHeight * 0.6);
  if (above >= Math.min(natural, 240) || above >= below) {
    pop.style.top = "";
    pop.style.bottom = `${window.innerHeight - rect.top + 8}px`;
    pop.style.maxHeight = `${Math.min(above, window.innerHeight * 0.6)}px`;
  } else {
    pop.style.bottom = "";
    pop.style.top = `${rect.bottom + 8}px`;
    pop.style.maxHeight = `${Math.min(below, window.innerHeight * 0.6)}px`;
  }
}

function closeInfo() {
  $("info-popover").hidden = true;
  state.infoAnchor = null;
}

$("info-close").addEventListener("click", closeInfo);
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeInfo(); });
document.addEventListener("click", (event) => {
  const pop = $("info-popover");
  if (!pop.hidden && !pop.contains(event.target) && !event.target.closest(".cite, .meta .link")) closeInfo();
});
window.addEventListener("resize", closeInfo);
$("messages").addEventListener("scroll", () => { if (state.infoAnchor?.isConnected) placeInfo(state.infoAnchor); });
$("scrim").addEventListener("click", () => $("app").classList.remove("drawer-open-small"));

function highlightSource(number, kind = "source") {
  const key = kind === "web" ? "web" : kind === "result" ? "result" : "source";
  document.querySelectorAll(".source-card").forEach((card) =>
    card.classList.toggle("is-active", card.dataset[key] === String(number)));
  document.querySelector(`.source-card[data-${key}="${number}"]`)?.scrollIntoView({ behavior: "smooth",
    block: kind === "result" ? "start" : "nearest" });
}

function autosize() {
  const area = $("question");
  area.style.height = "auto";
  area.style.height = `${Math.min(area.scrollHeight, 220)}px`;
}
$("question").addEventListener("input", autosize);
$("question").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (!state.busy) $("composer").requestSubmit(); // Enter nunca interrompe uma resposta em curso
  }
});

function setBusy(busy) {
  state.busy = busy;
  $("send").classList.toggle("is-stop", busy);
  $("send").setAttribute("aria-label", busy ? "Parar resposta" : "Enviar");
  $("send").title = busy ? "Parar resposta" : "";
}

function nearBottom(node) { return node.scrollHeight - node.scrollTop - node.clientHeight < 120; }

$("composer").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy) { state.controller?.abort(); return; }
  const text = $("question").value.trim();
  if (!text) return;
  if (!$("model").value) return toast("Nenhum modelo configurado. Confira o .env e reinicie.");
  setBusy(true);
  state.controller = new AbortController();
  const token = Symbol("pedido");
  state.token = token;
  try {
    if (!state.conversation) {
      state.conversation = await api("/api/conversas", { method: "POST" });
      state.conversation.messages = [];
      $("messages").replaceChildren();
    }
    const messages = $("messages");
    if (WELCOME.isConnected) WELCOME.remove();
    messages.append(renderMessage({ role: "user", content: text }));
    const thinking = el("div", { class: "thinking" }, el("span", { class: "dots" }, el("i"), el("i"), el("i")),
      el("span", { text: "AL-IAdo está pensando…" }));
    messages.append(thinking);
    messages.scrollTop = messages.scrollHeight;
    $("question").value = "";
    autosize();
    const skill = $("skill").value;
    const supportOn = !$("support").hidden && $("support").getAttribute("aria-pressed") === "true";
    const userBubble = messages.lastElementChild.previousElementSibling;
    const live = el("div", { class: "answer is-live" });
    const liveNode = el("article", { class: "msg-assistant" }, live);
    let written = "";
    let shown = false;
    try {
      await streamMessage(state.conversation.id, {
        texto: text, skill, apoio: supportOn ? "confiabilidade" : null, modelo: $("model").value,
        biblioteca: $("use-library").checked, web: $("use-web").checked,
        resultados: !$("results-switch").hidden && $("use-results").checked,
      }, {
        onText(piece) {
          const follow = nearBottom(messages);
          if (thinking.isConnected) thinking.replaceWith(liveNode);
          written += piece;
          // As citações [K…] só viram números depois da checagem final no servidor.
          live.textContent = written.replace(/\[K[^\]\s]*\]/g, "[fonte]").replace(/\[R\d+(?:\s*(?:[,;]|e|[-–])\s*R\d+)*\]/g, "[resultado]");
          if (follow) messages.scrollTop = messages.scrollHeight;
        },
        onFinal(data) {
          shown = true;
          // A resposta está salva; o revisor de memória segue em segundo plano sem travar o envio.
          if (state.token === token) { setBusy(false); state.controller = null; }
          thinking.remove();
          liveNode.remove();
          userBubble.remove();
          for (const message of data.mensagens) messages.append(renderMessage(message));
          state.conversation.messages.push(...data.mensagens);
          messages.scrollTop = messages.scrollHeight;
          loadConversations();
          api("/api/estado").then((s) => showUsage(s.uso)).catch(() => {});
        },
        onMemory(event) {
          const message = state.conversation?.messages.find((m) => m.id === event.mensagem);
          if (message) {
            message.memorias_criadas = event.criadas;
            const node = document.querySelector(`[data-message="${event.mensagem}"]`);
            node?.replaceWith(renderMessage(message));
            if (state.sourcesOf?.id === message.id && !$("info-popover").hidden) {
              state.sourcesOf = message;
              renderMemoryPanel(message);
            }
          }
          if (event.criadas?.length) {
            toast(`${event.criadas.length} anotação(ões) nova(s) na memória.`);
            refreshMemoryBadge();
          }
        },
      }, state.controller.signal);
    } catch (error) {
      if (shown) return; // a resposta já foi salva; só o aviso de memória se perdeu
      thinking.remove();
      liveNode.remove();
      userBubble.remove();
      $("question").value = text; // a pergunta volta ao campo para nova tentativa
      autosize();
      toast(error.name === "AbortError" ? "Resposta interrompida. Nada foi gravado." : error.message);
    }
  } catch (error) {
    toast(error.message);
  } finally {
    if (state.token === token) setBusy(false);
  }
});

/* Envio de documentos (lote 27): um pop-up no canto superior direito, visível em todas as abas.
   Os arquivos escolhidos juntos formam um lote; o servidor indexa os que já recebeu e só depois cria as fichas. */
const UPLOAD_OK_MS = 6000;
const UPLOAD_POLL_MS = 1500;
const UPLOAD_PARALLEL = 3;  // envios simultâneos: os arquivos chegam antes de o primeiro terminar a indexação
const UPLOAD_READY_NOTE = "Pronto: o documento já pode ser buscado e citado. As fichas são criadas em seguida.";
const uploads = { lote: null, items: [], earlier: [], polling: false, hidden: false, minimized: false, timer: null,
  misses: 0, issuesKey: null };

const pieces = (count) => (count === 1 ? "1 trecho" : `${count} trechos`);
const STAGE_TEXT = {
  lendo: (job) => `Lendo a página ${job.atual} de ${job.total}`,
  ocr: (job) => `Reconhecendo o texto da página ${job.atual} de ${job.total}`,
  indexando: (job) => (job.atual ? `Indexando: ${job.atual} de ${pieces(job.total)}` : `Indexando ${pieces(job.total)}`),
  "ficha do documento": () => "Criando a ficha do documento",
  ficha: () => "Criando a ficha de leitura",
};

function newBatch() {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

// espera (ainda não enviado), envio, fila, andamento, pronto, parcial ou falha.
function uploadStatus(item) {
  if (item.error) return "falha";
  const job = item.job;
  if (!job) return item.sending ? "envio" : "espera";
  if (job.estado === "falhou" || job.resultado?.status === "failed") return "falha";
  if (job.indexado || job.estado === "concluido") return job.resultado?.status === "partial" ? "parcial" : "pronto";
  return job.estado === "na fila" ? "fila" : "andamento";
}

const uploadIndexed = (item) => ["pronto", "parcial", "falha"].includes(uploadStatus(item));
// Terminado de vez: indexado e com as fichas feitas (ou com falha).
const uploadDone = (item) => Boolean(item.error) || ["concluido", "falhou"].includes(item.job?.estado);
// Falha ou documento indexado só em parte, com o aviso ainda aberto.
const uploadOpen = (item) => !item.dismissed && ["falha", "parcial"].includes(uploadStatus(item));

function uploadFraction(item) {
  const job = item.job;
  if (!job || job.estado !== "processando" || !job.total) return 0;
  if (job.etapa === "lendo" || job.etapa === "ocr") return 0.5 * (job.atual / job.total);
  if (job.etapa === "indexando") return 0.5 + 0.5 * (job.atual / job.total);
  return 0;
}

function uploadStage(item) {
  const status = uploadStatus(item);
  if (status === "espera") return "Aguardando o envio";
  if (status === "envio") return "Enviando o arquivo";
  if (status === "fila") return "Na fila";
  return STAGE_TEXT[item.job.etapa]?.(item.job) || "Preparando a leitura";
}

// Documento já indexado, com as fichas ainda por fazer: elas esperam a indexação dos outros arquivos.
function cardStage(item) {
  const stage = item.job?.etapa;
  return stage === "ficha" || stage === "ficha do documento" ? STAGE_TEXT[stage]() : "As fichas vêm em seguida";
}

// As pendências vêm do servidor; os nomes internos de erro saem do texto mostrado.
const plainIssues = (issues) => (issues || []).map((issue) => issue.replace(/\s*\((?:\w+Error|\w+Exception|TimeoutExpired)\)/g, "")).join(" ");

function uploadProblem(item) {
  const result = item.job?.resultado;
  if (item.error) return item.error;
  if (item.job?.estado === "falhou") return `Não foi possível indexar: ${item.job.erro}`;
  if (result?.status === "failed") return `Não foi possível ler o documento. ${plainIssues(result.issues)}`.trim();
  // O documento reenviado já estava na biblioteca, com a extração incompleta; a duplicata não traz a contagem.
  if (result?.duplicate) return `Este documento já estava na biblioteca, indexado só em parte. ${plainIssues(result.issues)}`.trim();
  return `Indexado só em parte (${pieces(result.trechos)}). ${plainIssues(result.issues)}`.trim();
}

const cardWarning = (item) => item.job?.resultado?.aviso_ficha || item.job?.resultado?.aviso_ficha_documento;

// O que aconteceu com as fichas: as anotações criadas e os avisos de ficha que não pôde ser criada.
function cardNotes(result) {
  const parts = [];
  if (result.fichas) {
    parts.push(`Ficha de leitura: ${result.fichas === 1 ? "1 anotação inferida" : `${result.fichas} anotações inferidas`} na memória.`);
  }
  if (result.aviso_ficha) parts.push(result.aviso_ficha);
  if (result.aviso_ficha_documento) parts.push(result.aviso_ficha_documento);
  return parts;
}

function uploadSummary(item) {
  const result = item.job?.resultado || {};
  if (result.duplicate) return "Este documento já estava na biblioteca.";
  const version = result.version > 1 ? ` (versão ${result.version})` : "";
  return [`Pronto · ${pieces(result.trechos)}${version}. Ligue “Usar biblioteca” para citá-lo.`, ...cardNotes(result)].join(" ");
}

// Uma falha reaparece mesmo com o aviso fechado ou recolhido.
function raiseUploads() {
  uploads.hidden = false;
  uploads.minimized = false;
}

// Para onde o foco vai quando o aviso some: a caixa de mensagem no chat; nas outras abas, o botão da aba aberta.
function focusAfterUploads() {
  ($("chat-view").hidden ? document.querySelector(".rail-item.is-active") : $("question"))?.focus();
}

function renderUploads() {
  const pop = $("upload-pop");
  const items = uploads.items;
  if (!items.length || uploads.hidden) {
    const inside = pop.contains(document.activeElement);
    pop.hidden = true;
    placeUploads();  // devolve o espaço reservado para o aviso
    if (inside) focusAfterUploads();  // o foco não pode ficar num botão que sumiu
    return;
  }
  const statuses = items.map(uploadStatus);
  const ready = statuses.filter((status) => status === "pronto" || status === "parcial").length;
  const failed = statuses.filter((status) => status === "falha").length;
  // O documento atual é o que o servidor está processando; sem isso, o primeiro que ainda não ficou pronto.
  const current = items.find((item) => uploadStatus(item) === "andamento") || items.find((item) => !uploadIndexed(item));
  // Indexado, com as fichas ainda por fazer: de preferência o documento cujas fichas estão sendo criadas agora.
  const pending = items.filter((item) => !uploadDone(item));
  const cards = pending.find((item) => ["ficha", "ficha do documento"].includes(item.job?.etapa)) || pending[0];
  const single = items.length === 1;
  const title = $("upload-title");
  title.textContent = single ? `${items[0].name}${failed ? " · com falha" : ""}`
    : `Documentos: ${ready} de ${items.length} prontos${failed ? ` · ${failed} com falha` : ""}`;
  title.title = single ? title.textContent : UPLOAD_READY_NOTE;
  // O resumo de vários documentos e o nome com " · com falha" quebram a linha, para a falha não ficar cortada.
  title.classList.toggle("is-summary", !single || failed > 0);

  const bar = $("upload-bar");
  const fraction = (ready + failed + (current ? uploadFraction(current) : 0)) / items.length;
  // Um documento só, antes de haver páginas ou trechos para contar: a barra fica em movimento.
  if (single && current && !uploadFraction(current)) bar.removeAttribute("value");
  else bar.value = Math.min(1, fraction);
  bar.textContent = `${Math.round(fraction * 100)}%`;

  let now;
  if (current) now = single ? uploadStage(current) : `Agora: ${current.name} · ${uploadStage(current)}`;
  else if (cards) now = single ? `Pronto para buscar. ${cardStage(cards)}…` : `Fichas de ${cards.name}: ${cardStage(cards).toLowerCase()}…`;
  // Um documento indexado só em parte tem o aviso na lista abaixo; aqui fica o que aconteceu com as fichas dele.
  else if (single) now = failed ? "" : statuses[0] === "parcial" ? cardNotes(items[0].job?.resultado || {}).join(" ") : uploadSummary(items[0]);
  else if (!ready) now = "";
  else {
    const noCards = items.filter(cardWarning).length;
    now = `${failed ? "Envio terminado" : "Tudo pronto"}. Ligue “Usar biblioteca” para citar os documentos${failed ? " prontos" : ""}.`
      + (noCards ? ` As fichas de ${noCards === 1 ? "1 documento" : `${noCards} documentos`} não puderam ser criadas agora.` : "");
  }
  $("upload-now").textContent = now;
  $("upload-now").hidden = !now;

  // Os avisos do lote e os do lote anterior que ainda não foram fechados.
  const problems = [...uploads.earlier, ...items].filter(uploadOpen);
  const key = problems.map((item) => `${item.name}\u0000${uploadProblem(item)}`).join("\u0001");
  if (key !== uploads.issuesKey) {
    // Só refaz a lista quando ela muda: refeita a cada consulta, o foco do teclado no "×" se perderia.
    uploads.issuesKey = key;
    $("upload-issues").replaceChildren(...problems.map((item) => el("li", { class: uploadStatus(item) === "falha" ? "is-fail" : "is-warn" },
      el("span", {}, el("b", { text: `${item.name}: ` }), uploadProblem(item)),
      el("button", { class: "dismiss", type: "button", "aria-label": `Fechar o aviso de ${item.name}`, text: "×",
        onclick: () => {
          item.dismissed = true;
          settleUploads();
          if (!$("upload-pop").hidden) $("upload-min").focus();
        } }))));
  }
  $("upload-issues").hidden = !problems.length;

  pop.classList.toggle("is-min", uploads.minimized);
  $("upload-min").setAttribute("aria-expanded", String(!uploads.minimized));
  $("upload-min").setAttribute("aria-label", uploads.minimized ? "Mostrar os detalhes do envio" : "Recolher o aviso de envio");
  pop.hidden = false;
  placeUploads();
}

// No canto inferior direito, em todas as abas. No chat fica logo acima da caixa de mensagem. A área da aba
// termina acima do aviso (uma faixa reservada, do tamanho dele), para ele nunca ficar por cima de um botão.
function placeUploads() {
  const pop = $("upload-pop");
  const app = $("app");
  if (pop.hidden) {
    app.classList.remove("has-upload-pop");
    return;
  }
  const chat = !$("chat-view").hidden;
  const messages = $("messages");
  const atEnd = messages.scrollHeight - messages.scrollTop - messages.clientHeight < 40;
  const first = !app.classList.contains("has-upload-pop");
  const height = Math.round(pop.getBoundingClientRect().height);
  // No chat a faixa fica entre as mensagens e a caixa de mensagem; nas outras abas, no pé da tela.
  app.style.setProperty("--upload-space", `${height + (chat ? 6 : 20)}px`);
  app.classList.add("has-upload-pop");
  pop.style.bottom = `${chat ? Math.round(window.innerHeight - $("composer").getBoundingClientRect().top) + 8 : 16}px`;
  if (first && chat && atEnd) messages.scrollTop = messages.scrollHeight;  // o fim da conversa continua à vista
}

function announceUploads(text) { $("upload-status").textContent = text; }

async function refreshDocuments() {
  try {
    const status = await api("/api/estado");
    state.documents = status.biblioteca.documentos;
    updateLibraryLabel();
    if (!$("library-view").hidden) loadLibrary();
  } catch { /* o rótulo se atualiza no próximo envio */ }
}

// A tarefa de um lote que deixou de ser o mais recente (um envio feito em outra aba) é consultada pelo id.
// Só "não encontrada" quer dizer que o envio se perdeu; outra falha é passageira, e vale a consulta seguinte.
async function uploadJob(id) {
  const response = await fetch(`/api/biblioteca/tarefas/${id}`, { headers: { "x-aliado": "1" } });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("consulta sem resposta");
  return response.json();
}

async function applyUploadJobs(data) {
  const jobs = new Map(data.tarefas.map((job) => [job.id, job]));
  let changed = false;
  for (const item of uploads.items) {
    if (!item.id || uploadDone(item)) continue;
    const before = uploadStatus(item);
    let job = jobs.get(item.id);
    if (!job) {
      try { job = await uploadJob(item.id); } catch { continue; }
      if (!job) item.error = "O envio se perdeu: o AL-IAdo foi reiniciado. Envie de novo.";
    }
    if (job) item.job = job;
    const after = uploadStatus(item);
    if (after !== before && ["pronto", "parcial", "falha"].includes(after)) {
      changed = true;
      announceUploads(after === "falha" ? `${item.name}: não foi possível indexar.` : `${item.name}: pronto para buscar.`);
      if (after !== "pronto") raiseUploads();
    }
    if (uploadDone(item)) changed = true;  // as fichas terminaram: a lista da biblioteca mostra a referência
  }
  if (changed) refreshDocuments();
}

async function pollUploads() {
  if (uploads.polling) return;
  uploads.polling = true;
  try {
    while (uploads.items.some((item) => !uploadDone(item))) {
      if (uploads.items.some((item) => item.id && !uploadDone(item))) {
        try {
          await applyUploadJobs(await api("/api/biblioteca/tarefas"));
          uploads.misses = 0;
        } catch {
          uploads.misses += 1;
          if (uploads.misses >= 4) {
            raiseUploads();
            for (const item of uploads.items) {
              if (item.id && !uploadDone(item)) item.error = "O AL-IAdo não respondeu. Confira o documento na aba Biblioteca.";
            }
          }
        }
      }
      renderUploads();
      await new Promise((resolve) => setTimeout(resolve, UPLOAD_POLL_MS));
    }
  } finally {
    uploads.polling = false;
  }
  settleUploads();
}

// Com tudo terminado: some em 6 s se deu certo; falhas e documentos indexados em parte ficam até serem fechados.
function settleUploads() {
  renderUploads();
  if (!uploads.items.length || uploads.items.some((item) => !uploadDone(item))) return;
  const open = [...uploads.earlier, ...uploads.items].some(uploadOpen);
  clearTimeout(uploads.timer);
  if (uploads.hidden) return clearUploads();
  if (!open) uploads.timer = setTimeout(clearUploads, uploads.items.every((item) => item.dismissed) ? 0 : UPLOAD_OK_MS);
  else announceUploads("Envio terminado, com avisos.");
}

function clearUploads() {
  clearTimeout(uploads.timer);
  Object.assign(uploads, { lote: null, items: [], earlier: [], hidden: false, misses: 0, issuesKey: null });
  renderUploads();
}

async function uploadFiles(files) {
  const accepted = files.filter((file) => {
    const ok = /\.(pdf|md|json)$/i.test(file.name);
    if (!ok) toast(`${file.name}: envie PDF, Markdown ou JSON.`);
    return ok;
  });
  if (!accepted.length) return;
  // Arquivos escolhidos enquanto um lote ainda corre entram no mesmo lote; senão, começa outro, e os avisos
  // do lote anterior que não foram fechados continuam à vista.
  if (!uploads.items.some((item) => !uploadDone(item))) {
    const kept = [...uploads.earlier, ...uploads.items].filter(uploadOpen);
    clearUploads();
    uploads.earlier = kept;
  }
  clearTimeout(uploads.timer);
  uploads.lote = uploads.lote || newBatch();
  uploads.hidden = false;
  // A ficha de leitura herda a skill ativa, para a memória separar pesquisa de engenharia.
  const skill = $("skill").value;
  const added = accepted.map((file) => ({ name: file.name, file, id: null, job: null, error: null, sending: false, dismissed: false }));
  uploads.items.push(...added);
  renderUploads();
  pollUploads();
  const send = async (item) => {
    item.sending = true;
    renderUploads();
    try {
      const form = new FormData();
      form.append("arquivo", item.file);
      form.append("lote", uploads.lote);
      if (skill !== "nenhuma") form.append("skill", skill);
      const job = await api("/api/biblioteca", { method: "POST", body: form });
      item.id = job.tarefa;
      item.job = { estado: "na fila" };
    } catch (error) {
      // Sem resposta do servidor, o navegador devolve um texto técnico em inglês: a tela diz em palavras.
      item.error = error instanceof TypeError ? "Não foi possível enviar: o AL-IAdo não respondeu." : error.message;
      raiseUploads();
      announceUploads(`${item.name}: não foi possível enviar.`);
    }
    item.sending = false;
    item.file = null;
    renderUploads();
  };
  // Alguns envios ao mesmo tempo: assim os arquivos do lote entram na fila antes das fichas do primeiro.
  const waiting = [...added];
  const lane = async () => { for (let item = waiting.shift(); item; item = waiting.shift()) await send(item); };
  await Promise.all(Array.from({ length: Math.min(UPLOAD_PARALLEL, added.length) }, lane));
}

// Ao abrir ou recarregar a página com envios em andamento, o pop-up volta com os totais do lote.
async function restoreUploads() {
  try {
    const data = await api("/api/biblioteca/tarefas");
    if (!data.tarefas.some((job) => job.estado === "na fila" || job.estado === "processando")) return;
    uploads.lote = data.lote;
    uploads.items = data.tarefas.map((job) => ({ name: job.arquivo, file: null, id: job.id, job, error: null,
      sending: false, dismissed: false }));
    uploads.hidden = false;
    renderUploads();
    pollUploads();
  } catch { /* sem envios para mostrar */ }
}

$("upload-min").addEventListener("click", () => { uploads.minimized = !uploads.minimized; renderUploads(); });
// Fechar só esconde o aviso: o envio continua, e um novo envio ou uma falha o mostra de novo.
$("upload-close").addEventListener("click", () => {
  uploads.hidden = true;
  settleUploads();
});
window.addEventListener("resize", placeUploads);
// A caixa de mensagem cresce com o texto: o aviso sobe junto, para não ficar por cima dela.
new ResizeObserver(placeUploads).observe($("composer"));

$("attach").addEventListener("click", () => $("file").click());
$("library-add").addEventListener("click", () => $("file").click());
$("file").addEventListener("change", () => { uploadFiles([...$("file").files]); $("file").value = ""; });

let dragDepth = 0;
document.addEventListener("dragenter", (event) => {
  if (![...(event.dataTransfer?.types || [])].includes("Files")) return;
  dragDepth += 1;
  $("dropzone").hidden = false;
});
document.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) $("dropzone").hidden = true; });
document.addEventListener("dragover", (event) => event.preventDefault());
document.addEventListener("drop", (event) => {
  event.preventDefault();
  dragDepth = 0;
  $("dropzone").hidden = true;
  // O pop-up aparece em qualquer aba: soltar um arquivo não troca mais de tela.
  if (event.dataTransfer?.files?.length) uploadFiles([...event.dataTransfer.files]);
});

/* Biblioteca */
function showView(name) {
  const app = $("app");
  app.classList.toggle("library-mode", name !== "chat");
  app.classList.remove("drawer-open-small");
  closeInfo();
  $("chat-view").hidden = name !== "chat";
  $("library-view").hidden = name !== "library";
  $("memory-view").hidden = name !== "memory";
  $("science-view").hidden = name !== "science";
  for (const [id, view] of [["nav-chats", "chat"], ["nav-library", "library"], ["nav-memory", "memory"],
    ["nav-science", "science"]]) {
    $(id).classList.toggle("is-active", view === name);
  }
  placeUploads();
}

function showChat() { showView("chat"); }

async function openLibrary(selectId) {
  showView("library");
  await loadLibrary(selectId);
}

const STATUS = { ready: ["pronto", "badge-ok"], partial: ["parcial", "badge-warn"], failed: ["falhou", "badge-fail"] };
let libraryDocuments = [];

async function loadLibrary(selectId) {
  let documents = [];
  try { documents = await api("/api/biblioteca"); } catch (error) { toast(error.message); }
  libraryDocuments = documents;
  const list = $("doc-list");
  if (!documents.length) {
    list.replaceChildren(el("li", { class: "empty",
      text: "A biblioteca está vazia. Adicione um PDF aqui ou solte o arquivo na conversa." }));
    return;
  }
  list.replaceChildren(...documents.map((doc) => {
    const [label, badge] = STATUS[doc.status] || [doc.status, ""];
    return el("li", {}, el("button", { class: "doc-item", type: "button", "data-doc": doc.id,
      onclick: () => showDocument(doc) },
      el("span", { class: "doc-title", text: doc.title }),
      ...(doc.referencia ? [el("span", { class: "doc-ref", text: doc.referencia })] : []),
      el("span", { class: "doc-meta" }, el("span", { class: `badge ${badge}`, text: label }),
        el("span", { text: `v${doc.version}` }), el("span", { text: relativeDate(doc.created_at) }))));
  }));
  const pending = documents.filter((doc) => doc.ficha_pendente).length;
  $("library-cards").hidden = !pending;
  $("library-cards").textContent = `Completar fichas (${pending})`;
  $("library-cards").dataset.pending = String(pending);
  const chosen = documents.find((doc) => doc.id === selectId);
  if (chosen) showDocument(chosen);
  else if (selectId) toast("Este documento não está mais na biblioteca: ele pode ter sido apagado.");
}

/* Apagar documento (lote 22): de vez, com todas as versões; as deduções tiradas dele são revogadas. */
async function deleteDocument(doc) {
  const ids = libraryDocuments.filter((item) => item.title === doc.title).map((item) => item.id);
  let count = null;
  try {
    const data = await api("/api/memoria?origem=inferido");
    count = data.itens.filter((m) => ["ativa", "conflito"].includes(m.status) && ids.includes(m.source?.document_id)).length;
  } catch { /* sem memória: o aviso fica genérico */ }
  const notes = count === null ? "As anotações inferidas tiradas dele são revogadas."
    : count === 0 ? "Nenhuma anotação da memória foi tirada dele."
    : count === 1 ? "1 anotação inferida tirada dele é revogada."
    : `${count} anotações inferidas tiradas dele são revogadas.`;
  const versions = ids.length > 1 ? `, com as ${ids.length} versões` : "";
  if (!window.confirm(`Apagar de vez «${doc.title}»${versions}?\n\nO PDF, a extração e o índice somem da biblioteca. ` +
    `${notes}\n\nNão tem volta.`)) return;
  try {
    const result = await api(`/api/biblioteca/${doc.id}`, { method: "DELETE" });
    const revoked = result.anotacoes_revogadas;
    toast(`«${result.apagado}» foi apagado` +
      (revoked ? `; ${revoked} ${revoked === 1 ? "anotação revogada" : "anotações revogadas"}` : "") +
      (result.sobras.length ? ". Alguns arquivos não puderam ser removidos agora." : "."));
    $("doc-viewer").replaceChildren(el("p", { class: "muted", text: "Escolha um documento para ver a versão em Markdown." }));
    loadLibrary();
  } catch (error) {
    toast(error.message);
  }
}

/* Ficha do documento (lote 19): título, autores, ano e DOI, inferidos e editáveis. */
function cardBox(doc) {
  const card = doc.ficha || {};
  const rows = [["Título", card.titulo], ["Autores", (card.autores || []).join("; ")], ["Ano", card.ano], ["DOI", card.doi]];
  const origin = !doc.ficha ? "sem ficha" : doc.ficha_origem === "sua" ? "sua" : "inferida: confira no original";
  const box = el("section", { class: "doc-card" },
    el("div", { class: "doc-card-head" }, el("h2", { class: "panel-title", text: "Ficha do documento" }),
      el("span", { class: "muted", text: origin }),
      el("button", { class: "link", type: "button", text: "Editar", onclick: () => box.replaceWith(cardForm(doc)) })),
    el("dl", {}, ...rows.flatMap(([label, value]) => [el("dt", { text: label }), el("dd", { text: value ? String(value) : "—" })])));
  return box;
}

function cardForm(doc) {
  const card = doc.ficha || {};
  const input = (label, value, name) => el("label", { class: "field" }, label,
    el("input", { name, value: value == null ? "" : String(value) }));
  const form = el("form", { class: "doc-card" },
    el("h2", { class: "panel-title", text: "Editar ficha" }),
    input("Título", card.titulo, "titulo"),
    input("Autores, separados por ponto e vírgula", (card.autores || []).join("; "), "autores"),
    input("Ano", card.ano, "ano"),
    input("DOI", card.doi, "doi"),
    el("div", { class: "dialog-actions" },
      el("button", { class: "secondary", type: "button", text: "Cancelar", onclick: () => form.replaceWith(cardBox(doc)) }),
      el("button", { class: "primary", type: "submit", text: "Salvar" })));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    try {
      const saved = await api(`/api/biblioteca/${doc.id}/ficha`, { method: "POST", json: data });
      Object.assign(doc, saved);
      form.replaceWith(cardBox(doc));
      loadLibrary();
    } catch (error) {
      toast(error.message);
    }
  });
  return form;
}

$("library-cards").addEventListener("click", async () => {
  const pending = Number($("library-cards").dataset.pending || 0);
  if (!pending || !window.confirm(`Criar a ficha de ${pending} documento(s)?\n\nSão ${pending} chamada(s) ao modelo ` +
    "mais barato. O título, os autores, o ano e o DOI só entram se aparecerem no texto do documento.")) return;
  const button = $("library-cards");
  button.disabled = true;
  try {
    const job = await api("/api/biblioteca/fichas", { method: "POST" });
    for (;;) {
      const status = await api(`/api/biblioteca/tarefas/${job.tarefa}`);
      button.textContent = `Fichas: ${status.atual || 0} de ${status.total}`;
      if (status.estado === "concluido") {
        const r = status.resultado;
        toast(`${r.fichas} ficha(s) criada(s)` + (r.sem_dados ? `, ${r.sem_dados} sem dados no texto` : "") +
          (r.falhas ? `, ${r.falhas} com falha` : "") + ".");
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    loadLibrary();
  }
});

async function showDocument(doc) {
  document.querySelectorAll(".doc-item").forEach((item) => item.classList.toggle("is-current", item.dataset.doc === doc.id));
  const viewer = $("doc-viewer");
  viewer.replaceChildren(el("p", { class: "muted", text: "Carregando a extração…" }));
  try {
    const data = await api(`/api/biblioteca/${doc.id}/markdown`);
    const body = el("div", { class: "answer" });
    body.innerHTML = data.html; // Markdown da extração renderizado no servidor, sem HTML bruto
    renderMath(body);
    const issues = doc.issues?.length ? el("div", { class: "note note-warn", text: `Pendências: ${doc.issues.join(" ")}` }) : null;
    viewer.replaceChildren(
      el("div", { class: "doc-viewer-head" }, el("span", { class: "muted", text: "Extração em Markdown · confira fórmulas, tabelas e OCR no original" }),
        el("span", { class: "doc-viewer-actions" },
          el("a", { class: "link", href: `/api/biblioteca/${doc.id}/original`, target: "_blank", rel: "noopener", text: "Abrir original" }),
          el("button", { class: "link danger", type: "button", text: "Apagar", onclick: () => deleteDocument(doc) }))),
      cardBox(doc), ...(issues ? [issues] : []), body);
  } catch (error) {
    viewer.replaceChildren(el("p", { class: "muted", text: error.message }));
  }
}

$("nav-library").addEventListener("click", () => openLibrary());
$("nav-chats").addEventListener("click", () => {
  if ($("chat-view").hidden) return showChat();
  const small = SMALL.matches;
  const app = $("app");
  if (small) app.classList.toggle("drawer-open-small");
  else app.classList.toggle("drawer-closed");
  $("nav-chats").setAttribute("aria-expanded", String(small ? app.classList.contains("drawer-open-small") : !app.classList.contains("drawer-closed")));
});
$("brand").addEventListener("click", showChat);

/* Início */
(async () => {
  try {
    await loadState();
  } catch (error) {
    toast(error.message);
  }
  await loadConversations().catch((error) => toast(error.message));
  refreshMemoryBadge();
  // Abrir ou recarregar cai sempre na tela de apresentação (lote 27); as conversas ficam na lista.
  showWelcome();
  restoreUploads();
  $("question").focus();
})();
