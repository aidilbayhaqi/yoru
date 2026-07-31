const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

export function getPublicApiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const url = new URL(value);
  if (!["http:", "https:"].includes(url.protocol)) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must use HTTP or HTTPS");
  }
  return url.toString().replace(/\/$/, "");
}
