import type { Metadata } from "next";
import { OrderDetailScreen } from "@/components/order-detail-screen";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
type Props = { params: Promise<{ id: string }> };
export const metadata: Metadata = { title: "Detail Pesanan" };
export default async function OrderPage({ params }: Props) { const { id } = await params; return <><SiteHeader /><OrderDetailScreen orderId={id} /><SiteFooter /></>; }
