"use client";

import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { buildBooking, buildOrder, randomId } from "@/lib/storefront-domain";
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
  favorites: ["prd_glow_reset", "svc_home_facial"],
  orders: [],
  bookings: [],
};

type CreateOrderInput = {
  address: ShippingAddress;
  paymentMethod: string;
  deliveryMethod: string;
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
  updateCartQuantity: (lineId: string, quantity: number) => void;
  removeCartLine: (lineId: string) => void;
  clearCart: () => void;
  toggleFavorite: (id: string) => void;
  createOrder: (input: CreateOrderInput) => DemoOrder;
  createBooking: (input: CreateBookingInput) => DemoBooking;
};

const StorefrontContext = createContext<StorefrontContextValue | null>(null);

function readStoredState(): StorefrontState {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (!value) return initialState;
    const parsed = JSON.parse(value) as Partial<StorefrontState>;
    return {
      cart: Array.isArray(parsed.cart) ? parsed.cart : [],
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
    const order = buildOrder({
      lines: state.cart,
      address: input.address,
      paymentMethod: input.paymentMethod,
      deliveryMethod: input.deliveryMethod,
    });
    setState((current) => ({
      ...current,
      cart: [],
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

  const value = useMemo<StorefrontContextValue>(
    () => ({
      state,
      hydrated,
      cartCount: state.cart.reduce((total, line) => total + line.quantity, 0),
      addProduct,
      updateCartQuantity,
      removeCartLine,
      clearCart,
      toggleFavorite,
      createOrder,
      createBooking,
    }),
    [hydrated, state],
  );

  return <StorefrontContext.Provider value={value}>{children}</StorefrontContext.Provider>;
}

export function useStorefront(): StorefrontContextValue {
  const value = useContext(StorefrontContext);
  if (!value) {
    throw new Error("useStorefront must be used inside StorefrontProvider");
  }
  return value;
}
