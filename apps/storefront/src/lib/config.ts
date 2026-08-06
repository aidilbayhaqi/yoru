const DEFAULT_PUBLIC_API_BASE_URL = "http://localhost:8000/api/v1";
const DEFAULT_INTERNAL_API_BASE_URL = "http://api:8000/api/v1";

function normalizeAbsoluteUrl(value: string, variableName: string): string {
  try {
    return new URL(value).toString().replace(/\/$/, "");
  } catch {
    throw new Error(`${variableName} must be an absolute URL`);
  }
}

export function getPublicApiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return normalizeAbsoluteUrl(value || DEFAULT_PUBLIC_API_BASE_URL, "NEXT_PUBLIC_API_BASE_URL");
}

export function getServerApiBaseUrl(): string {
  const value = process.env.API_INTERNAL_BASE_URL?.trim();
  if (value) {
    return normalizeAbsoluteUrl(value, "API_INTERNAL_BASE_URL");
  }
  return typeof window === "undefined" ? DEFAULT_INTERNAL_API_BASE_URL : getPublicApiBaseUrl();
}
