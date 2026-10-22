"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const script = fs.readFileSync(path.join(__dirname, "../../src/aliado/interfaces/web/static/app.js"), "utf8").replace(/\r\n/g, "\n");
const tick = () => new Promise(setImmediate);
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function harness() {
  const nodes = new Map();
  function node() {
    return { value: "", isConnected: false, messages: [], children: [], lastElementChild: {previousElementSibling: {remove() {}}},
      append(...items) { this.children.push(...items); }, replaceChildren(...items) { this.children = items; }, remove() {}, replaceWith() {}, focus() {},
      addEventListener(event, handler) { this[event] = handler; }, classList: {remove() {}} };
  }
  const $ = id => { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); };
  const state = { conversation: null, pendingPins: [], models: [{}], confirmed: {}, busy: false,
    conversationVersion: 0, creatingConversation: null };
  const uploads = {items: [], earlier: [], lote: null};
  const posts = [], sent = [], questions = [], patches = [], notices = [];
  const sandbox = { $, state, uploads, WELCOME: node(), UPLOAD_PARALLEL: 3, AbortController,
    FormData: class { constructor() { this.data = new Map(); } append(key, value) { this.data.set(key, value); } },
    clearTimeout() {}, newBatch: () => "batch", renderUploads() {}, pollUploads() {}, uploadDone: () => false,
    uploadOpen: () => false, clearUploads() { uploads.items = []; }, conversationSkill: () => null,
    toast: text => notices.push(text), setBusy: value => { state.busy = value; }, el: () => node(),
    renderMessage: message => Object.assign(node(), {content: message.content}), renderPins() {}, showChat() {}, showWelcome() {}, loadConversations() {},
    autosize() {}, nearBottom: () => true,
    streamMessage: async (id, body, handlers) => { questions.push({id, body, handlers}); },
    api: async (url, options = {}) => {
      if (url === "/api/conversas" && options.method === "POST") {
        const task = deferred(); posts.push(task); return task.promise;
      }
      if (url === "/api/biblioteca") { sent.push(options.body.data); return {tarefa: "job"}; }
      if (options.method === "PATCH") {
        const task = deferred(); patches.push({url, options, ...task}); return task.promise;
      }
      return {id: url.split("/").at(-1), messages: [], fixados: []};
    },
  };
  vm.createContext(sandbox);
  // Executa as funcoes reais e seus chamadores; so I/O e renderizacao periferica sao simulados.
  for (const name of ["resetConversation", "startConversation", "setPins", "uploadFiles", "submitQuestion", "openConversation"]) {
    const match = new RegExp(`(?:async )?function ${name}\\(`).exec(script);
    if (!match && name === "resetConversation") continue;
    assert.ok(match, `function ${name}`);
    const end = script.indexOf("\n}", match.index) + 2;
    vm.runInContext(script.slice(match.index, end), sandbox);
  }
  const begin = script.indexOf('$("new-chat").addEventListener');
  vm.runInContext(script.slice(begin, script.indexOf("\n});", begin) + 4), sandbox);
  return {sandbox, state, posts, sent, questions, patches, notices, $,
    upload: () => sandbox.uploadFiles([{name: "paper.pdf"}]),
    question: () => sandbox.submitQuestion("question")};
}
for (const order of ["upload-first", "question-first"]) {
  test(`INT-01: concurrent creation (${order})`, async () => {
    const h = harness();
    const first = order === "upload-first" ? h.upload() : h.question();
    const second = order === "upload-first" ? h.question() : h.upload();
    assert.equal(h.posts.length, 1);
    h.posts[0].resolve({id: "created", fixados: []});
    await Promise.all([first, second]);
    assert.equal(h.sent[0].get("conversa"), "created");
    assert.equal(h.questions[0].id, "created");
  });
}
test("INT-01: opening another conversation preserves the upload destination", async () => {
  const h = harness(), upload = h.upload();
  await h.sandbox.openConversation("existing");
  h.posts[0].resolve({id: "created", fixados: []});
  await upload;
  assert.equal(h.state.conversation.id, "existing");
  assert.equal(h.sent[0].get("conversa"), "created");
});
test("INT-01: navigating while the first question waits does not send it to another conversation", async () => {
  const h = harness(), question = h.question();
  await h.sandbox.openConversation("existing");
  h.posts[0].resolve({id: "created", fixados: []});
  await question;
  assert.equal(h.state.conversation.id, "existing");
  assert.equal(h.questions.length, 0);
});
test("INT-01: new chat starts an independent creation and ignores the late result", async () => {
  const h = harness(), first = h.upload();
  h.$("new-chat").click();
  const second = h.upload();
  assert.equal(h.posts.length, 2);
  h.posts[1].resolve({id: "new", fixados: []});
  await second;
  h.posts[0].resolve({id: "old", fixados: []});
  await first;
  assert.equal(h.state.conversation.id, "new");
  assert.deepEqual(h.sent.map(form => form.get("conversa")), ["new", "old"]);
});
test("INT-01: failed creation is shared and a later attempt can retry", async () => {
  const h = harness(), first = h.upload(), question = h.question();
  assert.equal(h.posts.length, 1);
  h.posts[0].reject(new Error("offline"));
  await Promise.all([first, question]);
  assert.equal(h.sent.length + h.questions.length, 0);
  const second = h.upload();
  assert.equal(h.posts.length, 2);
  h.posts[1].resolve({id: "retry", fixados: []});
  await second;
  assert.equal(h.sent[0].get("conversa"), "retry");
});
test("INT-01: question waits for pending pins and their PATCH cannot change another chat", async () => {
  const h = harness();
  h.state.pendingPins = [{id: "document"}];
  const upload = h.upload();
  h.posts[0].resolve({id: "created", fixados: []});
  await tick();
  assert.equal(h.patches[0].url, "/api/conversas/created");
  const question = h.question();
  await tick();
  assert.equal(h.questions.length, 0);
  await h.sandbox.openConversation("existing");
  h.patches[0].resolve({fixados: [{id: "document"}]});
  await Promise.all([upload, question]);
  assert.equal(h.state.conversation.id, "existing");
  assert.equal(h.state.conversation.fixados.length, 0);
  assert.equal(h.sent[0].get("conversa"), "created");
  assert.equal(h.questions.length, 0);
});

test("INT-01: late messages cannot enter the conversation opened later", async () => {
  const h = harness(), question = h.question();
  h.posts[0].resolve({id: "created", fixados: []});
  await question;
  await h.sandbox.openConversation("existing");
  h.questions[0].handlers.onFinal({mensagens: [{role: "assistant", content: "late"}]});
  assert.equal(h.state.conversation.id, "existing");
  assert.equal(h.state.conversation.messages.length, 0);
});
test("INT-01: a late pin PATCH cannot replace the current pins", async () => {
  const h = harness();
  await h.sandbox.openConversation("old");
  const pin = h.sandbox.setPins([{id: "document"}]);
  await h.sandbox.openConversation("existing");
  h.patches[0].resolve({fixados: [{id: "document"}]});
  await pin;
  assert.equal(h.state.conversation.fixados.length, 0);
});
test("INT-01: an upload during navigation waits for the selected conversation", async () => {
  const h = harness(), oldUpload = h.upload(), selected = deferred();
  const original = h.sandbox.api;
  h.sandbox.api = (url, options) => url === "/api/conversas/existing" ? selected.promise : original(url, options);
  const navigation = h.sandbox.openConversation("existing"), newUpload = h.upload();
  assert.equal(h.posts.length, 1);
  selected.resolve({id: "existing", messages: [], fixados: []});
  await Promise.all([navigation, newUpload]);
  h.posts[0].resolve({id: "old", fixados: []});
  await oldUpload;
  assert.equal(h.state.conversation.id, "existing");
  assert.deepEqual(h.sent.map(form => form.get("conversa")), ["existing", "old"]);
});

test("INT-01: a question during navigation preserves the rendered history", async () => {
  const h = harness(), selected = deferred(), original = h.sandbox.api;
  h.sandbox.api = (url, options) => url === "/api/conversas/existing" ? selected.promise : original(url, options);
  const navigation = h.sandbox.openConversation("existing"), question = h.question();
  selected.resolve({id: "existing", messages: [{role: "user", content: "history"}], fixados: []});
  await Promise.all([navigation, question]);
  assert.equal(h.questions[0].id, "existing");
  assert.ok(h.$("messages").children.some(child => child.content === "history"));
});
for (const ids of [["first", "second"], []]) {
  test(`INT-01: pins changed during transfer (${ids.length ? "add" : "remove"}) are preserved`, async () => {
    const h = harness();
    h.state.pendingPins = [{id: "first"}];
    const upload = h.upload();
    h.posts[0].resolve({id: "created", fixados: []});
    await tick();
    await h.sandbox.setPins(ids.map(id => ({id})));
    h.patches[0].resolve({fixados: [{id: "first"}]});
    await tick();
    assert.equal(h.patches.length, 2);
    assert.deepEqual(Array.from(h.patches[1].options.json.fixados), ids);
    h.patches[1].resolve({fixados: ids.map(id => ({id}))});
    await upload;
    assert.deepEqual(Array.from(h.state.conversation.fixados, doc => doc.id), ids);
  });
}
