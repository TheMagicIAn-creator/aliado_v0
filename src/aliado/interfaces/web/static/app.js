"use strict";

const $ = (id) => document.getElementById(id);
// A tela inicial sai do DOM quando há mensagens; a referência permite recolocá-la.
const WELCOME = $("welcome");
// pendingPins: documentos fixados antes de a conversa existir (tela de apresentação); seguem na primeira pergunta.
const state = { conversation: null, models: [], busy: false, sourcesOf: null, infoAnchor: null, reading: null,
  pendingPins: [], confirmed: {}, conversationVersion: 0, creatingConversation: null };
// O rótulo sai do nome da skill: "engenharia" → "Engenharia"; sem skill, "Sem especialização".
const skillLabel = (name) => name && name !== "nenhuma"
  ? name[0].toUpperCase() + name.slice(1).replace(/-/g, " · ") : "Sem especialização";
// Lote 35: a tela não tem seletores; quem quer escolher escreve o pedido na própria mensagem.
const WRITE_HINT = "Para escolher, escreva na mensagem: “use o modelo maior”, “só trechos”, “leia o documento inteiro”, "
  + "“leitura ampla”, “busque na web” ou “sem biblioteca”. Uma mensagem só com o pedido refaz a pergunta anterior.";
$("write-hint").textContent = WRITE_HINT;
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

// Resposta em fluxo: linhas JSON {tipo: texto|erro|fim|memoria|recomeco|confirmar}. "fim" chega antes do
// revisor de memória, então a resposta aparece sem esperar as anotações novas. "confirmar" (lote 31) encerra
// o fluxo sem resposta: a leitura passa do teto, e a tela pergunta antes de gastar.
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
      else if (event.tipo === "recomeco") handlers.onRestart?.(event);
      else if (event.tipo === "confirmar") { final = event; handlers.onConfirm?.(event); }
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
  // Lote 35: sem seletores na tela, o roteador escolhe a skill, o modelo e a leitura de cada mensagem.
  state.models = data.modelos;
  if (!data.modelos.length) toast("Nenhum modelo Gemini configurado. Confira o .env e reinicie.");
  state.reading = data.leitura || {};
  checkServerAge(data);
  showUsage(data.uso);
}

// A página é lida do disco a cada carga; o programa em execução só muda quando é reiniciado. Se a página é mais
// nova que ele, as escolhas novas da tela seriam ignoradas sem aviso: a tela pede o reinício.
async function checkServerAge(data) {
  let stale = !data.leitura?.modos || !data.iniciado;
  if (!stale) {
    try {
      const response = await fetch("/static/app.js", { method: "HEAD", cache: "no-store" });
      const changed = Date.parse(response.headers.get("last-modified") || "");
      stale = Number.isFinite(changed) && changed > Date.parse(data.iniciado) + 2000;
    } catch { /* sem a data do arquivo, não há o que comparar */ }
  }
  $("restart-note").hidden = !stale;
}

function showUsage(uso) {
  $("usage").textContent = `Hoje ${formatTokens(uso.hoje)} tokens · total ${formatTokens(uso.total)}`;
}

// A skill da conversa (lote 35): a da última resposta; as anotações e as fichas dos envios ficam com ela.
function conversationSkill() {
  const name = (state.conversation?.messages || []).filter((m) => m.rota?.skill).at(-1)?.rota.skill;
  return name && name !== "nenhuma" ? name : null;
}

/* Documentos fixados na conversa (lote 30): vão inteiros ao modelo nas perguntas dela que consultam os documentos. */
function pins() { return state.conversation ? (state.conversation.fixados || []) : state.pendingPins; }

async function setPins(list) {
  if (!state.conversation) {
    state.pendingPins.splice(0, state.pendingPins.length, ...list);
  } else {
    try {
      const conversation = state.conversation;
      const data = await api(`/api/conversas/${conversation.id}`,
        { method: "PATCH", json: { fixados: list.map((doc) => doc.id) } });
      if (state.conversation === conversation) conversation.fixados = data.fixados;
    } catch (error) { toast(error.message); }
  }
  renderPins();
}

function pinDocument(doc) {
  if (pins().some((item) => item.id === doc.id)) return Promise.resolve();
  return setPins([...pins(), { id: doc.id, title: doc.title, referencia: doc.referencia || null }]);
}

function unpinDocument(id) { return setPins(pins().filter((item) => item.id !== id)); }

// A conversa nasce na primeira pergunta ou no primeiro anexo (lote 35); os documentos fixados antes passam para ela.
function resetConversation() {
  state.conversationVersion += 1;
  state.creatingConversation = null;
  state.conversation = null;
  state.pendingPins = [];
  state.controller?.abort();
  state.controller = null;
  state.token = null;
  setBusy(false);
}

async function startConversation() {
  if (state.creatingConversation) return state.creatingConversation;
  if (state.conversation) return state.conversation;
  const version = state.conversationVersion;
  const pinned = state.pendingPins;
  const pending = (async () => {
    const conversation = await api("/api/conversas", { method: "POST" });
    conversation.messages = [];
    // A lista continua recebendo escolhas enquanto o PATCH espera, mesmo se outra conversa for aberta.
    let applied = false;
    for (;;) {
      const ids = pinned.map((doc) => doc.id);
      if (ids.length || applied) {
        const data = await api(`/api/conversas/${conversation.id}`,
          { method: "PATCH", json: { fixados: ids } });
        conversation.fixados = data.fixados;
      }
      applied = true;
      if (ids.join(",") === pinned.map((doc) => doc.id).join(",")) break;
    }
    if (version === state.conversationVersion) {
      state.conversation = conversation;
      state.pendingPins = [];
      renderPins();
    }
    return conversation;
  })();
  state.creatingConversation = pending;
  try { return await pending; }
  finally {
    if (state.creatingConversation === pending) state.creatingConversation = null;
  }
}

// As etiquetas dos fixados como o servidor as guardou: ele fixa os anexos da conversa (lote 35).
async function refreshPins() {
  const id = state.conversation?.id;
  if (!id) return;
  try {
    const data = await api(`/api/conversas/${id}`);
    if (state.conversation?.id === id) {
      state.conversation.fixados = data.fixados;
      renderPins();
    }
  } catch { /* as etiquetas se acertam ao reabrir a conversa */ }
}

// A ficha do documento chega depois de ele ser fixado: a etiqueta troca o nome do arquivo pela referência.
function refreshPin(doc) {
  const list = pins();
  const index = list.findIndex((item) => item.id === doc.id);
  if (index < 0 || list[index].referencia === doc.referencia) return;
  list[index] = { ...list[index], referencia: doc.referencia };
  renderPins();
}

function renderPins() {
  const list = pins();
  $("pinned").hidden = !list.length;
  $("pinned").replaceChildren(...list.map((doc) => {
    const name = doc.referencia || doc.title;
    return el("span", { class: "pin", title: `${doc.title}: lido inteiro nas perguntas desta conversa que consultam os documentos` },
      el("span", { class: "pin-name", text: name }),
      el("button", { class: "pin-remove", type: "button", "aria-label": `Soltar ${name} desta conversa`,
        title: "Soltar desta conversa", text: "×", onclick: () => unpinDocument(doc.id) }));
  }));
  if (!$("docs-panel").hidden) markPinnedDocuments();
  placeUploads();
}

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
      resetConversation();
      renderPins();
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
  resetConversation();
  const version = state.conversationVersion;
  const pending = api(`/api/conversas/${id}`);
  state.creatingConversation = pending;
  try {
    const conversation = await pending;
    if (version !== state.conversationVersion) return;
    state.conversation = conversation;
  } catch {
    if (version !== state.conversationVersion) return;
    state.conversation = null;
    renderPins();
    return showWelcome();
  } finally {
    if (state.creatingConversation === pending) state.creatingConversation = null;
  }
  renderPins();
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
  resetConversation();
  renderPins();
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
  if (message.cobertura?.unidades && !message.cobertura.completa) {
    const missing = message.cobertura.unidades.filter((u) => !u.citados.length);
    const none = missing.filter((u) => u.estado === "sem_candidato").map((u) => u.nome);
    const rest = missing.filter((u) => u.estado !== "sem_candidato").map((u) => u.nome);
    node.append(el("div", { class: "note note-uncited",
      text: (rest.length ? `Sem fonte nesta resposta: ${rest.join("; ")}. Isso não significa ausência na biblioteca. ` : "")
        + (none.length ? `A busca não achou material para: ${none.join("; ")}. ` : "")
        + (message.cobertura.complemento === "confirmacao_necessaria"
          ? "Completar passa do limite de leitura sem confirmação; use Completar pesquisa." : "") }));
  }
  if (message.validation_status === "uncited" && !message.result_sources?.length) {
    node.append(el("div", { class: "note note-uncited", text: "Esta resposta não cita trechos dos seus documentos." }));
  }
  const usage = message.usage || {};
  const meta = el("div", { class: "meta" });
  const route = message.provider !== "local" ? message.rota : null;
  if (route) {
    // Lote 31: o que o AL-IAdo escolheu para esta resposta (modelo, skill e leitura), com o motivo na dica.
    const auto = route.automatico || {};
    const who = (flag, what) => `${what}: ${flag ? "escolha do AL-IAdo" : "pedido por você"}`;
    const earlier = (route.tentativas || []).map((item) => item.descartada
      ? ` Depois, uma leitura por ${item.leitura} (${formatTokens(item.tokens)} tokens) não melhorou a resposta e foi descartada.`
      : ` Antes, uma leitura por ${item.leitura} (${formatTokens(item.tokens)} tokens) não achou a resposta.`).join("");
    // Lote 33: como a busca foi preparada (sem reescrita, reescrita pela conversa ou uma busca por parte do pedido).
    const search = { nenhuma: " Busca pela própria pergunta, que já dizia o assunto, sem reescrita.",
      simples: " Busca por uma consulta reescrita a partir da conversa.",
      plano: ` Uma busca para cada parte do pedido: ${(route.partes || []).join("; ")}.` }[route.busca] || "";
    meta.append(el("span", { class: "route",
      title: `${who(auto.modelo, "Modelo")}; ${who(auto.skill, "skill")}; ${who(auto.leitura, "leitura")}. `
        + `Motivo: ${(route.reasons || []).join("; ")}.${search}${earlier} ${WRITE_HINT}`,
      text: [message.model, skillLabel(route.skill), route.leitura].filter(Boolean).join(" · ") }));
    if (route.pedidos?.length) {
      // Lote 35: o que você escreveu como pedido saiu do texto e valeu como escolha sua.
      meta.append(el("span", { class: "route", text: "seguiu o seu pedido",
        title: `Você pediu por escrito: ${route.pedidos.join("; ")}.`
          + (route.refeita ? " A mensagem só tinha o pedido: a pergunta anterior foi refeita com ele." : "") }));
    }
    if (route.trilha) {
      // Lote 31: o atalho, sem nova busca; lote 33: com mais partes ou depois de uma reclamação, só apoio à busca.
      const asked = `Pergunta muito parecida com a de ${new Date(route.trilha.data).toLocaleDateString("pt-BR")}: `
        + `“${route.trilha.pergunta}”. `;
      meta.append(el("span", route.leitura === "páginas de uma resposta anterior"
        ? { class: "route", text: "partiu de uma resposta anterior",
          title: `${asked}O modelo recebeu aquela troca e as páginas que ela citou, sem nova busca, e escreveu uma resposta nova.` }
        : { class: "route", text: "usou uma lembrança na pesquisa",
          title: `${asked}As páginas que aquela resposta citou entraram como apoio de uma nova busca na biblioteca.` }));
    }
    if (route.aprendido?.length) {
      // Lote 33: escolhas que você fez numa mensagem muito parecida e que o AL-IAdo repetiu.
      meta.append(el("span", { class: "route",
        title: route.aprendido.map((item) => `${item.campo}: como você escolheu em `
          + `${new Date(item.data).toLocaleDateString("pt-BR")}, em “${item.pergunta}”`).join("; ")
          + ". Para mudar, peça outra por escrito; a nova vale daqui em diante.",
        text: "repetiu uma escolha sua" }));
    }
  } else if (message.model && message.provider !== "local") meta.append(el("span", { text: message.model }));
  // Lote 38: o modelo local roda neste computador; os tokens dele não são pagos nem entram no uso do dia.
  const free = message.provider === "ollama";
  if (usage.total_tokens) meta.append(el("span", { text: `${formatTokens(usage.total_tokens)} tokens${free ? " locais" : ""}`,
    title: free ? "Tokens do modelo local, neste computador: sem custo e fora do uso do dia."
      : "Tokens desta resposta, pagos ao provedor e somados ao uso do dia." }));
  if (usage.reasoning_tokens) meta.append(el("span", { text: `${formatTokens(usage.reasoning_tokens)} de raciocínio` }));
  const info = (event) => openInfo(message, event.currentTarget);
  if (message.cobertura?.unidades) {
    meta.append(el("button", { class: "link", type: "button", text: "Cobertura da pesquisa", onclick: info,
      title: "Cada parte do pedido, o material que a busca achou para ela e o que a resposta citou." }));
    // Lote 33: a complementação é automática dentro do limite; o botão aparece quando ela pediu confirmação.
    if (message.cobertura.complemento === "confirmacao_necessaria" && message.id) {
      meta.append(el("button", { class: "link", type: "button", text: "Completar pesquisa",
        title: `Refaz a pesquisa com páginas inteiras para completar as partes sem fonte (cerca de ${formatTokens(Math.round((message.cobertura.tokens_complemento || 0) / 1000))} mil tokens). A tela pergunta antes de passar do limite.`,
        onclick: () => {
          const messages = state.conversation?.messages || [];
          const question = messages[messages.findIndex((m) => m.id === message.id) - 1];
          // O texto guardado traz os pedidos escritos, que valem de novo; a leitura sobe para as páginas inteiras.
          if (question?.role === "user" && !state.busy) submitQuestion(question.content, { leitura: "paginas" });
        } }));
    }
  }
  if (message.result_sources?.length) {
    meta.append(el("button", { class: "link result-link", type: "button",
      text: `${message.result_sources.length} resultado(s)`, onclick: info }));
  }
  if (message.sources?.length) {
    meta.append(el("button", { class: "link", type: "button", text: `${message.sources.length} fonte(s)`,
      onclick: info }));
  }
  // Lote 30: o que o modelo leu inteiro ou em parte nesta resposta; a lista fica na janela de fontes.
  const read = message.leitura?.documentos || [];
  if (read.length) {
    const pages = read.reduce((sum, doc) => sum + doc.paginas, 0);
    const whole = read.filter((doc) => doc.inteiro).length;
    const parts = [whole ? `${whole} ${whole === 1 ? "inteiro" : "inteiros"}` : "",
      read.length - whole ? `${read.length - whole} em parte` : ""].filter(Boolean).join(" e ");
    meta.append(el("button", { class: "link reading-link", type: "button",
      onclick: (event) => openInfo(message, event.currentTarget, { kind: "reading" }),
      title: "Documentos enviados ao modelo nesta resposta, com as páginas inteiras. Clique para ver quais e quais páginas.",
      text: message.leitura.paginas_soltas
        ? `leu ${pages === 1 ? "1 página inteira" : `${formatTokens(pages)} páginas inteiras`} de ${read.length === 1 ? "1 documento" : `${read.length} documentos`}`
        : `leu ${read.length === 1 ? "1 documento" : `${read.length} documentos`} (${parts}) · ${formatTokens(pages)} páginas` }));
  }
  if (message.leitura_por_trechos) {
    meta.append(el("span", { title: "Com a busca na web ligada, os documentos seguem por trechos, e os fixados não são enviados.",
      text: "com a busca na web, a leitura foi por trechos" }));
  }
  // Lote 27: quantos dos documentos que a busca trouxe a resposta citou; os outros ficam na janela de fontes.
  const cited = new Set((message.sources || []).map((source) => source.title));
  const brought = new Set([...cited, ...(message.recuperados || []).map((source) => source.title)]);
  if (brought.size > cited.size && !read.length) {
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
  const deeper = message.id ? message.aprofundar : null;
  if (deeper) {
    // Lote 31: o degrau seguinte da escada de leitura, com o custo estimado antes do clique.
    const what = { paginas: "Envia as 10 páginas mais próximas da pergunta, inteiras, com figuras e tabelas.",
      documento: `Envia ${deeper.titulo || "o documento mais citado"} inteiro, ou em blocos de páginas se for grande.`,
      integral: "Leitura ampla: os documentos que a busca escolher, inteiros, até o teto." }[deeper.leitura];
    const size = `${deeper.ate ? "até" : "cerca de"} ${formatTokens(Math.round(deeper.tokens / 1000))} mil tokens`;
    meta.append(el("button", { class: "link deeper-link", type: "button", text: `Ler mais fundo (${size})`,
      title: `${what} A pergunta é refeita com essa leitura; acima de ${formatTokens(state.reading?.limite || 30000)} tokens, a tela pergunta antes.`,
      onclick: () => {
        const list = state.conversation?.messages || [];
        const question = list[list.findIndex((m) => m.id === message.id) - 1];
        if (question?.role === "user" && !state.busy) {
          submitQuestion(question.content, { leitura: deeper.leitura, documentos: deeper.documentos });
        }
      } }));
  }
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
      await api("/api/memoria", { method: "POST", json: {
        texto: text, tipo: $("remember-kind").value, skill: conversationSkill(),
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
    memory.skill ? el("span", { class: "badge", text: skillLabel(memory.skill) }) : null);
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
  if (message?.cobertura?.unidades) {
    const labels ={ citada: "Com citação associada", sem_citacao: "Sem fonte nesta resposta",
      nao_enviado: "Material encontrado, mas não enviado", sem_candidato: "Nenhum candidato encontrado nesta busca" };
    query.push(el("h3", { class: "source-group", text: "Cobertura por parte do pedido" }),
      el("p", { class: "muted", text: "A associação de citações não certifica toda a interpretação científica."
        + (message.cobertura.decomposicao === "local" ? " A divisão local do pedido pode estar incompleta." : "") }),
      ...message.cobertura.unidades.map((unit) => el("div", { class: "source-card" },
        el("b", { text: unit.nome }), el("p", { text: labels[unit.estado] || unit.estado }),
        el("ul", {}, ...unit.enviados.map((source) => el("li", { text:
          `${source.title}${source.page ? `, p. ${source.page}` : ""} — ${unit.citados.includes(source.citation_id) ? "citado" : "enviado"}` }))))));
  }
  const results = message?.result_sources || [];
  const retrieved = message?.recuperados || [];
  const read = message?.leitura?.documentos || [];
  if (!sources.length && !web.length && !results.length && !retrieved.length && !read.length) {
    list.replaceChildren(...query,
      el("p", { class: "muted", text: "Esta resposta não usou resultados da pesquisa, documentos da biblioteca nem a web." }));
    return;
  }
  // Abrir a página no original e fixar o documento na conversa: valem para o citado e para o só recuperado.
  const sourceActions = (source) => {
    const actions = el("div", { class: "source-actions" });
    if (source.document_id) {
      const page = source.page ? `#page=${source.page}` : "";
      const fixed = pins().some((doc) => doc.id === source.document_id);
      actions.append(
        el("a", { class: "link", href: `/api/biblioteca/${source.document_id}/original${page}`, target: "_blank",
          rel: "noopener", text: "Abrir página" }),
        fixed ? el("span", { class: "muted", text: "Fixado nesta conversa" })
          : el("button", { class: "link", type: "button", text: "Fixar nesta conversa",
            title: "O documento passa a ir inteiro ao modelo nas perguntas desta conversa que consultam os documentos.",
            onclick: () => pinDocument({ id: source.document_id, title: source.title, referencia: source.referencia })
              .then(() => { if (state.sourcesOf === message) showSources(message); }) }));
    }
    return actions;
  };
  // As quebras de linha do PDF viram espaço; só a linha em branco continua separando parágrafos.
  const flowText = (value) => String(value || "").replace(/([^\n])\n(?!\n)/g, "$1 ");
  // Os avisos de um trecho, cada um com a sua nota ao passar o mouse.
  const sourceFlags = (source) => {
    const flags = [];
    if (source.method === "ocr") flags.push(["OCR: conferir no original",
      "O texto desta página veio do reconhecimento de texto sobre a imagem: pode ter letras trocadas."]);
    if (source.method === "figura") flags.push(["texto reconhecido dentro de figura: conferir no original",
      "Palavras que o computador leu dentro de uma figura da página. Não é texto corrido do documento."]);
    if (source.method === "descricao") flags.push(["descrição automática de figura ou tabela: conferir no original",
      "Texto escrito por um modelo a partir da imagem da página. Não é texto do documento: confira a figura ou a tabela no original antes de usar."]);
    if (source.status === "partial") flags.push(["extração parcial", "Parte das páginas deste documento não pôde ser lida."]);
    if (source.leitura === "pagina") flags.push(["página lida inteira",
      "O modelo recebeu esta página inteira, no PDF. O texto abaixo é o que foi extraído dela; as figuras e as tabelas estão em Abrir página."]);
    if (source.method === "imagem") flags.push(["sem texto extraído",
      "Nenhum texto pôde ser extraído desta página: o modelo a leu pela imagem. Confira em Abrir página."]);
    return flags;
  };
  const sourceLine = (tag, parts, source) => el(tag, { class: "source-loc" }, parts.filter(Boolean).join(" · "),
    ...sourceFlags(source).flatMap(([label, note]) => [" · ", el("span", { class: "source-flag", title: note, text: label })]));
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
  if (read.length) {
    // Lote 30: o que foi enviado inteiro ou em parte, e o que não coube no teto.
    const reading = message.leitura;
    const spent = message.usage?.input_tokens;
    parts.push(el("h3", { class: "source-group source-reading", text: "O que o modelo leu" }),
      el("p", { class: "muted source-queries",
        title: "O teto limita quantos tokens de documentos vão ao modelo numa pergunta; uma página de PDF custa cerca de 600.",
        text: `Páginas inteiras, com figuras e tabelas, até o teto de ${formatTokens(reading.teto)} tokens`
          + (spent ? `; o pedido todo usou ${formatTokens(spent)} tokens de entrada.` : ".") }),
      el("ul", { class: "reading-list" }, ...read.map((doc) => el("li", {},
        el("span", { class: "source-title", title: doc.titulo, text: doc.titulo }),
        el("span", { class: "source-loc", text: [
          doc.inteiro ? `inteiro: ${doc.paginas} ${doc.pdf === false ? "seções" : "páginas"}`
            : `páginas ${doc.blocos}, de ${doc.total}`,
          doc.fixado ? "fixado nesta conversa" : null].filter(Boolean).join(" · ") })))));
    if (reading.fora?.length) {
      parts.push(el("p", { class: "muted source-queries",
        text: `Não couberam no teto: ${reading.fora.join("; ")}. Aumente o teto ou fixe o documento na conversa.` }));
    }
  }
  if (sources.length && (web.length || results.length || read.length)) parts.push(el("h3", { class: "source-group", text: "Páginas e trechos citados" }));
  parts.push(...sources.map((source, index) => {
    const number = index + 1;
    const where = [source.locator, source.page ? `p. ${source.page}` : null].filter(Boolean).join(" · ");
    return el("div", { class: "source-card", "data-source": String(number) },
      el("div", { class: "source-head" }, el("span", { class: "cite", text: String(number) }),
        el("span", { class: "source-title", title: source.title,
          text: source.referencia ? `${source.referencia} · ${source.title}` : source.title })),
      sourceLine("div", [`v${source.version}`, where], source),
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
          sourceLine("span", [where], source),
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
  else if (focus?.kind === "reading") pop.querySelector(".source-reading")?.scrollIntoView({ block: "start" });
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

$("composer").addEventListener("submit", (event) => {
  event.preventDefault();
  if (state.busy) { state.controller?.abort(); return; }
  const text = $("question").value.trim();
  if (text) submitQuestion(text);
});

// A leitura passou do teto (lote 31): a tela diz quanto custa e o que vai, e só envia com a sua escolha.
function confirmReading(event, text, extra, bubble) {
  const thousand = (value) => `${formatTokens(Math.round(value / 1000))} mil`;
  const read = event.leitura?.documentos || [];
  const what = read.length ? ` (${read.slice(0, 4).map((doc) => `${doc.titulo}: ${doc.paginas} ${doc.paginas === 1 ? "página" : "páginas"}`).join("; ")}`
    + `${read.length > 4 ? `; e mais ${read.length - 4}` : ""})` : "";
  const why = event.motivo === "dia"
    ? `Hoje já foram usados ${thousand(event.hoje)} tokens (o aviso é em ${thousand(event.aviso_diario)}). `
    : event.motivo === "ampla" ? "Leitura ampla, como você pediu. " : "";
  const box = el("div", { class: "note note-ask" });
  const close = () => { box.remove(); bubble.remove(); };
  box.append(
    el("span", { text: `${why}Esta leitura envia cerca de ${thousand(event.tokens)} tokens ao modelo${what}.` }),
    el("span", { class: "ask-actions" },
      el("button", { class: "secondary", type: "button", text: "Ler assim",
        title: event.lembrar ? "Envia como está. Nesta conversa, a mesma leitura não pergunta de novo."
          : event.motivo === "ampla" ? "Envia como está. A leitura ampla pergunta todas as vezes."
          : "Envia como está. Depois do aviso diário, cada leitura pergunta de novo.",
        onclick: () => {
          close();
          if (event.lembrar && state.conversation) state.confirmed[state.conversation.id] = event.chave;
          submitQuestion(text, { ...extra, confirmado: event.chave });
        } }),
      el("button", { class: "secondary", type: "button", text: "Responder só com os trechos",
        title: "Refaz a pergunta no modo barato: só os trechos que a busca achou.",
        onclick: () => { close(); submitQuestion(text, { leitura: "trechos" }); } }),
      el("button", { class: "link", type: "button", text: "Cancelar",
        onclick: () => { close(); $("question").value = text; autosize(); $("question").focus(); } })));
  bubble.after(box);
  $("messages").scrollTop = $("messages").scrollHeight;
}

async function submitQuestion(text, extra = {}) {
  if (state.busy) return;
  if (!state.models.length) return toast("Nenhum modelo configurado. Confira o .env e reinicie.");
  setBusy(true);
  const controller = new AbortController();
  state.controller = controller;
  const token = Symbol("pedido");
  const version = state.conversationVersion;
  state.token = token;
  try {
    const conversation = await startConversation();
    const active = () => version === state.conversationVersion && state.conversation?.id === conversation.id;
    if (!active() || controller.signal.aborted) return;
    const messages = $("messages");
    if (WELCOME.isConnected) WELCOME.remove();
    messages.append(renderMessage({ role: "user", content: text }));
    // Com documentos inteiros, a resposta demora mais: o aviso diz o que está acontecendo. Sem o pedido na tela, só
    // se sabe antes quando a leitura vem de um botão ou de uma confirmação; senão, o servidor avisa ao subir a leitura.
    const whole = ["integral", "documento"].includes(extra.leitura) || Boolean(extra.confirmado);
    const thinkingText = el("span", { text: whole ? "AL-IAdo está lendo os documentos: pode levar alguns minutos…" : "AL-IAdo está pensando…" });
    const thinking = el("div", { class: "thinking" }, el("span", { class: "dots" }, el("i"), el("i"), el("i")), thinkingText);
    messages.append(thinking);
    messages.scrollTop = messages.scrollHeight;
    if ($("question").value.trim() === text) { $("question").value = ""; autosize(); }
    const userBubble = messages.lastElementChild.previousElementSibling;
    const live = el("div", { class: "answer is-live" });
    const liveNode = el("article", { class: "msg-assistant" }, live);
    let written = "";
    let shown = false;
    try {
      const remembered = state.confirmed[conversation.id];
      await streamMessage(conversation.id, {
        texto: text, ...(remembered ? { confirmado: remembered } : {}), ...extra,
      }, {
        onRestart(event) {
          if (!active()) return;
          // A primeira leitura não achou a resposta: o texto parcial sai, e o aviso diz que a leitura subiu.
          written = "";
          live.textContent = "";
          thinkingText.textContent = event.texto;
          if (liveNode.isConnected) liveNode.replaceWith(thinking);
        },
        onConfirm(event) {
          if (!active()) return;
          shown = true;
          if (state.token === token) { setBusy(false); state.controller = null; }
          thinking.remove();
          liveNode.remove();
          confirmReading(event, text, extra, userBubble);
        },
        onText(piece) {
          if (!active()) return;
          const follow = nearBottom(messages);
          if (thinking.isConnected) thinking.replaceWith(liveNode);
          written += piece;
          // As citações [K…] só viram números depois da checagem final no servidor.
          live.textContent = written.replace(/\[K[^\]\s]*\]/g, "[fonte]").replace(/\[R\d+(?:\s*(?:[,;]|e|[-–])\s*R\d+)*\]/g, "[resultado]");
          if (follow) messages.scrollTop = messages.scrollHeight;
        },
        onFinal(data) {
          if (!active()) return;
          shown = true;
          // A resposta está salva; o revisor de memória segue em segundo plano sem travar o envio.
          if (state.token === token) { setBusy(false); state.controller = null; }
          thinking.remove();
          liveNode.remove();
          userBubble.remove();
          for (const message of data.mensagens) messages.append(renderMessage(message));
          conversation.messages.push(...data.mensagens);
          messages.scrollTop = messages.scrollHeight;
          loadConversations();
          api("/api/estado").then((s) => showUsage(s.uso)).catch(() => {});
        },
        onMemory(event) {
          if (!active()) return;
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
      }, controller.signal);
    } catch (error) {
      if (!active() || shown) return; // a resposta já foi salva; só o aviso de memória se perdeu
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
}

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
  figuras: (job) => `Lendo o texto das figuras: ${job.atual} de ${job.total}`,
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
  if (job.etapa === "figuras") return 0.5;
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
  // Lote 30: o arquivo solto na conversa fica fixado nela e vai inteiro ao modelo a cada pergunta.
  const next = item.pinned ? "Fixado nesta conversa: é lido inteiro a cada pergunta." : "Está na biblioteca: o AL-IAdo o consulta quando a pergunta pede.";
  if (result.duplicate) return `Este documento já estava na biblioteca.${item.pinned ? ` ${next}` : ""}`;
  const version = result.version > 1 ? ` (versão ${result.version})` : "";
  return [`Pronto · ${pieces(result.trechos)}${version}. ${next}`, ...cardNotes(result)].join(" ");
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
    now = `${failed ? "Envio terminado" : "Tudo pronto"}: os documentos${failed ? " prontos" : ""} já estão na biblioteca`
      + `${items.every((item) => item.pinned) ? " e fixados nesta conversa" : ""}.`
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

function refreshDocuments() {
  if (!$("docs-panel").hidden && $("doc-viewer").hidden) loadLibrary();
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
    // O servidor fixa o anexo na conversa do envio assim que ele pode ser lido (lotes 30 e 35), mesmo que a
    // página tenha mudado de conversa ou sido recarregada; a tela só refaz as etiquetas da conversa aberta.
    const sent = job?.resultado;
    if (item.pin && !item.pinned && job?.fixado) {
      item.pinned = true;
      if (item.conversation === state.conversation?.id) refreshPins();
    }
    if (after !== before && ["pronto", "parcial", "falha"].includes(after)) {
      changed = true;
      announceUploads(after === "falha" ? `${item.name}: não foi possível indexar.` : `${item.name}: pronto para buscar.`);
      if (after !== "pronto") raiseUploads();
    }
    if (uploadDone(item)) {
      changed = true;  // as fichas terminaram: a lista de documentos e a etiqueta do fixado mostram a referência
      if (item.pinned && sent?.referencia) refreshPin(sent);
    }
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
              if (item.id && !uploadDone(item)) item.error = "O AL-IAdo não respondeu. Confira o documento na lista de documentos.";
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

// `pin`: o arquivo veio pela conversa (clipe ou arrastar) e fica fixado nela; pelo painel de documentos, não.
async function uploadFiles(files, pin = true) {
  const accepted = files.filter((file) => {
    const ok = /\.(pdf|md|json)$/i.test(file.name);
    if (!ok) toast(`${file.name}: envie PDF, Markdown ou JSON.`);
    return ok;
  });
  if (!accepted.length) return;
  // A criacao e compartilhada com a primeira pergunta; o destino do envio nao muda com a navegacao (lote 44).
  let conversation = null;
  if (pin) {
    try { conversation = await startConversation(); } catch (error) { toast(error.message); return; }
  }
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
  // A ficha de leitura herda a skill da conversa, para a memória separar pesquisa de engenharia.
  const skill = conversationSkill();
  const conversationId = conversation?.id || null;
  const added = accepted.map((file) => ({ name: file.name, file, id: null, job: null, error: null, sending: false,
    dismissed: false, pin, pinned: false, conversation: conversationId }));
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
      if (skill) form.append("skill", skill);
      if (item.pin && item.conversation) form.append("conversa", item.conversation);
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
      sending: false, dismissed: false, pin: Boolean(job.conversa), pinned: Boolean(job.fixado),
      conversation: job.conversa || null }));
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

// O clipe anexa à conversa (o documento fica fixado nela); o botão do painel só põe na biblioteca.
let attachToConversation = true;
$("attach").addEventListener("click", () => { attachToConversation = true; $("file").click(); });
$("library-add").addEventListener("click", () => { attachToConversation = false; $("file").click(); });
$("file").addEventListener("change", () => { uploadFiles([...$("file").files], attachToConversation); $("file").value = ""; });

let dragDepth = 0;
document.addEventListener("dragenter", (event) => {
  if (![...(event.dataTransfer?.types || [])].includes("Files")) return;
  dragDepth += 1;
  $("dropzone").firstElementChild.textContent = $("chat-view").hidden
    ? "Solte para adicionar à biblioteca" : "Solte para ler nesta conversa";
  $("dropzone").hidden = false;
});
document.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) $("dropzone").hidden = true; });
document.addEventListener("dragover", (event) => event.preventDefault());
document.addEventListener("drop", (event) => {
  event.preventDefault();
  dragDepth = 0;
  $("dropzone").hidden = true;
  // O pop-up aparece em qualquer aba: soltar um arquivo não troca mais de tela. Solto na conversa, o
  // documento fica fixado nela (lote 30); nas outras abas, só entra na biblioteca.
  if (event.dataTransfer?.files?.length) uploadFiles([...event.dataTransfer.files], !$("chat-view").hidden);
});

/* Abas: conversa, ciência e memória. A biblioteca deixou de ser uma aba (lote 30): os documentos ficam num
   painel aberto pelo botão "Documentos", ao lado do clipe. */
function showView(name) {
  const app = $("app");
  app.classList.toggle("library-mode", name !== "chat");
  app.classList.remove("drawer-open-small");
  closeInfo();
  closeDocuments();
  $("chat-view").hidden = name !== "chat";
  $("memory-view").hidden = name !== "memory";
  $("science-view").hidden = name !== "science";
  for (const [id, view] of [["nav-chats", "chat"], ["nav-memory", "memory"], ["nav-science", "science"]]) {
    $(id).classList.toggle("is-active", view === name);
  }
  placeUploads();
}

function showChat() { showView("chat"); }

/* Painel de documentos: a lista da biblioteca e, por documento, fixar na conversa, abrir o original,
   a ficha, as figuras e apagar. */
async function openDocuments(selectId) {
  const panel = $("docs-panel");
  panel.hidden = false;
  $("docs-open").setAttribute("aria-expanded", "true");
  placeDocuments();
  showDocumentList();
  loadGoogleFiles();
  await loadLibrary(selectId);
  placeDocuments();
}

function closeDocuments() {
  $("docs-panel").hidden = true;
  $("docs-open").setAttribute("aria-expanded", "false");
}

// O painel abre acima do botão, dentro da área da conversa, e nunca passa da altura da tela.
function placeDocuments() {
  const panel = $("docs-panel");
  if (panel.hidden) return;
  const area = $("chat-view").getBoundingClientRect();
  const rect = $("composer").getBoundingClientRect();
  // Em telas muito estreitas, o painel encolhe e fica sempre dentro da janela.
  const width = Math.min(560, Math.max(240, area.width - 24), window.innerWidth - 16);
  panel.style.width = `${width}px`;
  panel.style.left = `${Math.max(8, Math.min(Math.max(rect.left, area.left + 12), area.right - width - 12))}px`;
  panel.style.bottom = `${Math.round(window.innerHeight - rect.top) + 8}px`;
  panel.style.maxHeight = `${Math.max(200, Math.min(rect.top - 76, window.innerHeight * 0.72))}px`;
}

function showDocumentList() {
  $("doc-viewer").hidden = true;
  $("doc-viewer").replaceChildren();
  $("doc-list").hidden = false;
  markPinnedDocuments();
}

const megabytes = (bytes) => `${(bytes / 1048576).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MB`;

// O que a leitura de documentos inteiros deixou no serviço de arquivos do Google, e o botão de apagar de lá.
async function loadGoogleFiles() {
  const line = $("docs-files");
  let info;
  try { info = await api("/api/biblioteca/arquivos"); } catch { line.hidden = true; return; }
  line.hidden = !info.disponivel;
  if (!info.disponivel) return;
  const note = "Para o modelo ler um documento inteiro, o PDF é enviado ao serviço de arquivos do Google, que o guarda "
    + "por até 48 horas. Enquanto está lá, as próximas perguntas não precisam enviá-lo de novo.";
  if (!info.arquivos) {
    line.replaceChildren(el("span", { title: note, text: "Nenhum documento seu está guardado no Google agora." }));
    return;
  }
  const until = new Date(info.expira).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  line.replaceChildren(
    el("span", { title: note,
      text: `Guardado no Google para a leitura: ${info.arquivos} ${info.arquivos === 1 ? "arquivo" : "arquivos"} `
        + `(${megabytes(info.bytes)}), até ${until}. ` }),
    el("button", { class: "link danger", type: "button", text: "Apagar de lá",
      title: "Apaga do serviço do Google o que foi enviado. A biblioteca não muda; a próxima leitura envia de novo.",
      onclick: async () => {
        try {
          const done = await api("/api/biblioteca/arquivos", { method: "DELETE" });
          toast(done.falhas ? `${done.apagados} apagados; ${done.falhas} não puderam ser apagados agora.`
            : "Apagado do serviço de arquivos do Google.");
        } catch (error) { toast(error.message); }
        loadGoogleFiles();
      } }));
}

const STATUS = { ready: ["pronto", "badge-ok"], partial: ["parcial", "badge-warn"], failed: ["falhou", "badge-fail"] };
let libraryDocuments = [];

function markPinnedDocuments() {
  const fixed = new Set(pins().map((doc) => doc.id));
  document.querySelectorAll("#doc-list .doc-item").forEach((item) => {
    item.querySelector(".doc-pinned").hidden = !fixed.has(item.dataset.doc);
  });
}

async function loadLibrary(selectId) {
  let documents = [];
  try { documents = await api("/api/biblioteca"); } catch (error) { toast(error.message); }
  libraryDocuments = documents;
  const list = $("doc-list");
  const pending = documents.filter((doc) => doc.ficha_pendente).length;
  $("library-cards").hidden = !pending;
  $("library-cards").textContent = `Completar fichas (${pending})`;
  $("library-cards").dataset.pending = String(pending);
  if (!documents.length) {
    list.replaceChildren(el("li", { class: "empty",
      text: "A biblioteca está vazia. Adicione um PDF aqui ou solte o arquivo na conversa." }));
    return;
  }
  const newest = [...documents].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  list.replaceChildren(...newest.map((doc) => {
    const [label, badge] = STATUS[doc.status] || [doc.status, ""];
    return el("li", {}, el("button", { class: "doc-item", type: "button", "data-doc": doc.id,
      onclick: () => showDocument(doc) },
      el("span", { class: "doc-title", text: doc.referencia || doc.title }),
      ...(doc.referencia ? [el("span", { class: "doc-ref", text: doc.title })] : []),
      el("span", { class: "doc-meta" }, el("span", { class: `badge ${badge}`, text: label }),
        el("span", { text: `v${doc.version}` }), el("span", { text: relativeDate(doc.created_at) }),
        el("span", { class: "badge badge-ok doc-pinned", text: "fixado nesta conversa", hidden: true }))));
  }));
  markPinnedDocuments();
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
    // O documento apagado sai dos fixados: da conversa aberta agora, e das outras quando forem abertas.
    if (pins().some((item) => ids.includes(item.id))) await setPins(pins().filter((item) => !ids.includes(item.id)));
    showDocumentList();
    loadLibrary();
    refreshDocuments();
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

/* Figuras e tabelas (lote 29): o que o computador leu dentro das figuras e a descrição pelo modelo. */
const pagesText = (count) => (count === 1 ? "1 página" : `${count} páginas`);

function figuresBox(doc) {
  const box = el("section", { class: "doc-card doc-figures" });
  const draw = (info) => {
    const read = doc.figuras || { com_texto: 0 };
    const rows = [
      ["Páginas com figura ou tabela", String(info.paginas),
        "Páginas com imagem embutida, desenho ou legenda de figura, tabela, quadro ou gráfico."],
      ["Com texto lido nas figuras", String(read.com_texto || 0),
        "Páginas em que o computador reconheceu, sem custo, palavras dentro de uma figura."],
      ["Descritas pelo modelo", `${info.paginas - info.por_ler} de ${info.paginas}`,
        "Páginas enviadas ao modelo como imagem. A descrição entra na busca marcada como automática."],
    ];
    const when = read.data ? ` · ${read.modelo || "modelo"} em ${new Date(read.data).toLocaleDateString("pt-BR")}` : "";
    const actions = [];
    if (info.tarefa) {
      actions.push(el("span", { class: "muted", id: "figures-progress", text: "Descrevendo as páginas…" }),
        el("button", { class: "link danger", type: "button", text: "Parar", onclick: () => stopFigures(doc) }));
    } else if (info.disponivel && info.por_ler) {
      actions.push(el("button", { class: "secondary", type: "button",
        text: `Descrever figuras e tabelas (${pagesText(info.por_ler)})`, onclick: () => describeFigures(doc, info, redraw) }));
    } else if (info.por_ler) {
      actions.push(el("span", { class: "muted", text: "A descrição pelo modelo não está configurada." }));
    }
    box.replaceChildren(
      el("div", { class: "doc-card-head" }, el("h2", { class: "panel-title", text: "Figuras e tabelas" }),
        el("span", { class: "muted", text: info.paginas ? `conferir sempre no original${when}` : "nenhuma encontrada" })),
      ...(info.paginas ? [el("dl", {}, ...rows.flatMap(([label, value, note]) =>
        [el("dt", { title: note, text: label }), el("dd", { title: note, text: value })]))] : []),
      ...(actions.length ? [el("div", { class: "doc-figures-actions" }, ...actions)] : []));
    if (info.tarefa) followFigures(doc, info.tarefa);
  };
  const redraw = () => api(`/api/biblioteca/${doc.id}/figuras`).then(draw).catch(() => box.remove());
  box.append(el("div", { class: "doc-card-head" }, el("h2", { class: "panel-title", text: "Figuras e tabelas" })));
  redraw();
  return box;
}

async function describeFigures(doc, info, redraw) {
  const tokens = info.tokens_por_pagina || { entrada: 0, saida: 0 };
  const total = formatTokens(info.por_ler * (tokens.entrada + tokens.saida));
  if (!window.confirm(`Descrever as figuras e tabelas de «${doc.title}»?\n\n` +
    `São ${info.por_ler} chamada(s) ao modelo ${info.modelo || ""}, uma por página com figura ou tabela ` +
    `(cerca de ${total} tokens). Cada página é enviada como imagem.\n\n` +
    "As descrições entram na busca marcadas como automáticas, para conferir no original. Dá para parar no meio: " +
    "o que já foi lido fica guardado.")) return;
  try {
    await api(`/api/biblioteca/${doc.id}/figuras`, { method: "POST", json: {} });
    redraw();
  } catch (error) {
    toast(error.message);
  }
}

async function stopFigures(doc) {
  try {
    await api(`/api/biblioteca/${doc.id}/figuras`, { method: "DELETE" });
    toast("Parando: as páginas que já começaram ainda terminam.");
  } catch (error) {
    toast(error.message);
  }
}

async function followFigures(doc, job) {
  for (;;) {
    let status;
    try { status = await api(`/api/biblioteca/tarefas/${job}`); } catch { return; }
    const line = $("figures-progress");
    if (line) line.textContent = status.etapa === "indexando" ? "Refazendo o índice do documento…"
      : `Descrevendo: ${status.atual || 0} de ${pagesText(status.total || 0)}`;
    if (status.estado === "concluido") {
      const r = status.resultado;
      if (status.erro) toast(status.erro);
      else toast(`${pagesText(r.lidas)} ${r.lidas === 1 ? "descrita" : "descritas"}, com ${r.itens} ` +
        (r.itens === 1 ? "figura ou tabela" : "figuras ou tabelas") +
        (r.falhas ? `; ${r.falhas} não puderam ser lidas e ficam para outra vez` : "") +
        (r.interrompido ? "; parado antes do fim" : "") + "." + (status.aviso ? ` ${status.aviso}` : ""));
      // A lista traz as contagens novas; o documento aberto é redesenhado com elas.
      if (!$("docs-panel").hidden && $("doc-viewer").dataset.doc === doc.id) loadLibrary(doc.id);
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}

// Um documento do painel: o que fazer com ele (fixar, abrir, apagar), a ficha, as figuras e as pendências.
function showDocument(doc) {
  const viewer = $("doc-viewer");
  viewer.dataset.doc = doc.id;
  const fixed = pins().some((item) => item.id === doc.id);
  const issues = doc.issues?.length ? el("div", { class: "note note-warn", text: `Pendências: ${plainIssues(doc.issues)}` }) : null;
  const pin = el("button", { class: fixed ? "secondary" : "primary", type: "button",
    text: fixed ? "Soltar desta conversa" : "Fixar nesta conversa",
    title: fixed ? "O documento deixa de ir inteiro ao modelo nesta conversa."
      : "O documento vai inteiro ao modelo nas perguntas desta conversa que consultam os documentos.",
    onclick: async () => {
      await (fixed ? unpinDocument(doc.id) : pinDocument(doc));
      if (!viewer.hidden && viewer.dataset.doc === doc.id) showDocument(doc);
    } });
  viewer.replaceChildren(
    el("button", { class: "link doc-back", type: "button", text: "‹ Todos os documentos", onclick: showDocumentList }),
    el("h3", { class: "doc-detail-title", text: doc.referencia || doc.title }),
    ...(doc.referencia ? [el("p", { class: "muted doc-detail-file", text: `${doc.title} · versão ${doc.version}` })] : []),
    el("div", { class: "doc-detail-actions" }, pin,
      el("a", { class: "link", href: `/api/biblioteca/${doc.id}/original`, target: "_blank", rel: "noopener", text: "Abrir original" }),
      el("button", { class: "link danger", type: "button", text: "Apagar", onclick: () => deleteDocument(doc) })),
    ...(issues ? [issues] : []),
    cardBox(doc), ...(doc.title.toLowerCase().endsWith(".pdf") ? [figuresBox(doc)] : []));
  $("doc-list").hidden = true;
  viewer.hidden = false;
  $("docs-panel").scrollTop = 0;
}

$("docs-open").addEventListener("click", () => ($("docs-panel").hidden ? openDocuments() : closeDocuments()));
$("docs-close").addEventListener("click", closeDocuments);
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeDocuments(); });
document.addEventListener("click", (event) => {
  const panel = $("docs-panel");
  // Clicar fora fecha o painel; os avisos, o envio de arquivos e as confirmações não contam como fora.
  if (panel.hidden || panel.contains(event.target) || !event.target.isConnected
    || event.target.closest("#docs-open, #upload-pop, #toast, .pin")) return;
  closeDocuments();
});
window.addEventListener("resize", placeDocuments);
new ResizeObserver(placeDocuments).observe($("composer"));
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
