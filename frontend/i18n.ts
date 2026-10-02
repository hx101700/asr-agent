import type { Language } from "./types";

const en = {
  title: "Audio transcription", brand: "Alibaba Cloud Model Studio", preview: "Preview",
  intro: "Turn meeting, interview, and lecture recordings into text.",
  region: "China (Beijing)", language: "Interface language", theme: "Appearance",
  system: "System", light: "Light", dark: "Dark", skip: "Skip to transcription settings",
  stepConfigure: "Configure", stepReview: "Review", stepSaved: "Save settings",
  beforeStart: "Save your settings, then return to Codex to authorize the upload and start transcription.",
  audioHeading: "Add audio", oneFile: "One file at a time", chooseAudio: "Choose an audio file",
  replaceAudio: "Replace audio", drag: "or drag it here",
  formatLimits: "Supported formats and limits",
  audioLimits: "Select a file up to {size} GB and {hours} hours. The audio uploaded to Alibaba Cloud must be no larger than {upload} GB. If channels are merged, the converted file must meet this limit. Supported formats: {formats}.",
  emptyUpload: "No file selected", uploading: "Adding {name}…", uploadReady: "{name} · {size}",
  uploadFailed: "The file could not be added. Select it again to try manually.",
  settings: "Transcription settings", audioLanguage: "Audio language", automatic: "Auto-detect",
  diarization: "Speaker diarization", diarizationHelp: "Label speech from different speakers in the transcript.",
  monoHelp: "Multi-channel audio is merged into a mono copy. Your original file is preserved.",
  speakers: "Number of speakers", optional: "Optional", speakerHint: "Enter {min}–{max} as a hint, or leave blank for automatic detection.",
  enhancement: "Improve recognition accuracy", enhancementHint: "Use hotwords and context together or separately.",
  hotwords: "Add hotwords", hotwordsHelp: "Improve recognition of names, product names, and technical terms.",
  hotwordFile: "Hotword list", chooseHotwords: "Choose an Excel file", replaceHotwords: "Replace hotword list",
  template: "Download template", hotwordLimit: ".xlsx · Up to {size} MB",
  hotwordHelp: "Enter hotwords and weights in the template. Up to {count} hotwords.",
  context: "Add context", contextHelp: "Provide relevant terms, dialogue, or reference material.",
  reference: "Reference text", contextHint: "Include specific terms that may occur in the recording. Up to {count} characters.",
  contextPlaceholder: "For example: This technical review covers Kubernetes, container orchestration, canary releases, and service rollback.",
  savingLocations: "Save locations", rawResult: "Original result (JSON)", documents: "Transcripts",
  chooseFolder: "Choose folder", resetFolder: "Reset", choosingFolder: "Choose in the dialog…",
  folderWaiting: "Choose a folder in the system dialog. You can cancel if the dialog is not visible.",
  cancelWaiting: "Cancel", cancelling: "Cancelling…", timestamps: "Timestamps included",
  useKey: "Use a standard API Key", consoleDefault: "Otherwise, use Console login.",
  enterKey: "Enter your Model Studio API key (Beijing)",
  keySaveHelp: "Check and preview saves this key locally to .asr-transcription/.env in your working folder.",
  loadingKey: "Reading…",
  review: "Transcription details", pending: "Not checked", validated: "Ready to save", validating: "Checking…",
  saving: "Saving…", unknown: "Save result unknown",
  audioFile: "Audio file", duration: "Duration", fileSize: "File size", formatChannels: "Format / channels",
  channel: "{count} channel", channels: "{count} channels", sampleRate: "Sample rate", connection: "Authentication",
  consoleLogin: "Console login", enabled: "On", disabled: "Off", notAdded: "Not added",
  speakerValue: "{count} speakers (hint)", character: "{count} character", characters: "{count} characters",
  hotwordCount: "{count} hotword", hotwordsCount: "{count} hotwords", hotwordsLabel: "Hotwords", contextLabel: "Context",
  draftHelp: "Check your settings to see the duration, channels, and file details.",
  modelRegion: "Model and region", quickLinks: "Jump to section", jsonLocation: "JSON folder", documentLocation: "Transcript folder",
  next: "Next: review transcription settings", nextHelp: "Check the audio, recognition options, and save locations.",
  reviewTitle: "Review and save", reviewHelp: "Saving settings does not start transcription.",
  unknownTitle: "The save result could not be confirmed", unknownHelp: "Return to Codex to check the result before submitting again.",
  check: "Check and preview", save: "Save settings", edit: "Edit settings", viewDetails: "View details",
  savedTitle: "Your settings are saved", savedHelp: "You can close this page. Return to Codex to authorize the upload and start transcription.",
  savedLocal: "Your audio has not been sent to Alibaba Cloud.", job: "Task ID",
  changed: "Your settings changed. Check them again to refresh the preview.",
  languageChanged: "The interface language changed. Check your settings again to refresh the preview.",
  saveRejected: "The settings were not saved. Correct the highlighted field and check again.",
  network: "The connection was lost. Return to Codex to check that the app is running. This operation will not retry automatically.",
  unknownResponse: "The operation result is unavailable. Return to Codex for details.",
  failed: "The operation could not be completed. Check your input and try again manually.",
  templateFailed: "The template could not be downloaded. Check that the app is running and try again.",
  keyNotReady: "Enter a Model Studio API key for the Beijing region.",
  missingAudio: "Choose an audio file.", missingHotwords: "Choose a hotword list.", missingContext: "Enter reference text.",
  invalidSpeaker: "Enter an integer from {min} to {max}, or leave blank for automatic detection.",
  contextTooLong: "Reference text exceeds {count} characters. Shorten it and check again. Your full input has been kept.",
  singleFile: "Select one file at a time.", wrongHotwords: "Select a hotword list in .xlsx format.",
  unsupportedFormat: "This file format is not supported.", tooLarge: "The file exceeds {size} MB. Select another file.",
  row: "Row {row}", textColumn: "Hotword", weightColumn: "Weight", headerColumn: "Header", rowColumn: "Content",
  loading: "Loading settings…", unavailable: "Settings are unavailable. Return to Codex to reopen the page.",
  footer: "asr-transcription", readyBadge: "Added",
};
const zh: Record<keyof typeof en, string> = {
  title: "录音转写", brand: "阿里云百炼", preview: "预览版",
  intro: "将会议、访谈或课程录音转换为文字。",
  region: "华北 2（北京）", language: "界面语言", theme: "外观",
  system: "跟随系统", light: "浅色", dark: "深色", skip: "跳到转写设置",
  stepConfigure: "转写设置", stepReview: "核对信息", stepSaved: "保存设置",
  beforeStart: "保存设置后，返回 Codex 确认上传并开始转写。",
  audioHeading: "添加音频", oneFile: "每次 1 个文件", chooseAudio: "选择音频文件",
  replaceAudio: "更换音频", drag: "或拖拽至此处",
  formatLimits: "支持格式与文件限制",
  audioLimits: "可添加不超过 {size} GB、{hours} 小时的文件。发送至阿里云的音频须不超过 {upload} GB；合并声道后，以转换后的文件大小为准。支持 {formats}。",
  emptyUpload: "尚未选择文件", uploading: "正在添加 {name}…", uploadReady: "{name} · {size}",
  uploadFailed: "文件添加失败，请重新选择。",
  settings: "转写设置", audioLanguage: "音频语言", automatic: "自动识别",
  diarization: "区分发言人", diarizationHelp: "在转写内容中标记不同发言人。",
  monoHelp: "多声道音频将合并为单声道副本，保留原文件。",
  speakers: "发言人数", optional: "选填", speakerHint: "可填写 {min}–{max} 人供识别参考，留空自动判断。",
  enhancement: "精度增强", enhancementHint: "热词与上下文可单独使用，也可同时开启。",
  hotwords: "添加热词", hotwordsHelp: "提高人名、产品名称和专业术语的识别准确率。",
  hotwordFile: "热词表", chooseHotwords: "选择 Excel 文件", replaceHotwords: "更换热词表",
  template: "下载模板", hotwordLimit: ".xlsx · 最大 {size} MB",
  hotwordHelp: "按模板填写词语和权重，最多 {count} 个热词。",
  context: "添加上下文", contextHelp: "提供与录音相关的术语、对话或参考资料。",
  reference: "参考文本", contextHint: "包含录音中可能出现的具体词语，最多 {count} 个字符。",
  contextPlaceholder: "例如：本次技术评审讨论 Kubernetes、容器编排、灰度发布和服务回滚方案。",
  savingLocations: "保存位置", rawResult: "原始结果（JSON）", documents: "转写文档",
  chooseFolder: "选择文件夹", resetFolder: "恢复默认", choosingFolder: "请在弹窗中选择…",
  folderWaiting: "请在系统窗口中选择文件夹。未看到窗口时可取消等待。",
  cancelWaiting: "取消等待", cancelling: "正在取消…", timestamps: "保留时间戳",
  useKey: "使用指定 API Key", consoleDefault: "未开启时使用百炼控制台登录。",
  enterKey: "填写北京地域的百炼 API Key",
  keySaveHelp: "点击“检查并预览”时，将 Key 保存到当前工作目录的 .asr-transcription/.env。",
  loadingKey: "正在读取…",
  review: "转写信息", pending: "待检查", validated: "检查通过", validating: "正在检查…",
  saving: "正在保存…", unknown: "保存结果待确认",
  audioFile: "音频文件", duration: "音频时长", fileSize: "文件大小", formatChannels: "格式 / 声道",
  channel: "{count} 声道", channels: "{count} 声道", sampleRate: "采样率", connection: "认证方式",
  consoleLogin: "百炼控制台登录", enabled: "开启", disabled: "关闭", notAdded: "尚未添加",
  speakerValue: "{count} 人（参考）", character: "{count} 字符", characters: "{count} 字符",
  hotwordCount: "{count} 个热词", hotwordsCount: "{count} 个热词", hotwordsLabel: "热词", contextLabel: "上下文",
  draftHelp: "检查后显示时长、声道等音频信息。",
  modelRegion: "模型与地域", quickLinks: "快速定位设置", jsonLocation: "JSON 保存位置", documentLocation: "文档保存位置",
  next: "下一步：核对转写信息", nextHelp: "检查音频、识别选项和保存位置。",
  reviewTitle: "核对并保存", reviewHelp: "保存设置不会启动转写。",
  unknownTitle: "暂时无法确认保存结果", unknownHelp: "请返回 Codex 查看保存情况，避免重复提交。",
  check: "检查并预览", save: "保存设置", edit: "返回修改", viewDetails: "查看转写信息",
  savedTitle: "转写设置已保存", savedHelp: "您可以关闭此页面，返回 Codex 确认上传并开始转写。",
  savedLocal: "音频尚未发送至阿里云。", job: "任务编号",
  changed: "设置已修改，请重新检查并预览。",
  languageChanged: "界面语言已更改，请重新检查设置以更新预览。",
  saveRejected: "未能保存，请按提示修改后重新检查。",
  network: "连接已断开，请返回 Codex 检查应用是否仍在运行。本次操作不会自动重试。",
  unknownResponse: "暂时无法获取操作结果，请返回 Codex 查看详情。",
  failed: "本次操作未完成，请检查输入后手动再试。",
  templateFailed: "模板下载失败，请确认应用仍在运行后重试。",
  keyNotReady: "请填写北京地域的百炼 API Key。",
  missingAudio: "请选择音频文件。", missingHotwords: "请选择热词文件。", missingContext: "请填写参考文本。",
  invalidSpeaker: "请输入 {min}–{max} 的整数，或留空自动判断。",
  contextTooLong: "参考文本超过 {count} 个字符，请精简后重新检查。已保留您输入的全部内容。",
  singleFile: "一次只能添加 1 个文件。", wrongHotwords: "请选择 .xlsx 格式的热词文件。",
  unsupportedFormat: "暂不支持此文件格式。", tooLarge: "文件超过 {size} MB，请重新选择。",
  row: "第 {row} 行", textColumn: "热词", weightColumn: "权重", headerColumn: "表头", rowColumn: "内容",
  loading: "正在加载设置…", unavailable: "暂时无法加载设置，请返回 Codex 重新打开页面。",
  footer: "asr-transcription", readyBadge: "已添加",
};
export type MessageKey = keyof typeof en;
export type Translate = (key: MessageKey, values?: Record<string, string | number>) => string;

// 按界面语言读取文案，仅替换开发者定义的命名占位符。
export function translate(language: Language, key: MessageKey, values: Record<string, string | number> = {}): string {
  const template = (language === "en" ? en : zh)[key];
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(values[name] ?? `{${name}}`));
}

// 使用标准语言代码显示本地化名称，保留百炼使用的菲律宾语名称。
export function languageName(code: string, language: Language): string {
  if (code === "tl") return language === "en" ? "Filipino" : "菲律宾语";
  return new Intl.DisplayNames([language], { type: "language" }).of(code) ?? code;
}

// 将文件大小显示为与服务端限制一致的十进制单位。
export function fileSize(bytes: number): string {
  return bytes < 1_000_000 ? `${(bytes / 1000).toFixed(1)} KB` : `${(bytes / 1_000_000).toFixed(2)} MB`;
}

// 将秒数显示为跨语言一致的时分秒。
export function durationText(seconds: number): string {
  const total = Math.round(seconds);
  return [Math.floor(total / 3600), Math.floor(total / 60) % 60, total % 60].map(value => String(value).padStart(2, "0")).join(":");
}
