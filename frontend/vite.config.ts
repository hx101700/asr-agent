import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// 将开发源码编译为可由 Python 直接提供的本机页面资源。
export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  plugins: [vue()],
  build: {
    outDir: fileURLToPath(new URL("../skills/asr-transcription/scripts/asr_runtime/static", import.meta.url)),
    emptyOutDir: true,
    target: "es2022",
    cssCodeSplit: false,
    modulePreload: false,
    license: { fileName: "THIRD_PARTY_LICENSES.txt" },
    rolldownOptions: {
      output: { entryFileNames: "app.js", assetFileNames: "app.[ext]", codeSplitting: false },
    },
  },
});
