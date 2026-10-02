export type Language = "zh-CN" | "en";
export type Theme = "system" | "light" | "dark";
export type UploadKind = "audio" | "hotwords";
export type DirectoryKind = "json" | "document";
export type Phase = "loading" | "editing" | "validating" | "review" | "saving" | "saved" | "save_unknown" | "unavailable";
export type EnhancementMode = "none" | "hotwords" | "context" | "both";

export interface Limits {
  audio_bytes: number; hotwords_bytes: number; upload_bytes: number; audio_seconds: number;
  hotwords_count: number; context_chars: number; speaker_min: number; speaker_max: number;
}
export interface Receipt {
  job_id: string; config_path: string; json_directory: string; document_directory: string;
  auth_mode: "console" | "api_key"; execution_started: false;
}
export interface SessionDescription {
  model: string; region: string; limits: Limits; audio_suffixes: string[];
  languages: [string, string][]; output_defaults: Record<DirectoryKind, string>;
  confirmed: Receipt | null;
}
export interface Configuration {
  auth_mode: "console" | "api_key"; audio_upload_id: string | null; diarization_enabled: boolean;
  enhancement_mode: EnhancementMode; hotwords_upload_id: string | null; context: string;
  language_hint: string | null; speaker_count: number | null;
  json_directory: string; document_directory: string;
}
export interface FormValues {
  useApiKey: boolean; diarizationEnabled: boolean; hotwordsEnabled: boolean; contextEnabled: boolean;
  context: string; language: string; speaker: string;
}
export interface Summary {
  auth_mode: "console" | "api_key";
  audio: { name: string; duration_seconds: number; size_bytes: number; format_name: string; channels: number; sample_rate: number };
  enhancement: { mode: EnhancementMode; count: number; context_chars: number };
  json_directory: string; document_directory: string; warnings: string[];
}
export interface ValidationResult { validation_id: string; summary: Summary }
export interface Preview { id: string; summary: Summary; configuration: Configuration }
export interface UploadState { status: "empty" | "uploading" | "ready" | "failed"; id: string | null; name: string; size: number }
export interface Picker { id: string; kind: DirectoryKind; cancelling: boolean }
export interface Model {
  phase: Phase; revision: number; preview: Preview | null; receipt: Receipt | null;
  session: SessionDescription | null; directories: Record<DirectoryKind, string>;
  uploads: Record<UploadKind, UploadState>;
  auth: { revision: number; status: "idle" | "loading" | "saving" | "ready" | "dirty" | "failed" };
  picker: Picker | null; downloadingTemplate: boolean; statusMessage: "changed" | "languageChanged" | "saveRejected" | "";
}
export interface ErrorDetail { row?: number; field?: string; message: string }
export interface ErrorPayload { error?: string; ok?: boolean; field?: string; details?: ErrorDetail[] }
export interface UploadResult { upload_id: string; name: string; size_bytes: number }
export type DirectoryResult = { cancelled: true } | { cancelled: false; path: string };
export interface Endpoints {
  "/api/session": SessionDescription;
  "/api/api-key": { value: string };
  "/api/save-api-key": { ok: true };
  "/api/upload-audio": UploadResult;
  "/api/upload-hotwords": UploadResult;
  "/api/select-directory": DirectoryResult;
  "/api/cancel-directory": { ok: true };
  "/api/validate": ValidationResult;
  "/api/confirm": Receipt;
}
export interface Api {
  request<K extends keyof Endpoints>(path: K, payload?: object, file?: File): Promise<Endpoints[K]>;
  template(): Promise<Blob>;
}
