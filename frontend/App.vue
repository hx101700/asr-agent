<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { ElAlert, ElButton, ElConfigProvider, ElForm, ElFormItem, ElInput, ElOption, ElSelect, ElStep, ElSteps, ElSwitch, ElTag } from "element-plus";
import en from "element-plus/es/locale/lang/en";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import { availability } from "./model";
import { languageName, type MessageKey, type Translate } from "./i18n";
import { usePreferences } from "./preferences";
import { useTranscription } from "./useTranscription";
import type { Api, DirectoryKind, Language } from "./types";
import KeyDisplay from "./components/KeyDisplay.vue";
import ReviewPanel from "./components/ReviewPanel.vue";
import UploadField from "./components/UploadField.vue";

const props = defineProps<{ connect: (language: () => Language, t: Translate) => Api }>();
const { language, theme, t } = usePreferences();
const keyDisplay = ref<InstanceType<typeof KeyDisplay>>();
const aliases: Record<string, string> = { audio_path: "audio_upload_id", hotwords_path: "hotwords_upload_id" };

// 在控件完成渲染后定位错误字段或当前操作区域。
async function focus(target: string): Promise<void> {
  await nextTick();
  const region = document.getElementById(aliases[target] ?? target) ?? document.getElementById("error-panel");
  if (!region) return;
  const control = Array.from(region.querySelectorAll<HTMLElement>(
    'input:not(:disabled), textarea:not(:disabled), button:not(:disabled), [role="button"][tabindex="0"]',
  )).find(element => element.getClientRects().length > 0);
  (control ?? region).focus({ preventScroll: true });
  region.scrollIntoView({ block: "center", behavior: "auto" });
}

// 将已取得的模板交给浏览器下载。
function download(blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "hotwords-template.xlsx";
  link.click();
  URL.revokeObjectURL(url);
}

const { model, form, error, actions } = useTranscription(props.connect(() => language.value, t), {
  focus: target => { void focus(target); },
  setApiKey: value => keyDisplay.value?.setValue(value),
  getApiKey: () => keyDisplay.value?.getValue() ?? "",
  download,
}, t);
const available = computed(() => availability(model));
const locale = computed(() => language.value === "en" ? en : zhCn);
const step = computed(() => model.phase === "saved" ? 3 : model.preview || model.phase === "save_unknown" ? 1 : 0);
const contextLength = computed(() => Array.from(form.context).length);
const outputKinds: DirectoryKind[] = ["json", "document"];

// 将后端字段别名映射到当前页面的可访问输入区域。
function invalid(field: string): boolean {
  return Boolean(error.value && (aliases[error.value.field ?? ""] ?? error.value.field) === field);
}

// 读取输入位置的错误说明，供 Element Plus 表单关联。
function fieldMessage(field: string): string {
  return invalid(field) ? error.value?.message ?? "" : "";
}

// 显示热词行级错误所指向的列名。
function detailLabel(field?: string): string {
  const labels: Record<string, MessageKey> = { text: "textColumn", weight: "weightColumn", header: "headerColumn", row: "rowColumn" };
  const key = labels[field ?? ""];
  return key ? t(key) : field ?? "";
}

// 切换页面语言后重新生成需要本地化的预览。
function changeLanguage(): void {
  actions.languageChanged();
}

onMounted(actions.start);
</script>

<template>
  <ElConfigProvider :locale="locale">
    <a class="skip-link" href="#config-fields">{{ t('skip') }}</a>
    <header class="topbar">
      <div class="topbar-inner">
        <a class="brand" href="#" @click.prevent="focus('page-title')">
          <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
          <span>{{ t('title') }}<small>{{ t('brand') }}</small></span>
        </a>
        <div class="appearance-controls">
          <ElSelect id="interface-language" v-model="language" :aria-label="t('language')" :disabled="!available.changeLanguage" @change="changeLanguage" class="language-select">
            <ElOption value="zh-CN" label="简体中文" /><ElOption value="en" label="English" />
          </ElSelect>
          <ElSelect id="theme" v-model="theme" :aria-label="t('theme')" class="theme-select">
            <ElOption value="system" :label="t('system')" /><ElOption value="light" :label="t('light')" /><ElOption value="dark" :label="t('dark')" />
          </ElSelect>
        </div>
      </div>
    </header>

    <main class="page-shell">
      <div class="intro">
        <div><div class="eyebrow">ASR TRANSCRIPTION <ElTag size="small" type="info" effect="plain">{{ t('preview') }}</ElTag></div>
          <h1 id="page-title" tabindex="-1">{{ model.phase === 'saved' ? t('savedTitle') : t('title') }}</h1>
          <p>{{ model.phase === 'saved' ? t('savedLocal') : t('intro') }}</p>
        </div>
        <span class="region"><span aria-hidden="true">●</span>{{ t('region') }}</span>
      </div>

      <ElSteps :active="step" finish-status="success" class="steps" align-center>
        <ElStep :title="t('stepConfigure')" /><ElStep :title="t('stepReview')" /><ElStep :title="t('stepSaved')" />
      </ElSteps>
      <ElAlert v-if="model.phase !== 'saved'" :title="t('beforeStart')" type="info" :closable="false" show-icon class="intro-note" />
      <ElAlert v-if="model.statusMessage" :title="t(model.statusMessage)" type="info" :closable="false" show-icon class="page-notice" />
      <section v-if="error" id="error-panel" tabindex="-1" role="alert" class="page-notice">
        <ElAlert :title="error.message" type="error" :closable="false" show-icon>
          <ul v-if="error.details.length" class="error-details">
            <li v-for="(detail, index) in error.details" :key="index">
              <strong v-if="detail.row">{{ t('row', { row: detail.row }) }} · </strong>
              {{ detailLabel(detail.field) }}
              {{ detail.field ? ': ' : '' }}{{ detail.message }}
            </li>
          </ul>
        </ElAlert>
      </section>
      <p v-if="model.phase === 'loading'" class="loading-note" role="status">{{ t('loading') }}</p>
      <ElAlert v-if="model.phase === 'unavailable'" :title="t('unavailable')" type="error" :closable="false" />

      <section v-if="model.phase === 'saved' && model.receipt" id="receipt" class="surface receipt" tabindex="-1">
        <div class="success-mark" aria-hidden="true">✓</div>
        <h2>{{ t('savedTitle') }}</h2><p>{{ t('savedHelp') }}</p>
        <dl class="detail-list">
          <div><dt>{{ t('job') }}</dt><dd>{{ model.receipt.job_id }}</dd></div>
          <div><dt>{{ t('jsonLocation') }}</dt><dd>{{ model.receipt.json_directory }}</dd></div>
          <div><dt>{{ t('documentLocation') }}</dt><dd>{{ model.receipt.document_directory }}</dd></div>
        </dl>
      </section>

      <div v-else-if="model.session" class="workspace">
        <ElForm id="config-fields" :disabled="!available.editable" label-position="top" class="form-column" tabindex="-1" @submit.prevent="actions.validate">
          <section id="audio_upload_id" class="surface" :class="{ 'needs-attention': invalid('audio_upload_id') }" tabindex="-1">
            <div class="section-heading"><span class="section-number">01</span><h2>{{ t('audioHeading') }}</h2><span class="section-aside">{{ t('oneFile') }}</span></div>
            <UploadField kind="audio" :upload="model.uploads.audio" :disabled="!available.upload.audio" :accept="model.session.audio_suffixes.join(',')" :t="t" @select="actions.upload('audio', $event)" />
            <p v-if="invalid('audio_upload_id')" class="field-error">{{ error?.message }}</p>
            <details class="format-help"><summary>{{ t('formatLimits') }}</summary><p>{{ t('audioLimits', {
              size: model.session.limits.audio_bytes / 1_000_000_000, hours: model.session.limits.audio_seconds / 3600,
              upload: model.session.limits.upload_bytes / 1_000_000_000, formats: model.session.audio_suffixes.map(s => s.slice(1).toUpperCase()).join(', ') }) }}</p></details>
          </section>

          <section id="settings" class="surface" tabindex="-1">
            <div class="section-heading"><span class="section-number">02</span><h2>{{ t('settings') }}</h2></div>
            <div id="language_hint" :class="{ 'needs-attention': invalid('language_hint') }" tabindex="-1">
              <ElFormItem :label="t('audioLanguage')" for="audio-language" :error="fieldMessage('language_hint')">
                <ElSelect id="audio-language" v-model="form.language" :empty-values="[null, undefined]" filterable @change="actions.changed()">
                  <ElOption value="" :label="t('automatic')" /><ElOption v-for="[code] in model.session.languages" :key="code" :value="code" :label="languageName(code, language)" />
                </ElSelect>
              </ElFormItem>
            </div>
            <div class="toggle-row">
              <div><label for="diarization">{{ t('diarization') }}</label><p>{{ t('diarizationHelp') }}</p></div>
              <ElSwitch id="diarization" v-model="form.diarizationEnabled" :aria-label="t('diarization')" @change="actions.changed()" />
            </div>
            <div v-if="form.diarizationEnabled" class="expanded-option">
              <p class="helper">{{ t('monoHelp') }}</p>
              <div id="speaker_count" :class="{ 'needs-attention': invalid('speaker_count') }" tabindex="-1">
                <ElFormItem :label="t('speakers') + ' · ' + t('optional')" for="speaker-count" :error="fieldMessage('speaker_count')">
                  <ElInput id="speaker-count" v-model="form.speaker" inputmode="numeric" :placeholder="t('automatic')" @input="actions.changed()" />
                </ElFormItem>
                <p class="helper">{{ t('speakerHint', { min: model.session.limits.speaker_min, max: model.session.limits.speaker_max }) }}</p>
              </div>
            </div>
          </section>

          <section id="enhancement" class="surface" tabindex="-1">
            <div class="section-heading"><span class="section-number">03</span><h2>{{ t('enhancement') }}</h2></div>
            <p class="section-description">{{ t('enhancementHint') }}</p>
            <div class="enhancement-option">
              <div class="toggle-row">
                <div><label for="hotwords-enabled">{{ t('hotwords') }}</label><p>{{ t('hotwordsHelp') }}</p></div>
                <ElSwitch id="hotwords-enabled" v-model="form.hotwordsEnabled" :aria-label="t('hotwords')" @change="actions.changed()" />
              </div>
              <div v-if="form.hotwordsEnabled" id="hotwords_upload_id" class="expanded-option" :class="{ 'needs-attention': invalid('hotwords_upload_id') }" tabindex="-1">
                <div class="label-action"><span class="field-label">{{ t('hotwordFile') }}</span><ElButton text type="primary" :disabled="!available.template" :loading="model.downloadingTemplate" @click="actions.downloadTemplate">{{ t('template') }}</ElButton></div>
                <UploadField kind="hotwords" :upload="model.uploads.hotwords" :disabled="!available.upload.hotwords" accept=".xlsx" :t="t" @select="actions.upload('hotwords', $event)" />
                <p class="helper">{{ t('hotwordLimit', { size: model.session.limits.hotwords_bytes / 1_000_000 }) }}</p>
                <p class="helper">{{ t('hotwordHelp', { count: model.session.limits.hotwords_count }) }}</p>
                <p v-if="invalid('hotwords_upload_id')" class="field-error">{{ error?.message }}</p>
              </div>
            </div>
            <div class="enhancement-option">
              <div class="toggle-row">
                <div><label for="context-enabled">{{ t('context') }}</label><p>{{ t('contextHelp') }}</p></div>
                <ElSwitch id="context-enabled" v-model="form.contextEnabled" :aria-label="t('context')" @change="actions.changed()" />
              </div>
              <div v-if="form.contextEnabled" id="context" class="expanded-option" :class="{ 'needs-attention': invalid('context') }" tabindex="-1">
                <ElFormItem :label="t('reference')" for="context-text" :error="fieldMessage('context')">
                  <ElInput id="context-text" v-model="form.context" type="textarea" :autosize="{ minRows: 4, maxRows: 10 }" :placeholder="t('contextPlaceholder')" @input="actions.changed()" />
                </ElFormItem>
                <div class="textarea-footer"><p class="helper">{{ t('contextHint', { count: model.session.limits.context_chars }) }}</p><span :class="{ 'field-error': contextLength > model.session.limits.context_chars }">{{ contextLength }} / {{ model.session.limits.context_chars }}</span></div>
              </div>
            </div>
          </section>

          <section id="outputs" class="surface" tabindex="-1">
            <div class="section-heading"><span class="section-number">04</span><h2>{{ t('savingLocations') }}</h2></div>
            <div v-for="kind in outputKinds" :id="kind + '_directory'" :key="kind" class="output-field" :class="{ 'needs-attention': invalid(kind + '_directory') }" tabindex="-1">
              <div class="label-action"><label :for="kind + '-folder'">{{ t(kind === 'json' ? 'rawResult' : 'documents') }}</label>
                <ElButton v-if="model.directories[kind] !== 'default'" text type="primary" :disabled="!available.chooseDirectory" @click="actions.resetDirectory(kind)">{{ t('resetFolder') }}</ElButton></div>
              <div class="directory-row"><ElInput :id="kind + '-folder'" :model-value="model.directories[kind] === 'default' ? '' : model.directories[kind]" :placeholder="model.session.output_defaults[kind]" :title="model.directories[kind] === 'default' ? model.session.output_defaults[kind] : model.directories[kind]" readonly />
                <ElButton :disabled="!available.chooseDirectory" @click="actions.selectDirectory(kind)">{{ model.picker?.kind === kind ? t('choosingFolder') : t('chooseFolder') }}</ElButton></div>
              <p v-if="invalid(kind + '_directory')" class="field-error">{{ error?.message }}</p>
            </div>
            <div class="format-tags"><ElTag v-for="format in ['Word', 'Excel', 'Markdown']" :key="format" type="info" effect="plain">{{ format }}</ElTag><span>{{ t('timestamps') }}</span></div>
            <div v-if="model.picker" class="picker-wait" role="status"><span>{{ t('folderWaiting') }}</span><ElButton :disabled="!available.cancelDirectory" @click="actions.cancelDirectory">{{ model.picker.cancelling ? t('cancelling') : t('cancelWaiting') }}</ElButton></div>
          </section>

          <section id="auth_mode" class="surface" :class="{ 'needs-attention': invalid('auth_mode') }" tabindex="-1">
            <div class="toggle-row">
              <div><label for="use-api-key">{{ t('useKey') }}</label><p>{{ t('consoleDefault') }}</p></div>
              <ElSwitch id="use-api-key" :model-value="form.useApiKey" :disabled="!available.changeAuth" :aria-label="t('useKey')" @update:model-value="actions.setAuthMode($event === true)" />
            </div>
            <div v-if="form.useApiKey" class="expanded-option">
              <KeyDisplay ref="keyDisplay" :loading="model.auth.status === 'loading'" :disabled="!available.changeAuth || model.auth.status === 'loading'" :t="t" @changed="actions.keyChanged" />
              <p class="helper">{{ t('keySaveHelp') }}</p>
            </div>
            <p v-if="invalid('auth_mode')" class="field-error">{{ error?.message }}</p>
          </section>
        </ElForm>

        <aside class="review-column">
          <ReviewPanel :model="model" :form="form" :language="language" :t="t" :editable="available.editable" @jump="focus" />
        </aside>
      </div>
      <footer>{{ t('footer') }}<span>{{ t('brand') }}</span></footer>
    </main>

    <div v-if="model.session && model.phase !== 'saved'" class="action-bar">
      <div class="action-inner">
        <div class="action-copy"><strong>{{ model.phase === 'save_unknown' ? t('unknownTitle') : model.preview ? t('reviewTitle') : t('next') }}</strong><p>{{ model.phase === 'save_unknown' ? t('unknownHelp') : model.preview ? t('reviewHelp') : t('nextHelp') }}</p></div>
        <div class="action-buttons">
          <ElButton class="mobile-review" :disabled="!available.editable" @click="focus('review')">{{ t('viewDetails') }}</ElButton>
          <ElButton v-if="model.preview" :disabled="!available.editable" @click="actions.edit">{{ t('edit') }}</ElButton>
          <ElButton v-if="model.preview" type="primary" :loading="model.phase === 'saving'" :disabled="!available.confirm" @click="actions.confirm">{{ t('save') }}</ElButton>
          <ElButton v-else type="primary" :loading="model.phase === 'validating'" :disabled="!available.validate" @click="actions.validate">{{ t('check') }}</ElButton>
        </div>
      </div>
    </div>
  </ElConfigProvider>
</template>
