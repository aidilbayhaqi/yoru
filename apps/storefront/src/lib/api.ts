import type { ProblemDetails } from "@yoru/contracts";

import { getPublicApiBaseUrl } from "@/lib/config";

export type ApiFieldErrors = Record<string, string[]>;

type ValidationIssue = {
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isValidationIssue(value: unknown): value is ValidationIssue {
  return isRecord(value);
}

function validationField(issue: ValidationIssue): string {
  const location = issue.loc ?? [];
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
  const message = typeof issue.msg === "string" ? issue.msg : "Nilai tidak valid.";
  return message.replace(/^Value error,\s*/i, "").trim();
}

export function parseApiErrorPayload(
  payload: unknown,
  status: number,
): ParsedApiError {
  if (!isRecord(payload)) {
    return {
      message: "Permintaan tidak dapat diproses.",
      code: "REQUEST_FAILED",
      fieldErrors: {},
    };
  }

  const detail = payload.detail;
  const requestId =
    typeof payload.request_id === "string" ? payload.request_id : undefined;

  if (Array.isArray(detail)) {
    const fieldErrors: ApiFieldErrors = {};

    for (const rawIssue of detail) {
      if (!isValidationIssue(rawIssue)) continue;
      const field = validationField(rawIssue);
      const message = validationMessage(rawIssue);
      fieldErrors[field] = [...(fieldErrors[field] ?? []), message];
    }

    return {
      message: "Periksa kembali data yang disorot.",
      code: "REQUEST_VALIDATION_FAILED",
      fieldErrors,
      requestId,
    };
  }

  const problem = payload as Partial<ProblemDetails>;
  const message =
    typeof detail === "string" && detail.trim()
      ? detail
      : typeof problem.title === "string" && problem.title.trim()
        ? problem.title
        : status === 422
          ? "Data yang dikirim belum valid."
          : "Permintaan tidak dapat diproses.";

  return {
    message,
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

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
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
    const payload = (await response.json().catch(() => null)) as unknown;
    const parsed = parseApiErrorPayload(payload, response.status);

    throw new ApiError(
      parsed.message,
      response.status,
      parsed.code,
      parsed.fieldErrors,
      parsed.requestId,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
