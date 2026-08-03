import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  CSRF_COOKIE,
  safeDashboardReturnPath,
} from "@/lib/console-auth";

function loginRedirect(request: NextRequest, reason?: string): NextResponse {
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set(
    "next",
    safeDashboardReturnPath(`${request.nextUrl.pathname}${request.nextUrl.search}`),
  );
  if (reason) loginUrl.searchParams.set("reason", reason);
  return NextResponse.redirect(loginUrl);
}

export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  if (pathname === "/") {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const isDashboard = pathname === "/dashboard" || pathname.startsWith("/dashboard/");
  const isLogin = pathname === "/login";
  const hasAccessCookie = Boolean(request.cookies.get(ACCESS_COOKIE)?.value);
  const hasRefreshSessionHint = Boolean(request.cookies.get(CSRF_COOKIE)?.value);

  // Optimistic route gate. The dashboard and every backend endpoint still validate
  // the opaque session, role, tenant, capability, and RLS at the data boundary.
  if (isDashboard && !hasAccessCookie && !hasRefreshSessionHint) {
    return loginRedirect(request, "authentication_required");
  }

  // A valid access-cookie holder does not need to see the login form again.
  // A CSRF cookie alone is not enough for this redirect because it may be stale;
  // the dashboard client will perform refresh + /auth/me validation when opened.
  if (isLogin && hasAccessCookie) {
    const nextPath = safeDashboardReturnPath(request.nextUrl.searchParams.get("next"));
    return NextResponse.redirect(new URL(nextPath, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/login", "/dashboard/:path*"],
};
