import assert from "node:assert/strict";
import test from "node:test";
import { useTranscription, type ViewEffects } from "../frontend/useTranscription";
import { createApi, UiError } from "../frontend/api";
import { availability, configuration, createModel, receiveSaveError } from "../frontend/model";
import { translate, type Translate } from "../frontend/i18n";
import type { Api, Configuration, Endpoints, Language, Limits, Model, Receipt, SessionDescription, ValidationResult } from "../frontend/types";

const limits: Limits = { audio_bytes: 2_000_000_000, hotwords_bytes: 5_000_000, upload_bytes: 1_000_000_000,
  audio_seconds: 43200, hotwords_count: 2000, context_chars: 400, speaker_min: 2, speaker_max: 100 };
const description: SessionDescription = { model: "fixed-model", region: "cn-beijing", limits,
  audio_suffixes: [".wav"], languages: ["zh"], output_defaults: { json: "D:/example", document: "D:/example" }, confirmed: null };
const audio = new File(["synthetic audio"], "sample.wav");
const words = new File(["synthetic spreadsheet"], "words.xlsx");
const hotwordRows = [{ row: 2, text: "术语", weight: 4 }];
const receipt: Receipt = { job_id: "job", config_path: "fixture/config.json", json_directory: "fixture/json",
  document_directory: "fixture/documents", auth_mode: "console", execution_started: false };

// 生成具备真实协议字段的合成预览。
function validation(id = "validation-1"): ValidationResult {
  return { validation_id: id, summary: { auth_mode: "console", audio: { name: audio.name, duration_seconds: 2,
    size_bytes: audio.size, format_name: "wav", channels: 1, sample_rate: 16000 },
    enhancement: { mode: "none", count: 0, context_chars: 0 }, json_directory: "fixture/json",
    document_directory: "fixture/documents", warnings: [] } };
}

// 创建可控制完成时点的异步结果。
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}
type Handler<K extends keyof Endpoints> = (payload?: object, file?: File) => Endpoints[K] | Promise<Endpoints[K]>;
type Handlers = { [K in keyof Endpoints]: Handler<K> };

// 连接真实前端用例与本机接口替身，记录可观察的请求和视图效果。
function harness(overrides: Partial<Handlers> = {}) {
  let language: Language = "zh-CN";
  const t: Translate = (key, values) => translate(language, key, values);
  const calls: { path: keyof Endpoints; payload?: object; file?: File }[] = [];
  const view = { apiKey: "", focus: "", downloaded: false };
  const effects: ViewEffects = {
    // 保存最后一次焦点目标。
    focus(target) { view.focus = target; },
    // 模拟凭据显示组件的私有值。
    setApiKey(value) { view.apiKey = value; },
    // 在用户检查时读取显示组件中的合成Key。
    getApiKey() { return view.apiKey; },
    // 记录模板已交给下载视图。
    download() { view.downloaded = true; },
  };
  const handlers: Handlers = {
    "/api/session": () => description,
    "/api/upload-audio": () => ({ upload_id: "audio-1", name: audio.name, size_bytes: audio.size }),
    "/api/upload-hotwords": () => ({ name: words.name, size_bytes: words.size, rows: hotwordRows.map(row => ({ ...row })), issues: [], warnings: [] }),
    "/api/validate-hotwords": () => ({ issues: [], warnings: [], count: 1 }),
    "/api/validate": () => validation(),
    "/api/api-key": () => ({ value: "" }),
    "/api/save-api-key": () => ({ ok: true }),
    "/api/select-directory": () => ({ cancelled: true }),
    "/api/cancel-directory": () => ({ ok: true }),
    "/api/confirm": () => receipt,
    "/api/reopen": () => ({ ok: true, configuration: { auth_mode: "console", audio_upload_id: "audio-1", diarization_enabled: true,
      enhancement_mode: "none", hotword_rows: [], context: "", language_hint: null, speaker_count: null,
      json_directory: "default", document_directory: "default" }, audio: { upload_id: "audio-1", name: audio.name, size_bytes: audio.size } }),
    ...overrides,
  };
  const api: Api = {
    // 记录调用后执行对应的类型化接口替身。
    async request<K extends keyof Endpoints>(path: K, payload?: object, file?: File): Promise<Endpoints[K]> {
      calls.push({ path, payload, file });
      return handlers[path](payload, file);
    },
    // 返回合成模板文件。
    async template() { return new Blob(["fixture"]); },
  };
  let sequence = 0;
  const controller = useTranscription(api, effects, t, () => `request-${++sequence}`);
  return { ...controller, calls, handlers, view, t,
    // 切换翻译器语言并应用同一用例的语言变更操作。
    setLanguage(value: Language) { language = value; controller.actions.languageChanged(); } };
}
type Page = ReturnType<typeof harness>;

// 启动会话并添加合成音频。
async function addAudio(page: Page): Promise<void> {
  await page.actions.start();
  await page.actions.upload("audio", [audio]);
}

// 将页面推进到已检查状态。
async function preview(page: Page): Promise<void> {
  await addAudio(page);
  await page.actions.validate();
  assert.equal(page.model.phase, "review");
}

// 取得最近一次校验请求的配置数据。
function lastConfig(page: Page): Configuration {
  return page.calls.filter(call => call.path === "/api/validate").at(-1)?.payload as Configuration;
}

test("未加载会话时不产生上传或保存请求", async () => {
  const pending = deferred<SessionDescription>();
  const page = harness({ "/api/session": () => pending.promise });
  const starting = page.actions.start();
  await page.actions.upload("audio", [audio]);
  await page.actions.validate();
  assert.deepEqual(page.calls.map(call => call.path), ["/api/session"]);
  pending.resolve(description);
  await starting;
  assert.equal(availability(page.model).editable, true);
});

test("初始化失败明确显示不可用", async () => {
  const page = harness({ "/api/session": () => { throw new Error("服务不可用"); } });
  await page.actions.start();
  assert.equal(page.model.phase, "unavailable");
  assert.equal(availability(page.model).editable, false);
  assert.equal(page.error.value?.message, "服务不可用");
});

test("某类上传和目录等待不冻结其它普通输入", () => {
  const model = createModel();
  model.phase = "editing";
  model.picker = { id: "picker", kind: "json", cancelling: false };
  model.auth.status = "loading";
  model.uploads.audio.status = "uploading";
  assert.equal(availability(model).editable, true);
  assert.equal(availability(model).upload.hotwords, true);
  assert.equal(availability(model).validate, false);
  assert.equal(availability(model).changeLanguage, false);
});

test("保存响应未知后阻止重复上传、校验和提交", async () => {
  const page = harness({ "/api/confirm": () => { throw new Error("连接中断"); } });
  await preview(page);
  await page.actions.confirm();
  const count = page.calls.length;
  assert.equal(page.model.phase, "save_unknown");
  await page.actions.upload("audio", [audio]);
  await page.actions.validate();
  await page.actions.confirm();
  await page.actions.selectDirectory("json");
  page.setLanguage("en");
  assert.equal(page.calls.length, count);
  assert.equal(page.model.phase, "save_unknown");
});

test("明确保存拒绝可修改字段后重新检查", async () => {
  const page = harness({ "/api/confirm": () => { throw new UiError("目录不可写", "document_directory", 422); },
    "/api/select-directory": () => ({ cancelled: false, path: "D:/revised" }) });
  await preview(page);
  await page.actions.confirm();
  assert.equal(page.model.phase, "editing");
  assert.equal(page.view.focus, "document_directory");
  await page.actions.selectDirectory("document");
  await page.actions.validate();
  assert.equal(lastConfig(page).document_directory, "D:/revised");
  assert.equal(page.model.phase, "review");
  assert.equal(page.calls.filter(call => call.path === "/api/confirm").length, 1);
});

test("校验中修改表单会丢弃旧结果，且不并发第二次校验", async () => {
  const pending = deferred<ValidationResult>();
  const page = harness({ "/api/validate": () => pending.promise });
  await addAudio(page);
  const checking = page.actions.validate();
  page.form.diarizationEnabled = false;
  await page.actions.changed();
  await page.actions.validate();
  pending.resolve(validation("stale"));
  await checking;
  assert.equal(page.model.preview, null);
  assert.equal(page.model.phase, "editing");
  await page.actions.confirm();
  assert.equal(page.calls.filter(call => call.path === "/api/validate").length, 1);
  page.handlers["/api/validate"] = () => validation("current");
  await page.actions.validate();
  assert.equal((page.model as Model).preview?.id, "current");
  assert.equal(page.view.focus, "review");
});

test("缺少音频时定位到上传区域", async () => {
  const page = harness();
  await page.actions.start();
  await page.actions.validate();
  assert.equal(page.error.value?.field, "audio_upload_id");
  assert.equal(page.calls.length, 1);
});

for (const kind of ["hotwords", "context"] as const) {
  test(`启用${kind}却没有内容时阻止预览`, async () => {
    const page = harness();
    await addAudio(page);
    page.form[kind === "hotwords" ? "hotwordsEnabled" : "contextEnabled"] = true;
    page.form.context = " \n ";
    await page.actions.validate();
    assert.equal(page.error.value?.field, kind === "hotwords" ? "hotword_rows" : "context");
    assert.equal(page.calls.filter(call => call.path === "/api/validate").length, 0);
  });
}

test("取消目录选择保留预览，选定目录后作废预览，可恢复默认", async () => {
  const page = harness();
  await preview(page);
  const first = page.model.preview;
  await page.actions.selectDirectory("json");
  assert.equal(page.model.preview, first);
  page.handlers["/api/select-directory"] = () => ({ cancelled: false, path: "D:/chosen" });
  await page.actions.selectDirectory("json");
  assert.equal(page.model.preview, null);
  await page.actions.validate();
  assert.equal(lastConfig(page).json_directory, "D:/chosen");
  page.actions.resetDirectory("json");
  await page.actions.validate();
  assert.equal(lastConfig(page).json_directory, "default");
});

test("等待窗口时仍可编辑，取消沿用原请求编号", async () => {
  const pending = deferred<Endpoints["/api/select-directory"]>();
  const page = harness({ "/api/select-directory": () => pending.promise });
  await preview(page);
  const selecting = page.actions.selectDirectory("json");
  page.form.speaker = "4";
  await page.actions.changed();
  await page.actions.cancelDirectory();
  assert.equal(availability(page.model).chooseDirectory, false);
  assert.equal(availability(page.model).cancelDirectory, false);
  const open = page.calls.find(call => call.path === "/api/select-directory")?.payload as { picker_id: string };
  assert.equal((page.calls.at(-1)?.payload as { picker_id: string }).picker_id, open.picker_id);
  pending.resolve({ cancelled: true });
  await selecting;
  assert.equal(availability(page.model).chooseDirectory, true);
  await page.actions.validate();
  assert.equal(lastConfig(page).speaker_count, 4);
});

test("目录失败恢复控件并定位字段，不自动重开", async () => {
  const page = harness({ "/api/select-directory": () => { throw new UiError("窗口异常", undefined, 422); } });
  await preview(page);
  await page.actions.selectDirectory("json");
  assert.equal(page.model.picker, null);
  assert.equal(availability(page.model).chooseDirectory, true);
  assert.equal(page.error.value?.field, "json_directory");
  assert.equal(page.calls.filter(call => call.path === "/api/select-directory").length, 1);
});

test("已有Key只交给显示组件，模式切换清除，迟到读取不恢复", async () => {
  const key = "fixture-key-not-a-credential";
  const page = harness({ "/api/api-key": () => ({ value: key }) });
  await addAudio(page);
  page.form.useApiKey = true;
  await page.actions.setAuthMode(page.form.useApiKey);
  assert.equal(page.view.apiKey, key);
  await page.actions.validate();
  assert.equal(lastConfig(page).auth_mode, "api_key");
  assert.equal(JSON.stringify(page.model).includes(key), false);
  assert.equal(JSON.stringify(page.form).includes(key), false);
  assert.equal(page.calls.some(call => call.path === "/api/save-api-key"), false);
  const pending = deferred<{ value: string }>();
  page.handlers["/api/api-key"] = () => pending.promise;
  const loading = page.actions.setAuthMode(page.form.useApiKey);
  page.form.useApiKey = false;
  await page.actions.setAuthMode(page.form.useApiKey);
  pending.resolve({ value: key });
  await loading;
  assert.equal(page.view.apiKey, "");
  assert.equal(page.model.auth.status, "idle");
});

test("空Key允许网页填写，检查时先保存，再提交无Key配置", async () => {
  const page = harness();
  await addAudio(page);
  page.form.useApiKey = true;
  await page.actions.setAuthMode(page.form.useApiKey);
  assert.equal(page.error.value, null);
  page.view.apiKey = "fixture-new-key";
  page.actions.keyChanged();
  await page.actions.validate();
  assert.equal(page.model.phase, "review");
  assert.deepEqual(page.calls.slice(-2).map(call => call.path), ["/api/save-api-key", "/api/validate"]);
  assert.deepEqual(page.calls.at(-2)?.payload, { value: "fixture-new-key" });
  assert.equal(JSON.stringify(lastConfig(page)).includes("fixture-new-key"), false);
  assert.equal(JSON.stringify(page.model).includes("fixture-new-key"), false);
});

test("无音频可单独保存Key，后续校验复用已保存值且不创建任务", async () => {
  const page = harness();
  await page.actions.start();
  await page.actions.setAuthMode(true);
  page.view.apiKey = "fixture-standalone-key";
  page.actions.keyChanged();
  assert.equal(await page.actions.saveApiKey(), true);
  assert.equal(page.model.auth.status, "ready");
  assert.equal(page.model.phase, "editing");
  assert.equal(page.model.uploads.audio.id, null);
  assert.equal(page.model.receipt, null);
  assert.deepEqual(page.calls.map(call => call.path), ["/api/session", "/api/api-key", "/api/save-api-key"]);
  assert.deepEqual(page.calls.at(-1)?.payload, { value: "fixture-standalone-key" });
  assert.equal(JSON.stringify(page.model).includes("fixture-standalone-key"), false);
  assert.equal(JSON.stringify(page.form).includes("fixture-standalone-key"), false);
  assert.equal(await page.actions.saveApiKey(), false);
  await page.actions.upload("audio", [audio]);
  await page.actions.validate();
  assert.equal(page.model.phase, "review");
  assert.equal(lastConfig(page).auth_mode, "api_key");
  assert.equal(JSON.stringify(lastConfig(page)).includes("fixture-standalone-key"), false);
  assert.equal(page.calls.filter(call => call.path === "/api/save-api-key").length, 1);
  assert.equal(page.calls.filter(call => call.path === "/api/confirm").length, 0);
});

test("单独保存Key失败保留输入与失败状态，不校验或自动重试", async () => {
  const page = harness({ "/api/save-api-key": () => { throw new UiError("不能写入", "auth_mode", 422); } });
  await page.actions.start();
  await page.actions.setAuthMode(true);
  page.view.apiKey = "fixture-standalone-key";
  page.actions.keyChanged();
  assert.equal(await page.actions.saveApiKey(), false);
  assert.equal(page.model.auth.status, "failed");
  assert.equal(page.model.phase, "editing");
  assert.equal(page.view.apiKey, "fixture-standalone-key");
  assert.equal(page.view.focus, "auth_mode");
  assert.equal(page.error.value?.field, "auth_mode");
  assert.deepEqual(page.calls.map(call => call.path), ["/api/session", "/api/api-key", "/api/save-api-key"]);
});

test("单独保存Key期间不重复保存或发起表单校验", async () => {
  const pending = deferred<Endpoints["/api/save-api-key"]>();
  const page = harness({ "/api/save-api-key": () => pending.promise });
  await page.actions.start();
  await page.actions.setAuthMode(true);
  page.view.apiKey = "fixture-standalone-key";
  page.actions.keyChanged();
  const saving = page.actions.saveApiKey();
  assert.equal(page.model.auth.status, "saving");
  assert.equal(await page.actions.saveApiKey(), false);
  await page.actions.validate();
  await page.actions.setAuthMode(false);
  assert.equal(page.form.useApiKey, true);
  assert.deepEqual(page.calls.map(call => call.path), ["/api/session", "/api/api-key", "/api/save-api-key"]);
  pending.resolve({ ok: true });
  assert.equal(await saving, true);
  assert.equal(page.model.auth.status, "ready");
  assert.equal(page.model.phase, "editing");
});

test("Key保存失败保留输入，停止校验且不自动重试", async () => {
  const page = harness({ "/api/save-api-key": () => { throw new UiError("不能写入", "auth_mode", 422); } });
  await addAudio(page);
  page.form.useApiKey = true;
  await page.actions.setAuthMode(page.form.useApiKey);
  page.view.apiKey = "fixture-key";
  page.actions.keyChanged();
  await page.actions.validate();
  assert.equal(page.model.phase, "editing");
  assert.equal(page.model.auth.status, "failed");
  assert.equal(page.view.apiKey, "fixture-key");
  assert.equal(page.error.value?.field, "auth_mode");
  assert.equal(page.calls.filter(call => call.path === "/api/save-api-key").length, 1);
  assert.equal(page.calls.filter(call => call.path === "/api/validate").length, 0);
});

test("Key写入期间保持认证方式与显示值一致，不重新读取旧Key", async () => {
  const pending = deferred<Endpoints["/api/save-api-key"]>();
  const page = harness({ "/api/save-api-key": () => pending.promise });
  await addAudio(page);
  await page.actions.setAuthMode(true);
  page.view.apiKey = "fixture-new-key";
  page.actions.keyChanged();
  const checking = page.actions.validate();
  assert.equal(availability(page.model).changeAuth, false);
  await page.actions.setAuthMode(false);
  await page.actions.setAuthMode(true);
  assert.equal(page.form.useApiKey, true);
  assert.equal(page.calls.filter(call => call.path === "/api/api-key").length, 1);
  pending.resolve({ ok: true });
  await checking;
  assert.equal(page.view.apiKey, "fixture-new-key");
  assert.equal(page.model.phase, "review");
});

test("检查保存Key期间修改表单会停止旧校验，重新检查复用保存结果", async () => {
  const pending = deferred<Endpoints["/api/save-api-key"]>();
  const page = harness({ "/api/save-api-key": () => pending.promise });
  await addAudio(page);
  await page.actions.setAuthMode(true);
  page.view.apiKey = "fixture-new-key";
  page.actions.keyChanged();
  const checking = page.actions.validate();
  page.form.diarizationEnabled = false;
  page.actions.changed();
  pending.resolve({ ok: true });
  await checking;
  assert.equal(page.model.auth.status, "ready");
  assert.equal(page.model.phase, "editing");
  assert.equal(page.model.preview, null);
  assert.equal(page.calls.filter(call => call.path === "/api/validate").length, 0);
  await page.actions.validate();
  assert.equal(page.model.phase, "review");
  assert.equal(lastConfig(page).diarization_enabled, false);
  assert.equal(page.calls.filter(call => call.path === "/api/save-api-key").length, 1);
});

test("空Key阻止检查；切回控制台后可继续", async () => {
  const page = harness();
  await addAudio(page);
  page.form.useApiKey = true;
  await page.actions.setAuthMode(page.form.useApiKey);
  await page.actions.validate();
  assert.equal(page.error.value?.field, "auth_mode");
  page.form.useApiKey = false;
  await page.actions.setAuthMode(page.form.useApiKey);
  await page.actions.validate();
  assert.equal(page.model.phase, "review");
});

test("修改Key或认证方式使旧预览失效", async () => {
  const page = harness({ "/api/api-key": () => ({ value: "fixture-key" }) });
  await addAudio(page);
  page.form.useApiKey = true;
  await page.actions.setAuthMode(page.form.useApiKey);
  await page.actions.validate();
  page.actions.keyChanged();
  assert.equal(page.model.preview, null);
  assert.equal(page.model.auth.status, "dirty");
  await page.actions.confirm();
  assert.equal(page.calls.filter(call => call.path === "/api/confirm").length, 0);
});

test("关闭说话人区分后不发送旧人数或非法数值", async () => {
  const page = harness();
  await addAudio(page);
  page.form.speaker = "3";
  await page.actions.validate();
  assert.equal(lastConfig(page).speaker_count, 3);
  page.form.diarizationEnabled = false;
  page.form.speaker = "1e";
  await page.actions.changed();
  await page.actions.validate();
  assert.equal(lastConfig(page).speaker_count, null);
});

test("不完整数字会报错，空白输入才使用自动人数", async () => {
  const page = harness();
  await addAudio(page);
  page.form.speaker = "1e";
  await page.actions.validate();
  assert.equal(page.error.value?.field, "speaker_count");
  page.form.speaker = "";
  await page.actions.validate();
  assert.equal(lastConfig(page).speaker_count, null);
});

test("人数和上下文使用服务端限制", async () => {
  const session = { ...description, limits: { ...limits, speaker_max: 4, context_chars: 3 } };
  const page = harness({ "/api/session": () => session });
  await addAudio(page);
  page.form.speaker = "5";
  assert.throws(() => configuration(page.model, page.form, session.limits, page.t), /2–4/);
  page.form.speaker = "";
  page.form.contextEnabled = true;
  page.form.context = "甲乙丙丁";
  await page.actions.validate();
  assert.match(page.error.value?.message ?? "", /3 个字符/);
  assert.match(page.error.value?.message ?? "", /当前 4 个字符/);
  assert.match(page.error.value?.message ?? "", /超出 1 个/);
  assert.equal(page.view.focus, "context");
  assert.equal(page.form.context, "甲乙丙丁");
});

test("仅空白上下文保留输入，指出内容为空并提示重新填写", async () => {
  const page = harness();
  await addAudio(page);
  page.form.contextEnabled = true;
  page.form.context = " \n\t";
  await page.actions.validate();
  assert.equal(page.form.context, " \n\t");
  assert.equal(page.view.focus, "context");
  assert.match(page.error.value?.message ?? "", /仅包含空白/);
  assert.match(page.error.value?.message ?? "", /当前 3 个字符/);
  assert.match(page.error.value?.message ?? "", /400 个字符/);
  assert.equal(page.calls.some(call => call.path === "/api/validate"), false);
});

test("音频扩展名使用服务端列表并支持大写", async () => {
  const page = harness({ "/api/session": () => ({ ...description, audio_suffixes: [".flac"] }) });
  await page.actions.start();
  await page.actions.upload("audio", [audio]);
  assert.equal(page.calls.filter(call => call.path === "/api/upload-audio").length, 0);
  await page.actions.upload("audio", [new File(["fixture"], "sample.FLAC")]);
  assert.equal(page.calls.filter(call => call.path === "/api/upload-audio").length, 1);
});

test("同类上传不并发，失败不自动重试", async () => {
  const pending = deferred<Endpoints["/api/upload-audio"]>();
  const page = harness({ "/api/upload-audio": () => pending.promise });
  await page.actions.start();
  const uploading = page.actions.upload("audio", [audio]);
  await page.actions.upload("audio", [audio]);
  assert.equal(availability(page.model).upload.hotwords, true);
  pending.reject(new Error("传输中断"));
  await uploading;
  assert.equal(page.model.uploads.audio.status, "failed");
  assert.equal(page.model.uploads.audio.id, null);
  assert.equal(page.calls.filter(call => call.path === "/api/upload-audio").length, 1);
});

test("热词与上下文同时提交，关闭增强后不发送旧输入", async () => {
  const page = harness();
  await addAudio(page);
  await page.actions.upload("hotwords", [words]);
  page.form.hotwordsEnabled = true;
  page.form.contextEnabled = true;
  page.form.context = "相关术语";
  await page.actions.validate();
  assert.equal(lastConfig(page).enhancement_mode, "both");
  assert.deepEqual(lastConfig(page).hotword_rows, hotwordRows);
  assert.equal(lastConfig(page).context, "相关术语");
  page.form.hotwordsEnabled = false;
  page.form.contextEnabled = false;
  await page.actions.changed();
  await page.actions.validate();
  assert.deepEqual(lastConfig(page).hotword_rows, []);
  assert.equal(lastConfig(page).context, "");
});

test("导入错误词表后保留原行号和原值，问题交给就地表格显示", async () => {
  const rows = [{ row: 4, text: 100, weight: 8 }, { row: 9, text: "合法术语", weight: 4 }];
  const issues = [{ row: 4, field: "text", message: "热词应为文本。" }, { row: 4, field: "weight", message: "权重应为1–5或50。" }];
  const page = harness({ "/api/upload-hotwords": () => ({ name: words.name, size_bytes: words.size, rows, issues, warnings: [] }) });
  await addAudio(page);
  page.form.hotwordsEnabled = true;
  await page.actions.upload("hotwords", [words]);
  assert.deepEqual(page.form.hotwordRows, rows);
  assert.deepEqual(page.model.hotwords.issues, issues);
  assert.equal(page.view.focus, "hotword_rows");
  assert.equal(page.model.uploads.hotwords.status, "ready");
  const before = page.calls.length;
  page.actions.changeHotword(4, "text", "修改后的术语");
  page.actions.changeHotword(4, "weight", "5");
  assert.equal(page.calls.length, before);
  assert.equal(page.model.hotwords.checked, false);
  await page.actions.checkHotwords();
  assert.equal(page.model.hotwords.checked, true);
  assert.deepEqual(page.model.hotwords.issues, []);
  assert.deepEqual(page.calls.at(-1)?.payload, { rows: [{ row: 4, text: "修改后的术语", weight: "5" }, rows[1]] });
});

test("手填热词无需Excel，删除行后保留其他行号，新增使用下一行号", async () => {
  const page = harness();
  await addAudio(page);
  page.form.hotwordsEnabled = true;
  page.actions.addHotword();
  page.actions.changeHotword(1, "text", "甲词");
  page.actions.addHotword();
  page.actions.changeHotword(2, "text", "乙词");
  page.actions.removeHotword(1);
  page.actions.addHotword();
  page.actions.changeHotword(3, "text", "丙词");
  await page.actions.validate();
  assert.deepEqual(lastConfig(page).hotword_rows, [{ row: 2, text: "乙词", weight: 4 }, { row: 3, text: "丙词", weight: 4 }]);
  assert.equal(page.calls.some(call => call.path === "/api/upload-hotwords"), false);
  const snapshot = page.model.preview?.configuration.hotword_rows;
  page.actions.changeHotword(2, "text", "修改词");
  assert.equal(page.model.preview, null);
  assert.equal(snapshot?.[0].text, "乙词");
});

test("编辑Excel异常单元格只清除该格的类型标记", async () => {
  const page = harness();
  await page.actions.start();
  page.form.hotwordRows = [{ row: 12, text: "2026-10-03", weight: "#N/A", invalid_fields: ["text", "weight"] }];
  page.actions.changeHotword(12, "text", "技术术语");
  assert.deepEqual(page.form.hotwordRows[0].invalid_fields, ["weight"]);
  page.actions.changeHotword(12, "weight", "4");
  assert.equal(page.form.hotwordRows[0].invalid_fields, undefined);
});

test("文件导入失败保留已编辑词条，结构错误携带行号", async () => {
  const page = harness({ "/api/upload-hotwords": () => {
    throw new UiError("表头不正确", "hotword_rows", 422, [{ row: 1, field: "header", message: "请使用text和weight列。" }]);
  } });
  await page.actions.start();
  page.actions.addHotword();
  page.actions.changeHotword(1, "text", "原有词条");
  await page.actions.upload("hotwords", [words]);
  assert.equal(page.form.hotwordRows[0].text, "原有词条");
  assert.equal(page.model.hotwords.issues[0].row, 1);
  assert.equal(page.error.value?.field, "hotword_rows");
  assert.equal(page.model.uploads.hotwords.status, "failed");
});

test("最终校验的热词错误同步到表格，编辑后可重新检查", async () => {
  const detail = { row: 2, field: "weight", message: "请修改权重。" };
  const page = harness({ "/api/validate": () => { throw new UiError("请修正热词。", "hotword_rows", 422, [detail]); } });
  await addAudio(page);
  page.form.hotwordsEnabled = true;
  await page.actions.upload("hotwords", [words]);
  await page.actions.validate();
  assert.equal(page.model.phase, "editing");
  assert.equal(page.view.focus, "hotword_rows");
  assert.deepEqual(page.model.hotwords.issues, [detail]);
  page.actions.changeHotword(2, "weight", "4");
  await page.actions.checkHotwords();
  assert.deepEqual(page.model.hotwords.issues, []);
});

test("词表检查期间阻止重复检查和覆盖输入，不冻结其他设置", async () => {
  const pending = deferred<Endpoints["/api/validate-hotwords"]>();
  const page = harness({ "/api/validate-hotwords": () => pending.promise });
  await page.actions.start();
  page.actions.addHotword();
  page.actions.changeHotword(1, "text", "现有词条");
  const checking = page.actions.checkHotwords();
  await page.actions.checkHotwords();
  page.actions.changeHotword(1, "text", "应忽略");
  await page.actions.upload("hotwords", [words]);
  assert.equal(page.form.hotwordRows[0].text, "现有词条");
  assert.equal(availability(page.model).editable, true);
  assert.equal(availability(page.model).validate, false);
  assert.equal(page.calls.filter(call => call.path === "/api/validate-hotwords").length, 1);
  pending.resolve({ issues: [], warnings: [], count: 1 });
  await checking;
  assert.equal(availability(page.model).editHotwords, true);
});

test("保存成功清空显示凭据，刷新只恢复回执", async () => {
  const page = harness();
  await preview(page);
  page.view.apiKey = "fixture-key";
  await page.actions.confirm();
  assert.deepEqual(page.model.receipt, receipt);
  assert.equal(page.view.apiKey, "");
  assert.equal(page.view.focus, "receipt");
  assert.equal(availability(page.model).editable, false);
  const refreshed = harness({ "/api/session": () => ({ ...description, confirmed: receipt }) });
  await refreshed.actions.start();
  await refreshed.actions.validate();
  assert.equal(refreshed.model.phase, "saved");
  assert.equal(refreshed.calls.length, 1);
});

test("刷新后的保存页可撤回未执行任务并恢复完整输入，重新保存使用新任务", async () => {
  const restored: Configuration = { auth_mode: "api_key", audio_upload_id: "restored-audio", diarization_enabled: false,
    enhancement_mode: "both", hotword_rows: [{ row: 11, text: "术语", weight: "4" }], context: " 完整参考文本\n",
    language_hint: "en", speaker_count: null, json_directory: "D:/approved-json", document_directory: "D:/approved-documents" };
  const page = harness({ "/api/session": () => ({ ...description, confirmed: receipt }),
    "/api/reopen": () => ({ ok: true, configuration: restored, audio: { upload_id: "restored-audio", name: "original.wav", size_bytes: 123 } }),
    "/api/api-key": () => ({ value: "fixture-restored-key" }), "/api/confirm": () => ({ ...receipt, job_id: "new-job" }) });
  await page.actions.start();
  await page.actions.reopen();
  assert.equal(page.model.phase, "editing");
  assert.equal(page.model.receipt, null);
  assert.equal(page.model.session?.confirmed, null);
  assert.equal(page.model.statusMessage, "reopened");
  assert.equal(page.view.apiKey, "fixture-restored-key");
  assert.equal(JSON.stringify(page.form).includes("fixture-restored-key"), false);
  assert.equal(page.form.context, " 完整参考文本\n");
  assert.equal(page.model.uploads.audio.name, "original.wav");
  assert.deepEqual(configuration(page.model, page.form, limits, page.t), restored);
  await page.actions.validate();
  await page.actions.confirm();
  assert.equal((page.model as Model).receipt?.job_id, "new-job");
  assert.deepEqual(page.calls.filter(call => call.path === "/api/reopen").map(call => call.payload), [{ job_id: "job" }]);
});

test("撤回请求等待中不会重复提交，执行中任务被拒绝时保留原回执", async () => {
  const pending = deferred<Endpoints["/api/reopen"]>();
  const page = harness({ "/api/session": () => ({ ...description, confirmed: receipt }), "/api/reopen": () => pending.promise });
  await page.actions.start();
  const reopening = page.actions.reopen();
  await page.actions.reopen();
  assert.equal(page.model.reopening, true);
  assert.equal(availability(page.model).editable, false);
  assert.equal(availability(page.model).reopen, false);
  pending.reject(new UiError("任务已经开始，请等待当前任务。", undefined, 409));
  await reopening;
  assert.equal(page.model.phase, "saved");
  assert.deepEqual(page.model.receipt, receipt);
  assert.match(page.error.value?.message ?? "", /已经开始/);
  assert.equal(page.calls.filter(call => call.path === "/api/reopen").length, 1);
});

test("语言切换保留表单但作废预览，且不会发起请求", async () => {
  const page = harness();
  await preview(page);
  page.form.context = "保留原文";
  const count = page.calls.length;
  page.setLanguage("en");
  assert.equal(page.form.context, "保留原文");
  assert.equal(page.model.phase, "editing");
  assert.equal(page.model.preview, null);
  assert.equal(page.model.statusMessage, "languageChanged");
  assert.equal(page.calls.length, count);
});

test("已保存状态的语言切换不会解锁任务", async () => {
  const page = harness();
  await preview(page);
  await page.actions.confirm();
  page.setLanguage("en");
  assert.equal(page.model.phase, "saved");
  assert.equal(availability(page.model).editable, false);
});

test("HTTP保留明确错误状态，无法解析结果时保持未知保存状态", async () => {
  const t: Translate = (key, values) => translate("en", key, values);
  const api = createApi(async () => new Response(JSON.stringify({ error: "Invalid context", field: "context" }), { status: 422 }), "fixture-token", () => "en", t);
  await assert.rejects(api.request("/api/validate", {}), (reason: unknown) => reason instanceof UiError && reason.httpStatus === 422 && reason.field === "context");
  const invalid = createApi(async () => new Response("invalid JSON", { status: 422 }), "", () => "en", t);
  const model = createModel();
  model.phase = "saving";
  try { await invalid.request("/api/confirm", {}); } catch (reason) { receiveSaveError(model, reason as UiError); }
  assert.equal(model.phase, "save_unknown");
});

test("上下文和热词HTTP传输保留特殊字符，语言只放请求头", async () => {
  const page = harness();
  await addAudio(page);
  page.form.contextEnabled = true;
  page.form.context = '--help a=b "中文"\r\nC:\\voice files\\\t😀𠮷 cafe\u0301 $HOME &|<>^%! `文本`';
  await page.actions.validate();
  const config = lastConfig(page);
  assert.equal(config.context, page.form.context);
  let sent: RequestInit | undefined;
  const api = createApi(async (_url, options) => { sent = options; return new Response(JSON.stringify(validation())); }, "fixture-token", () => "en", page.t);
  await api.request("/api/validate", config);
  assert.deepEqual(JSON.parse(sent?.body as string), config);
  assert.equal(new Headers(sent?.headers).get("Accept-Language"), "en");
  assert.equal(JSON.stringify(config).includes("fixture-token"), false);
});
