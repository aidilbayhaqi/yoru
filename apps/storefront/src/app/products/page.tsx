import type { Metadata } from "next";

import { ProductCatalog } from "@/components/product-catalog";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { getCatalogProducts } from "@/lib/catalog-api";

export const metadata: Metadata = { title: "Produk" };

export default async function ProductsPage() {
  const products = await getCatalogProducts();
  return (
    <>
      <SiteHeader />
      <main className="catalog-page">
        <ProductCatalog items={products} />
      </main>
      <SiteFooter />
    </>
  );
}
