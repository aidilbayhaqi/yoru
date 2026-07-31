import type { ProblemDetails } from "@yoru/contracts";

import { getPublicApiBaseUrl } from "@/lib/config";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
  ) {
    super(message);
  }
}

function csrfToken(): string | undefined {
  if (typeof document === "undefined") {
    return undefined;
  }
  const prefix = "yoru_csrf=";
  const cookie = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = csrfToken();
    if (token) {
      headers.set("X-CSRF-Token", token);
    }
  }

  let response = await fetch(`${getPublicApiBaseUrl()}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (
    response.status === 401 &&
    !["/auth/login", "/auth/register", "/auth/refresh"].includes(path)
  ) {
    const token = csrfToken();
    if (token) {
      const refresh = await fetch(`${getPublicApiBaseUrl()}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          "X-CSRF-Token": token,
        },
      });
      if (refresh.ok) {
        const retryHeaders = new Headers(headers);
        const refreshedCsrf = csrfToken();
        if (refreshedCsrf && !["GET", "HEAD", "OPTIONS"].includes(method)) {
          retryHeaders.set("X-CSRF-Token", refreshedCsrf);
        }
        response = await fetch(`${getPublicApiBaseUrl()}${path}`, {
          ...init,
          method,
          headers: retryHeaders,
          credentials: "include",
          cache: "no-store",
        });
      }
    }
  }
  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as ProblemDetails | null;
    throw new ApiError(
      problem?.detail ?? problem?.title ?? "Permintaan tidak dapat diproses.",
      response.status,
      problem?.code ?? "REQUEST_FAILED",
    );
  }
  return (await response.json()) as T;
}
