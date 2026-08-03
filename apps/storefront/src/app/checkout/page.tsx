import type { Metadata } from "next";
import { CheckoutFlow } from "@/components/checkout-flow";
import { SiteHeader } from "@/components/site-header";
export const metadata: Metadata = { title: "Checkout" };
export default function CheckoutPage() { return <><SiteHeader /><CheckoutFlow /></>; }
