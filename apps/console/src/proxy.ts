import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, CSRF_COOKIE, safeDashboardReturnPath } from "@/lib/console-auth";

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
  if (pathname === "/") return NextResponse.redirect(new URL("/login", request.url));

  const isDashboard = pathname === "/dashboard" || pathname.startsWith("/dashboard/");
  const isPublicAuthPage = pathname === "/login" || pathname === "/register";
  const hasAccessCookie = Boolean(request.cookies.get(ACCESS_COOKIE)?.value);
  const hasRefreshSessionHint = Boolean(request.cookies.get(CSRF_COOKIE)?.value);

  if (isDashboard && !hasAccessCookie && !hasRefreshSessionHint) {
    return loginRedirect(request, "authentication_required");
  }

  if (isPublicAuthPage && hasAccessCookie) {
    return NextResponse.redirect(
      new URL(safeDashboardReturnPath(request.nextUrl.searchParams.get("next")), request.url),
    );
  }

  return NextResponse.next();
}

export const config = { matcher: ["/", "/login", "/register", "/dashboard/:path*"] };
