import type { Api, Endpoints, ErrorDetail, ErrorPayload, Language } from "./types";
import type { Translate } from "./i18n";

export class UiError extends Error {
  // 保存公开错误说明、字段位置与明确的 HTTP 状态。
  constructor(message: string, public field?: string, public httpStatus?: number, public details: ErrorDetail[] = []) {
    super(message);
    this.name = "UiError";
  }
}

// 将未知异常转换为可显示的错误对象，保留服务端字段与状态。
export function uiError(error: unknown, fallback: string, field?: string): UiError {
  if (error instanceof UiError) {
    if (field) error.field = field;
    return error;
  }
  return new UiError(error instanceof Error ? error.message : fallback, field);
}

// 创建仅访问当前本机会话的接口，凭据令牌保留在闭包中。
export function createApi(fetchRequest: typeof fetch, sessionToken: string, language: () => Language, t: Translate): Api {
  // 构造本机请求头和缓存策略。
  function options(): RequestInit {
    return { headers: { ...(sessionToken ? { "X-ASR-Token": sessionToken } : {}), "Accept-Language": language() },
      cache: "no-store", credentials: "same-origin" };
  }
  return {
    // 发送 JSON 或文件字节，并传递明确的错误状态。
    async request<K extends keyof Endpoints>(path: K, payload?: object, file?: File): Promise<Endpoints[K]> {
      const init = options();
      const headers = new Headers(init.headers);
      init.headers = headers;
      if (file) {
        init.method = "POST";
        headers.set("Content-Type", "application/octet-stream");
        headers.set("X-File-Name", encodeURIComponent(file.name));
        init.body = file;
      } else if (payload !== undefined) {
        init.method = "POST";
        headers.set("Content-Type", "application/json");
        init.body = JSON.stringify(payload);
      }
      let response: Response;
      try { response = await fetchRequest(path, init); }
      catch { throw new UiError(t("network")); }
      let data: Endpoints[K] & ErrorPayload;
      try { data = await response.json() as Endpoints[K] & ErrorPayload; }
      catch { throw new UiError(t("unknownResponse")); }
      if (!response.ok || data.ok === false) {
        throw new UiError(data.error || t("failed"), data.field, response.status, data.details);
      }
      return data;
    },
    // 下载本机生成的热词模板。
    async template(): Promise<Blob> {
      try {
        const response = await fetchRequest("/api/hotwords-template", options());
        if (!response.ok) throw new UiError(t("templateFailed"));
        return await response.blob();
      } catch { throw new UiError(t("templateFailed")); }
    },
  };
}
