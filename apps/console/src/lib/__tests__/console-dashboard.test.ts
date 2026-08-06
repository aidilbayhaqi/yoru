import { describe, expect, it } from "vitest";

import { formatCurrency, navigationForRole, resolveConsoleRole } from "../console-dashboard";

describe("console dashboard model", () => {
  it("resolves platform roles as superadmin", () => {
    expect(
      resolveConsoleRole({
        platform_roles: ["super_admin"],
        memberships: [],
        active_partner_id: null,
      }),
    ).toBe("superadmin");
  });

  it("resolves partner memberships as partner role", () => {
    expect(
      resolveConsoleRole({
        platform_roles: [],
        memberships: [
          {
            partner_id: "p1",
            role: "partner_owner",
            partner_status: "verified",
            membership_status: "active",
          },
        ],
        active_partner_id: "p1",
      }),
    ).toBe("partner");
  });

  it("exposes role-specific navigation", () => {
    expect(
      navigationForRole("partner")
        .flatMap((group) => group.items)
        .some((item) => item.id === "products"),
    ).toBe(true);
    expect(
      navigationForRole("superadmin")
        .flatMap((group) => group.items)
        .some((item) => item.id === "partner-verification"),
    ).toBe(true);
  });

  it("formats IDR currency", () => {
    expect(formatCurrency(1250000)).toContain("1.250.000");
  });
});
