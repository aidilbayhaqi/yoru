import type { Metadata } from "next";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { ProductCard } from "@/components/product-card";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { products } from "@/lib/storefront-data";

export const metadata: Metadata = { title: "Collections" };

export default function CollectionsPage() {
  const collections = [
    { title: "Barrier First", detail: "A quiet routine for hydration and comfort.", query: "barrier", products: products.filter((item) => item.tags.some((tag) => ["barrier", "ceramide", "sensitive"].includes(tag))) },
    { title: "After Dark", detail: "Color and texture with a deeper point of view.", query: "makeup", products: products.filter((item) => item.category === "Makeup") },
    { title: "Desk to Dinner", detail: "Functional fashion for a long day out.", query: "fashion", products: products.filter((item) => item.category === "Fashion") },
  ];

  return (
    <>
      <SiteHeader />
      <main className="v5-content-page">
        <section className="v5-page-hero v5-page-hero--collections">
          <p className="section-eyebrow">Curated stories</p><h1>Collections with a point of view.</h1>
          <p>Editorial groupings built from the catalog you already have, ready to evolve into campaign-managed collections.</p>
        </section>
        {collections.map((collection, index) => (
          <section className={`collection-story collection-story--${index + 1}`} key={collection.title}>
            <div className="collection-story__heading">
              <span>0{index + 1}</span><div><p className="section-eyebrow">Yoru collection</p><h2>{collection.title}</h2><p>{collection.detail}</p></div>
              <Link className="text-link" href={`/search?q=${encodeURIComponent(collection.query)}`}>Explore <Icon name="arrow" width="17" /></Link>
            </div>
            {collection.products.length > 0 ? <div className="catalog-grid">{collection.products.map((product) => <ProductCard key={product.id} product={product} />)}</div> : <p className="collection-placeholder">Campaign products can be assigned here from the catalog console.</p>}
          </section>
        ))}
      </main>
      <SiteFooter />
    </>
  );
}
