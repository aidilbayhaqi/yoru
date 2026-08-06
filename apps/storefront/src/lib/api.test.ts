import { describe, expect, it } from "vitest";

import { parseApiErrorPayload } from "@/lib/api";

describe("parseApiErrorPayload", () => {
  it("parses the stable Yoru validation contract", () => {
    const result = parseApiErrorPayload(
      {
        code: "REQUEST_VALIDATION_FAILED",
        detail: "One or more request fields are invalid.",
        request_id: "req-422",
        errors: [
          {
            field: "email",
            message: "value is not a valid email address",
            code: "value_error",
            location: ["body", "email"],
          },
        ],
      },
      422,
    );

    expect(result.code).toBe("REQUEST_VALIDATION_FAILED");
    expect(result.requestId).toBe("req-422");
    expect(result.fieldErrors.email).toEqual(["value is not a valid email address"]);
  });

  it("remains compatible with FastAPI's default validation payload", () => {
    const result = parseApiErrorPayload(
      {
        detail: [
          {
            loc: ["body", "full_name"],
            msg: "String should have at least 2 characters",
            type: "string_too_short",
          },
        ],
      },
      422,
      "header-request-id",
    );

    expect(result.fieldErrors.full_name).toEqual(["String should have at least 2 characters"]);
    expect(result.requestId).toBe("header-request-id");
  });
});
