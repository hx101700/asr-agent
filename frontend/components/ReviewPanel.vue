<script setup lang="ts">
import { computed } from "vue";
import { ElAlert, ElButton, ElTag } from "element-plus";
import { durationText, fileSize, languageName, type MessageKey, type Translate } from "../i18n";
import type { FormValues, Language, Model } from "../types";

const props = defineProps<{ model: Model; form: FormValues; language: Language; t: Translate; editable: boolean }>();
const emit = defineEmits<{ jump: [id: string] }>();

// 从当前表单或已检查快照生成摘要，避免维护第二份编辑状态。
const rows = computed<[string, string][]>(() => {
  const { model, form, t } = props;
  const preview = model.preview;
  const config = preview?.configuration;
  const summary = preview?.summary;
  const audio = model.uploads.audio;
  const words = model.uploads.hotwords;
  const language = config ? config.language_hint : form.language;
  const diarization = config ? config.diarization_enabled : form.diarizationEnabled;
  const speakers = config ? config.speaker_count : form.speaker;
  const values: [string, string][] = [[t("audioFile"), audio.status === "ready" ? audio.name : t(audio.status === "uploading" ? "loading" : "notAdded")]];
  if (summary) {
    values.push([t("duration"), durationText(summary.audio.duration_seconds)],
      [t("fileSize"), fileSize(summary.audio.size_bytes)],
      [t("formatChannels"), `${summary.audio.format_name} / ${t(summary.audio.channels === 1 ? "channel" : "channels", { count: summary.audio.channels })}`],
      [t("sampleRate"), `${summary.audio.sample_rate.toLocaleString(props.language)} Hz`]);
  }
  values.push([t("audioLanguage"), language ? languageName(language, props.language) : t("automatic")],
    [t("diarization"), t(diarization ? "enabled" : "disabled")]);
  if (diarization) values.push([t("speakers"), speakers ? t("speakerValue", { count: speakers }) : t("automatic")]);
  const contextChars = summary ? summary.enhancement.context_chars : Array.from(form.context).length;
  values.push([t("hotwordsLabel"), form.hotwordsEnabled ? (summary ? t(summary.enhancement.count === 1 ? "hotwordCount" : "hotwordsCount", { count: summary.enhancement.count }) : words.name || t("notAdded")) : t("disabled")],
    [t("contextLabel"), form.contextEnabled ? t(contextChars === 1 ? "character" : "characters", { count: contextChars }) : t("disabled")],
    [t("connection"), (config ? config.auth_mode === "api_key" : form.useApiKey) ? "API Key" : t("consoleLogin")]);
  if (summary) values.push([t("jsonLocation"), summary.json_directory], [t("documentLocation"), summary.document_directory]);
  return values;
});

// 根据当前阶段显示摘要状态。
const status = computed<MessageKey>(() => {
  const phase = props.model.phase;
  if (phase === "validating") return "validating";
  if (phase === "saving") return "saving";
  if (phase === "save_unknown") return "unknown";
  return props.model.preview ? "validated" : "pending";
});
const sections: [string, MessageKey][] = [["audio_upload_id", "audioHeading"], ["settings", "settings"],
  ["enhancement", "enhancement"], ["outputs", "savingLocations"]];
</script>

<template>
  <section id="review" class="surface review-panel" tabindex="-1" :aria-label="t('review')">
    <div class="panel-title"><h2>{{ t('review') }}</h2><ElTag :type="model.preview ? 'success' : 'info'" effect="plain">{{ t(status) }}</ElTag></div>
    <div class="review-scroll" tabindex="0" :aria-label="t('review')">
      <dl class="detail-list">
        <div v-for="[label, value] in rows" :key="label"><dt>{{ label }}</dt><dd>{{ value }}</dd></div>
      </dl>
      <p v-if="!model.preview" class="helper">{{ t('draftHelp') }}</p>
      <ElAlert v-for="warning in model.preview?.summary.warnings ?? []" :key="warning" :title="warning" type="warning" :closable="false" show-icon class="review-warning" />
      <details class="model-info"><summary>{{ t('modelRegion') }}</summary><code>{{ model.session?.model }}</code><p>{{ t('region') }}</p></details>
    </div>
    <nav class="review-links" :aria-label="t('quickLinks')">
      <ElButton v-for="[id, label] in sections" :key="id" text :disabled="!editable" @click="emit('jump', id)">{{ t(label) }}</ElButton>
    </nav>
  </section>
</template>
