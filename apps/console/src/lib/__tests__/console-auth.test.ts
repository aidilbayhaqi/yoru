import { describe, expect, it } from "vitest";

import { hasConsoleAccess, safeDashboardReturnPath } from "@/lib/console-auth";

describe("hasConsoleAccess", () => {
  it("allows platform operators", () => {
    expect(hasConsoleAccess({ platform_roles: ["super_admin"], memberships: [] })).toBe(true);
  });

  it("allows active partner members", () => {
    expect(
      hasConsoleAccess({
        platform_roles: [],
        memberships: [
          {
            partner_id: "partner-1",
            membership_status: "active",
            partner_status: "verified",
          },
        ],
      }),
    ).toBe(true);
  });

  it("rejects accounts without operational access", () => {
    expect(hasConsoleAccess({ platform_roles: [], memberships: [] })).toBe(false);
  });

  it("rejects blocked or inactive partner access", () => {
    expect(
      hasConsoleAccess({
        platform_roles: [],
        memberships: [
          {
            partner_id: "partner-1",
            membership_status: "inactive",
            partner_status: "blocked",
          },
        ],
      }),
    ).toBe(false);
  });
});

describe("safeDashboardReturnPath", () => {
  it("keeps safe dashboard paths", () => {
    expect(safeDashboardReturnPath("/dashboard/products?status=draft")).toBe(
      "/dashboard/products?status=draft",
    );
  });

  it("rejects external and unrelated paths", () => {
    expect(safeDashboardReturnPath("https://evil.test")).toBe("/dashboard");
    expect(safeDashboardReturnPath("//evil.test/dashboard")).toBe("/dashboard");
    expect(safeDashboardReturnPath("/login")).toBe("/dashboard");
  });
});
