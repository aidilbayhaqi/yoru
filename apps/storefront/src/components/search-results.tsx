import { ProductCard } from "@/components/product-card";
import { ServiceCard } from "@/components/service-card";
import { products, services } from "@/lib/storefront-data";

export function SearchResults({ query }: { query: string }) {
  const normalized = query.trim().toLowerCase();
  const productResults = products.filter((product) =>
    [product.name, product.category, product.partner, ...product.tags].join(" ").toLowerCase().includes(normalized),
  );
  const serviceResults = services.filter((service) =>
    [service.name, service.category, service.partner, ...service.tags].join(" ").toLowerCase().includes(normalized),
  );

  return (
    <main className="search-page">
      <div className="page-heading"><p className="section-eyebrow">Unified search</p><h1>Hasil untuk “{query}”</h1><p>{productResults.length + serviceResults.length} item ditemukan dari produk dan layanan.</p></div>
      {productResults.length > 0 ? <section className="search-section"><h2>Produk</h2><div className="catalog-grid">{productResults.map((product) => <ProductCard key={product.id} product={product} />)}</div></section> : null}
      {serviceResults.length > 0 ? <section className="search-section"><h2>Home service</h2><div className="catalog-grid">{serviceResults.map((service) => <ServiceCard key={service.id} service={service} />)}</div></section> : null}
      {productResults.length === 0 && serviceResults.length === 0 ? <section className="empty-state inline-empty-state"><h2>Belum menemukan yang cocok.</h2><p>Coba kata lain seperti skincare, facial, hair, makeup, atau grooming.</p></section> : null}
    </main>
  );
}
