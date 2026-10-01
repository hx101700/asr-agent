// 创建本机 HTTP 接口，统一请求参数、响应解析和错误传递。
export function createApi(fetchRequest, sessionToken) {
  // 为本次请求构造会话令牌头。
  const headers = () => sessionToken ? { "X-ASR-Token": sessionToken } : {};
  // 统一本机会话请求的缓存与凭据策略。
  const options = () => ({ headers: headers(), cache: "no-store", credentials: "same-origin" });
  return {
    // 发送表单 JSON 或文件字节，并将服务端错误交给界面定位。
    async request(path, payload, file) {
      const init = options();
      if (file) {
        init.method = "POST";
        init.headers["Content-Type"] = "application/octet-stream";
        init.headers["X-File-Name"] = encodeURIComponent(file.name);
        init.body = file;
      } else if (payload !== undefined) {
        init.method = "POST";
        init.headers["Content-Type"] = "application/json";
        init.body = JSON.stringify(payload);
      }
      let response;
      try {
        response = await fetchRequest(path, init);
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
        throw Object.assign(new Error(data.error || "本次操作未完成，请检查输入后手动再试。"), {
          httpStatus: response.status, field: data.field, details: data.details,
        });
      }
      return data;
    },
    // 取得热词模板的二进制内容，由视图触发下载。
    async template() {
      const response = await fetchRequest("/api/hotwords-template", options());
      if (!response.ok) throw new Error("模板下载失败，请确认应用仍在运行后重试。");
      return response.blob();
    },
  };
}
