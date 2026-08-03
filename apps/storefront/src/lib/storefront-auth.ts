export { safeReturnPath } from "@/lib/storefront-domain";

export const protectedStorefrontPrefixes = [
  "/account",
  "/checkout",
  "/orders",
  "/bookings",
  "/assistant",
  "/tracking",
  "/history",
];

export function isProtectedStorefrontPath(pathname: string): boolean {
  return (
    protectedStorefrontPrefixes.some(
      (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
    ) ||
    (pathname.startsWith("/services/") && pathname.endsWith("/book"))
  );
}
