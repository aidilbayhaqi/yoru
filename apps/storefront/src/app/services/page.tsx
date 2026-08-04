import type { Metadata } from "next";

import { ServiceCatalog } from "@/components/service-catalog";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { getCatalogServices } from "@/lib/catalog-api";

export const metadata: Metadata = { title: "Home Service" };

export default async function ServicesPage() {
  const services = await getCatalogServices();
  return (
    <>
      <SiteHeader />
      <main className="catalog-page">
        <ServiceCatalog items={services} />
      </main>
      <SiteFooter />
    </>
  );
}
