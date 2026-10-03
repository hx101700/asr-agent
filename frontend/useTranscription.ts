import { nextTick, reactive, shallowRef } from "vue";
import { UiError, uiError } from "./api";
import { availability, checkRequiredInputs, configuration, createModel, invalidatePreview, receiveReceipt, receiveSaveError, receiveValidation } from "./model";
import type { Translate } from "./i18n";
import type { Api, DirectoryKind, FormValues, HotwordField, ReopenResult, UploadKind } from "./types";

export interface ViewEffects {
  focus(target: string): void;
  setApiKey(value: string): void;
  getApiKey(): string;
  download(blob: Blob): void;
}

// 编排页面用例，状态由 Vue 渲染，浏览器操作由视图提供。
export function useTranscription(api: Api, view: ViewEffects, t: Translate, makeRequestId: () => string = () => crypto.randomUUID()) {
  const model = reactive(createModel());
  const form = reactive<FormValues>({ useApiKey: false, diarizationEnabled: true, hotwordsEnabled: false,
    contextEnabled: false, context: "", language: "", speaker: "", hotwordRows: [] });
  const error = shallowRef<UiError | null>(null);

  // 保存可见错误并将焦点移到相应输入。
  function fail(reason: unknown, field?: string): void {
    error.value = uiError(reason, t("failed"), field);
    if (error.value.field === "hotword_rows") {
      model.hotwords.issues = error.value.details;
      model.hotwords.checked = false;
    }
    view.focus(error.value.field ?? "error-panel");
  }

  // 读取当前凭据方式，在视图中显示 Key 并丢弃迟到结果。
  async function updateAuth(): Promise<void> {
    const revision = ++model.auth.revision;
    view.setApiKey("");
    if (!form.useApiKey) { model.auth.status = "idle"; return; }
    model.auth.status = "loading";
    try {
      const result = await api.request("/api/api-key", {});
      if (revision !== model.auth.revision) return;
      view.setApiKey(result.value);
      model.auth.status = result.value ? "ready" : "dirty";
    } catch (reason) {
      if (revision !== model.auth.revision) return;
      model.auth.status = "failed";
      fail(reason, "auth_mode");
    }
  }

  // 保存显示组件中的 Key，并按凭据版本更新保存状态。
  async function persistApiKey(): Promise<boolean> {
    const revision = model.auth.revision;
    const value = view.getApiKey();
    if (!value) throw new UiError(t("keyNotReady"), "auth_mode");
    model.auth.status = "saving";
    try { await api.request("/api/save-api-key", { value }); }
    catch (reason) {
      if (revision === model.auth.revision) model.auth.status = "failed";
      throw uiError(reason, t("failed"), "auth_mode");
    }
    if (revision !== model.auth.revision) return false;
    model.auth.status = "ready";
    return true;
  }

  // 将服务端保留的确认快照恢复为编辑表单，并重新读取所选凭据。
  async function restoreForm(result: ReopenResult): Promise<void> {
    const config = result.configuration;
    Object.assign(form, { useApiKey: config.auth_mode === "api_key", diarizationEnabled: config.diarization_enabled,
      hotwordsEnabled: ["hotwords", "both"].includes(config.enhancement_mode),
      contextEnabled: ["context", "both"].includes(config.enhancement_mode), context: config.context,
      language: config.language_hint ?? "", speaker: config.speaker_count === null ? "" : String(config.speaker_count),
      hotwordRows: config.hotword_rows });
    model.uploads.audio = { status: "ready", id: result.audio.upload_id, name: result.audio.name, size: result.audio.size_bytes };
    model.uploads.hotwords = { status: "empty", id: null, name: "", size: 0 };
    model.directories = { json: config.json_directory, document: config.document_directory };
    Object.assign(model.hotwords, { issues: [], warnings: [], checked: false, count: 0 });
    model.receipt = null;
    if (model.session) model.session.confirmed = null;
    model.phase = "editing";
    invalidatePreview(model);
    model.statusMessage = "reopened";
    await nextTick();
    await updateAuth();
    if (model.auth.status !== "failed") view.focus("config-fields");
  }

  const actions = {
    // 标记凭据输入已修改，使当前预览失效。
    keyChanged(): void {
      if (!availability(model).changeAuth) return;
      model.auth.revision += 1;
      model.auth.status = "dirty";
      error.value = null;
      invalidatePreview(model);
    },

    // 将当前 Key 单独保存到工作目录并返回保存结果。
    async saveApiKey(): Promise<boolean> {
      if (!form.useApiKey || !availability(model).changeAuth || !["dirty", "failed"].includes(model.auth.status)) return false;
      error.value = null;
      try { return await persistApiKey(); }
      catch (reason) { fail(reason); return false; }
    },

    // 加载本机会话并恢复确认回执或已撤回的表单。
    async start(): Promise<void> {
      try {
        model.session = await api.request("/api/session");
        if (model.session.confirmed) {
          receiveReceipt(model, model.session.confirmed);
          view.setApiKey("");
          view.focus("receipt");
        } else if (model.session.reopened) {
          await restoreForm(model.session.reopened);
        } else {
          model.phase = "editing";
        }
      } catch (reason) { model.phase = "unavailable"; fail(reason); }
    },

    // 切换认证方式并读取或清空密码输入框。
    async setAuthMode(useApiKey: boolean): Promise<void> {
      if (!availability(model).changeAuth) return;
      form.useApiKey = useApiKey;
      error.value = null;
      invalidatePreview(model);
      await updateAuth();
    },

    // 输入改变时作废旧预览及对应的错误说明。
    changed(): void {
      if (!availability(model).editable) return;
      error.value = null;
      invalidatePreview(model);
    },

    // 更新热词单元格并标记词表需要重新检查。
    changeHotword(rowNumber: number, field: HotwordField, value: string): void {
      if (!availability(model).editHotwords) return;
      const row = form.hotwordRows.find(entry => entry.row === rowNumber);
      if (!row) return;
      row[field] = value;
      if (row.invalid_fields) {
        row.invalid_fields = row.invalid_fields.filter(invalid => invalid !== field);
        if (!row.invalid_fields.length) delete row.invalid_fields;
      }
      model.hotwords.checked = false;
      actions.changed();
    },

    // 在词表末尾添加带独立行号的可编辑词条。
    addHotword(): void {
      if (!availability(model).editHotwords) return;
      const row = Math.max(0, ...form.hotwordRows.map(entry => entry.row)) + 1;
      form.hotwordRows.push({ row, text: "", weight: 4 });
      model.hotwords.checked = false;
      actions.changed();
    },

    // 删除选定词条并保留其他词条的来源行号。
    removeHotword(rowNumber: number): void {
      if (!availability(model).editHotwords) return;
      form.hotwordRows = form.hotwordRows.filter(entry => entry.row !== rowNumber);
      model.hotwords.issues = model.hotwords.issues.filter(issue => issue.row !== rowNumber);
      model.hotwords.checked = false;
      actions.changed();
    },

    // 使用服务端同一套词表规则检查当前编辑内容。
    async checkHotwords(): Promise<void> {
      if (!availability(model).editHotwords) return;
      error.value = null;
      model.hotwords.checking = true;
      const revision = model.revision;
      try {
        const result = await api.request("/api/validate-hotwords", { rows: form.hotwordRows });
        if (revision !== model.revision) return;
        Object.assign(model.hotwords, { issues: result.issues, warnings: result.warnings, count: result.count, checked: true });
        if (result.issues.length) view.focus("hotword_rows");
      } catch (reason) { fail(reason, "hotword_rows"); }
      finally { model.hotwords.checking = false; }
    },

    // 保留用户输入，并使上一种语言生成的预览与错误失效。
    languageChanged(): void {
      if (!availability(model).changeLanguage) return;
      error.value = null;
      model.hotwords.issues = [];
      model.hotwords.warnings = [];
      model.hotwords.checked = false;
      if (model.preview) {
        invalidatePreview(model);
        model.statusMessage = "languageChanged";
      }
    },

    // 将单个文件传入本机服务并保存会话引用。
    async upload(kind: UploadKind, files: readonly File[]): Promise<void> {
      const session = model.session;
      if (!session || !availability(model).upload[kind] || !files.length) return;
      error.value = null;
      invalidatePreview(model);
      model.uploads[kind] = { status: "empty", id: null, name: "", size: 0 };
      const upload = model.uploads[kind];
      const field = kind === "audio" ? "audio_upload_id" : "hotword_rows";
      try {
        if (files.length !== 1) throw new UiError(t("singleFile"), field);
        const file = files[0];
        const suffixes = kind === "audio" ? session.audio_suffixes : [".xlsx"];
        if (!suffixes.some(extension => file.name.toLowerCase().endsWith(extension))) {
          throw new UiError(t(kind === "hotwords" ? "wrongHotwords" : "unsupportedFormat"), field);
        }
        const limit = session.limits[kind === "audio" ? "audio_bytes" : "hotwords_bytes"];
        if (file.size > limit) throw new UiError(t("tooLarge", { size: limit / 1_000_000 }), field);
        upload.status = "uploading";
        upload.name = file.name;
        if (kind === "audio") {
          const result = await api.request("/api/upload-audio", undefined, file);
          Object.assign(upload, { status: "ready", id: result.upload_id, name: result.name, size: result.size_bytes });
        } else {
          const result = await api.request("/api/upload-hotwords", undefined, file);
          form.hotwordRows = result.rows;
          Object.assign(model.hotwords, { issues: result.issues, warnings: result.warnings, checked: false, count: 0 });
          Object.assign(upload, { status: "ready", name: result.name, size: result.size_bytes });
          view.focus("hotword_rows");
        }
      } catch (reason) {
        upload.status = "failed";
        fail(reason, field);
      }
    },

    // 等待系统目录选择结果，选定后更新已批准的保存位置。
    async selectDirectory(kind: DirectoryKind): Promise<void> {
      if (!availability(model).chooseDirectory) return;
      const id = makeRequestId();
      model.picker = { id, kind, cancelling: false };
      let failure: unknown;
      try {
        const result = await api.request("/api/select-directory", { kind, picker_id: id });
        if (model.picker?.id !== id) return;
        if (!result.cancelled) {
          model.directories[kind] = result.path;
          error.value = null;
          invalidatePreview(model);
        }
      } catch (reason) { failure = reason; }
      finally { if (model.picker?.id === id) model.picker = null; }
      if (failure) fail(failure, `${kind}_directory`);
    },

    // 取消当前目录选择，等待原请求结束后恢复按钮。
    async cancelDirectory(): Promise<void> {
      const picker = model.picker;
      if (!picker || !availability(model).cancelDirectory) return;
      picker.cancelling = true;
      try { await api.request("/api/cancel-directory", { picker_id: picker.id }); }
      catch (reason) {
        if (model.picker?.id === picker.id) { picker.cancelling = false; fail(reason); }
      }
    },

    // 恢复指定输出目录的默认位置。
    resetDirectory(kind: DirectoryKind): void {
      if (!availability(model).chooseDirectory) return;
      model.directories[kind] = "default";
      error.value = null;
      invalidatePreview(model);
    },

    // 返回表单修改设置。
    edit(): void {
      if (!availability(model).editable) return;
      invalidatePreview(model);
      view.focus("config-fields");
    },

    // 检查必填内容并取得本次输入版本的服务端预览。
    async validate(): Promise<void> {
      const session = model.session;
      if (!session || !availability(model).validate) return;
      error.value = null;
      invalidatePreview(model);
      let config;
      try {
        config = configuration(model, form, session.limits, t);
        checkRequiredInputs(config, session.limits, t);
      } catch (reason) { fail(reason); return; }
      const revision = model.revision;
      model.phase = "validating";
      if (form.useApiKey && model.auth.status !== "ready") {
        try {
          const saved = await persistApiKey();
          if (!saved || revision !== model.revision) {
            model.phase = "editing";
            return;
          }
        } catch (reason) {
          // Key保存期间凭据不可改动，其他表单变化不能使本次凭据错误过期。
          model.phase = "editing";
          fail(reason);
          return;
        }
      }
      try {
        const result = await api.request("/api/validate", config);
        if (receiveValidation(model, revision, result, config)) {
          Object.assign(model.hotwords, { issues: [], warnings: [], checked: form.hotwordsEnabled, count: result.summary.enhancement.count });
          view.focus("review");
        }
      } catch (reason) {
        model.phase = "editing";
        if (revision === model.revision) fail(reason);
      }
    },

    // 保存当前预览，并区分明确拒绝与保存结果未知。
    async confirm(): Promise<void> {
      const preview = model.preview;
      if (!preview || !availability(model).confirm) return;
      model.phase = "saving";
      error.value = null;
      try {
        const receipt = await api.request("/api/confirm", { validation_id: preview.id });
        receiveReceipt(model, receipt);
        view.setApiKey("");
        view.focus("receipt");
      } catch (reason) {
        const problem = uiError(reason, t("failed"));
        receiveSaveError(model, problem);
        fail(problem);
      }
    },

    // 撤回尚未执行的任务，恢复该任务的完整输入供重新确认。
    async reopen(): Promise<void> {
      if (!availability(model).reopen || !model.receipt) return;
      model.reopening = true;
      error.value = null;
      try {
        const result = await api.request("/api/reopen", { job_id: model.receipt.job_id });
        await restoreForm(result);
      } catch (reason) { fail(reason); }
      finally { model.reopening = false; }
    },

    // 下载热词模板，保留其它表单操作。
    async downloadTemplate(): Promise<void> {
      if (!availability(model).template) return;
      model.downloadingTemplate = true;
      error.value = null;
      try { view.download(await api.template()); }
      catch (reason) { fail(reason); }
      finally { model.downloadingTemplate = false; }
    },
  };
  return { model, form, error, actions };
}
