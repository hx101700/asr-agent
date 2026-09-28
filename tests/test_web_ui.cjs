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

function sessionResponse() {
  return response({
    model: "fixed-model", region: "beijing",
    output_defaults: { json: "D:\\Example\\outputs", document: "D:\\Example\\outputs" },
    languages: [["zh", "中文"], ["en", "英语"]],
  });
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
      type: attributes.type, readOnly: "readonly" in attributes, placeholder: attributes.placeholder,
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
    if (selector.startsWith(".")) return elements.find((node) => node.classList.contains(selector.slice(1)));
    return elements.find((node) => node.tagName === selector);
  }
  const handlers = {
    "/api/session": sessionResponse,
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
    crypto: { randomUUID: require("node:crypto").randomUUID },
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
    change: (id, property, value) => {
      const target = byId(id);
      target[property] = value;
      byId("config-form").dispatch("input", { target });
      byId("config-form").dispatch("change", { target });
    },
  };
}

async function addAudio(page) {
  await settle();
  assert.equal(page.node("config-fields").disabled, false);
  page.drop();
  await settle();
}

async function preparePreview(page) {
  await addAudio(page);
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
  session.resolve(sessionResponse());
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
  const page = harness({
    "/api/confirm": () => response({ error: "配置已过期" }, 409),
    "/api/select-directory": () => response({ path: "D:\\Example\\revised" }),
  });
  await preparePreview(page);
  await page.confirm();
  assert.equal(page.node("config-fields").disabled, false);
  assert.equal(page.node("confirm-button").disabled, true);
  await page.node("document-browse").dispatch("click");
  await page.submit();
  const validations = page.calls.filter((call) => call.url === "/api/validate");
  assert.equal(validations.length, 2);
  assert.equal(JSON.parse(validations[1].options.body).document_directory, "D:\\Example\\revised");
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

test("漏选音频时就地提示并聚焦，不发送校验请求", async () => {
  const page = harness();
  await settle();
  await page.submit();
  assert.equal(page.calls.filter((call) => call.url === "/api/validate").length, 0);
  assert.equal(page.focused().id, "audio-file");
  assert.equal(page.node("audio-error").hidden, false);
  assert.equal(page.node("audio-dropzone").classList.contains("needs-attention"), true);
  assert.equal(page.node("audio-file").getAttribute("aria-invalid"), "true");
  assert.equal(page.node("error-panel").hidden, true);
});

for (const [kind, field] of [["hotwords", "hotwords-file"], ["context", "context"]]) {
  test(`启用 ${kind} 却漏填时定位对应字段，不发送校验请求`, async () => {
    const page = harness();
    await addAudio(page);
    page.change(`${kind}-enabled`, "checked", true);
    if (kind === "context") page.change("context", "value", " \n ");
    await page.submit();
    assert.equal(page.calls.filter((call) => call.url === "/api/validate").length, 0);
    assert.equal(page.node(`${kind}-fields`).hidden, false);
    assert.equal(page.node(`${kind}-error`).hidden, false);
    assert.equal(page.focused().id, field);
    assert.ok(page.node(field).getAttribute("aria-describedby").includes(`${kind}-error`));
  });
}

test("取消目录选择保留预览，选定后需要重检且提交所选路径", async () => {
  const page = harness({ "/api/select-directory": () => response({ cancelled: true }) });
  await preparePreview(page);
  const before = page.node("json-directory").value;
  assert.equal(page.node("json-directory").readOnly, true);
  await page.node("json-browse").dispatch("click");
  assert.equal(page.node("json-directory").value, before);
  assert.equal(page.node("review-content").hidden, false);
  assert.equal(page.node("confirm-button").disabled, false);
  page.handlers["/api/select-directory"] = () => response({ path: "D:\\Example\\chosen" });
  await page.node("json-browse").dispatch("click");
  assert.equal(page.node("json-directory").value, "D:\\Example\\chosen");
  assert.equal(page.node("review-content").hidden, true);
  assert.equal(page.node("confirm-button").disabled, true);
  await page.submit();
  const calls = page.calls.filter((call) => call.url === "/api/validate");
  assert.equal(JSON.parse(calls.at(-1).options.body).json_directory, "D:\\Example\\chosen");
  assert.equal(JSON.parse(calls.at(-1).options.body).document_directory, "outputs");
  assert.equal(page.calls.filter((call) => call.url === "/api/select-directory").every((call) => JSON.parse(call.options.body).kind === "json"), true);
  page.node("json-reset").dispatch("click");
  await page.submit();
  assert.equal(JSON.parse(page.calls.at(-1).options.body).json_directory, "outputs");
});

test("API Key 仅在只读控件显示，不进入校验参数，关闭模式立即清空", async () => {
  const fakeKey = "fixture-key-not-a-credential";
  const page = harness({ "/api/api-key": () => response({ value: fakeKey }) });
  await addAudio(page);
  page.change("use-api-key", "checked", true);
  await settle();
  assert.equal(page.node("api-key-value").readOnly, true);
  assert.equal(page.node("api-key-value").type, "password");
  assert.equal(page.node("api-key-value").value, fakeKey);
  page.node("api-key-toggle").dispatch("click");
  assert.equal(page.node("api-key-value").type, "text");
  await page.submit();
  const request = page.calls.find((call) => call.url === "/api/validate");
  assert.equal(JSON.parse(request.options.body).auth_mode, "api_key");
  assert.equal(JSON.stringify(request.options).includes(fakeKey), false);
  page.change("use-api-key", "checked", false);
  assert.equal(page.node("api-key-value").value, "");
  assert.equal(page.node("api-key-value").type, "password");
  assert.equal(page.node("api-key-fields").hidden, true);
  await page.submit();
  assert.equal(JSON.parse(page.calls.at(-1).options.body).auth_mode, "console");
  assert.equal(page.calls.filter((call) => call.url === "/api/api-key").length, 1);
});

test("关闭发言人区分后，不提交先前填写的人数", async () => {
  const page = harness();
  await addAudio(page);
  page.change("speaker-count", "value", "3");
  await page.submit();
  assert.equal(JSON.parse(page.calls.at(-1).options.body).speaker_count, 3);
  page.change("diarization-enabled", "checked", false);
  assert.equal(page.node("speaker-fields").hidden, true);
  assert.equal(page.node("speaker-count").disabled, true);
  await page.submit();
  const payload = JSON.parse(page.calls.at(-1).options.body);
  assert.equal(payload.diarization_enabled, false);
  assert.equal(payload.speaker_count, null);
});

test("等待目录窗口时仍可编辑，取消会结束当前请求并保留保存位置", async () => {
  const selection = deferred();
  const page = harness({
    "/api/select-directory": () => selection.promise,
    "/api/cancel-directory": () => {
      selection.resolve(response({ cancelled: true }));
      return response({ ok: true });
    },
  });
  await preparePreview(page);
  const selecting = page.node("json-browse").dispatch("click");
  assert.equal(page.node("config-fields").disabled, false);
  assert.equal(page.node("json-browse").disabled, true);
  assert.equal(page.node("directory-wait").hidden, false);
  assert.equal(page.node("cancel-directory").disabled, false);
  page.change("speaker-count", "value", "4");
  await page.node("cancel-directory").dispatch("click");
  await selecting;
  assert.equal(page.node("json-directory").value, "");
  assert.equal(page.node("json-browse").disabled, false);
  assert.equal(page.node("directory-wait").hidden, true);
  assert.equal(page.node("speaker-count").value, "4");
  const opened = page.calls.find((call) => call.url === "/api/select-directory");
  const cancelled = page.calls.find((call) => call.url === "/api/cancel-directory");
  assert.equal(JSON.parse(opened.options.body).picker_id, JSON.parse(cancelled.options.body).picker_id);
  await page.submit();
  assert.equal(JSON.parse(page.calls.at(-1).options.body).speaker_count, 4);
});

test("目录窗口超时后可继续操作，不自动重开窗口", async () => {
  const page = harness({ "/api/select-directory": () => response({ ok: false, error: "窗口等待超时" }, 422) });
  await preparePreview(page);
  await page.node("json-browse").dispatch("click");
  assert.equal(page.node("config-fields").disabled, false);
  assert.equal(page.node("json-browse").disabled, false);
  assert.equal(page.node("json-error").hidden, false);
  assert.equal(page.node("directory-wait").hidden, true);
  assert.equal(page.calls.filter((call) => call.url === "/api/select-directory").length, 1);
});
