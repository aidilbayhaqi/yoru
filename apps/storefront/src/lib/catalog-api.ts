import { getServerApiBaseUrl } from "@/lib/config";
import { products as fallbackProducts, services as fallbackServices } from "@/lib/storefront-data";
import type { Product, Service } from "@/lib/storefront-types";

type ProductMediaResponse = {
  object_key: string;
  content_type: string;
  alt_text: string | null;
  status: string;
};

type CatalogProductResponse = {
  id: string;
  sku: string | null;
  name: string;
  slug: string;
  description: string;
  unit_price: string | number;
  currency: string;
  available_quantity: number | null;
  media: ProductMediaResponse[];
};

type CatalogServiceResponse = {
  id: string;
  name: string;
  slug: string;
  description: string;
  duration_minutes: number;
  price: string | number;
  currency: string;
  professionals: Array<{
    id: string;
    name: string;
    title: string | null;
  }>;
};

type ListResponse<T> = { data: T[] };

function toMinor(value: string | number): number {
  const amount = Number(value);
  return Number.isFinite(amount) ? Math.round(amount * 100) : 0;
}

function safeMediaPath(item: CatalogProductResponse, fallback: string): string {
  const media = item.media.find(
    (candidate) =>
      candidate.status === "ready" &&
      candidate.content_type.startsWith("image/") &&
      candidate.object_key.startsWith("/"),
  );
  return media?.object_key ?? fallback;
}

function mapProduct(item: CatalogProductResponse): Product | null {
  const fallback = fallbackProducts.find((product) => product.slug === item.slug);
  // Current cart/order demo resolves products from storefront-data by stable IDs.
  // Keep that identity until the cart is migrated to server-side catalog snapshots.
  if (!fallback) return null;

  const priceMinor = toMinor(item.unit_price);
  const stock = item.available_quantity ?? fallback.variants[0]?.stock ?? 0;
  return {
    ...fallback,
    name: item.name,
    description: item.description,
    image: safeMediaPath(item, fallback.image),
    priceMinor: priceMinor || fallback.priceMinor,
    variants: fallback.variants.map((variant, index) =>
      index === 0
        ? {
            ...variant,
            sku: item.sku ?? variant.sku,
            priceMinor: priceMinor || variant.priceMinor,
            stock,
          }
        : variant,
    ),
  };
}

function mapService(item: CatalogServiceResponse): Service | null {
  const fallback = fallbackServices.find((service) => service.slug === item.slug);
  if (!fallback) return null;

  const professionals =
    item.professionals.length > 0
      ? item.professionals.map((professional, index) => ({
          id: professional.id,
          name: professional.name,
          title: professional.title ?? "Professional",
          rating: fallback.professionals[index]?.rating ?? 4.8,
          completedJobs: fallback.professionals[index]?.completedJobs ?? 100,
          avatar:
            professional.name
              .split(/\s+/)
              .slice(0, 2)
              .map((part) => part[0]?.toUpperCase() ?? "")
              .join("") || "YP",
        }))
      : fallback.professionals;

  return {
    ...fallback,
    name: item.name,
    description: item.description,
    durationMin: item.duration_minutes,
    priceMinor: toMinor(item.price) || fallback.priceMinor,
    professionals,
  };
}

async function readList<T>(path: string): Promise<T[]> {
  const response = await fetch(`${getServerApiBaseUrl()}${path}`, {
    headers: { Accept: "application/json" },
    next: { revalidate: 30 },
  });
  if (!response.ok) {
    throw new Error(`Catalog API returned ${response.status}`);
  }
  const payload = (await response.json()) as ListResponse<T>;
  return Array.isArray(payload.data) ? payload.data : [];
}

export async function getCatalogProducts(): Promise<Product[]> {
  try {
    const items = await readList<CatalogProductResponse>(
      "/catalog/products?limit=100",
    );
    const mapped = items
      .map(mapProduct)
      .filter((item): item is Product => item !== null);
    return mapped.length > 0 ? mapped : fallbackProducts;
  } catch {
    return fallbackProducts;
  }
}

export async function getCatalogServices(): Promise<Service[]> {
  try {
    const items = await readList<CatalogServiceResponse>(
      "/catalog/services?limit=100",
    );
    const mapped = items
      .map(mapService)
      .filter((item): item is Service => item !== null);
    return mapped.length > 0 ? mapped : fallbackServices;
  } catch {
    return fallbackServices;
  }
}

export async function getCatalogProductBySlug(
  slug: string,
): Promise<Product | undefined> {
  return (await getCatalogProducts()).find((product) => product.slug === slug);
}

export async function getCatalogServiceBySlug(
  slug: string,
): Promise<Service | undefined> {
  return (await getCatalogServices()).find((service) => service.slug === slug);
}
