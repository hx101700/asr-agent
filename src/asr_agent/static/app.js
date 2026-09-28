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
    throw new Error("无法连接本地服务。请检查 Codex 中的程序是否仍在运行；页面不会自动重试。");
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("本地服务返回了无法读取的响应，请返回 Codex 检查运行状态。");
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
  for (const detail of error.details || []) {
    const item = document.createElement("li");
    const location = [detail.row ? `第 ${detail.row} 行` : "", detail.field || ""].filter(Boolean).join(" · ");
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
  element("validate-button").textContent = uploading ? "正在传入本机…" : validating ? "正在检查…" : "检查配置 →";
  element("confirm-button").textContent = confirming ? "正在保存…" : confirmed ? "配置已保存" : "确认并保存配置";
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
  element("action-title").textContent = "下一步：检查配置";
  element("confirmation-help").textContent = "检查音频和识别选项，通过后核对并保存。";
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
  document.querySelector(".summary-hint").textContent = defaults ? "默认：项目 outputs 目录" : "已自定义，检查后显示完整路径";
}

async function updateAuthStatus() {
  const mode = selected("auth_mode");
  element("api-key-help").hidden = mode !== "api_key";
  element("auth-status").textContent = mode === "api_key" ? "正在检查项目 .env 配置…" : "正在读取本地状态…";
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
  element(`${kind}-action`).textContent = kind === "audio" ? "点击选择音频" : "选择或拖入热词表";
  if (files.length !== 1) {
    input.value = "";
    status.textContent = "请选择一个文件，当前未传入任何新文件。";
    showError(new Error("每个位置只支持一个文件，请重新选择。"));
    return;
  }
  const file = files[0];
  const allowedExtensions = input.accept.split(",");
  if (!allowedExtensions.some((extension) => file.name.toLowerCase().endsWith(extension))) {
    input.value = "";
    status.textContent = "文件格式不符合要求，请重新选择。";
    showError(new Error(kind === "hotwords" ? "热词表需要使用 .xlsx 文件，请重新选择。" : "当前文件扩展名不在支持的音频格式中，请重新选择。"));
    return;
  }
  upload.busy = true;
  input.disabled = true;
  element(`${kind}-progress`).hidden = false;
  element(`${kind}-dropzone`).setAttribute("aria-busy", "true");
  status.textContent = `正在传入本机：${file.name}…`;
  updateButtons();
  try {
    const result = await request(`/api/upload-${kind}`, undefined, file);
    upload.id = result.upload_id;
    upload.name = result.name;
    status.textContent = `已就绪 · ${result.name} · ${(result.size_bytes / 1024 / 1024).toFixed(2)} MiB`;
    element(`${kind}-action`).textContent = kind === "audio" ? "更换音频文件" : "更换热词表";
    element(`${kind}-dropzone`).classList.add("is-ready");
  } catch (error) {
    input.value = "";
    status.textContent = "传入本机失败，未自动重试。请重新选择文件后再试。";
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
    none: "不使用",
    hotwords: `即时热词 · ${summary.enhancement.count} 个`,
    context: `上下文 · ${summary.enhancement.context_chars} 字符`,
    both: `即时热词 ${summary.enhancement.count} 个 + 上下文 ${summary.enhancement.context_chars} 字符`,
  };
  detailRow(details, "音频文件", uploads.audio.name || audio.name);
  detailRow(details, "音频时长", durationText(audio.duration_seconds));
  detailRow(details, "源文件大小", `${(audio.size_bytes / 1024 / 1024).toFixed(2)} MiB`);
  detailRow(details, "格式 / 声道", `${audio.format || audio.name.split(".").pop().toUpperCase()} / ${audio.channels} 声道`);
  detailRow(details, "采样率", `${audio.sample_rate.toLocaleString("zh-CN")} Hz`);
  detailRow(details, "连接方式", summary.auth_mode === "api_key" ? "API Key（项目 .env）" : "百炼控制台登录");
  detailRow(details, "区分说话人", config.diarization_enabled ? "开启" : "关闭");
  detailRow(details, "识别增强", enhancementLabels[summary.enhancement.mode]);
  if (config.enhancement_mode === "hotwords" || config.enhancement_mode === "both") detailRow(details, "热词表", uploads.hotwords.name);
  detailRow(details, "计划 JSON 目录", summary.json_directory);
  detailRow(details, "计划成品目录", summary.document_directory);
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
  element("review-state").textContent = "本地检查通过";
  element("review-state").classList.add("is-ready");
  element("action-title").textContent = "请核对配置与处理提示";
  element("confirmation-help").textContent = "确认后仅保存配置，尚不发送阿里云。";
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
  element("confirmation-help").textContent = "本次配置已保存在本机。文件尚未发送阿里云，也未开始转写。";
  const details = element("receipt-details");
  details.replaceChildren();
  detailRow(details, "本地任务编号", receipt.job_id);
  detailRow(details, "配置文件", receipt.config_path);
  if (receipt.json_directory) detailRow(details, "计划 JSON 目录", receipt.json_directory);
  if (receipt.document_directory) detailRow(details, "计划成品目录", receipt.document_directory);
  element("receipt-panel").hidden = false;
  document.querySelector("h1").textContent = "本次配置已保存";
  document.querySelector(".intro-description").textContent = "配置已准备好，可返回 Codex 继续。";
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
    const error = new Error("上下文超过 400 个字符，请修改后重新检查。内容不会被自动截断。");
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
      showStatus("检查期间配置已更改，请按当前内容重新检查。");
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
      element("confirmation-help").textContent = "本次确认被拒绝，请根据提示修改并重新检查配置。";
    } else {
      element("review-state").textContent = "保存未确认";
      element("review-state").classList.remove("is-ready");
      element("action-title").textContent = "保存结果未知，请返回 Codex";
      element("confirmation-help").textContent = "保存未获确认。请返回 Codex 检查配置文件，勿重复提交。";
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
    if (!response.ok) throw new Error("热词模板下载失败，请检查本地服务后手动再试。");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = "asr-hotwords-template.xlsx";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch {
    showError(new Error("热词模板下载失败，请检查本地服务后手动再试。"));
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
