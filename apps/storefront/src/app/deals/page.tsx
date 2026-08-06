import type { Metadata } from "next";

import { ProductCard } from "@/components/product-card";
import { ServiceCard } from "@/components/service-card";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { products, services } from "@/lib/storefront-data";

export const metadata: Metadata = { title: "Deals" };

export default function DealsPage() {
  const productDeals = products.filter((item) => item.compareAtMinor);
  const servicePicks = [...services].sort((a, b) => b.rating - a.rating).slice(0, 3);

  return (
    <>
      <SiteHeader />
      <main className="v5-content-page">
        <section className="v5-page-hero v5-page-hero--deals">
          <p className="section-eyebrow">Curated value</p>
          <h1>Good timing, better edit.</h1>
          <p>
            Promotional display based on catalog prices. Discount eligibility and final totals must
            still be calculated by the commerce API.
          </p>
        </section>
        <section className="home-section">
          <div className="section-heading-row">
            <div>
              <p className="section-eyebrow">Limited price edit</p>
              <h2>Products with visible markdowns.</h2>
            </div>
          </div>
          <div className="catalog-grid">
            {productDeals.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </section>
        <section className="home-section">
          <div className="section-heading-row">
            <div>
              <p className="section-eyebrow">Highly rated</p>
              <h2>Services worth booking ahead.</h2>
            </div>
          </div>
          <div className="catalog-grid">
            {servicePicks.map((service) => (
              <ServiceCard key={service.id} service={service} />
            ))}
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
