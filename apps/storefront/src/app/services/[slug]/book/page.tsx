import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ServiceBookingFlow } from "@/components/service-booking-flow";
import { SiteHeader } from "@/components/site-header";
import { serviceBySlug } from "@/lib/storefront-domain";

type Props = { params: Promise<{ slug: string }> };
export const metadata: Metadata = { title: "Booking Layanan" };

export default async function BookingPage({ params }: Props) {
  const { slug } = await params;
  const service = serviceBySlug(slug);
  if (!service) notFound();
  return <><SiteHeader /><ServiceBookingFlow service={service} /></>;
}
