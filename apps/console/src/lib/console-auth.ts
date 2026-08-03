export const ACCESS_COOKIE = "yoru_access";
export const REFRESH_COOKIE = "yoru_refresh";
export const CSRF_COOKIE = "yoru_csrf";

export type ConsoleRole = "superadmin" | "partner";

export type ConsoleSessionShape = {
  active_partner_id?: string | null;
  platform_roles: string[];
  memberships: Array<{
    partner_id: string;
    role?: string;
    membership_status?: string;
    partner_status?: string;
    permissions?: string[];
  }>;
};

const BLOCKED_PARTNER_STATES = new Set(["rejected", "suspended", "blocked"]);
const PARTNER_ROLES = new Set([
  "partner_owner",
  "partner_admin",
  "partner_finance",
  "professional",
]);

export function isSuperAdmin(session: ConsoleSessionShape): boolean {
  return session.platform_roles.some((role) => role.toLowerCase() === "super_admin");
}

export function eligiblePartnerMemberships(session: ConsoleSessionShape) {
  return session.memberships.filter((membership) => {
    const membershipActive =
      membership.membership_status === undefined || membership.membership_status === "active";
    const partnerAvailable =
      membership.partner_status === undefined ||
      !BLOCKED_PARTNER_STATES.has(membership.partner_status.toLowerCase());
    const roleAllowed =
      membership.role === undefined || PARTNER_ROLES.has(membership.role.toLowerCase());
    return membershipActive && partnerAvailable && roleAllowed;
  });
}

export function activePartnerMembership(session: ConsoleSessionShape) {
  const candidates = eligiblePartnerMemberships(session);
  return (
    candidates.find((membership) => membership.partner_id === session.active_partner_id) ??
    candidates[0] ??
    null
  );
}

export function resolveConsoleAccess(session: ConsoleSessionShape): ConsoleRole | null {
  if (isSuperAdmin(session)) return "superadmin";
  if (activePartnerMembership(session)) return "partner";
  return null;
}

export function hasConsoleAccess(session: ConsoleSessionShape): boolean {
  return resolveConsoleAccess(session) !== null;
}

export function safeDashboardReturnPath(value: string | null | undefined): string {
  if (!value) return "/dashboard";

  let decoded = value;
  try {
    decoded = decodeURIComponent(value);
  } catch {
    return "/dashboard";
  }

  if (!decoded.startsWith("/dashboard")) return "/dashboard";
  if (decoded.startsWith("//") || decoded.includes("\\")) return "/dashboard";
  return decoded;
}
