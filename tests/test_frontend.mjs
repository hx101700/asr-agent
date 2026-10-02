import assert from "node:assert/strict";
import test from "node:test";
import { createPresenter } from "../skills/asr-transcription/scripts/asr_transcription/static/app.mjs";
import { createApi } from "../skills/asr-transcription/scripts/asr_transcription/static/api.mjs";
import { createModel, availability, configuration, receiveSaveError } from "../skills/asr-transcription/scripts/asr_transcription/static/model.mjs";

const limits = { audio_bytes: 2_000_000_000, hotwords_bytes: 5_000_000, context_chars: 400, speaker_min: 2, speaker_max: 100 };
const description = { model: "fixed-model", region: "华北2（北京）", limits, audio_suffixes: [".wav"], languages: [["zh", "中文"]], output_defaults: { json: "default", document: "default" } };
const audio = { name: "sample.wav", size: 64000 };
// 生成指定编号的合成预览回执。
const validation = (id = "validation-1") => ({ validation_id: id, summary: {} });

// 创建由测试主动决定成功或失败的等待任务。
function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

// View/API 替身提供前端交互测试所需的公开方法。
// 组合表单、界面和接口替身并记录交互顺序。
function harness(overrides = {}) {
  const events = [];
  const calls = [];
  const form = { useApiKey: false, diarizationEnabled: true, hotwordsEnabled: false, contextEnabled: false, context: "", language: "", speaker: { value: "", badInput: false } };
  const view = {
    apiKey: "", current: null, error: null, focus: null,
    /* 提供事件绑定契约的空替身。 */ bind() {}, /* 提供页面初始化契约的空替身。 */ initialize() {}, /* 返回测试表单的独立副本。 */ readForm: () => structuredClone(form),
    // 保存本轮界面状态并记录渲染顺序。
    render(model, available) {
      this.current = { phase: model.phase, available: structuredClone(available) };
      events.push(["render", model.phase, available.editable]);
    },
    /* 保存字段错误并记录呈现顺序。 */ showError(error) { this.error = error; events.push(["error", error.field]); },
    /* 清除测试界面的当前错误。 */ clearError() { this.error = null; },
    /* 清除界面替身持有的合成Key。 */ clearApiKey() { this.apiKey = ""; },
    /* 在界面替身中显示指定合成Key。 */ setApiKey(value) { this.apiKey = value; },
    /* 提供文件控件清理契约的空替身。 */ clearFile() {},
    /* 记录焦点已移至预览区。 */ focusPreview() { this.focus = "preview"; }, /* 记录焦点已移至表单区。 */ focusForm() { this.focus = "form"; },
    /* 记录焦点已移至保存回执。 */ focusReceipt() { this.focus = "receipt"; }, /* 提供文件下载契约的空替身。 */ download() {},
  };
  const handlers = {
    // 返回合成的会话规则和默认保存位置。
    "/api/session": () => description,
    // 返回测试音频已接收的合成回执。
    "/api/upload-audio": () => ({ upload_id: "audio-1", name: audio.name, size_bytes: audio.size }),
    // 返回测试热词已接收的合成回执。
    "/api/upload-hotwords": () => ({ upload_id: "words-1", name: "words.xlsx", size_bytes: 100 }),
    // 返回默认的合成配置预览。
    "/api/validate": () => validation(),
    ...overrides,
  };
  const api = {
    // 记录接口调用并交给对应的本机测试处理器。
    async request(path, payload, file) {
      calls.push({ path, payload: structuredClone(payload), file });
      assert.ok(handlers[path], `未预期的请求：${path}`);
      return handlers[path](payload, file);
    },
    /* 返回供下载流程使用的合成模板。 */ template: async () => "fixture-blob",
  };
  let sequence = 0;
  const presenter = createPresenter(view, api, () => `request-${++sequence}`);
  return { ...presenter, form, view, events, calls, handlers };
}

// 初始化测试页面并添加合成音频。
async function addAudio(page) {
  await page.actions.start();
  await page.actions.upload("audio", [audio]);
}

// 添加音频并确认测试页面进入预览状态。
async function preview(page) {
  await addAudio(page);
  await page.actions.validate();
  assert.equal(page.model.phase, "review");
}

test("Model 从 loading 开始，临时操作不冻结其他输入", () => {
  const model = createModel();
  assert.equal(availability(model).editable, false);
  model.phase = "editing";
  model.picker = { id: "picker", kind: "json", cancelling: false };
  model.auth.status = "loading";
  model.uploads.audio.status = "uploading";
  const available = availability(model);
  assert.equal(available.editable, true);
  assert.equal(available.cancelDirectory, true);
  assert.equal(available.upload.hotwords, true);
  assert.equal(available.validate, false);
});

test("会话未就绪时，拖拽和提交不产生请求", async () => {
  const pending = deferred();
  const page = harness({ "/api/session": () => pending.promise });
  const starting = page.actions.start();
  await page.actions.upload("audio", [audio]);
  await page.actions.validate();
  assert.deepEqual(page.calls.map((call) => call.path), ["/api/session"]);
  pending.resolve(description);
  await starting;
  assert.equal(page.view.current.available.editable, true);
});

test("初始化失败进入 unavailable，不把失败伪装成仍在加载", async () => {
  const page = harness({ "/api/session": () => { throw new Error("服务不可用"); } });
  await page.actions.start();
  assert.equal(page.model.phase, "unavailable");
  assert.equal(page.view.current.available.editable, false);
  await page.actions.upload("audio", [audio]);
  await page.actions.validate();
  assert.equal(page.calls.length, 1);
  assert.equal(page.view.error.message, "服务不可用");
});

test("保存网络结果未知后持续冻结，不能拖入、校验或重新保存", async () => {
  const page = harness({ "/api/confirm": () => { throw new Error("连接中断"); } });
  await preview(page);
  await page.actions.confirm();
  const count = page.calls.length;
  assert.equal(page.model.phase, "save_unknown");
  assert.equal(page.view.current.available.editable, false);
  await page.actions.upload("audio", [audio]);
  await page.actions.validate();
  await page.actions.confirm();
  await page.actions.selectDirectory("json");
  assert.equal(page.calls.length, count);
  assert.equal(page.model.receipt, null);
});

test("4xx 保存拒绝先恢复控件并渲染，再定位错误，随后可重新校验", async () => {
  const page = harness({
    "/api/confirm": () => { throw Object.assign(new Error("目录不可写"), { httpStatus: 422, field: "document_directory" }); },
    "/api/select-directory": () => ({ path: "D:\\Example\\revised" }),
  });
  await preview(page);
  await page.actions.confirm();
  assert.deepEqual(page.events.slice(-2), [["render", "editing", true], ["error", "document_directory"]]);
  assert.equal(page.view.current.available.chooseDirectory, true);
  await page.actions.selectDirectory("document");
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.document_directory, "D:\\Example\\revised");
  assert.equal(page.model.phase, "review");
  assert.equal(page.calls.filter((call) => call.path === "/api/confirm").length, 1);
});

test("校验期间修改输入，不接受过期结果，也不并发提交第二次校验", async () => {
  const pending = deferred();
  const page = harness({ "/api/validate": () => pending.promise });
  await addAudio(page);
  const validating = page.actions.validate();
  page.form.diarizationEnabled = false;
  await page.actions.changed("diarization-enabled");
  await page.actions.validate();
  pending.resolve(validation("stale"));
  await validating;
  assert.equal(page.model.preview, null);
  assert.equal(page.model.phase, "editing");
  await page.actions.confirm();
  assert.equal(page.calls.filter((call) => call.path === "/api/validate").length, 1);
  page.handlers["/api/validate"] = () => validation("current");
  await page.actions.validate();
  assert.equal(page.model.preview.id, "current");
  assert.equal(page.view.focus, "preview");
});

test("漏选音频时定位字段，不发送校验请求", async () => {
  const page = harness();
  await page.actions.start();
  await page.actions.validate();
  assert.equal(page.view.error.field, "audio_upload_id");
  assert.equal(page.calls.length, 1);
});

for (const [kind, field] of [["hotwords", "hotwords_upload_id"], ["context", "context"]]) {
  test(`启用 ${kind} 却漏填时定位对应字段`, async () => {
    const page = harness();
    await addAudio(page);
    page.form[`${kind}Enabled`] = true;
    page.form.context = " \n ";
    await page.actions.changed(`${kind}-enabled`);
    await page.actions.validate();
    assert.equal(page.view.error.field, field);
    assert.equal(page.calls.filter((call) => call.path === "/api/validate").length, 0);
  });
}

test("目录取消保留预览；选定使预览失效，恢复默认提交 default", async () => {
  const page = harness({ "/api/select-directory": () => ({ cancelled: true }) });
  await preview(page);
  const first = page.model.preview;
  await page.actions.selectDirectory("json");
  assert.equal(page.model.preview, first);
  page.handlers["/api/select-directory"] = () => ({ path: "D:\\Example\\chosen" });
  await page.actions.selectDirectory("json");
  assert.equal(page.model.preview, null);
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.json_directory, "D:\\Example\\chosen");
  page.actions.resetDirectory("json");
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.json_directory, "default");
});

test("API Key 只交给 View，关闭模式清空，迟到结果不能恢复凭据", async () => {
  const fakeKey = "fixture-key-not-a-credential";
  const page = harness({ "/api/api-key": () => ({ value: fakeKey }) });
  await addAudio(page);
  page.form.useApiKey = true;
  await page.actions.changed("use-api-key");
  assert.equal(page.view.apiKey, fakeKey);
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.auth_mode, "api_key");
  assert.equal(JSON.stringify(page.model).includes(fakeKey), false);
  assert.equal(JSON.stringify(page.calls).includes(fakeKey), false);
  const pending = deferred();
  page.handlers["/api/api-key"] = () => pending.promise;
  const loading = page.actions.changed("use-api-key");
  page.form.useApiKey = false;
  await page.actions.changed("use-api-key");
  pending.resolve({ value: fakeKey });
  await loading;
  assert.equal(page.view.apiKey, "");
  assert.equal(page.model.auth.status, "idle");
});

test("API Key 读取失败不能预览，关闭该模式后可以继续", async () => {
  const page = harness({ "/api/api-key": () => { throw new Error("请填写项目 .env"); } });
  await addAudio(page);
  page.form.useApiKey = true;
  await page.actions.changed("use-api-key");
  assert.equal(page.model.auth.status, "failed");
  await page.actions.validate();
  assert.equal(page.view.error.field, "auth_mode");
  assert.equal(page.calls.filter((call) => call.path === "/api/validate").length, 0);
  page.form.useApiKey = false;
  await page.actions.changed("use-api-key");
  await page.actions.validate();
  assert.equal(page.model.phase, "review");
});

test("预览后切换鉴权方式使预览失效，不能确认旧设置", async () => {
  const page = harness({ "/api/api-key": () => ({ value: "fixture-only" }) });
  await addAudio(page);
  page.form.useApiKey = true;
  await page.actions.changed("use-api-key");
  await page.actions.validate();
  assert.equal(page.model.phase, "review");
  page.form.useApiKey = false;
  await page.actions.changed("use-api-key");
  await page.actions.confirm();
  assert.equal(page.calls.filter((call) => call.path === "/api/confirm").length, 0);
  assert.equal(page.model.phase, "editing");
  assert.equal(page.model.preview, null);
});

test("关闭发言人区分不提交之前的人数或非法输入", async () => {
  const page = harness();
  await addAudio(page);
  page.form.speaker.value = "3";
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.speaker_count, 3);
  page.form.diarizationEnabled = false;
  page.form.speaker.badInput = true;
  await page.actions.changed("diarization-enabled");
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.speaker_count, null);
});

test("等待目录窗口可以编辑和上传；取消使用当前 ID，返回后才释放", async () => {
  const pending = deferred();
  const page = harness({ "/api/select-directory": () => pending.promise, "/api/cancel-directory": () => ({ ok: true }) });
  await preview(page);
  const selecting = page.actions.selectDirectory("json");
  assert.equal(page.view.current.available.editable, true);
  assert.equal(page.view.current.available.upload.audio, true);
  page.form.speaker.value = "4";
  await page.actions.changed("speaker-count");
  await page.actions.cancelDirectory();
  assert.equal(page.view.current.available.chooseDirectory, false);
  assert.equal(page.view.current.available.cancelDirectory, false);
  const opened = page.calls.find((call) => call.path === "/api/select-directory");
  assert.equal(page.calls.at(-1).payload.picker_id, opened.payload.picker_id);
  pending.resolve({ cancelled: true });
  await selecting;
  assert.equal(page.model.directories.json, "default");
  assert.equal(page.view.current.available.chooseDirectory, true);
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.speaker_count, 4);
});

test("目录窗口异常恢复按钮后再定位，不自动重开窗口", async () => {
  const page = harness({ "/api/select-directory": () => { throw Object.assign(new Error("窗口异常退出"), { httpStatus: 422 }); } });
  await preview(page);
  await page.actions.selectDirectory("json");
  assert.equal(page.model.picker, null);
  assert.equal(page.view.current.available.chooseDirectory, true);
  assert.deepEqual(page.events.slice(-2), [["render", "review", true], ["error", "json_directory"]]);
  assert.equal(page.calls.filter((call) => call.path === "/api/select-directory").length, 1);
});

test("不完整数字 badInput 不会按空白处理，真实空白才为自动人数", async () => {
  const page = harness();
  await addAudio(page);
  page.form.speaker = { value: "", badInput: true };
  await page.actions.validate();
  assert.equal(page.view.error.field, "speaker_count");
  assert.equal(page.calls.filter((call) => call.path === "/api/validate").length, 0);
  page.form.speaker.badInput = false;
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.speaker_count, null);
});

test("人数和上下文使用服务端 limits，而非重复的固定数值", async () => {
  const page = harness({ "/api/session": () => ({ ...description, limits: { ...limits, speaker_max: 4, context_chars: 3 } }) });
  await addAudio(page);
  page.form.speaker.value = "5";
  assert.throws(() => configuration(page.model, page.form), /2–4/);
  page.form.speaker.value = "";
  page.form.contextEnabled = true;
  page.form.context = "甲乙丙丁";
  await page.actions.validate();
  assert.match(page.view.error.message, /3 个字符/);
});

test("音频扩展名使用服务端列表，不从 DOM 反读业务规则", async () => {
  const page = harness({ "/api/session": () => ({ ...description, audio_suffixes: [".flac"] }) });
  await page.actions.start();
  await page.actions.upload("audio", [audio]);
  assert.equal(page.view.error.field, "audio_upload_id");
  assert.equal(page.calls.filter((call) => call.path === "/api/upload-audio").length, 0);
  await page.actions.upload("audio", [{ name: "sample.FLAC", size: 64000 }]);
  assert.equal(page.calls.filter((call) => call.path === "/api/upload-audio").length, 1);
});

test("上传期间禁止同类并发，成功后显示接收结果，失败不自动重试", async () => {
  const pending = deferred();
  const page = harness({ "/api/upload-audio": () => pending.promise });
  await page.actions.start();
  const uploading = page.actions.upload("audio", [audio]);
  await page.actions.upload("audio", [audio]);
  assert.equal(page.view.current.available.upload.hotwords, true);
  pending.reject(new Error("传输中断"));
  await uploading;
  assert.equal(page.model.uploads.audio.status, "failed");
  assert.equal(page.model.uploads.audio.id, null);
  assert.equal(page.view.current.available.upload.audio, true);
  assert.equal(page.calls.filter((call) => call.path === "/api/upload-audio").length, 1);
});

test("即时热词与上下文可以一起提交，关闭开关不发送遗留输入", async () => {
  const page = harness();
  await addAudio(page);
  await page.actions.upload("hotwords", [{ name: "words.xlsx", size: 100 }]);
  page.form.hotwordsEnabled = true;
  page.form.contextEnabled = true;
  page.form.context = "相关术语";
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.enhancement_mode, "both");
  assert.equal(page.calls.at(-1).payload.hotwords_upload_id, "words-1");
  assert.equal(page.calls.at(-1).payload.context, "相关术语");
  page.form.hotwordsEnabled = false;
  page.form.contextEnabled = false;
  await page.actions.changed("context-enabled");
  await page.actions.validate();
  assert.equal(page.calls.at(-1).payload.hotwords_upload_id, null);
  assert.equal(page.calls.at(-1).payload.context, "");
});

test("保存成功清除凭据并冻结；刷新恢复回执不允许新操作", async () => {
  const receipt = { job_id: "job", config_path: "fixture/config.json" };
  const page = harness({ "/api/confirm": () => receipt });
  await preview(page);
  page.view.apiKey = "fixture-only";
  await page.actions.confirm();
  assert.equal(page.model.receipt, receipt);
  assert.equal(page.view.apiKey, "");
  assert.equal(page.view.focus, "receipt");
  assert.equal(page.view.current.available.editable, false);
  const refreshed = harness({ "/api/session": () => ({ ...description, confirmed: receipt }) });
  await refreshed.actions.start();
  assert.equal(refreshed.model.phase, "saved");
  await refreshed.actions.validate();
  assert.equal(refreshed.calls.length, 1);
});

test("HTTP 适配器保留明确错误状态，未知 JSON 结果不能当作明确拒绝", async () => {
  const api = createApi(async () => ({ ok: false, status: 422, json: async () => ({ error: "字段无效", field: "context" }) }), "fixture-token");
  await assert.rejects(api.request("/api/validate", {}), (error) => error.httpStatus === 422 && error.field === "context");
  const invalid = createApi(async () => ({ ok: false, status: 422, json: async () => { throw new Error("invalid JSON"); } }), "");
  const model = createModel();
  model.phase = "saving";
  try { await invalid.request("/api/confirm", {}); } catch (error) { receiveSaveError(model, error); }
  assert.equal(model.phase, "save_unknown");
});

test("上下文中的引号、换行、路径和Unicode保留到HTTP JSON参数", async () => {
  const page = harness();
  await addAudio(page);
  page.form.contextEnabled = true;
  page.form.context = '--help a=b "中文"\r\nC:\\voice files\\\t😀𠮷 cafe\u0301 $HOME &|<>^%! `文本`';
  await page.actions.validate();
  const payload = page.calls.at(-1).payload;
  assert.equal(payload.context, page.form.context);
  let sent;
  const api = createApi(async (url, options) => {
    sent = JSON.parse(options.body);
    return { ok: true, json: async () => ({ ok: true }) };
  }, "fixture-token");
  await api.request("/api/validate", payload);
  assert.deepEqual(sent, payload);
});
