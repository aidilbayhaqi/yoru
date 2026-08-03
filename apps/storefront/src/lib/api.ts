import type { ProblemDetails } from "@yoru/contracts";

import { getPublicApiBaseUrl } from "@/lib/config";

export type ApiFieldErrors = Record<string, string[]>;

type ValidationIssue = {
  field?: string;
  message?: string;
  code?: string;
  location?: Array<string | number>;
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
};

type ParsedApiError = {
  message: string;
  code: string;
  fieldErrors: ApiFieldErrors;
  requestId?: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
    public readonly fieldErrors: ApiFieldErrors = {},
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let refreshPromise: Promise<boolean> | null = null;

function csrfToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const prefix = "yoru_csrf=";
  const cookie = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isValidationIssue(value: unknown): value is ValidationIssue {
  return isRecord(value);
}

function validationField(issue: ValidationIssue): string {
  if (typeof issue.field === "string" && issue.field) return issue.field;
  const location = issue.location ?? issue.loc ?? [];
  const candidate = [...location]
    .reverse()
    .find(
      (item): item is string =>
        typeof item === "string" &&
        !["body", "query", "path", "header", "cookie"].includes(item),
    );
  return candidate ?? "_form";
}

function validationMessage(issue: ValidationIssue): string {
  const message =
    typeof issue.message === "string"
      ? issue.message
      : typeof issue.msg === "string"
        ? issue.msg
        : "Nilai tidak valid.";
  return message.replace(/^Value error,\s*/i, "").trim();
}

export function parseApiErrorPayload(
  payload: unknown,
  status: number,
  responseRequestId?: string,
): ParsedApiError {
  if (!isRecord(payload)) {
    return {
      message:
        status >= 500
          ? "Layanan Yoru sedang mengalami gangguan."
          : "Permintaan tidak dapat diproses.",
      code: "REQUEST_FAILED",
      fieldErrors: {},
      requestId: responseRequestId,
    };
  }

  const requestId =
    typeof payload.request_id === "string" ? payload.request_id : responseRequestId;
  const detail = payload.detail;
  const rawIssues = Array.isArray(payload.errors)
    ? payload.errors
    : Array.isArray(detail)
      ? detail
      : [];

  if (rawIssues.length > 0) {
    const fieldErrors: ApiFieldErrors = {};
    for (const rawIssue of rawIssues) {
      if (!isValidationIssue(rawIssue)) continue;
      const field = validationField(rawIssue);
      const message = validationMessage(rawIssue);
      fieldErrors[field] = [...(fieldErrors[field] ?? []), message];
    }
    return {
      message:
        typeof detail === "string" && detail.trim()
          ? detail
          : "Periksa kembali data yang disorot.",
      code:
        typeof payload.code === "string" && payload.code
          ? payload.code
          : "REQUEST_VALIDATION_FAILED",
      fieldErrors,
      requestId,
    };
  }

  const problem = payload as Partial<ProblemDetails>;
  return {
    message:
      typeof detail === "string" && detail.trim()
        ? detail
        : typeof problem.title === "string" && problem.title.trim()
          ? problem.title
          : status === 422
            ? "Data yang dikirim belum valid."
            : "Permintaan tidak dapat diproses.",
    code:
      typeof problem.code === "string" && problem.code
        ? problem.code
        : status === 422
          ? "REQUEST_VALIDATION_FAILED"
          : "REQUEST_FAILED",
    fieldErrors: {},
    requestId,
  };
}

function shouldSetJsonContentType(body: BodyInit | null | undefined): boolean {
  if (typeof body !== "string") return false;
  return body.trimStart().startsWith("{") || body.trimStart().startsWith("[");
}

function buildHeaders(init: RequestInit, method: string): Headers {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && shouldSetJsonContentType(init.body) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = csrfToken();
    if (token) headers.set("X-CSRF-Token", token);
  }
  return headers;
}

async function refreshSession(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const token = csrfToken();
    if (!token) return false;
    try {
      const response = await fetch(`${getPublicApiBaseUrl()}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          "X-CSRF-Token": token,
        },
      });
      return response.ok;
    } catch {
      return false;
    }
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

async function performRequest(
  path: string,
  init: RequestInit,
  method: string,
): Promise<Response> {
  return fetch(`${getPublicApiBaseUrl()}${path}`, {
    ...init,
    method,
    headers: buildHeaders(init, method),
    credentials: "include",
    cache: "no-store",
  });
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  let response = await performRequest(path, init, method);

  const mayRefresh = !["/auth/login", "/auth/register", "/auth/refresh"].includes(path);
  if (response.status === 401 && mayRefresh && (await refreshSession())) {
    response = await performRequest(path, init, method);
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as unknown;
    const parsed = parseApiErrorPayload(
      payload,
      response.status,
      response.headers.get("X-Request-ID") ?? undefined,
    );
    throw new ApiError(
      parsed.message,
      response.status,
      parsed.code,
      parsed.fieldErrors,
      parsed.requestId,
    );
  }

  if (response.status === 204) return undefined as T;
  const contentLength = response.headers.get("content-length");
  if (contentLength === "0") return undefined as T;
  return (await response.json()) as T;
}
