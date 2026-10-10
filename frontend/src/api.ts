import { requestDemoApi } from "./demoApi";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export type ApiError = Error & { status?: number };

export function saveSession(data: {
  access_token: string;
  refresh_token: string;
  role: "candidate" | "employer";
  onboarding_completed: boolean;
}) {
  window.localStorage.setItem("fsp-access-token", data.access_token);
  window.localStorage.setItem("fsp-refresh-token", data.refresh_token);
  window.localStorage.setItem("fsp-role", data.role);
  window.localStorage.setItem("fsp-onboarding-completed", String(data.onboarding_completed));
}

export function clearSession() {
  window.localStorage.removeItem("fsp-access-token");
  window.localStorage.removeItem("fsp-refresh-token");
  window.localStorage.removeItem("fsp-role");
  window.localStorage.removeItem("fsp-onboarding-completed");
}

function errorMessage(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item && typeof item === "object" && "msg" in item ? String(item.msg) : String(item)).join("; ");
    }
  }
  return fallback;
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (window.localStorage.getItem("fsp-offline-demo") === "true") {
    return requestDemoApi<T>(path, options);
  }

  const headers = new Headers(options.headers);
  const token = window.localStorage.getItem("fsp-access-token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !(options.body instanceof Blob)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error("Не удалось связаться с сервером. Проверьте, запущен ли backend.");
  }

  if (!response.ok) {
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    const error = new Error(errorMessage(payload, `Ошибка сервера (${response.status})`)) as ApiError;
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/pdf") || contentType.startsWith("image/") || contentType.includes("application/octet-stream")) {
    return (await response.blob()) as T;
  }
  if (contentType.includes("application/json")) return (await response.json()) as T;
  return undefined as T;
}

export function apiGet<T>(path: string) {
  return apiRequest<T>(path);
}

export function apiPost<T>(path: string, body?: unknown) {
  return apiRequest<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
}

export function apiPut<T>(path: string, body: unknown) {
  return apiRequest<T>(path, { method: "PUT", body: JSON.stringify(body) });
}
