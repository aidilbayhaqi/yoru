import type { Metadata } from "next";
import { OrdersScreen } from "@/components/orders-screen";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
export const metadata: Metadata = { title: "Pesanan" };
export default function OrdersPage() { return <><SiteHeader /><OrdersScreen /><SiteFooter /></>; }
