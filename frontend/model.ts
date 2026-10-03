import { UiError } from "./api";
import type { Translate } from "./i18n";
import type { Configuration, FormValues, Limits, Model, Receipt, ValidationResult } from "./types";

// 初始化页面阶段、上传引用、凭据读取和目录选择状态。
export function createModel(): Model {
  return {
    phase: "loading", revision: 0, preview: null, receipt: null, session: null,
    directories: { json: "default", document: "default" },
    uploads: {
      audio: { status: "empty", id: null, name: "", size: 0 },
      hotwords: { status: "empty", id: null, name: "", size: 0 },
    },
    hotwords: { issues: [], warnings: [], checking: false, checked: false, count: 0 }, reopening: false,
    auth: { revision: 0, status: "idle" }, picker: null, downloadingTemplate: false, statusMessage: "",
  };
}

// 从同一份页面状态推导事件与控件的操作权限。
export function availability(model: Model) {
  const editable = ["editing", "validating", "review"].includes(model.phase);
  const uploading = Object.values(model.uploads).some(upload => upload.status === "uploading");
  const pending = uploading || model.hotwords.checking || model.auth.status === "loading" || model.auth.status === "saving" || Boolean(model.picker);
  return {
    editable,
    validate: editable && model.phase !== "validating" && !pending,
    confirm: model.phase === "review" && Boolean(model.preview) && !pending,
    chooseDirectory: editable && !model.picker,
    cancelDirectory: Boolean(model.picker) && !model.picker?.cancelling,
    template: editable && !model.downloadingTemplate,
    editHotwords: editable && model.uploads.hotwords.status !== "uploading" && !model.hotwords.checking,
    reopen: model.phase === "saved" && Boolean(model.receipt) && !model.reopening,
    changeAuth: editable && model.auth.status !== "saving",
    changeLanguage: !pending && !model.downloadingTemplate && !model.reopening && model.phase !== "validating" && model.phase !== "saving",
    upload: {
      audio: editable && model.uploads.audio.status !== "uploading",
      hotwords: editable && model.uploads.hotwords.status !== "uploading" && !model.hotwords.checking,
    },
  };
}

// 输入变化后作废旧预览，使迟到的校验结果失效。
export function invalidatePreview(model: Model): void {
  if (!availability(model).editable) return;
  model.revision += 1;
  model.preview = null;
  model.statusMessage = "";
  if (model.phase !== "validating") model.phase = "editing";
}

// 按输入版本接收校验结果并保存确认所需的预览。
export function receiveValidation(model: Model, revision: number, result: ValidationResult, config: Configuration): boolean {
  if (revision !== model.revision) {
    model.phase = "editing";
    model.statusMessage = "changed";
    return false;
  }
  model.preview = { id: result.validation_id, summary: result.summary, configuration: config };
  model.phase = "review";
  return true;
}

// 根据确定的拒绝或未知结果，恢复编辑或阻止重复提交。
export function receiveSaveError(model: Model, error: UiError): void {
  model.preview = null;
  if (error.httpStatus !== undefined && error.httpStatus >= 400 && error.httpStatus < 500) {
    model.phase = "editing";
    model.revision += 1;
    model.statusMessage = "saveRejected";
  } else {
    model.phase = "save_unknown";
  }
}

// 保存任务回执并使未结束的凭据读取失效。
export function receiveReceipt(model: Model, receipt: Receipt): void {
  model.phase = "saved";
  model.preview = null;
  model.receipt = receipt;
  model.statusMessage = "";
  model.auth.revision += 1;
  model.auth.status = "idle";
}

// 根据普通表单与上传引用构建确认配置。
export function configuration(model: Model, form: FormValues, limits: Limits, t: Translate): Configuration {
  let speakerCount: number | null = null;
  if (form.diarizationEnabled && form.speaker !== "") {
    speakerCount = Number(form.speaker);
    if (!Number.isInteger(speakerCount) || speakerCount < limits.speaker_min || speakerCount > limits.speaker_max) {
      throw new UiError(t("invalidSpeaker", { min: limits.speaker_min, max: limits.speaker_max }), "speaker_count");
    }
  }
  return {
    auth_mode: form.useApiKey ? "api_key" : "console",
    audio_upload_id: model.uploads.audio.id, diarization_enabled: form.diarizationEnabled,
    enhancement_mode: form.hotwordsEnabled ? (form.contextEnabled ? "both" : "hotwords") : (form.contextEnabled ? "context" : "none"),
    hotword_rows: form.hotwordsEnabled ? form.hotwordRows.map(row => ({ ...row, ...(row.invalid_fields ? { invalid_fields: [...row.invalid_fields] } : {}) })) : [],
    context: form.contextEnabled ? form.context : "", language_hint: form.language || null,
    speaker_count: speakerCount, json_directory: model.directories.json, document_directory: model.directories.document,
  };
}

// 检查必填输入并保留超长上下文的全部原文供用户修改。
export function checkRequiredInputs(config: Configuration, limits: Limits, t: Translate): void {
  if (!config.audio_upload_id) throw new UiError(t("missingAudio"), "audio_upload_id");
  if (["both", "hotwords"].includes(config.enhancement_mode) && !config.hotword_rows.length) {
    throw new UiError(t("missingHotwords"), "hotword_rows");
  }
  if (["both", "context"].includes(config.enhancement_mode)) {
    const length = Array.from(config.context).length;
    if (!config.context.trim()) throw new UiError(t("missingContext", { length, count: limits.context_chars }), "context");
    if (length > limits.context_chars) {
      throw new UiError(t("contextTooLong", { length, count: limits.context_chars, excess: length - limits.context_chars }), "context");
    }
  }
}
