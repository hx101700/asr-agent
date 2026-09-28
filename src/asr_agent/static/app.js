"use strict";

const element = (id) => document.getElementById(id);
const form = element("config-form");
const fragment = new URLSearchParams(window.location.hash.slice(1));
const sessionToken = fragment.get("token") || "";
// 令牌只保留在本页内存，避免进入历史记录、后续分享的链接或浏览器存储。
window.history.replaceState(null, "", window.location.pathname + window.location.search);

let revision = 0;
let validationId = null;
let validating = false;
let confirming = false;
let confirmed = false;
let errorField = null;
const uploads = {
  audio: { id: null, name: "", busy: false },
  hotwords: { id: null, name: "", busy: false },
};

function selected(name) {
  return form.querySelector(`input[name="${name}"]:checked`).value;
}

async function request(path, payload, file) {
  const headers = sessionToken ? { "X-ASR-Token": sessionToken } : {};
  const options = { headers, cache: "no-store", credentials: "same-origin" };
  if (file) {
    options.method = "POST";
    headers["Content-Type"] = "application/octet-stream";
    headers["X-File-Name"] = encodeURIComponent(file.name);
    options.body = file;
  } else if (payload !== undefined) {
    options.method = "POST";
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(payload);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("连接已断开，请返回 Codex 检查应用是否仍在运行。本次操作不会自动重试。");
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("暂时无法获取操作结果，请返回 Codex 查看详情。");
  }
  if (!response.ok || data.ok === false) {
    const error = new Error(data.error || "本次操作未完成，请检查输入后手动再试。");
    error.httpStatus = response.status;
    error.field = data.field;
    error.details = data.details;
    throw error;
  }
  return data;
}

function clearError() {
  element("error-panel").hidden = true;
  element("error-details").replaceChildren();
  if (errorField) {
    const descriptions = (errorField.getAttribute("aria-describedby") || "").split(" ").filter((id) => id !== "error-message");
    errorField.setAttribute("aria-describedby", descriptions.join(" "));
    errorField = null;
  }
  element("error-field-link").hidden = true;
  form.querySelectorAll('[aria-invalid="true"]').forEach((input) => input.removeAttribute("aria-invalid"));
}

function showError(error) {
  element("error-message").textContent = error.message;
  const details = element("error-details");
  details.replaceChildren();
  const fieldLabels = { text: "热词", weight: "权重", header: "表头", row: "内容" };
  for (const detail of error.details || []) {
    const item = document.createElement("li");
    const location = [detail.row ? `第 ${detail.row} 行` : "", fieldLabels[detail.field] || detail.field || ""].filter(Boolean).join(" · ");
    item.textContent = `${location ? location + "：" : ""}${detail.message || "内容不符合要求"}`;
    details.append(item);
  }
  details.hidden = details.childElementCount === 0;
  const fieldIds = {
    audio_upload_id: "audio-file", hotwords_upload_id: "hotwords-file",
    audio_path: "audio-file", hotwords_path: "hotwords-file", context: "context",
    json_directory: "json-directory", document_directory: "document-directory",
  };
  const input = error.field === "auth_mode" ? form.querySelector('input[name="auth_mode"]:checked') : element(fieldIds[error.field]);
  if (input) {
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", `${input.getAttribute("aria-describedby") || ""} error-message`.trim());
    errorField = input;
    element("error-field-link").hidden = false;
  }
  element("error-panel").hidden = false;
  element("error-panel").focus();
}

function showStatus(message) {
  element("page-status").textContent = message;
  element("page-status").hidden = !message;
}

function updateButtons() {
  const uploading = uploads.audio.busy || uploads.hotwords.busy;
  const locked = element("config-fields").disabled;
  element("validate-button").disabled = locked || uploading || validating || confirming || confirmed;
  element("validate-button").hidden = Boolean(validationId) || confirmed;
  element("confirm-button").disabled = locked || !validationId || uploading || validating || confirming || confirmed;
  element("confirm-button").hidden = !validationId || confirmed;
  element("edit-button").hidden = !validationId || confirmed;
  element("edit-button").disabled = locked || confirming;
  element("validate-button").textContent = uploading ? "正在添加文件…" : validating ? "正在检查…" : "检查并预览";
  element("confirm-button").textContent = confirming ? "正在保存…" : confirmed ? "已保存" : "保存设置";
}

function setStep(current) {
  ["step-config", "step-review", "step-saved"].forEach((id, index) => {
    const step = element(id);
    step.classList.toggle("is-current", index === current);
    step.classList.toggle("is-done", index < current);
    if (index === current) step.setAttribute("aria-current", "step");
    else step.removeAttribute("aria-current");
  });
}

function invalidatePreview() {
  if (confirmed) return;
  revision += 1;
  validationId = null;
  element("review-content").hidden = true;
  element("review-placeholder").hidden = false;
  element("review-state").textContent = "待检查";
  element("review-state").classList.remove("is-ready");
  element("action-title").textContent = "下一步：核对转写信息";
  element("confirmation-help").textContent = "检查文件规格、增强选项和保存位置。";
  setStep(0);
  showStatus("");
  updateButtons();
}

function updateContextCount() {
  const count = Array.from(element("context").value).length;
  element("context-count").textContent = `${count} / 400`;
  element("context-count").classList.toggle("over-limit", count > 400);
  element("context").setAttribute("aria-invalid", String(count > 400));
}

function updateEnhancement() {
  element("hotwords-fields").hidden = !element("hotwords-enabled").checked;
  element("context-fields").hidden = !element("context-enabled").checked;
  updateContextCount();
}

function updateOutputHint() {
  const defaults = element("json-directory").value.trim() === "outputs" && element("document-directory").value.trim() === "outputs";
  document.querySelector(".summary-hint").textContent = defaults ? "默认：项目内 outputs 文件夹" : "已自定义保存位置";
}

async function updateAuthStatus() {
  const mode = selected("auth_mode");
  element("api-key-help").hidden = mode !== "api_key";
  element("auth-status").textContent = mode === "api_key" ? "正在检查 API Key 设置…" : "正在加载账号设置…";
  try {
    const status = await request("/api/auth-status", { auth_mode: mode });
    if (selected("auth_mode") !== mode) return;
    element("auth-status").textContent = status.message;
  } catch (error) {
    if (selected("auth_mode") === mode) element("auth-status").textContent = error.message;
  }
}

async function uploadFile(kind, files) {
  const upload = uploads[kind];
  const input = element(`${kind}-file`);
  const status = element(`${kind}-file-status`);
  if (element("config-fields").disabled || confirming || confirmed || upload.busy || !files.length) return;
  clearError();
  invalidatePreview();
  upload.id = null;
  upload.name = "";
  element(`${kind}-dropzone`).classList.remove("is-ready");
  element(`${kind}-action`).textContent = kind === "audio" ? "选择音频文件" : "选择或拖入 Excel 文件";
  if (files.length !== 1) {
    input.value = "";
    status.textContent = "未添加文件，请每次选择 1 个文件。";
    showError(new Error("一次只能添加 1 个文件，请重新选择。"));
    return;
  }
  const file = files[0];
  const allowedExtensions = input.accept.split(",");
  if (!allowedExtensions.some((extension) => file.name.toLowerCase().endsWith(extension))) {
    input.value = "";
    status.textContent = "文件格式不符合要求，请重新选择。";
    showError(new Error(kind === "hotwords" ? "请选择 .xlsx 格式的热词文件。" : "暂不支持此文件格式，请选择支持的音频文件。"));
    return;
  }
  upload.busy = true;
  input.disabled = true;
  element(`${kind}-progress`).hidden = false;
  element(`${kind}-dropzone`).setAttribute("aria-busy", "true");
  status.textContent = `正在添加：${file.name}…`;
  updateButtons();
  try {
    const result = await request(`/api/upload-${kind}`, undefined, file);
    upload.id = result.upload_id;
    upload.name = result.name;
    status.textContent = `已添加 · ${result.name} · ${(result.size_bytes / 1024 / 1024).toFixed(2)} MiB`;
    element(`${kind}-action`).textContent = kind === "audio" ? "更换音频" : "更换热词文件";
    element(`${kind}-dropzone`).classList.add("is-ready");
  } catch (error) {
    input.value = "";
    status.textContent = "文件添加失败，请重新选择。未自动重试。";
    showError(error);
  } finally {
    upload.busy = false;
    element(`${kind}-progress`).hidden = true;
    element(`${kind}-dropzone`).setAttribute("aria-busy", "false");
    input.disabled = confirmed || confirming;
    updateButtons();
  }
}

function configuration() {
  const hotwords = element("hotwords-enabled").checked;
  const context = element("context-enabled").checked;
  const mode = hotwords && context ? "both" : hotwords ? "hotwords" : context ? "context" : "none";
  return {
    auth_mode: selected("auth_mode"),
    audio_upload_id: uploads.audio.id,
    diarization_enabled: element("diarization-enabled").checked,
    enhancement_mode: mode,
    hotwords_upload_id: hotwords ? uploads.hotwords.id : null,
    context: context ? element("context").value : "",
    json_directory: element("json-directory").value.trim(),
    document_directory: element("document-directory").value.trim(),
  };
}

function detailRow(parent, label, value) {
  const row = document.createElement("div");
  const title = document.createElement("dt");
  const text = document.createElement("dd");
  title.textContent = label;
  text.textContent = String(value);
  row.append(title, text);
  parent.append(row);
}

function durationText(seconds) {
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = total % 60;
  return [hours ? `${hours} 小时` : "", minutes ? `${minutes} 分` : "", `${rest} 秒`].filter(Boolean).join(" ");
}

function showPreview(summary, config) {
  const audio = summary.audio;
  const details = element("review-details");
  details.replaceChildren();
  const enhancementLabels = {
    none: "未开启",
    hotwords: `热词增强 · ${summary.enhancement.count} 个词`,
    context: `上下文增强 · ${summary.enhancement.context_chars} 字符`,
    both: `热词增强 ${summary.enhancement.count} 个词 + 上下文增强 ${summary.enhancement.context_chars} 字符`,
  };
  detailRow(details, "音频文件", uploads.audio.name || audio.name);
  detailRow(details, "音频时长", durationText(audio.duration_seconds));
  detailRow(details, "文件大小", `${(audio.size_bytes / 1024 / 1024).toFixed(2)} MiB`);
  detailRow(details, "格式 / 声道", `${audio.format || audio.name.split(".").pop().toUpperCase()} / ${audio.channels} 声道`);
  detailRow(details, "采样率", `${audio.sample_rate.toLocaleString("zh-CN")} Hz`);
  detailRow(details, "账号连接", summary.auth_mode === "api_key" ? "API Key" : "百炼账号登录");
  detailRow(details, "区分发言人", config.diarization_enabled ? "开启" : "关闭");
  detailRow(details, "精度增强", enhancementLabels[summary.enhancement.mode]);
  if (config.enhancement_mode === "hotwords" || config.enhancement_mode === "both") detailRow(details, "热词文件", uploads.hotwords.name);
  detailRow(details, "JSON 保存位置", summary.json_directory);
  detailRow(details, "文档保存位置", summary.document_directory);
  const warnings = element("review-warnings");
  warnings.replaceChildren();
  const messages = [...(summary.warnings || [])];
  for (const message of messages) {
    const paragraph = document.createElement("p");
    paragraph.textContent = message;
    warnings.append(paragraph);
  }
  warnings.hidden = messages.length === 0;
  element("review-content").hidden = false;
  element("review-placeholder").hidden = true;
  element("review-state").textContent = "检查通过";
  element("review-state").classList.add("is-ready");
  element("action-title").textContent = "请确认本次转写设置";
  element("confirmation-help").textContent = "保存设置不会启动转写。";
  setStep(1);
  // 窄屏下摘要位于表单之后，检查成功应把阅读位置带到摘要而非直接跳到保存按钮。
  element("review-card").focus({ preventScroll: true });
  element("review-card").scrollIntoView({ block: "start" });
}

function showReceipt(receipt) {
  confirmed = true;
  validationId = null;
  element("config-fields").disabled = true;
  element("config-fields").hidden = true;
  document.querySelector(".workspace").classList.add("is-confirmed");
  element("review-card").hidden = true;
  element("action-bar").hidden = true;
  document.querySelector(".skip-link").hidden = true;
  document.querySelector(".review-column").setAttribute("aria-labelledby", "receipt-heading");
  element("review-state").textContent = "已保存";
  element("review-placeholder").hidden = true;
  element("confirmation-help").textContent = "转写设置已保存，尚未开始转写。";
  const details = element("receipt-details");
  details.replaceChildren();
  detailRow(details, "设置编号", receipt.job_id);
  detailRow(details, "设置文件", receipt.config_path);
  if (receipt.json_directory) detailRow(details, "JSON 保存位置", receipt.json_directory);
  if (receipt.document_directory) detailRow(details, "文档保存位置", receipt.document_directory);
  element("receipt-panel").hidden = false;
  document.querySelector("h1").textContent = "设置完成";
  document.querySelector(".intro-description").textContent = "本次转写设置已保存。";
  setStep(2);
  showStatus("");
  updateButtons();
  element("receipt-panel").focus();
}

element("error-field-link").addEventListener("click", () => {
  if (!errorField) return;
  const section = errorField.closest("details");
  if (section) section.open = true;
  errorField.focus({ preventScroll: true });
  (errorField.closest(".file-dropzone") || errorField).scrollIntoView({ block: "center" });
});

element("edit-button").addEventListener("click", () => {
  if (element("config-fields").disabled) return;
  invalidatePreview();
  element("config-fields").focus({ preventScroll: true });
  element("config-fields").scrollIntoView({ block: "start" });
});

form.addEventListener("input", () => {
  if (element("config-fields").disabled) return;
  clearError();
  invalidatePreview();
  updateContextCount();
  updateOutputHint();
});
form.addEventListener("change", (event) => {
  if (element("config-fields").disabled) return;
  invalidatePreview();
  if (event.target.name === "auth_mode") updateAuthStatus();
  if (event.target.id === "hotwords-enabled" || event.target.id === "context-enabled") updateEnhancement();
  if (event.target.id === "audio-file") uploadFile("audio", event.target.files);
  if (event.target.id === "hotwords-file") uploadFile("hotwords", event.target.files);
});

for (const kind of ["audio", "hotwords"]) {
  const dropzone = element(`${kind}-dropzone`);
  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    if (!element("config-fields").disabled && !uploads[kind].busy) dropzone.classList.add("drag-over");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("drag-over");
    // 原生fieldset不会阻止drop事件；保存结果未知或会话未就绪时也必须禁止拖入。
    if (element("config-fields").disabled) return;
    // 只接收浏览器提供的文件对象，不从拖入的文本或URL推断本地路径。
    if (!confirmed && !confirming && !uploads[kind].busy && event.dataTransfer.files.length === 1) {
      element(`${kind}-file`).files = event.dataTransfer.files;
    }
    uploadFile(kind, event.dataTransfer.files);
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (element("config-fields").disabled || uploads.audio.busy || uploads.hotwords.busy || validating || confirming || confirmed) return;
  clearError();
  invalidatePreview();
  const config = configuration();
  if ((config.enhancement_mode === "context" || config.enhancement_mode === "both") && Array.from(config.context).length > 400) {
    const error = new Error("参考文本超过 400 个字符，请精简后重新检查。已保留您输入的全部内容。");
    error.field = "context";
    showError(error);
    return;
  }
  const currentRevision = revision;
  validating = true;
  updateButtons();
  try {
    const result = await request("/api/validate", config);
    if (currentRevision !== revision) {
      showStatus("设置已修改，请重新检查并预览。");
      return;
    }
    validationId = result.validation_id;
    showPreview(result.summary, config);
  } catch (error) {
    if (currentRevision === revision) showError(error);
  } finally {
    validating = false;
    updateButtons();
  }
});

element("confirm-button").addEventListener("click", async () => {
  if (element("config-fields").disabled || !validationId || uploads.audio.busy || uploads.hotwords.busy || validating || confirming || confirmed) return;
  confirming = true;
  // 保存过程中冻结表单，确保确认的内容始终对应刚才校验的配置。
  element("config-fields").disabled = true;
  clearError();
  updateButtons();
  try {
    const receipt = await request("/api/confirm", { validation_id: validationId });
    showReceipt(receipt);
  } catch (error) {
    showError(error);
    validationId = null;
    if (error.httpStatus >= 400 && error.httpStatus < 500) {
      // 明确拒绝没有保存成功，可以修改输入；网络结果未知则继续冻结。
      element("config-fields").disabled = false;
      invalidatePreview();
      element("confirmation-help").textContent = "未能保存，请按提示修改后重新检查。";
    } else {
      element("review-state").textContent = "保存结果待确认";
      element("review-state").classList.remove("is-ready");
      element("action-title").textContent = "暂时无法确认保存结果";
      element("confirmation-help").textContent = "请返回 Codex 查看保存情况，避免重复提交。";
    }
  } finally {
    confirming = false;
    updateButtons();
  }
});

element("download-template").addEventListener("click", async () => {
  const button = element("download-template");
  button.disabled = true;
  clearError();
  try {
    const response = await fetch("/api/hotwords-template", { headers: sessionToken ? { "X-ASR-Token": sessionToken } : {}, cache: "no-store", credentials: "same-origin" });
    if (!response.ok) throw new Error("模板下载失败，请确认应用仍在运行后重试。");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = "asr-hotwords-template.xlsx";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch {
    showError(new Error("模板下载失败，请确认应用仍在运行后重试。"));
  } finally {
    button.disabled = confirmed;
  }
});

async function start() {
  try {
    const session = await request("/api/session");
    element("model-name").textContent = session.model;
    element("region-name").textContent = session.region === "cn-beijing" || session.region === "beijing" ? "中国内地 · 北京" : session.region;
    element("auth-status").textContent = session.auth.console.message;
    if (session.confirmed) {
      showReceipt(session.confirmed);
      return;
    }
    element("config-fields").disabled = false;
    updateEnhancement();
    updateButtons();
  } catch (error) {
    showError(error);
  }
}

start();

// 底部操作区的高度会随窗口宽度和文字缩放变化，预留同等空间，避免遮住最后一项。
new ResizeObserver(([entry]) => {
  document.documentElement.style.setProperty("--action-height", `${entry.target.getBoundingClientRect().height}px`);
}).observe(element("action-bar"));
