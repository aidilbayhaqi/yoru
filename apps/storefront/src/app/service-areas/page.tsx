import type { Metadata } from "next";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { services } from "@/lib/storefront-data";

export const metadata: Metadata = { title: "Service Areas" };

export default function ServiceAreasPage() {
  return (
    <>
      <SiteHeader />
      <main className="v5-content-page">
        <section className="v5-page-hero">
          <p className="section-eyebrow">Where Yoru comes to you</p><h1>Service areas.</h1>
          <p>Browse the advertised coverage, then verify your exact address during booking before a slot is locked.</p>
        </section>
        <div className="service-area-grid">
          {services.map((service) => (
            <article key={service.id}>
              <span><Icon name="pin" width="20" /></span>
              <div><p>{service.category}</p><h2>{service.name}</h2><strong>{service.serviceArea}</strong></div>
              <Link href={`/services/${service.slug}`}>View service <Icon name="arrow" width="16" /></Link>
            </article>
          ))}
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
