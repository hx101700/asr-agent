import { createApp } from "vue";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import "./style.css";
import App from "./App.vue";
import { createApi } from "./api";
import type { Language } from "./types";
import type { Translate } from "./i18n";

const sessionToken = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "";
// 会话令牌只交给接口闭包，地址栏及历史记录保留无令牌页面地址。
window.history.replaceState(null, "", window.location.pathname + window.location.search);
createApp(App, { connect: (language: () => Language, t: Translate) => createApi(window.fetch.bind(window), sessionToken, language, t) }).mount("#app");
