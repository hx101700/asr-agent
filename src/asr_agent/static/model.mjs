// 初始化页面阶段、上传、凭据读取及目录选择状态。
export function createModel() {
  return {
    phase: "loading", revision: 0, preview: null, receipt: null, session: null,
    directories: { json: "outputs", document: "outputs" },
    uploads: {
      audio: { status: "empty", id: null, name: "", size: 0 },
      hotwords: { status: "empty", id: null, name: "", size: 0 },
    },
    auth: { revision: 0, status: "idle" },
    picker: null, downloadingTemplate: false, statusMessage: "",
  };
}

// 从当前状态推导可用操作，供事件处理和控件渲染共同使用。
export function availability(model) {
  const editable = ["editing", "validating", "review"].includes(model.phase);
  const uploading = Object.values(model.uploads).some((upload) => upload.status === "uploading");
  const pending = uploading || model.auth.status === "loading" || Boolean(model.picker);
  return {
    editable, uploading,
    validate: editable && model.phase !== "validating" && !pending,
    confirm: model.phase === "review" && Boolean(model.preview) && !pending,
    chooseDirectory: editable && !model.picker,
    cancelDirectory: Boolean(model.picker) && !model.picker.cancelling,
    template: editable && !model.downloadingTemplate,
    upload: Object.fromEntries(Object.entries(model.uploads).map(([kind, upload]) =>
      [kind, editable && upload.status !== "uploading"])),
  };
}

// 输入变化后作废旧预览，并递增版本以识别迟到的校验结果。
export function invalidatePreview(model) {
  if (!availability(model).editable) return;
  model.revision += 1;
  model.preview = null;
  model.statusMessage = "";
  // 输入可以在校验期间继续修改，但旧请求结束前不发起第二次校验。
  if (model.phase !== "validating") model.phase = "editing";
}

// 按输入版本接收校验结果并保存预览快照。
export function receiveValidation(model, revision, result, configuration) {
  if (revision !== model.revision) {
    model.phase = "editing";
    model.statusMessage = "设置已修改，请重新检查并预览。";
    return false;
  }
  model.preview = { id: result.validation_id, summary: result.summary, configuration };
  model.phase = "review";
  return true;
}

// 根据保存错误恢复编辑或切换为结果待确认状态。
export function receiveSaveError(model, error) {
  model.preview = null;
  if (error.httpStatus >= 400 && error.httpStatus < 500) {
    model.phase = "editing";
    model.revision += 1;
    model.statusMessage = "未能保存，请按提示修改后重新检查。";
  } else {
    // 网络中断和不明确的服务端错误不能证明未保存，必须持续禁止重复提交。
    model.phase = "save_unknown";
  }
}

// 保存服务端回执并结束编辑，同时使未完成的凭据读取失效。
export function receiveReceipt(model, receipt) {
  model.phase = "saved";
  model.preview = null;
  model.receipt = receipt;
  model.statusMessage = "";
  model.auth.revision += 1;
  model.auth.status = "idle";
}

// 将错误绑定到表单字段，供视图提示并聚焦对应位置。
export function fieldError(message, field) {
  return Object.assign(new Error(message), { field });
}

// 根据表单与会话状态生成服务端校验参数。
export function configuration(model, form) {
  const limits = model.session.limits;
  let speakerCount = null;
  if (form.diarizationEnabled) {
    // number 输入在不完整数字时 value 可能为空，必须先检查 badInput。
    if (form.speaker.badInput) throw fieldError("请输入完整的发言人数", "speaker_count");
    if (form.speaker.value !== "") {
      speakerCount = Number(form.speaker.value);
      if (!Number.isInteger(speakerCount) || speakerCount < limits.speaker_min || speakerCount > limits.speaker_max) {
        throw fieldError(`请输入 ${limits.speaker_min}–${limits.speaker_max} 的整数，或留空自动判断`, "speaker_count");
      }
    }
  }
  return {
    auth_mode: form.useApiKey ? "api_key" : "console",
    audio_upload_id: model.uploads.audio.id,
    diarization_enabled: form.diarizationEnabled,
    enhancement_mode: form.hotwordsEnabled ? (form.contextEnabled ? "both" : "hotwords") : (form.contextEnabled ? "context" : "none"),
    hotwords_upload_id: form.hotwordsEnabled ? model.uploads.hotwords.id : null,
    context: form.contextEnabled ? form.context : "",
    language_hint: form.language || null,
    speaker_count: speakerCount,
    json_directory: model.directories.json,
    document_directory: model.directories.document,
  };
}

// 检查音频、增强选项的必填内容和上下文长度。
export function checkRequiredInputs(config, limits) {
  if (!config.audio_upload_id) throw fieldError("请选择音频文件", "audio_upload_id");
  if (["both", "hotwords"].includes(config.enhancement_mode) && !config.hotwords_upload_id) {
    throw fieldError("请选择热词文件", "hotwords_upload_id");
  }
  if (["both", "context"].includes(config.enhancement_mode)) {
    if (!config.context.trim()) throw fieldError("请填写参考文本", "context");
    if (Array.from(config.context).length > limits.context_chars) {
      throw fieldError(`参考文本超过 ${limits.context_chars} 个字符，请精简后重新检查。已保留您输入的全部内容。`, "context");
    }
  }
}
