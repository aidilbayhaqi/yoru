"use client";

import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  buildBooking,
  buildOrder,
  randomId,
} from "@/lib/storefront-domain";
import {
  demoHistoryBookings,
  demoHistoryOrders,
} from "@/lib/storefront-demo-history";
import type {
  CartLine,
  DemoBooking,
  DemoOrder,
  Service,
  ShippingAddress,
  StorefrontState,
} from "@/lib/storefront-types";

const STORAGE_KEY = "yoru_storefront_demo_v1";

const initialState: StorefrontState = {
  cart: [],
  buyNow: null,
  favorites: ["prd_glow_reset", "svc_home_facial"],
  orders: [],
  bookings: [],
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
              line.lineId === lineId ? { ...line, quantity: Math.min(20, quantity) } : line,
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
    setState((current) => ({
      ...current,
      orders:
        current.orders.length > 0
          ? current.orders
          : demoHistoryOrders.map((order) => ({
              ...order,
              timeline: order.timeline.map((item) => ({ ...item })),
              items: order.items.map((item) => ({ ...item })),
            })),
      bookings:
        current.bookings.length > 0
          ? current.bookings
          : demoHistoryBookings.map((booking) => ({
              ...booking,
              timeline: booking.timeline.map((item) => ({ ...item })),
            })),
    }));
  }

  function retryOrderPayment(orderId: string) {
    const occurredAt = new Date().toISOString();
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
              updatedAt: occurredAt,
              timeline: [
                ...order.timeline,
                {
                  label: "Pembayaran berhasil",
                  detail: "Pembayaran ulang demo berhasil diverifikasi.",
                  occurredAt,
                  completed: true,
                },
              ],
            }
          : order,
      ),
    }));
  }

  function cancelOrder(orderId: string, reason: string) {
    const occurredAt = new Date().toISOString();
    setState((current) => ({
      ...current,
      orders: current.orders.map((order) =>
        order.id === orderId
          ? {
              ...order,
              status: "cancelled",
              fulfillmentStatus: "cancelled",
              cancellationReason: reason,
              refundStatus:
                order.paymentStatus === "paid" ? "processing" : "none",
              updatedAt: occurredAt,
              timeline: [
                ...order.timeline,
                {
                  label: "Pesanan dibatalkan",
                  detail:
                    order.paymentStatus === "paid"
                      ? `${reason} Refund sedang diproses.`
                      : reason,
                  occurredAt,
                  completed: true,
                },
              ],
            }
          : order,
      ),
    }));
  }

  function confirmOrderReceived(orderId: string) {
    const occurredAt = new Date().toISOString();
    setState((current) => ({
      ...current,
      orders: current.orders.map((order) =>
        order.id === orderId
          ? {
              ...order,
              status: "delivered",
              fulfillmentStatus: "delivered",
              updatedAt: occurredAt,
              timeline: [
                ...order.timeline,
                {
                  label: "Diterima customer",
                  detail: "Customer mengonfirmasi paket sudah diterima.",
                  occurredAt,
                  completed: true,
                },
              ],
            }
          : order,
      ),
    }));
  }

  function requestOrderRefund(orderId: string, reason: string) {
    const occurredAt = new Date().toISOString();
    setState((current) => ({
      ...current,
      orders: current.orders.map((order) =>
        order.id === orderId
          ? {
              ...order,
              refundStatus: "requested",
              disputeStatus: "open",
              updatedAt: occurredAt,
              timeline: [
                ...order.timeline,
                {
                  label: "Permintaan refund dibuat",
                  detail: reason,
                  occurredAt,
                  completed: true,
                },
              ],
            }
          : order,
      ),
    }));
  }

  function cancelBooking(bookingId: string, reason: string) {
    const occurredAt = new Date().toISOString();
    setState((current) => ({
      ...current,
      bookings: current.bookings.map((booking) =>
        booking.id === bookingId
          ? {
              ...booking,
              status: "cancelled",
              cancellationReason: reason,
              refundStatus:
                booking.paymentStatus === "paid" ? "processing" : "none",
              updatedAt: occurredAt,
              timeline: [
                ...booking.timeline,
                {
                  label: "Booking dibatalkan",
                  detail:
                    booking.paymentStatus === "paid"
                      ? `${reason} Refund sedang diproses.`
                      : reason,
                  occurredAt,
                  completed: true,
                },
              ],
            }
          : booking,
      ),
    }));
  }

  function rescheduleBooking(bookingId: string) {
    const occurredAt = new Date().toISOString();
    setState((current) => ({
      ...current,
      bookings: current.bookings.map((booking) => {
        if (booking.id !== bookingId) return booking;

        const nextSchedule = new Date(booking.scheduledAt);
        nextSchedule.setDate(nextSchedule.getDate() + 1);

        return {
          ...booking,
          scheduledAt: nextSchedule.toISOString(),
          status: "confirmed",
          rescheduleCount: (booking.rescheduleCount ?? 0) + 1,
          updatedAt: occurredAt,
          timeline: [
            ...booking.timeline,
            {
              label: "Jadwal diubah",
              detail: "Jadwal demo dipindahkan satu hari ke depan.",
              occurredAt,
              completed: true,
            },
          ],
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

  return <StorefrontContext.Provider value={value}>{children}</StorefrontContext.Provider>;
}

export function useStorefront(): StorefrontContextValue {
  const value = useContext(StorefrontContext);
  if (!value) {
    throw new Error("useStorefront must be used inside StorefrontProvider");
  }
  return value;
}
