function fileSize(bytes) {
  return bytes < 1_000_000 ? `${(bytes / 1000).toFixed(1)} KB` : `${(bytes / 1_000_000).toFixed(2)} MB`;
}

function durationText(seconds) {
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  return [hours ? `${hours} 小时` : "", minutes ? `${minutes} 分` : "", `${total % 60} 秒`].filter(Boolean).join(" ");
}

export function createView(document) {
  const element = (id) => document.getElementById(id);
  const form = element("config-form");
  let errorField = null;
  let errorBox = null;
  let errorTarget = null;
  let renderedPreview = null;
  let renderedReceipt = null;
  let controls = { editable: false, upload: { audio: false, hotwords: false } };
  let session = null;

  function detailRow(parent, label, value) {
    const row = document.createElement("div");
    const title = document.createElement("dt");
    const text = document.createElement("dd");
    title.textContent = label;
    text.textContent = String(value);
    row.append(title, text);
    parent.append(row);
    return row;
  }

  function focusRegion(id, block = "start") {
    element(id).focus({ preventScroll: true });
    element(id).scrollIntoView({ block });
  }

  function renderDraft(model, values) {
    // 摘要直接派生自表单与上传状态，不保存第二份配置，也不把选择当作校验成功。
    const details = element("draft-details");
    details.replaceChildren();
    const uploadLabel = (upload) => ({
      empty: "尚未添加", uploading: "正在添加…", failed: "添加失败", ready: upload.name,
    })[upload.status];
    let speaker = "人数自动判断";
    if (values.speaker.badInput) speaker = "人数待检查";
    else if (values.speaker.value) speaker = `${values.speaker.value} 人（参考）`;
    const context = values.context.trim() ? `${Array.from(values.context).length} 字符` : "待填写";
    detailRow(details, "音频文件", uploadLabel(model.uploads.audio));
    detailRow(details, "音频语言", values.language ? new Map(session.languages).get(values.language) : "自动识别");
    detailRow(details, "区分发言人", values.diarizationEnabled ? `开启 · ${speaker}` : "关闭");
    detailRow(details, "热词增强", values.hotwordsEnabled ? uploadLabel(model.uploads.hotwords) : "未开启");
    detailRow(details, "上下文增强", values.contextEnabled ? context : "未开启");
    detailRow(details, "账号连接", values.useApiKey ? "API Key" : "百炼账号登录");
  }

  function renderPreview(preview, uploads) {
    if (preview === renderedPreview) return;
    renderedPreview = preview;
    if (!preview) return;
    element("review-scroll").scrollTop = 0;
    const { summary, configuration: config } = preview;
    const audio = summary.audio;
    const details = element("review-details");
    details.replaceChildren();
    const enhancementLabels = {
      none: "未开启", hotwords: `热词增强 · ${summary.enhancement.count} 个词`,
      context: `上下文增强 · ${summary.enhancement.context_chars} 字符`,
      both: `热词增强 ${summary.enhancement.count} 个词 + 上下文增强 ${summary.enhancement.context_chars} 字符`,
    };
    detailRow(details, "音频文件", uploads.audio.name || audio.name);
    detailRow(details, "音频时长", durationText(audio.duration_seconds));
    detailRow(details, "文件大小", fileSize(audio.size_bytes));
    detailRow(details, "格式 / 声道", `${audio.format || audio.name.split(".").pop().toUpperCase()} / ${audio.channels} 声道`);
    detailRow(details, "采样率", `${audio.sample_rate.toLocaleString("zh-CN")} Hz`);
    detailRow(details, "账号连接", summary.auth_mode === "api_key" ? "API Key" : "百炼账号登录");
    detailRow(details, "区分发言人", config.diarization_enabled ? "开启" : "关闭");
    detailRow(details, "音频语言", config.language_hint ? new Map(session.languages).get(config.language_hint) : "自动识别");
    if (config.diarization_enabled) detailRow(details, "发言人数", config.speaker_count === null ? "自动判断" : `${config.speaker_count} 人（参考）`);
    detailRow(details, "精度增强", enhancementLabels[summary.enhancement.mode]);
    if (["hotwords", "both"].includes(config.enhancement_mode)) detailRow(details, "热词文件", uploads.hotwords.name);
    detailRow(details, "JSON 保存位置", summary.json_directory).classList.add("path-detail");
    detailRow(details, "文档保存位置", summary.document_directory).classList.add("path-detail");
    const warnings = element("review-warnings");
    warnings.replaceChildren();
    for (const message of summary.warnings || []) {
      const paragraph = document.createElement("p");
      paragraph.textContent = message;
      warnings.append(paragraph);
    }
    warnings.hidden = warnings.childElementCount === 0;
  }

  function renderReceipt(receipt) {
    if (!receipt || receipt === renderedReceipt) return;
    renderedReceipt = receipt;
    const details = element("receipt-details");
    details.replaceChildren();
    detailRow(details, "设置编号", receipt.job_id);
    detailRow(details, "设置文件", receipt.config_path);
    if (receipt.json_directory) detailRow(details, "JSON 保存位置", receipt.json_directory);
    if (receipt.document_directory) detailRow(details, "文档保存位置", receipt.document_directory);
    document.querySelector("h1").textContent = "设置完成";
    document.querySelector(".intro-description").textContent = "本次转写设置已保存。";
  }

  const view = {
    initialize(description) {
      session = description;
      element("model-name").textContent = session.model;
      element("region-name").textContent = ["cn-beijing", "beijing"].includes(session.region) ? "中国内地 · 北京" : session.region;
      for (const kind of ["json", "document"]) element(`${kind}-directory`).placeholder = session.output_defaults[kind];
      for (const [code, name] of session.languages) {
        const option = document.createElement("option");
        option.value = code;
        option.textContent = name;
        element("language-hint").append(option);
      }
      element("speaker-count").min = session.limits.speaker_min;
      element("speaker-count").max = session.limits.speaker_max;
      element("speaker-help").textContent = `可指定 ${session.limits.speaker_min}–${session.limits.speaker_max} 人，供识别参考。`;
      element("hotwords-file-limit").textContent = `或拖拽至此处 · .xlsx · 最大 ${session.limits.hotwords_bytes / 1_000_000} MB`;
      element("context-help").textContent = `包含录音中可能出现的具体词语，最多 ${session.limits.context_chars} 字符。`;
    },

    readForm() {
      return {
        useApiKey: element("use-api-key").checked,
        diarizationEnabled: element("diarization-enabled").checked,
        hotwordsEnabled: element("hotwords-enabled").checked,
        contextEnabled: element("context-enabled").checked,
        context: element("context").value,
        language: element("language-hint").value,
        speaker: { value: element("speaker-count").value, badInput: element("speaker-count").validity.badInput },
      };
    },

    render(model, available) {
      controls = available;
      const saved = model.phase === "saved";
      const saving = model.phase === "saving";
      const unknown = model.phase === "save_unknown";
      const hasPreview = Boolean(model.preview);
      const values = view.readForm();
      // 所有 disabled/hidden 属性集中从流程状态和当前表单推导，不作为业务状态反读。
      element("config-fields").disabled = !available.editable;
      element("config-fields").hidden = saved;
      element("review-card").hidden = saved;
      element("receipt-panel").hidden = !saved;
      element("action-bar").hidden = saved;
      document.querySelector(".workspace").classList.toggle("is-confirmed", saved);
      document.querySelector(".skip-link").hidden = saved;
      document.querySelector(".review-column").setAttribute("aria-labelledby", saved ? "receipt-heading" : "review-heading");
      element("validate-button").disabled = !available.validate;
      element("validate-button").hidden = hasPreview || saved;
      element("validate-button").textContent = available.uploading ? "正在添加文件…" : model.phase === "validating" ? "正在检查…" : "检查并预览";
      element("confirm-button").disabled = !available.confirm;
      element("confirm-button").hidden = !hasPreview || saved;
      element("confirm-button").textContent = saving ? "正在保存…" : "保存设置";
      element("edit-button").hidden = !hasPreview || saved;
      element("edit-button").disabled = !available.editable;
      element("show-review").hidden = hasPreview || saved;
      element("show-review").disabled = !available.editable;
      document.querySelectorAll("[data-section-target]").forEach((button) => { button.disabled = !available.editable; });
      element("download-template").disabled = !available.template;
      element("speaker-count").disabled = !available.editable || !values.diarizationEnabled;
      element("speaker-fields").hidden = !values.diarizationEnabled;
      element("diarization-help").hidden = !values.diarizationEnabled;
      element("hotwords-fields").hidden = !values.hotwordsEnabled;
      element("context-fields").hidden = !values.contextEnabled;
      element("api-key-fields").hidden = !values.useApiKey;
      element("api-key-toggle").disabled = !available.editable || model.auth.status !== "ready";
      element("api-key-value").placeholder = model.auth.status === "loading" ? "正在读取…" : model.auth.status === "failed" ? "未配置 API Key" : "";
      element("directory-wait").hidden = !model.picker;
      element("cancel-directory").disabled = !available.cancelDirectory;
      element("cancel-directory").textContent = model.picker?.cancelling ? "正在取消…" : "取消等待";
      for (const kind of ["json", "document"]) {
        const isDefault = model.directories[kind] === "outputs";
        element(`${kind}-directory`).value = isDefault ? "" : model.directories[kind];
        element(`${kind}-directory`).title = isDefault ? element(`${kind}-directory`).placeholder : model.directories[kind];
        element(`${kind}-browse`).disabled = !available.chooseDirectory;
        element(`${kind}-browse`).textContent = model.picker?.kind === kind ? "请在弹窗中选择…" : "选择文件夹";
        element(`${kind}-reset`).disabled = !available.chooseDirectory;
        element(`${kind}-reset`).hidden = isDefault;
      }
      for (const kind of ["audio", "hotwords"]) {
        const upload = model.uploads[kind];
        const ready = upload.status === "ready";
        element(`${kind}-file`).disabled = !available.upload[kind];
        element(`${kind}-progress`).hidden = upload.status !== "uploading";
        element(`${kind}-dropzone`).setAttribute("aria-busy", String(upload.status === "uploading"));
        element(`${kind}-dropzone`).classList.toggle("is-ready", ready);
        element(`${kind}-action`).textContent = ready ? (kind === "audio" ? "更换音频" : "更换热词文件") : (kind === "audio" ? "选择音频文件" : "选择 Excel 文件");
        const messages = {
          empty: "尚未选择文件", failed: "文件添加失败，请重新选择。未自动重试。",
          uploading: `正在添加：${upload.name}…`, ready: `已添加 · ${upload.name} · ${fileSize(upload.size)}`,
        };
        element(`${kind}-file-status`).textContent = messages[upload.status];
      }
      if (session) {
        const count = Array.from(values.context).length;
        const overLimit = count > session.limits.context_chars;
        element("context-count").textContent = `${count} / ${session.limits.context_chars}`;
        element("context-count").classList.toggle("over-limit", overLimit);
        element("context").setAttribute("aria-invalid", String(overLimit || errorField === element("context")));
      }
      element("review-content").hidden = !hasPreview;
      element("review-draft").hidden = hasPreview;
      const reviewLabels = { saved: "已保存", save_unknown: "保存结果待确认", saving: "正在保存", validating: "正在检查" };
      element("review-state").textContent = reviewLabels[model.phase] || (hasPreview ? "检查通过" : "待检查");
      element("review-state").classList.toggle("is-ready", hasPreview && !unknown);
      element("action-title").textContent = unknown ? "暂时无法确认保存结果" : hasPreview ? "请确认本次转写设置" : "下一步：核对转写信息";
      element("confirmation-help").textContent = unknown ? "请返回 Codex 查看保存情况，避免重复提交。" : hasPreview ? "保存设置不会启动转写。" : "检查文件规格、增强选项和保存位置。";
      element("page-status").textContent = model.statusMessage;
      element("page-status").hidden = !model.statusMessage;
      const currentStep = saved ? 2 : hasPreview || unknown ? 1 : 0;
      ["step-config", "step-review", "step-saved"].forEach((id, index) => {
        element(id).classList.toggle("is-current", index === currentStep);
        element(id).classList.toggle("is-done", index < currentStep);
        if (index === currentStep) element(id).setAttribute("aria-current", "step");
        else element(id).removeAttribute("aria-current");
      });
      renderPreview(model.preview, model.uploads);
      if (session && !hasPreview && !saved) renderDraft(model, values);
      renderReceipt(model.receipt);
    },

    clearError() {
      element("error-panel").hidden = true;
      element("error-details").replaceChildren();
      if (errorField) {
        const descriptions = (errorField.getAttribute("aria-describedby") || "").split(" ").filter((id) => id !== errorBox.id);
        errorField.setAttribute("aria-describedby", descriptions.join(" "));
        errorField = null;
      }
      if (errorBox) { errorBox.hidden = true; errorBox.replaceChildren(); errorBox = null; }
      if (errorTarget) { errorTarget.classList.remove("needs-attention"); errorTarget = null; }
      form.querySelectorAll('[aria-invalid="true"]').forEach((input) => input.removeAttribute("aria-invalid"));
    },

    showError(error) {
      view.clearError();
      const fields = {
        audio_upload_id: ["audio-file", "audio-error", "audio-dropzone"],
        audio_path: ["audio-file", "audio-error", "audio-dropzone"],
        hotwords_upload_id: ["hotwords-file", "hotwords-error", "hotwords-dropzone"],
        hotwords_path: ["hotwords-file", "hotwords-error", "hotwords-dropzone"],
        context: ["context", "context-error", "context"],
        speaker_count: ["speaker-count", "speaker-error", "speaker-count"],
        language_hint: ["language-hint", "language-error", "language-hint"],
        json_directory: ["json-browse", "json-error", "json-directory"],
        document_directory: ["document-browse", "document-error", "document-directory"],
        auth_mode: ["use-api-key", "auth-error", "auth-fields"],
      };
      const target = fields[error.field];
      const details = target ? document.createElement("ul") : element("error-details");
      const labels = { text: "热词", weight: "权重", header: "表头", row: "内容" };
      for (const detail of error.details || []) {
        const item = document.createElement("li");
        const location = [detail.row ? `第 ${detail.row} 行` : "", labels[detail.field] || detail.field || ""].filter(Boolean).join(" · ");
        item.textContent = `${location ? location + "：" : ""}${detail.message || "内容不符合要求"}`;
        details.append(item);
      }
      details.hidden = details.childElementCount === 0;
      if (target) {
        errorField = element(target[0]);
        errorBox = element(target[1]);
        errorTarget = element(target[2]);
        errorBox.textContent = error.message;
        if (details.childElementCount) errorBox.append(details);
        errorBox.hidden = false;
        errorField.setAttribute("aria-invalid", "true");
        errorField.setAttribute("aria-describedby", `${errorField.getAttribute("aria-describedby") || ""} ${errorBox.id}`.trim());
        errorField.focus({ preventScroll: true });
        errorTarget.scrollIntoView({ block: "center" });
        errorTarget.classList.add("needs-attention");
      } else {
        element("error-message").textContent = error.message;
        element("error-panel").hidden = false;
        element("error-panel").focus();
      }
    },

    fileExtensions: (kind) => element(`${kind}-file`).accept.split(","),
    clearFile: (kind) => { element(`${kind}-file`).value = ""; },
    clearApiKey() {
      element("api-key-value").value = "";
      element("api-key-value").type = "password";
      element("api-key-toggle").textContent = "显示";
    },
    setApiKey: (value) => { element("api-key-value").value = value; },
    focusForm: () => focusRegion("config-fields"),
    focusPreview: () => focusRegion("review-card"),
    focusReceipt: () => focusRegion("receipt-panel"),
    download(blob) {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "asr-hotwords-template.xlsx";
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },

    bind(actions) {
      form.addEventListener("input", (event) => {
        if (!["checkbox", "file", "select-one"].includes(event.target.type)) actions.changed(event.target.id);
      });
      form.addEventListener("change", (event) => {
        if (["checkbox", "file", "select-one"].includes(event.target.type)) actions.changed(event.target.id, event.target.files);
      });
      form.addEventListener("submit", (event) => { event.preventDefault(); actions.validate(); });
      element("confirm-button").addEventListener("click", actions.confirm);
      element("edit-button").addEventListener("click", actions.edit);
      element("show-review").addEventListener("click", () => view.focusPreview());
      document.querySelectorAll("[data-section-target]").forEach((button) => {
        button.addEventListener("click", () => {
          if (controls.editable) focusRegion(button.dataset.sectionTarget);
        });
      });
      element("cancel-directory").addEventListener("click", actions.cancelDirectory);
      element("download-template").addEventListener("click", actions.downloadTemplate);
      for (const kind of ["json", "document"]) {
        element(`${kind}-browse`).addEventListener("click", () => actions.selectDirectory(kind));
        element(`${kind}-reset`).addEventListener("click", () => actions.resetDirectory(kind));
      }
      element("api-key-toggle").addEventListener("click", () => {
        const input = element("api-key-value");
        input.type = input.type === "password" ? "text" : "password";
        element("api-key-toggle").textContent = input.type === "password" ? "显示" : "隐藏";
      });
      for (const kind of ["audio", "hotwords"]) {
        const zone = element(`${kind}-dropzone`);
        zone.addEventListener("dragover", (event) => {
          event.preventDefault();
          if (controls.upload[kind]) zone.classList.add("drag-over");
        });
        zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
        zone.addEventListener("drop", (event) => {
          event.preventDefault();
          zone.classList.remove("drag-over");
          // drop 不受 fieldset 的禁用机制约束，使用同一派生能力判断。
          if (!controls.upload[kind]) return;
          if (event.dataTransfer.files.length === 1) element(`${kind}-file`).files = event.dataTransfer.files;
          actions.upload(kind, event.dataTransfer.files);
        });
      }
      new ResizeObserver(([entry]) => {
        document.documentElement.style.setProperty("--action-height", `${entry.target.getBoundingClientRect().height}px`);
      }).observe(element("action-bar"));
    },
  };
  return view;
}
