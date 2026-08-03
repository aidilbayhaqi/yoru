import { type NextRequest, NextResponse } from "next/server";

import { isProtectedStorefrontPath } from "@/lib/storefront-auth";

export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  if (!isProtectedStorefrontPath(pathname)) {
    return NextResponse.next();
  }

  const hasSession =
    Boolean(request.cookies.get("yoru_access")?.value) ||
    Boolean(request.cookies.get("yoru_refresh")?.value);

  if (hasSession) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
  loginUrl.searchParams.set("reason", "authentication_required");
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/account/:path*",
    "/checkout/:path*",
    "/orders/:path*",
    "/bookings/:path*",
    "/assistant/:path*",
    "/tracking/:path*",
    "/history/:path*",
    "/services/:path*",
  ],
};
