import { describe, expect, it } from "vitest";

import { ApiError, parseApiErrorPayload } from "@/lib/api";
import { presentAuthError, validateLogin, validateRegistration } from "@/lib/auth-errors";

describe("auth error handling", () => {
  it("parses FastAPI validation issues into field errors", () => {
    const parsed = parseApiErrorPayload(
      {
        detail: [
          {
            loc: ["body", "password"],
            msg: "Value error, Password must use at least three character categories",
            type: "value_error",
          },
        ],
      },
      422,
    );

    expect(parsed.code).toBe("REQUEST_VALIDATION_FAILED");
    expect(parsed.fieldErrors.password?.[0]).toContain(
      "Password must use at least three character categories",
    );
  });

  it("maps account conflict to the email field", () => {
    const presented = presentAuthError(
      new ApiError("Account cannot be created", 409, "ACCOUNT_EXISTS"),
      "register",
    );

    expect(presented.fieldErrors.email).toContain("sudah terdaftar");
  });

  it("validates login before sending the request", () => {
    const errors = validateLogin({
      email: "not-an-email",
      password: "",
    });

    expect(errors.email).toBeTruthy();
    expect(errors.password).toBeTruthy();
  });

  it("validates registration before sending the request", () => {
    const errors = validateRegistration({
      fullName: "A",
      email: "not-an-email",
      password: "short",
      confirmPassword: "different",
      acceptedTerms: false,
    });

    expect(errors.full_name).toBeTruthy();
    expect(errors.email).toBeTruthy();
    expect(errors.password).toBeTruthy();
    expect(errors.confirm_password).toBeTruthy();
    expect(errors.terms).toBeTruthy();
  });
});
