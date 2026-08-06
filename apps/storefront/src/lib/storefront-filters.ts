import type { Product, Service } from "@/lib/storefront-types";

export type ProductSort = "recommended" | "price_asc" | "price_desc" | "rating_desc";
export type ServiceSort =
  | "recommended"
  | "price_asc"
  | "price_desc"
  | "rating_desc"
  | "duration_asc";

export type ProductFilters = {
  query: string;
  category: string;
  partner: string;
  maxPriceMinor: number | null;
  minRating: number;
  onlyInStock: boolean;
  sort: ProductSort;
};

export type ServiceFilters = {
  query: string;
  category: string;
  maxPriceMinor: number | null;
  maxDurationMin: number | null;
  minRating: number;
  sort: ServiceSort;
};

function includesQuery(values: string[], query: string): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return values.join(" ").toLowerCase().includes(normalized);
}

export function filterProducts(items: Product[], filters: ProductFilters): Product[] {
  const result = items.filter((product) => {
    const matchesQuery = includesQuery(
      [product.name, product.category, product.partner, product.description, ...product.tags],
      filters.query,
    );
    const matchesCategory = filters.category === "Semua" || product.category === filters.category;
    const matchesPartner = filters.partner === "Semua" || product.partner === filters.partner;
    const matchesPrice =
      filters.maxPriceMinor === null || product.priceMinor <= filters.maxPriceMinor;
    const matchesRating = product.rating >= filters.minRating;
    const matchesStock =
      !filters.onlyInStock || product.variants.some((variant) => variant.stock > 0);

    return (
      matchesQuery &&
      matchesCategory &&
      matchesPartner &&
      matchesPrice &&
      matchesRating &&
      matchesStock
    );
  });

  return [...result].sort((left, right) => {
    switch (filters.sort) {
      case "price_asc":
        return left.priceMinor - right.priceMinor;
      case "price_desc":
        return right.priceMinor - left.priceMinor;
      case "rating_desc":
        return right.rating - left.rating || right.reviewCount - left.reviewCount;
      default:
        return (
          Number(Boolean(right.badge)) - Number(Boolean(left.badge)) ||
          right.rating - left.rating ||
          right.reviewCount - left.reviewCount
        );
    }
  });
}

export function filterServices(items: Service[], filters: ServiceFilters): Service[] {
  const result = items.filter((service) => {
    const matchesQuery = includesQuery(
      [
        service.name,
        service.category,
        service.partner,
        service.description,
        service.serviceArea,
        ...service.tags,
      ],
      filters.query,
    );
    const matchesCategory = filters.category === "Semua" || service.category === filters.category;
    const matchesPrice =
      filters.maxPriceMinor === null || service.priceMinor <= filters.maxPriceMinor;
    const matchesDuration =
      filters.maxDurationMin === null || service.durationMin <= filters.maxDurationMin;
    const matchesRating = service.rating >= filters.minRating;

    return matchesQuery && matchesCategory && matchesPrice && matchesDuration && matchesRating;
  });

  return [...result].sort((left, right) => {
    switch (filters.sort) {
      case "price_asc":
        return left.priceMinor - right.priceMinor;
      case "price_desc":
        return right.priceMinor - left.priceMinor;
      case "rating_desc":
        return right.rating - left.rating || right.reviewCount - left.reviewCount;
      case "duration_asc":
        return left.durationMin - right.durationMin || right.rating - left.rating;
      default:
        return (
          Number(Boolean(right.badge)) - Number(Boolean(left.badge)) ||
          right.rating - left.rating ||
          right.reviewCount - left.reviewCount
        );
    }
  });
}
