import { products, services } from "@/lib/storefront-data";
import type {
  CartLine,
  DemoBooking,
  DemoOrder,
  Product,
  Service,
  ShippingAddress,
} from "@/lib/storefront-types";

export function formatMoney(amountMinor: number, currency = "IDR"): string {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amountMinor / 100);
}

export function productBySlug(slug: string): Product | undefined {
  return products.find((product) => product.slug === slug);
}

export function productById(id: string): Product | undefined {
  return products.find((product) => product.id === id);
}

export function serviceBySlug(slug: string): Service | undefined {
  return services.find((service) => service.slug === slug);
}

export function serviceById(id: string): Service | undefined {
  return services.find((service) => service.id === id);
}

export function cartLineAmount(line: CartLine): number {
  const product = productById(line.productId);
  const variant = product?.variants.find((item) => item.id === line.variantId);
  return (variant?.priceMinor ?? product?.priceMinor ?? 0) * line.quantity;
}

export function cartSubtotal(lines: CartLine[]): number {
  return lines.reduce((total, line) => total + cartLineAmount(line), 0);
}

export function productCheckoutTotals(
  lines: CartLine[],
  deliveryMethod: string,
): {
  subtotalMinor: number;
  shippingMinor: number;
  serviceFeeMinor: number;
  discountMinor: number;
  totalMinor: number;
} {
  const subtotalMinor = cartSubtotal(lines);
  const shippingMinor =
    deliveryMethod === "express" ? 3500000 : deliveryMethod === "pickup" ? 0 : 1800000;
  const serviceFeeMinor = subtotalMinor > 0 ? 200000 : 0;
  const discountMinor = subtotalMinor >= 50000000 ? 2000000 : 0;

  return {
    subtotalMinor,
    shippingMinor,
    serviceFeeMinor,
    discountMinor,
    totalMinor: subtotalMinor + shippingMinor + serviceFeeMinor - discountMinor,
  };
}

export function serviceBookingTotals(service: Service): {
  serviceSubtotalMinor: number;
  transportMinor: number;
  platformFeeMinor: number;
  totalMinor: number;
} {
  const transportMinor = 2000000;
  const platformFeeMinor = 500000;
  return {
    serviceSubtotalMinor: service.priceMinor,
    transportMinor,
    platformFeeMinor,
    totalMinor: service.priceMinor + transportMinor + platformFeeMinor,
  };
}

export function safeReturnPath(candidate: string | undefined, fallback = "/account"): string {
  if (!candidate || !candidate.startsWith("/") || candidate.startsWith("//")) {
    return fallback;
  }

  try {
    const parsed = new URL(candidate, "https://yoru.local");
    if (parsed.origin !== "https://yoru.local") {
      return fallback;
    }
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return fallback;
  }
}

export function randomId(prefix: string): string {
  const suffix =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().replaceAll("-", "").slice(0, 12)
      : `${Date.now()}${Math.random().toString(16).slice(2, 8)}`;
  return `${prefix}_${suffix}`;
}

export function buildOrder(input: {
  lines: CartLine[];
  address: ShippingAddress;
  paymentMethod: string;
  deliveryMethod: string;
}): DemoOrder {
  const createdAt = new Date().toISOString();
  const totals = productCheckoutTotals(input.lines, input.deliveryMethod);
  const id = randomId("ord");

  return {
    id,
    number: `YR-${new Date().getFullYear()}-${id.slice(-6).toUpperCase()}`,
    createdAt,
    status: "processing",
    paymentStatus: "paid",
    paymentMethod: input.paymentMethod,
    deliveryMethod: input.deliveryMethod,
    address: input.address,
    items: input.lines,
    ...totals,
    timeline: [
      {
        label: "Pesanan dibuat",
        detail: "Harga, stok, dan alamat sudah dikonfirmasi.",
        occurredAt: createdAt,
        completed: true,
      },
      {
        label: "Pembayaran berhasil",
        detail: "Pembayaran demo terverifikasi dan pesanan diteruskan ke partner.",
        occurredAt: createdAt,
        completed: true,
      },
      {
        label: "Diproses partner",
        detail: "Partner menyiapkan produk dan nomor pengiriman.",
        occurredAt: createdAt,
        completed: true,
      },
      {
        label: "Dalam pengiriman",
        detail: "Status akan berubah setelah shipment dibuat.",
        occurredAt: createdAt,
        completed: false,
      },
      {
        label: "Selesai",
        detail: "Pesanan diterima customer.",
        occurredAt: createdAt,
        completed: false,
      },
    ],
  };
}

export function buildBooking(input: {
  service: Service;
  address: ShippingAddress;
  scheduledAt: string;
  professionalId: string;
  paymentMethod: string;
  notes?: string;
}): DemoBooking {
  const createdAt = new Date().toISOString();
  const totals = serviceBookingTotals(input.service);
  const professional =
    input.service.professionals.find((item) => item.id === input.professionalId) ??
    input.service.professionals[0];
  const id = randomId("bkg");

  return {
    id,
    number: `YB-${new Date().getFullYear()}-${id.slice(-6).toUpperCase()}`,
    createdAt,
    status: "confirmed",
    paymentStatus: "paid",
    paymentMethod: input.paymentMethod,
    serviceId: input.service.id,
    serviceName: input.service.name,
    scheduledAt: input.scheduledAt,
    professionalId: professional.id,
    professionalName: professional.name,
    address: input.address,
    notes: input.notes,
    otp: "4821",
    ...totals,
    timeline: [
      {
        label: "Booking dibuat",
        detail: "Slot dan area layanan sudah dikunci.",
        occurredAt: createdAt,
        completed: true,
      },
      {
        label: "Pembayaran berhasil",
        detail: "Pembayaran demo terverifikasi.",
        occurredAt: createdAt,
        completed: true,
      },
      {
        label: "Profesional dikonfirmasi",
        detail: `${professional.name} ditugaskan untuk booking ini.`,
        occurredAt: createdAt,
        completed: true,
      },
      {
        label: "Perjalanan dimulai",
        detail: "Tracking aktif saat profesional menuju lokasi.",
        occurredAt: createdAt,
        completed: false,
      },
      {
        label: "Layanan dimulai",
        detail: "Customer memberikan OTP setelah profesional tiba.",
        occurredAt: createdAt,
        completed: false,
      },
      {
        label: "Selesai",
        detail: "Checklist dan bukti penyelesaian tersimpan.",
        occurredAt: createdAt,
        completed: false,
      },
    ],
  };
}
