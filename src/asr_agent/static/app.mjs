import {
  createModel, availability, invalidatePreview, receiveValidation, receiveSaveError,
  receiveReceipt, configuration, checkRequiredInputs, fieldError,
} from "./model.mjs";
import { createView } from "./view.mjs";

// HTTP 契约集中在入口；失败不自动重试，未知保存结果由 Presenter 保留。
export function createApi(fetchRequest, sessionToken) {
  const headers = () => sessionToken ? { "X-ASR-Token": sessionToken } : {};
  const options = () => ({ headers: headers(), cache: "no-store", credentials: "same-origin" });
  return {
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
    async template() {
      const response = await fetchRequest("/api/hotwords-template", options());
      if (!response.ok) throw new Error("模板下载失败，请确认应用仍在运行后重试。");
      return response.blob();
    },
  };
}

export function createPresenter(view, api, makeRequestId = () => crypto.randomUUID()) {
  const model = createModel();
  const render = () => view.render(model, availability(model));
  const fail = (error) => { render(); view.showError(error); };

  async function updateAuth() {
    const revision = ++model.auth.revision;
    view.clearApiKey();
    if (!view.readForm().useApiKey) {
      model.auth.status = "idle";
      render();
      return;
    }
    model.auth.status = "loading";
    render();
    let failure = null;
    try {
      const result = await api.request("/api/api-key", {});
      if (revision !== model.auth.revision) return;
      // 凭据只交给密码控件，不写入 Model、校验参数、日志或存储。
      view.setApiKey(result.value);
      model.auth.status = "ready";
    } catch (error) {
      if (revision !== model.auth.revision) return;
      model.auth.status = "failed";
      failure = Object.assign(error, { field: "auth_mode" });
    } finally {
      if (revision === model.auth.revision) render();
    }
    if (failure) view.showError(failure);
  }

  const actions = {
    async start() {
      render();
      try {
        model.session = await api.request("/api/session");
        view.initialize(model.session);
        if (model.session.confirmed) {
          receiveReceipt(model, model.session.confirmed);
          view.clearApiKey();
        } else {
          model.phase = "editing";
        }
        render();
        if (model.receipt) view.focusReceipt();
        else if (view.readForm().useApiKey) await updateAuth();
      } catch (error) {
        model.phase = "unavailable";
        fail(error);
      }
    },

    async changed(id, files) {
      if (!availability(model).editable) return;
      if (id === "audio-file") return actions.upload("audio", files);
      if (id === "hotwords-file") return actions.upload("hotwords", files);
      view.clearError();
      invalidatePreview(model);
      render();
      if (id === "use-api-key") await updateAuth();
    },

    async upload(kind, files) {
      if (!availability(model).upload[kind] || !files.length) return;
      view.clearError();
      invalidatePreview(model);
      model.uploads[kind] = { status: "empty", id: null, name: "", size: 0 };
      const upload = model.uploads[kind];
      try {
        if (files.length !== 1) throw fieldError("一次只能添加 1 个文件。", `${kind}_upload_id`);
        const file = files[0];
        if (!view.fileExtensions(kind).some((extension) => file.name.toLowerCase().endsWith(extension))) {
          throw fieldError(kind === "hotwords" ? "请选择 .xlsx 格式的热词文件。" : "暂不支持此文件格式。", `${kind}_upload_id`);
        }
        const limit = model.session.limits[`${kind}_bytes`];
        if (file.size > limit) {
          throw fieldError(`文件超过 ${limit / 1_000_000} MB，请重新选择。`, `${kind}_upload_id`);
        }
        upload.status = "uploading";
        upload.name = file.name;
        render();
        const result = await api.request(`/api/upload-${kind}`, undefined, file);
        Object.assign(upload, { status: "ready", id: result.upload_id, name: result.name, size: result.size_bytes });
        render();
      } catch (error) {
        upload.status = "failed";
        view.clearFile(kind);
        fail(error.field ? error : Object.assign(error, { field: `${kind}_upload_id` }));
      }
    },

    async selectDirectory(kind) {
      if (!availability(model).chooseDirectory) return;
      const picker = { id: makeRequestId(), kind, cancelling: false };
      model.picker = picker;
      render();
      let failure = null;
      try {
        const result = await api.request("/api/select-directory", { kind, picker_id: picker.id });
        if (model.picker !== picker) return;
        if (!result.cancelled) {
          model.directories[kind] = result.path;
          view.clearError();
          invalidatePreview(model);
        }
      } catch (error) {
        failure = Object.assign(error, { field: `${kind}_directory` });
      } finally {
        if (model.picker === picker) {
          model.picker = null;
          render();
        }
      }
      if (failure) view.showError(failure);
    },

    async cancelDirectory() {
      if (!availability(model).cancelDirectory) return;
      const picker = model.picker;
      picker.cancelling = true;
      render();
      try {
        await api.request("/api/cancel-directory", { picker_id: picker.id });
        // 原选择请求结束后才恢复按钮，防止旧进程尚未退出就打开新窗口。
      } catch (error) {
        if (model.picker === picker) {
          picker.cancelling = false;
          fail(error);
        }
      }
    },

    resetDirectory(kind) {
      if (!availability(model).chooseDirectory) return;
      model.directories[kind] = "outputs";
      view.clearError();
      invalidatePreview(model);
      render();
    },

    edit() {
      if (!availability(model).editable) return;
      invalidatePreview(model);
      render();
      view.focusForm();
    },

    async validate() {
      if (!availability(model).validate) return;
      view.clearError();
      invalidatePreview(model);
      let config;
      try {
        config = configuration(model, view.readForm());
        checkRequiredInputs(config, model.session.limits);
      } catch (error) {
        fail(error);
        return;
      }
      const revision = model.revision;
      model.phase = "validating";
      render();
      try {
        const result = await api.request("/api/validate", config);
        const accepted = receiveValidation(model, revision, result, config);
        render();
        if (accepted) view.focusPreview();
      } catch (error) {
        model.phase = "editing";
        render();
        if (revision === model.revision) view.showError(error);
      }
    },

    async confirm() {
      if (!availability(model).confirm) return;
      model.phase = "saving";
      view.clearError();
      render();
      try {
        const receipt = await api.request("/api/confirm", { validation_id: model.preview.id });
        receiveReceipt(model, receipt);
        view.clearApiKey();
        render();
        view.focusReceipt();
      } catch (error) {
        receiveSaveError(model, error);
        // 恢复控件后再聚焦错误；未知结果的冻结状态不会被 finally 意外清除。
        fail(error);
      }
    },

    async downloadTemplate() {
      if (!availability(model).template) return;
      model.downloadingTemplate = true;
      view.clearError();
      render();
      try {
        view.download(await api.template());
      } catch {
        view.showError(new Error("模板下载失败，请确认应用仍在运行后重试。"));
      } finally {
        model.downloadingTemplate = false;
        render();
      }
    },
  };
  view.bind(actions);
  return { model, actions };
}

if (typeof document !== "undefined") {
  const sessionToken = new URLSearchParams(window.location.hash.slice(1)).get("token") || "";
  // 会话令牌只留在请求闭包，不进入历史、链接或浏览器持久存储。
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
  createPresenter(createView(document), createApi(window.fetch.bind(window), sessionToken)).actions.start();
}
