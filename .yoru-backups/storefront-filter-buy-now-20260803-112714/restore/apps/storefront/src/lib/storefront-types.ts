export type ProductVariant = {
  id: string;
  name: string;
  sku: string;
  priceMinor: number;
  stock: number;
};

export type Product = {
  id: string;
  slug: string;
  name: string;
  category: string;
  partner: string;
  partnerLocation: string;
  image: string;
  priceMinor: number;
  compareAtMinor?: number;
  rating: number;
  reviewCount: number;
  badge?: string;
  description: string;
  highlights: string[];
  variants: ProductVariant[];
  shippingEta: string;
  tags: string[];
};

export type ServiceProfessional = {
  id: string;
  name: string;
  title: string;
  rating: number;
  completedJobs: number;
  avatar: string;
};

export type Service = {
  id: string;
  slug: string;
  name: string;
  category: string;
  partner: string;
  image: string;
  priceMinor: number;
  durationMin: number;
  rating: number;
  reviewCount: number;
  badge?: string;
  description: string;
  includes: string[];
  serviceArea: string;
  professionals: ServiceProfessional[];
  tags: string[];
};

export type CartLine = {
  lineId: string;
  productId: string;
  variantId: string;
  quantity: number;
};

export type ShippingAddress = {
  recipientName: string;
  phone: string;
  addressLine: string;
  city: string;
  postalCode: string;
  notes?: string;
};

export type TimelineItem = {
  label: string;
  detail: string;
  occurredAt: string;
  completed: boolean;
};

export type DemoOrder = {
  id: string;
  number: string;
  createdAt: string;
  status: "awaiting_payment" | "processing" | "shipped" | "delivered" | "cancelled";
  paymentStatus: "pending" | "paid" | "failed" | "refunded";
  paymentMethod: string;
  paymentExpiresAt?: string | null;
  fulfillmentStatus?:
    | "unfulfilled"
    | "packing"
    | "shipped"
    | "delivered"
    | "cancelled";
  deliveryMethod: string;
  courier?: string | null;
  trackingNumber?: string | null;
  estimatedDeliveryAt?: string | null;
  refundStatus?: "none" | "requested" | "processing" | "refunded";
  disputeStatus?: "none" | "open" | "resolved";
  cancellationReason?: string | null;
  updatedAt?: string;
  subtotalMinor: number;
  shippingMinor: number;
  serviceFeeMinor: number;
  discountMinor: number;
  totalMinor: number;
  address: ShippingAddress;
  items: CartLine[];
  timeline: TimelineItem[];
};

export type DemoBooking = {
  id: string;
  number: string;
  createdAt: string;
  status:
    | "requested"
    | "confirmed"
    | "assigned"
    | "en_route"
    | "arrived"
    | "in_service"
    | "completed"
    | "cancelled";
  paymentStatus: "pending" | "paid" | "failed" | "refunded";
  paymentMethod: string;
  paymentExpiresAt?: string | null;
  refundStatus?: "none" | "requested" | "processing" | "refunded";
  cancellationReason?: string | null;
  rescheduleCount?: number;
  updatedAt?: string;
  serviceId: string;
  serviceName: string;
  scheduledAt: string;
  professionalId: string;
  professionalName: string;
  address: ShippingAddress;
  notes?: string;
  serviceSubtotalMinor: number;
  transportMinor: number;
  platformFeeMinor: number;
  totalMinor: number;
  otp: string;
  timeline: TimelineItem[];
};

export type StorefrontState = {
  cart: CartLine[];
  buyNow: CartLine | null;
  orders: DemoOrder[];
  bookings: DemoBooking[];
  favorites: string[];
};
