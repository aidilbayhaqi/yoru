import { describe, expect, it } from "vitest";

import { products, services } from "@/lib/storefront-data";
import {
  cartSubtotal,
  productCheckoutTotals,
  safeReturnPath,
  serviceBookingTotals,
} from "@/lib/storefront-domain";
import { isProtectedStorefrontPath } from "@/lib/storefront-auth";

describe("storefront domain", () => {
  it("calculates product cart separately from service booking", () => {
    const line = {
      lineId: "line_1",
      productId: products[0].id,
      variantId: products[0].variants[0].id,
      quantity: 2,
    };

    expect(cartSubtotal([line])).toBe(products[0].variants[0].priceMinor * 2);
    expect(productCheckoutTotals([line], "regular").totalMinor).toBeGreaterThan(0);
    expect(serviceBookingTotals(services[0]).totalMinor).toBeGreaterThan(services[0].priceMinor);
  });

  it("keeps redirects on the storefront origin", () => {
    expect(safeReturnPath("/checkout?step=2")).toBe("/checkout?step=2");
    expect(safeReturnPath("https://evil.example")).toBe("/account");
    expect(safeReturnPath("//evil.example")).toBe("/account");
  });

  it("protects customer transaction routes", () => {
    expect(isProtectedStorefrontPath("/checkout")).toBe(true);
    expect(isProtectedStorefrontPath("/orders/ord_1")).toBe(true);
    expect(isProtectedStorefrontPath("/services/home-facial-reset/book")).toBe(true);
    expect(isProtectedStorefrontPath("/products")).toBe(false);
    expect(isProtectedStorefrontPath("/services/home-facial-reset")).toBe(false);
  });
});
