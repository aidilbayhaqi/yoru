import type { Metadata } from "next";

import { ServiceCatalog } from "@/components/service-catalog";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = { title: "Home Service" };

export default function ServicesPage() {
  return (
    <>
      <SiteHeader />
      <main className="catalog-page">
        <ServiceCatalog />
      </main>
      <SiteFooter />
    </>
  );
}
