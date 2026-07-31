export const PLATFORM_ROLES = [
  "customer",
  "partner_owner",
  "partner_admin",
  "partner_finance",
  "professional",
  "super_admin",
  "platform_verifier",
  "platform_support",
  "platform_finance",
] as const;

export type PlatformRole = (typeof PLATFORM_ROLES)[number];

export type HealthStatus = "ok" | "degraded" | "unavailable";

export interface DependencyHealth {
  status: HealthStatus;
  latency_ms?: number;
}

export interface HealthResponse {
  status: HealthStatus;
  service: string;
  version: string;
  request_id: string;
  dependencies?: Record<string, DependencyHealth>;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  code: string;
  detail?: string;
  instance?: string;
  request_id: string;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  status: string;
}

export interface PartnerMembership {
  partner_id: string;
  partner_status: string;
  membership_status: string;
  role: string;
  permissions: string[];
}

export interface AuthSession {
  user: AuthUser;
  active_partner_id: string | null;
  platform_roles: string[];
  permissions: string[];
  memberships: PartnerMembership[];
}
