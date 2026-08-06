import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ServiceDetail } from "@/components/service-detail";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { serviceBySlug } from "@/lib/storefront-domain";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  return { title: serviceBySlug(slug)?.name ?? "Home Service" };
}

export default async function ServicePage({ params }: Props) {
  const { slug } = await params;
  const service = serviceBySlug(slug);
  if (!service) notFound();
  return (
    <>
      <SiteHeader />
      <ServiceDetail service={service} />
      <SiteFooter />
    </>
  );
}
