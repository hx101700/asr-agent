<script setup lang="ts">
import { ElUpload, ElProgress, ElTag } from "element-plus";
import type { UploadFile } from "element-plus";
import { fileSize, type Translate } from "../i18n";
import type { UploadKind, UploadState } from "../types";

defineProps<{ kind: UploadKind; upload: UploadState; disabled: boolean; accept: string; t: Translate }>();
const emit = defineEmits<{ select: [files: readonly File[]] }>();

// 传递单个原始文件给本机会话用例。
function selected(file: UploadFile): void {
  if (file.raw) emit("select", [file.raw]);
}

// 将多文件选择交给统一的单文件规则报告。
function exceeded(files: File[]): void {
  emit("select", files);
}
</script>

<template>
  <div class="upload-field" :aria-busy="upload.status === 'uploading'">
    <ElUpload drag :auto-upload="false" :show-file-list="false" :file-list="[]" :limit="1"
      :disabled="disabled" :accept="accept" :on-change="selected" :on-exceed="exceeded"
      :aria-label="t(kind === 'audio' ? 'chooseAudio' : 'chooseHotwords')">
      <svg class="upload-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <path d="M11 31v7h26v-7M24 31V10m-8 8 8-8 8 8" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div class="upload-title">{{ t(kind === 'audio' ? (upload.status === 'ready' ? 'replaceAudio' : 'chooseAudio') : (upload.status === 'ready' ? 'replaceHotwords' : 'chooseHotwords')) }}</div>
      <div class="subtle">{{ t('drag') }}</div>
    </ElUpload>
    <ElProgress v-if="upload.status === 'uploading'" :percentage="100" :indeterminate="true" :show-text="false" :stroke-width="3" />
    <div class="upload-status" role="status" aria-live="polite">
      <template v-if="upload.status === 'ready'">
        <ElTag size="small" type="success" effect="plain">{{ t('readyBadge') }}</ElTag>
        <span>{{ t('uploadReady', { name: upload.name, size: fileSize(upload.size) }) }}</span>
      </template>
      <template v-else-if="upload.status === 'uploading'">{{ t('uploading', { name: upload.name }) }}</template>
      <template v-else-if="upload.status === 'failed'">{{ t('uploadFailed') }}</template>
      <template v-else>{{ t('emptyUpload') }}</template>
    </div>
  </div>
</template>
