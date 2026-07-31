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

describe("console config", () => {
  it("normalizes the API base URL", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "https://api.yoru.test/api/v1/";
    expect(getPublicApiBaseUrl()).toBe("https://api.yoru.test/api/v1");
  });

  it("rejects non-http schemes", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "file:///tmp/api";
    expect(() => getPublicApiBaseUrl()).toThrow(/HTTP or HTTPS/);
  });
});
