"use strict";

const $ = (id) => document.getElementById(id);
// A tela inicial sai do DOM quando há mensagens; a referência permite recolocá-la.
const WELCOME = $("welcome");
const state ={ conversation: null, models: [], skills: [], documents: 0, busy: false, sourcesOf: null };
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

function updateLibraryLabel() {
  const count = state.documents;
  $("library-label").textContent = count ? `Usar biblioteca (${count})` : "Usar biblioteca";
}

$("skill").addEventListener("change", () => { store.set("aliado.skill", $("skill").value); updateSupportVisibility(); });
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
  const items = await api("/api/conversas");
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
    "(data/conversas/lixeira). As memórias geradas a partir dela continuam valendo.");
  if (!ok) return;
  if (state.busy && state.conversation?.id === item.id) state.controller?.abort();
  try {
    await api(`/api/conversas/${item.id}`, { method: "DELETE" });
    if (state.conversation?.id === item.id) {
      state.conversation = null;
      store.set("aliado.conversation", "");
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
    store.set("aliado.conversation", "");
    return showWelcome();
  }
  store.set("aliado.conversation", id);
  showChat();
  const messages = $("messages");
  messages.replaceChildren();
  for (const message of state.conversation.messages) messages.append(renderMessage(message));
  if (!state.conversation.messages.length) showWelcome();
  const last = [...state.conversation.messages].reverse().find((m) => m.role === "assistant");
  showSources(last);
  messages.scrollTop = messages.scrollHeight;
  loadConversations();
}

function showWelcome() {
  WELCOME.hidden = false;
  $("messages").replaceChildren(WELCOME);
  $("suggestions").replaceChildren(...SUGGESTIONS.map((text) =>
    el("button", { class: "suggestion", type: "button", text, onclick: () => { $("question").value = text; autosize(); $("question").focus(); } })));
  showSources(null);
}

$("new-chat").addEventListener("click", () => {
  state.conversation = null;
  store.set("aliado.conversation", "");
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
    button.addEventListener("click", () => {
      showSources(message);
      openSourcesPanel();
      if (button.dataset.web) highlightSource(button.dataset.web, "web");
      else highlightSource(button.dataset.cite);
    }));
  const node = el("article", { class: "msg-assistant", "data-message": message.id }, answer);
  if (message.validation_status === "insufficient_evidence" || message.validation_status === "invalid_citations") {
    node.append(el("div", { class: "note note-warn",
      text: "Resposta local: a biblioteca não sustentou uma resposta com citações. Ela não entra no histórico enviado ao modelo." }));
  }
  const usage = message.usage || {};
  const meta = el("div", { class: "meta" });
  if (message.model && message.provider !== "local") meta.append(el("span", { text: message.model }));
  if (usage.total_tokens) meta.append(el("span", { text: `${formatTokens(usage.total_tokens)} tokens` }));
  if (usage.reasoning_tokens) meta.append(el("span", { text: `${formatTokens(usage.reasoning_tokens)} de raciocínio` }));
  if (message.sources?.length) {
    meta.append(el("button", { class: "link", type: "button", text: `${message.sources.length} fonte(s)`,
      onclick: () => { showSources(message); openSourcesPanel(); } }));
  }
  if (message.web_sources?.length || message.web_queries?.length) {
    const searches = message.web_queries?.length || 0;
    meta.append(el("button", { class: "link web-link", type: "button",
      text: `${searches} ${searches === 1 ? "busca" : "buscas"} na web · ${message.web_sources?.length || 0} fonte(s)`,
      onclick: () => { showSources(message); openSourcesPanel(); } }));
  }
  const openPanel = () => { showSources(message); openSourcesPanel(); };
  const used = message.memorias_usadas?.length || 0;
  const created = message.memorias_criadas?.length || 0;
  if (used) meta.append(el("button", { class: "link memory-link", type: "button",
    text: `usou ${used} ${used === 1 ? "memória" : "memórias"}`, onclick: openPanel }));
  if (created) meta.append(el("button", { class: "link memory-link is-new", type: "button",
    text: `${created} ${created === 1 ? "anotação nova" : "anotações novas"}`, onclick: openPanel }));
  if (message.id && message.provider !== "local") {
    meta.append(el("button", { class: "link", type: "button", text: "Lembrar…",
      onclick: () => openRemember() }));
  }
  if (meta.childElementCount) node.append(meta);
  return node;
}

/* Memória */
const KIND_LABELS = { preferencia: "Preferência", correcao: "Correção", fato: "Fato", decisao: "Decisão" };
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
  if (!used.length && !created.length) { panel.replaceChildren(); return; }
  const parts = [el("h2", { class: "panel-title panel-title-spaced", text: "Memória nesta resposta" })];
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
  if (!sources.length && !web.length) {
    list.replaceChildren(el("p", { class: "muted", text: message
      ? "Esta resposta não usou trechos da biblioteca nem a web."
      : "As fontes citadas aparecem aqui. Ligue “Usar biblioteca” ou “Buscar na web” para respostas com fontes." }));
    return;
  }
  const parts = [];
  if (sources.length && web.length) parts.push(el("h3", { class: "source-group", text: "Seus documentos" }));
  parts.push(...sources.map((source, index) => {
    const number = index + 1;
    const where = [source.locator, source.page ? `p. ${source.page}` : null].filter(Boolean).join(" · ");
    const flags = [];
    if (source.method === "ocr") flags.push("OCR: conferir no original");
    if (source.status === "partial") flags.push("extração parcial");
    const actions = el("div", { class: "source-actions" });
    if (source.document_id) {
      const page = source.page ? `#page=${source.page}` : "";
      actions.append(
        el("a", { class: "link", href: `/api/biblioteca/${source.document_id}/original${page}`, target: "_blank",
          rel: "noopener", text: "Abrir página" }),
        el("button", { class: "link", type: "button", text: "Ver Markdown",
          onclick: () => openLibrary(source.document_id) }));
    }
    return el("div", { class: "source-card", "data-source": String(number) },
      el("div", { class: "source-head" }, el("span", { class: "cite", text: String(number) }),
        el("span", { class: "source-title", title: source.title, text: source.title })),
      el("div", { class: "source-loc", text: [`v${source.version}`, where, ...flags].filter(Boolean).join(" · ") }),
      el("p", { class: "source-text", text: source.text }),
      actions);
  }));
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

function openSourcesPanel() {
  // Em telas estreitas o painel fica oculto e abre sobreposto; em telas largas já está visível.
  if (SMALL.matches) $("app").classList.add("sources-open");
}

$("sources-close").addEventListener("click", () => $("app").classList.remove("sources-open"));
$("scrim").addEventListener("click", () => $("app").classList.remove("sources-open", "drawer-open-small"));

function highlightSource(number, kind = "source") {
  const key = kind === "web" ? "web" : "source";
  document.querySelectorAll(".source-card").forEach((card) =>
    card.classList.toggle("is-active", card.dataset[key] === String(number)));
  document.querySelector(`.source-card[data-${key}="${number}"]`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
      store.set("aliado.conversation", state.conversation.id);
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
      }, {
        onText(piece) {
          const follow = nearBottom(messages);
          if (thinking.isConnected) thinking.replaceWith(liveNode);
          written += piece;
          // As citações [K…] só viram números depois da checagem final no servidor.
          live.textContent = written.replace(/\[K[^\]\s]*\]/g, "[fonte]");
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
          showSources(data.mensagens[data.mensagens.length - 1]);
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
            if (state.sourcesOf?.id === message.id) showSources(message);
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

/* Envio de documentos */
function uploadCard(name) {
  const state_ = el("span", { class: "state", text: "Enviando…" });
  const bar = el("span", { class: "bar" }, el("i"));
  const close = el("button", { class: "dismiss", type: "button", "aria-label": "Fechar aviso", text: "×",
    onclick: () => card.remove() });
  const card = el("div", { class: "upload-card" },
    el("div", { class: "grow" }, el("div", { class: "name", text: name }), state_), bar, close);
  $("uploads").append(card);
  const setProgress = (fraction) => {
    bar.classList.toggle("is-determinate", fraction !== null);
    bar.firstElementChild.style.width = fraction === null ? "" : `${Math.round(fraction * 100)}%`;
  };
  return { card, state: state_, bar, setProgress };
}

const STAGES = { lendo: "Lendo página", ocr: "OCR na página" };

function progressText(job) {
  if (job.etapa === "ficha") return "Criando a ficha de leitura na memória…";
  if (job.etapa === "indexando") return `Indexando ${job.total} trechos…`;
  if (job.etapa in STAGES) return `${STAGES[job.etapa]} ${job.atual} de ${job.total}…`;
  return "Preparando a extração…";
}

async function uploadFiles(files) {
  for (const file of files) {
    if (!/\.(pdf|md|json)$/i.test(file.name)) { toast(`${file.name}: envie PDF, Markdown ou JSON.`); continue; }
    const view = uploadCard(file.name);
    try {
      const form = new FormData();
      form.append("arquivo", file);
      // A ficha de leitura herda a skill ativa, para a memória separar pesquisa de engenharia.
      if ($("skill").value !== "nenhuma") form.append("skill", $("skill").value);
      const job = await api("/api/biblioteca", { method: "POST", body: form });
      view.state.textContent = "Na fila para indexação";
      await pollJob(job.tarefa, view);
    } catch (error) {
      view.bar.remove();
      view.card.classList.add("is-fail");
      view.state.textContent = error.message;
    }
  }
}

async function pollJob(id, view) {
  for (;;) {
    const job = await api(`/api/biblioteca/tarefas/${id}`);
    if (job.estado === "processando") {
      view.state.textContent = progressText(job);
      view.setProgress(job.etapa in STAGES && job.total ? job.atual / job.total : null);
    }
    if (job.estado === "concluido" || job.estado === "falhou") {
      view.bar.remove();
      if (job.estado === "falhou") {
        view.card.classList.add("is-fail");
        view.state.textContent = `Não foi possível indexar: ${job.erro}`;
        return;
      }
      const r = job.resultado;
      const issues = r.issues?.length ? ` Pendências: ${r.issues.join(" ")}` : "";
      if (r.duplicate) {
        view.card.classList.add("is-ok");
        view.state.textContent = "Este documento já estava na biblioteca.";
      } else if (r.status === "ready") {
        view.card.classList.add("is-ok");
        view.state.textContent = `Indexado · ${r.trechos} trechos · versão ${r.version}. Ligue “Usar biblioteca” para citá-lo.`;
      } else {
        view.card.classList.add(r.status === "failed" ? "is-fail" : "is-warn");
        view.state.textContent = (r.status === "failed" ? "Falha na extração." : `Indexado parcialmente · ${r.trechos} trechos.`) + issues;
      }
      if (r.fichas) view.state.textContent += ` Ficha de leitura: ${r.fichas} anotações inferidas na memória.`;
      if (r.aviso_ficha) view.state.textContent += ` ${r.aviso_ficha}`;
      const status = await api("/api/estado");
      state.documents = status.biblioteca.documentos;
      updateLibraryLabel();
      if (!$("library-view").hidden) loadLibrary();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}

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
  if (event.dataTransfer?.files?.length) { showChat(); uploadFiles([...event.dataTransfer.files]); }
});

/* Biblioteca */
function showView(name) {
  const app = $("app");
  app.classList.toggle("library-mode", name !== "chat");
  app.classList.remove("sources-open", "drawer-open-small");
  $("chat-view").hidden = name !== "chat";
  $("sources").hidden = name !== "chat";
  $("library-view").hidden = name !== "library";
  $("memory-view").hidden = name !== "memory";
  for (const [id, view] of [["nav-chats", "chat"], ["nav-library", "library"], ["nav-memory", "memory"]]) {
    $(id).classList.toggle("is-active", view === name);
  }
}

function showChat() { showView("chat"); }

async function openLibrary(selectId) {
  showView("library");
  await loadLibrary(selectId);
}

const STATUS = { ready: ["pronto", "badge-ok"], partial: ["parcial", "badge-warn"], failed: ["falhou", "badge-fail"] };

async function loadLibrary(selectId) {
  let documents = [];
  try { documents = await api("/api/biblioteca"); } catch (error) { toast(error.message); }
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
      el("span", { class: "doc-meta" }, el("span", { class: `badge ${badge}`, text: label }),
        el("span", { text: `v${doc.version}` }), el("span", { text: relativeDate(doc.created_at) }))));
  }));
  const chosen = documents.find((doc) => doc.id === selectId);
  if (chosen) showDocument(chosen);
}

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
        el("a", { class: "link", href: `/api/biblioteca/${doc.id}/original`, target: "_blank", rel: "noopener", text: "Abrir original" })),
      ...(issues ? [issues] : []), body);
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
  const last = store.get("aliado.conversation", "");
  if (last) await openConversation(last);
  else showWelcome();
  $("question").focus();
})();
