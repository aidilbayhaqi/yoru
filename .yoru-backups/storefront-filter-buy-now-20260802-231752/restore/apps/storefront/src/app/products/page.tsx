import type { Metadata } from "next";
import { ProductCard } from "@/components/product-card";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { productCategories, products } from "@/lib/storefront-data";

export const metadata: Metadata = { title: "Produk" };

export default function ProductsPage() {
  return (
    <><SiteHeader /><main className="catalog-page">
      <section className="catalog-hero catalog-hero--product"><p className="section-eyebrow">Yoru commerce</p><h1>Produk terkurasi untuk rutinitas dan gayamu.</h1><p>Setiap produk berasal dari partner terverifikasi. Harga dan stok final diperiksa ulang saat checkout.</p></section>
      <div className="category-chips" aria-label="Kategori produk">{productCategories.map((category, index) => <span className={index === 0 ? "is-active" : ""} key={category}>{category}</span>)}</div>
      <div className="catalog-toolbar"><span>{products.length} produk</span><span>Urutkan: Rekomendasi</span></div>
      <div className="catalog-grid catalog-grid--page">{products.map((product) => <ProductCard key={product.id} product={product} />)}</div>
    </main><SiteFooter /></>
  );
}
