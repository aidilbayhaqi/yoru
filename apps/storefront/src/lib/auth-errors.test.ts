import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import { presentAuthError, validateRegistration } from "@/lib/auth-errors";

describe("registration validation", () => {
  it("matches the backend password policy", () => {
    expect(
      validateRegistration({
        fullName: "Aidil Bayhaqi",
        email: "aidil@example.com",
        password: "onlylowercase",
        confirmPassword: "onlylowercase",
        acceptedTerms: true,
      }).password,
    ).toContain("3 kategori");
  });

  it("maps backend 422 issues to the correct input", () => {
    const result = presentAuthError(
      new ApiError(
        "One or more request fields are invalid.",
        422,
        "REQUEST_VALIDATION_FAILED",
        { email: ["value is not a valid email address"] },
        "req-123",
      ),
      "register",
    );

    expect(result.fieldErrors.email).toContain("nama@domain.com");
    expect(result.message).toContain("email");
    expect(result.requestId).toBe("req-123");
  });
});
