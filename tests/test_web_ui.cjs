"use strict";

const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const staticDirectory = path.join(__dirname, "../src/asr_agent/static");
const script = readFileSync(path.join(staticDirectory, "app.js"), "utf8");
const html = readFileSync(path.join(staticDirectory, "index.html"), "utf8");
const settle = () => new Promise((resolve) => setImmediate(resolve));

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

function response(data, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => data };
}

function validation(id = "validation-1") {
  return response({
    validation_id: id,
    summary: {
      audio: { name: "sample.wav", duration_seconds: 1, size_bytes: 64000, channels: 2, sample_rate: 16000, format: "WAV" },
      auth_mode: "console", enhancement: { mode: "none", count: 0, context_chars: 0 },
      json_directory: "outputs", document_directory: "outputs", warnings: [],
    },
  });
}

// 只模拟状态测试需要的 DOM；元素及初始属性来自实际 HTML，不接入网络或浏览器。
function harness(overrides = {}) {
  const elements = [];
  const calls = [];
  let focused = null;
  function makeElement(tag, attributes = {}) {
    const classes = new Set((attributes.class || "").split(" "));
    const listeners = new Map();
    const node = {
      tagName: tag, id: attributes.id, value: attributes.value || "", files: [],
      checked: "checked" in attributes, disabled: "disabled" in attributes,
      hidden: "hidden" in attributes, accept: attributes.accept || "",
      name: attributes.name, children: [], textContent: "",
      classList: {
        add: (...names) => names.forEach((name) => classes.add(name)),
        remove: (...names) => names.forEach((name) => classes.delete(name)),
        toggle: (name, force) => force ? classes.add(name) : classes.delete(name),
        contains: (name) => classes.has(name),
      },
      getAttribute: (name) => attributes[name] ?? null,
      setAttribute: (name, value) => { attributes[name] = value; },
      removeAttribute: (name) => { delete attributes[name]; },
      addEventListener: (name, listener) => { listeners.set(name, listener); },
      dispatch: (name, event = {}) => listeners.get(name)?.({ preventDefault() {}, target: node, ...event }),
      append: (...children) => node.children.push(...children),
      replaceChildren: (...children) => { node.children = children; },
      get childElementCount() { return node.children.length; },
      focus: () => { focused = node; },
      scrollIntoView() {},
      closest: () => null,
      querySelector: (selector) => select(selector),
      querySelectorAll: () => elements.filter((item) => item.getAttribute("aria-invalid") === "true"),
    };
    elements.push(node);
    return node;
  }
  for (const [, tag, source] of html.matchAll(/<([a-z][\w-]*)\b([^>]*)>/gi)) {
    const attributes = {};
    for (const [, name, value] of source.matchAll(/([\w:-]+)(?:="([^"]*)")?/g)) attributes[name] = value ?? "";
    makeElement(tag, attributes);
  }
  const byId = (id) => elements.find((node) => node.id === id) || null;
  function select(selector) {
    if (selector.startsWith("input[name=")) return elements.find((node) => node.name === "auth_mode" && node.checked);
    if (selector.startsWith(".")) return elements.find((node) => node.classList.contains(selector.slice(1)));
    return elements.find((node) => node.tagName === selector);
  }
  const handlers = {
    "/api/session": () => response({ model: "fixed-model", region: "beijing", auth: { console: { message: "本地会话已就绪" } } }),
    "/api/upload-audio": () => response({ upload_id: "audio-1", name: "sample.wav", size_bytes: 64000 }),
    "/api/validate": () => validation(),
    ...overrides,
  };
  const context = vm.createContext({
    document: {
      getElementById: byId, querySelector: select, createElement: makeElement,
      documentElement: { style: { setProperty() {} } },
    },
    window: { location: { hash: "", pathname: "/", search: "" }, history: { replaceState() {} } },
    URLSearchParams, ResizeObserver: class { observe() {} },
    fetch: async (url, options) => {
      calls.push({ url, options });
      assert.ok(handlers[url], `未预期的请求：${url}`);
      return handlers[url](options);
    },
  });
  vm.runInContext(script, context, { filename: "app.js" });
  return {
    node: byId, calls, handlers, focused: () => focused,
    drop: () => byId("audio-dropzone").dispatch("drop", { dataTransfer: { files: [{ name: "sample.wav" }] } }),
    submit: () => byId("config-form").dispatch("submit"),
    confirm: () => byId("confirm-button").dispatch("click"),
  };
}

async function preparePreview(page) {
  await settle();
  assert.equal(page.node("config-fields").disabled, false);
  page.drop();
  await settle();
  await page.submit();
  assert.equal(page.node("confirm-button").disabled, false);
  assert.equal(page.node("review-content").hidden, false);
}

test("会话未就绪时，拖拽和提交不产生上传或校验请求", async () => {
  const session = deferred();
  const page = harness({ "/api/session": () => session.promise });
  page.drop();
  await page.submit();
  await settle();
  assert.deepEqual(page.calls.map((call) => call.url), ["/api/session"]);
  assert.equal(page.node("audio-file").files.length, 0);
  session.resolve(response({ model: "fixed-model", region: "beijing", auth: { console: { message: "就绪" } } }));
  await settle();
  assert.equal(page.node("config-fields").disabled, false);
});

test("保存网络结果未知后保持冻结，拖拽和提交均不能发送新请求", async () => {
  const page = harness({ "/api/confirm": () => { throw new Error("连接中断"); } });
  await preparePreview(page);
  await page.confirm();
  const requestCount = page.calls.length;
  assert.equal(page.node("config-fields").disabled, true);
  assert.equal(page.node("validate-button").disabled, true);
  page.drop();
  await page.submit();
  await page.confirm();
  await settle();
  assert.equal(page.calls.length, requestCount);
  assert.equal(page.node("error-panel").hidden, false);
  assert.equal(page.node("receipt-panel").hidden, true);
});

test("保存收到明确 4xx 拒绝后，可修改输入并重新校验", async () => {
  const page = harness({ "/api/confirm": () => response({ error: "配置已过期" }, 409) });
  await preparePreview(page);
  await page.confirm();
  assert.equal(page.node("config-fields").disabled, false);
  assert.equal(page.node("confirm-button").disabled, true);
  page.node("document-directory").value = "outputs/revised";
  page.node("config-form").dispatch("input", { target: page.node("document-directory") });
  await page.submit();
  const validations = page.calls.filter((call) => call.url === "/api/validate");
  assert.equal(validations.length, 2);
  assert.equal(JSON.parse(validations[1].options.body).document_directory, "outputs/revised");
  assert.equal(page.node("confirm-button").disabled, false);
  assert.equal(page.calls.filter((call) => call.url === "/api/confirm").length, 1);
});

test("校验期间输入已修改时，不接受旧预览或允许确认", async () => {
  const pending = deferred();
  const page = harness({ "/api/validate": () => pending.promise });
  await settle();
  page.drop();
  await settle();
  const submitted = page.submit();
  page.node("diarization-enabled").checked = false;
  page.node("config-form").dispatch("input", { target: page.node("diarization-enabled") });
  pending.resolve(validation("stale-validation"));
  await submitted;
  assert.equal(page.node("review-content").hidden, true);
  assert.equal(page.node("confirm-button").disabled, true);
  await page.confirm();
  assert.equal(page.calls.filter((call) => call.url === "/api/confirm").length, 0);
  page.handlers["/api/validate"] = () => validation("current-validation");
  await page.submit();
  assert.equal(page.node("confirm-button").disabled, false);
  assert.equal(page.focused().id, "review-card");
});
