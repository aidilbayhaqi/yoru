import type { Metadata } from "next";

import { ProductCatalog } from "@/components/product-catalog";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = { title: "Produk" };

export default function ProductsPage() {
  return (
    <>
      <SiteHeader />
      <main className="catalog-page">
        <ProductCatalog />
      </main>
      <SiteFooter />
    </>
  );
}
