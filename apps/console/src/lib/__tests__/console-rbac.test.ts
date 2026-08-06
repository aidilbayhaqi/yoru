import { describe, expect, it } from "vitest";

import {
  hasConsoleAccess,
  isSuperAdmin,
  resolveConsoleAccess,
  safeDashboardReturnPath,
} from "@/lib/console-auth";
import { sectionBelongsToRole } from "@/lib/console-dashboard";

const partner = {
  active_partner_id: "p-1",
  platform_roles: [],
  memberships: [
    {
      partner_id: "p-1",
      role: "partner_owner",
      membership_status: "active",
      partner_status: "verified",
    },
  ],
};

const admin = { active_partner_id: null, platform_roles: ["super_admin"], memberships: [] };

const verifier = {
  active_partner_id: null,
  platform_roles: ["platform_verifier"],
  memberships: [],
};

const blockedPartner = {
  active_partner_id: "p-2",
  platform_roles: [],
  memberships: [
    {
      partner_id: "p-2",
      role: "partner_owner",
      membership_status: "active",
      partner_status: "suspended",
    },
  ],
};

const unknownPartnerRole = {
  active_partner_id: "p-3",
  platform_roles: [],
  memberships: [
    {
      partner_id: "p-3",
      role: "customer",
      membership_status: "active",
      partner_status: "verified",
    },
  ],
};

describe("console RBAC", () => {
  it("resolves only exact super_admin as superadmin", () => {
    expect(isSuperAdmin(admin)).toBe(true);
    expect(resolveConsoleAccess(verifier)).toBeNull();
  });

  it("allows only supported active partner memberships", () => {
    expect(resolveConsoleAccess(partner)).toBe("partner");
    expect(hasConsoleAccess(partner)).toBe(true);
    expect(resolveConsoleAccess(blockedPartner)).toBeNull();
    expect(resolveConsoleAccess(unknownPartnerRole)).toBeNull();
  });

  it("separates partner and superadmin sections", () => {
    expect(sectionBelongsToRole("partner", "products")).toBe(true);
    expect(sectionBelongsToRole("partner", "security")).toBe(false);
    expect(sectionBelongsToRole("superadmin", "security")).toBe(true);
    expect(sectionBelongsToRole("superadmin", "products")).toBe(false);
  });

  it("rejects unsafe return paths", () => {
    expect(safeDashboardReturnPath("https://evil.test")).toBe("/dashboard");
    expect(safeDashboardReturnPath("/dashboard?section=finance")).toBe(
      "/dashboard?section=finance",
    );
  });
});
