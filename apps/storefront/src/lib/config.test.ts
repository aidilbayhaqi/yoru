import { afterEach, describe, expect, it } from "vitest";

import { getPublicApiBaseUrl } from "./config";

const originalValue = process.env.NEXT_PUBLIC_API_BASE_URL;

afterEach(() => {
  if (originalValue === undefined) {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  } else {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalValue;
  }
});

describe("storefront config", () => {
  it("uses a safe local default", () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    expect(getPublicApiBaseUrl()).toBe("http://localhost:8000/api/v1");
  });

  it("rejects a relative API URL", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "/api";
    expect(() => getPublicApiBaseUrl()).toThrow(/absolute URL/);
  });
});
