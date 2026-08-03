import { describe, expect, it } from "vitest";

import { products, services } from "@/lib/storefront-data";
import { filterProducts, filterServices } from "@/lib/storefront-filters";

describe("catalog filtering", () => {
  it("filters products by category, stock, price, and rating", () => {
    const result = filterProducts(products, {
      query: "",
      category: "Skincare",
      partner: "Semua",
      maxPriceMinor: 20000000,
      minRating: 4.6,
      onlyInStock: true,
      sort: "price_asc",
    });

    expect(result.length).toBeGreaterThan(0);
    expect(result.every((product) => product.category === "Skincare")).toBe(true);
    expect(result.every((product) => product.priceMinor <= 20000000)).toBe(true);
  });

  it("filters services by query, duration, price, and rating", () => {
    const result = filterServices(services, {
      query: "home",
      category: "Semua",
      maxPriceMinor: 35000000,
      maxDurationMin: 90,
      minRating: 4.7,
      sort: "duration_asc",
    });

    expect(result.length).toBeGreaterThan(0);
    expect(result.every((service) => service.durationMin <= 90)).toBe(true);
    expect(result.every((service) => service.priceMinor <= 35000000)).toBe(true);
  });
});
