"use client";

import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";

import { buildBooking, buildOrder, randomId } from "@/lib/storefront-domain";
import { products, services } from "@/lib/storefront-data";
import type {
  CartLine,
  DemoBooking,
  DemoOrder,
  Service,
  ShippingAddress,
  StorefrontState,
  TimelineItem,
} from "@/lib/storefront-types";

const STORAGE_KEY = "yoru_storefront_demo_v1";
const initialState: StorefrontState = {
  cart: [],
  buyNow: null,
  favorites: ["prd_glow_reset", "svc_home_facial"],
  orders: [],
  bookings: [],
};

const demoAddress: ShippingAddress = {
  recipientName: "Aidil Bayhaqi",
  phone: "+62 812 0000 0000",
  addressLine: "Jl. Contoh No. 9",
  city: "Jakarta Selatan",
  postalCode: "12190",
  notes: "Data development untuk menguji lifecycle transaksi.",
};

type CreateOrderInput = {
  address: ShippingAddress;
  paymentMethod: string;
  deliveryMethod: string;
  lines?: CartLine[];
};

type CreateBookingInput = {
  service: Service;
  address: ShippingAddress;
  scheduledAt: string;
  professionalId: string;
  paymentMethod: string;
  notes?: string;
};

type StorefrontContextValue = {
  state: StorefrontState;
  hydrated: boolean;
  cartCount: number;
  addProduct: (productId: string, variantId: string, quantity?: number) => void;
  setBuyNowProduct: (productId: string, variantId: string, quantity?: number) => void;
  clearBuyNow: () => void;
  updateCartQuantity: (lineId: string, quantity: number) => void;
  removeCartLine: (lineId: string) => void;
  clearCart: () => void;
  toggleFavorite: (id: string) => void;
  createOrder: (input: CreateOrderInput) => DemoOrder;
  createBooking: (input: CreateBookingInput) => DemoBooking;
  loadDemoHistory: () => void;
  retryOrderPayment: (orderId: string) => void;
  cancelOrder: (orderId: string, reason: string) => void;
  confirmOrderReceived: (orderId: string) => void;
  requestOrderRefund: (orderId: string, reason: string) => void;
  cancelBooking: (bookingId: string, reason: string) => void;
  rescheduleBooking: (bookingId: string) => void;
};

const StorefrontContext = createContext<StorefrontContextValue | null>(null);

function nowIso(): string {
  return new Date().toISOString();
}

function appendTimeline(
  timeline: TimelineItem[],
  label: string,
  detail: string,
  occurredAt = nowIso(),
): TimelineItem[] {
  return [
    ...timeline,
    {
      label,
      detail,
      occurredAt,
      completed: true,
    },
  ];
}

function completeTimeline(timeline: TimelineItem[], labels: string[]): TimelineItem[] {
  const normalized = new Set(labels.map((label) => label.toLowerCase()));
  return timeline.map((item) =>
    normalized.has(item.label.toLowerCase()) ? { ...item, completed: true } : item,
  );
}

function readStoredState(): StorefrontState {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (!value) return initialState;
    const parsed = JSON.parse(value) as Partial<StorefrontState>;
    return {
      cart: Array.isArray(parsed.cart) ? parsed.cart : [],
      buyNow:
        parsed.buyNow &&
        typeof parsed.buyNow === "object" &&
        "productId" in parsed.buyNow &&
        "variantId" in parsed.buyNow
          ? (parsed.buyNow as CartLine)
          : null,
      favorites: Array.isArray(parsed.favorites) ? parsed.favorites : [],
      orders: Array.isArray(parsed.orders) ? parsed.orders : [],
      bookings: Array.isArray(parsed.bookings) ? parsed.bookings : [],
    };
  } catch {
    return initialState;
  }
}

export function StorefrontProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<StorefrontState>(initialState);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setState(readStoredState());
      setHydrated(true);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [hydrated, state]);

  function addProduct(productId: string, variantId: string, quantity = 1) {
    setState((current) => {
      const existing = current.cart.find(
        (line) => line.productId === productId && line.variantId === variantId,
      );
      if (existing) {
        return {
          ...current,
          cart: current.cart.map((line) =>
            line.lineId === existing.lineId
              ? { ...line, quantity: Math.min(20, line.quantity + quantity) }
              : line,
          ),
        };
      }

      const line: CartLine = {
        lineId: randomId("line"),
        productId,
        variantId,
        quantity,
      };
      return { ...current, cart: [...current.cart, line] };
    });
  }

  function setBuyNowProduct(productId: string, variantId: string, quantity = 1) {
    const line: CartLine = {
      lineId: randomId("buy"),
      productId,
      variantId,
      quantity: Math.max(1, Math.min(20, quantity)),
    };
    setState((current) => ({ ...current, buyNow: line }));
  }

  function clearBuyNow() {
    setState((current) => ({ ...current, buyNow: null }));
  }

  function updateCartQuantity(lineId: string, quantity: number) {
    setState((current) => ({
      ...current,
      cart:
        quantity <= 0
          ? current.cart.filter((line) => line.lineId !== lineId)
          : current.cart.map((line) =>
              line.lineId === lineId
                ? { ...line, quantity: Math.min(20, quantity) }
                : line,
            ),
    }));
  }

  function removeCartLine(lineId: string) {
    setState((current) => ({
      ...current,
      cart: current.cart.filter((line) => line.lineId !== lineId),
    }));
  }

  function clearCart() {
    setState((current) => ({ ...current, cart: [] }));
  }

  function toggleFavorite(id: string) {
    setState((current) => ({
      ...current,
      favorites: current.favorites.includes(id)
        ? current.favorites.filter((item) => item !== id)
        : [...current.favorites, id],
    }));
  }

  function createOrder(input: CreateOrderInput): DemoOrder {
    const orderLines = input.lines ?? state.cart;
    const order = buildOrder({
      lines: orderLines,
      address: input.address,
      paymentMethod: input.paymentMethod,
      deliveryMethod: input.deliveryMethod,
    });
    setState((current) => ({
      ...current,
      cart: input.lines ? current.cart : [],
      buyNow: input.lines ? null : current.buyNow,
      orders: [order, ...current.orders],
    }));
    return order;
  }

  function createBooking(input: CreateBookingInput): DemoBooking {
    const booking = buildBooking(input);
    setState((current) => ({
      ...current,
      bookings: [booking, ...current.bookings],
    }));
    return booking;
  }

  function loadDemoHistory() {
    const product = products[0];
    const variant = product?.variants[0];
    const service = services[0];
    const professional = service?.professionals[0];
    if (!product || !variant || !service || !professional) return;

    const order = buildOrder({
      lines: [
        {
          lineId: randomId("line"),
          productId: product.id,
          variantId: variant.id,
          quantity: 1,
        },
      ],
      address: demoAddress,
      paymentMethod: "virtual_account",
      deliveryMethod: "regular",
    });
    const pendingOrder: DemoOrder = {
      ...order,
      status: "awaiting_payment",
      paymentStatus: "pending",
      paymentExpiresAt: new Date(Date.now() + 30 * 60_000).toISOString(),
      fulfillmentStatus: "unfulfilled",
      timeline: order.timeline.map((item, index) => ({
        ...item,
        completed: index === 0,
      })),
    };

    const booking = buildBooking({
      service,
      address: demoAddress,
      scheduledAt: new Date(Date.now() + 2 * 86_400_000).toISOString(),
      professionalId: professional.id,
      paymentMethod: "qris",
      notes: "Data development untuk menguji booking dan tracking.",
    });

    setState((current) => ({
      ...current,
      orders: current.orders.length > 0 ? current.orders : [pendingOrder],
      bookings: current.bookings.length > 0 ? current.bookings : [booking],
    }));
  }

  function retryOrderPayment(orderId: string) {
    const updatedAt = nowIso();
    setState((current) => ({
      ...current,
      orders: current.orders.map((order) =>
        order.id === orderId
          ? {
              ...order,
              status: "processing",
              paymentStatus: "paid",
              paymentExpiresAt: null,
              fulfillmentStatus: "packing",
              updatedAt,
              timeline: completeTimeline(order.timeline, [
                "Pembayaran berhasil",
                "Diproses partner",
              ]),
            }
          : order,
      ),
    }));
  }

  function cancelOrder(orderId: string, reason: string) {
    const updatedAt = nowIso();
    setState((current) => ({
      ...current,
      orders: current.orders.map((order) => {
        if (order.id !== orderId) return order;
        const wasPaid = order.paymentStatus === "paid";
        return {
          ...order,
          status: "cancelled",
          fulfillmentStatus: "cancelled",
          paymentStatus: wasPaid ? "refunded" : order.paymentStatus,
          refundStatus: wasPaid ? "refunded" : "none",
          cancellationReason: reason,
          updatedAt,
          timeline: appendTimeline(
            order.timeline,
            "Pesanan dibatalkan",
            wasPaid
              ? `${reason} Pembayaran demo dikembalikan.`
              : reason,
            updatedAt,
          ),
        };
      }),
    }));
  }

  function confirmOrderReceived(orderId: string) {
    const updatedAt = nowIso();
    setState((current) => ({
      ...current,
      orders: current.orders.map((order) =>
        order.id === orderId
          ? {
              ...order,
              status: "delivered",
              fulfillmentStatus: "delivered",
              updatedAt,
              timeline: completeTimeline(order.timeline, [
                "Dalam pengiriman",
                "Selesai",
              ]),
            }
          : order,
      ),
    }));
  }

  function requestOrderRefund(orderId: string, reason: string) {
    const updatedAt = nowIso();
    setState((current) => ({
      ...current,
      orders: current.orders.map((order) =>
        order.id === orderId
          ? {
              ...order,
              refundStatus: "requested",
              disputeStatus: "opened",
              updatedAt,
              timeline: appendTimeline(
                order.timeline,
                "Refund atau dispute diajukan",
                reason,
                updatedAt,
              ),
            }
          : order,
      ),
    }));
  }

  function cancelBooking(bookingId: string, reason: string) {
    const updatedAt = nowIso();
    setState((current) => ({
      ...current,
      bookings: current.bookings.map((booking) => {
        if (booking.id !== bookingId) return booking;
        const wasPaid = booking.paymentStatus === "paid";
        return {
          ...booking,
          status: "cancelled",
          paymentStatus: wasPaid ? "refunded" : booking.paymentStatus,
          refundStatus: wasPaid ? "refunded" : "none",
          cancellationReason: reason,
          updatedAt,
          timeline: appendTimeline(
            booking.timeline,
            "Booking dibatalkan",
            wasPaid
              ? `${reason} Pembayaran demo dikembalikan.`
              : reason,
            updatedAt,
          ),
        };
      }),
    }));
  }

  function rescheduleBooking(bookingId: string) {
    const updatedAt = nowIso();
    setState((current) => ({
      ...current,
      bookings: current.bookings.map((booking) => {
        if (booking.id !== bookingId) return booking;
        const scheduledAt = new Date(
          new Date(booking.scheduledAt).getTime() + 86_400_000,
        ).toISOString();
        return {
          ...booking,
          status: "confirmed",
          scheduledAt,
          rescheduleCount: (booking.rescheduleCount ?? 0) + 1,
          updatedAt,
          timeline: appendTimeline(
            booking.timeline,
            "Jadwal diubah",
            `Jadwal dipindahkan ke ${new Intl.DateTimeFormat("id-ID", {
              dateStyle: "medium",
              timeStyle: "short",
            }).format(new Date(scheduledAt))}.`,
            updatedAt,
          ),
        };
      }),
    }));
  }

  const value: StorefrontContextValue = {
    state,
    hydrated,
    cartCount: state.cart.reduce((total, line) => total + line.quantity, 0),
    addProduct,
    setBuyNowProduct,
    clearBuyNow,
    updateCartQuantity,
    removeCartLine,
    clearCart,
    toggleFavorite,
    createOrder,
    createBooking,
    loadDemoHistory,
    retryOrderPayment,
    cancelOrder,
    confirmOrderReceived,
    requestOrderRefund,
    cancelBooking,
    rescheduleBooking,
  };

  return (
    <StorefrontContext.Provider value={value}>
      {children}
    </StorefrontContext.Provider>
  );
}

export function useStorefront(): StorefrontContextValue {
  const value = useContext(StorefrontContext);
  if (!value) {
    throw new Error("useStorefront must be used inside StorefrontProvider");
  }
  return value;
}
