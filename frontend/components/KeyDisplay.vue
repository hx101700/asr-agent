<script setup lang="ts">
import { onBeforeUnmount, ref } from "vue";
import { ElInput } from "element-plus";
import type { Translate } from "../i18n";

defineProps<{ loading: boolean; disabled: boolean; t: Translate }>();
// 凭据仅驻留在显示组件中，保存或关闭组件时清空。
const value = ref("");
const emit = defineEmits<{ changed: [] }>();

// 将已有 Key 显示到密码输入框。
function setValue(key: string): void { value.value = key; }

// 在用户确认检查时交付当前输入，供接口保存到本机环境文件。
function getValue(): string { return value.value; }

onBeforeUnmount(() => { value.value = ""; });
defineExpose({ setValue, getValue });
</script>

<template>
  <label class="field-label" for="api-key-value">DASHSCOPE_API_KEY</label>
  <ElInput id="api-key-value" v-model="value" type="password" show-password
    autocomplete="off" :disabled="disabled" :placeholder="loading ? t('loadingKey') : t('enterKey')" @input="emit('changed')" />
</template>
