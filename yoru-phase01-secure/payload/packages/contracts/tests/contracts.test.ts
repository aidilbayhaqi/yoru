import { describe, expect, it } from "vitest";

import { PLATFORM_ROLES } from "../src";

describe("platform contracts", () => {
  it("keeps customer and platform administration roles explicit", () => {
    expect(PLATFORM_ROLES).toContain("customer");
    expect(PLATFORM_ROLES).toContain("super_admin");
    expect(new Set(PLATFORM_ROLES).size).toBe(PLATFORM_ROLES.length);
  });
});
