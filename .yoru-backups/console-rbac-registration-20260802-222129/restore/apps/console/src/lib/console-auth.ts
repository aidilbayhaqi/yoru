export const ACCESS_COOKIE = "yoru_access";
export const REFRESH_COOKIE = "yoru_refresh";
export const CSRF_COOKIE = "yoru_csrf";

export type ConsoleSessionShape = {
  platform_roles: string[];
  memberships: Array<{
    partner_id: string;
    membership_status?: string;
    partner_status?: string;
  }>;
};

export function hasConsoleAccess(session: ConsoleSessionShape): boolean {
  const hasPlatformRole = session.platform_roles.length > 0;
  const hasActiveMembership = session.memberships.some((membership) => {
    const membershipActive =
      membership.membership_status === undefined || membership.membership_status === "active";
    const partnerAvailable =
      membership.partner_status === undefined ||
      !["rejected", "suspended", "blocked"].includes(membership.partner_status);

    return membershipActive && partnerAvailable;
  });

  return hasPlatformRole || hasActiveMembership;
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
