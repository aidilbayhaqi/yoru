import Link from "next/link";

import { Icon } from "@/components/icons";
import { ProductCard } from "@/components/product-card";
import { ServiceCard } from "@/components/service-card";
import { products, services } from "@/lib/storefront-data";

type SearchMode = "query" | "ai" | "image";

export function SearchResults({ query, mode = "query" }: { query: string; mode?: SearchMode }) {
  const normalized = query.trim().toLowerCase();
  const productResults = products.filter((product) =>
    [product.name, product.category, product.partner, product.description, ...product.tags]
      .join(" ")
      .toLowerCase()
      .includes(normalized),
  );
  const serviceResults = services.filter((service) =>
    [
      service.name,
      service.category,
      service.partner,
      service.serviceArea,
      service.description,
      ...service.tags,
    ]
      .join(" ")
      .toLowerCase()
      .includes(normalized),
  );
  const count = productResults.length + serviceResults.length;
  const modeLabel =
    mode === "ai"
      ? "AI intent search"
      : mode === "image"
        ? "Visual search preview"
        : "Query search";

  return (
    <main className="search-page v5-search-page">
      <section className="v5-search-hero">
        <p className="section-eyebrow">{modeLabel}</p>
        <h1>{query ? <>Results for “{query}”</> : "Explore Yoru"}</h1>
        <p>{count} matches across products and home services.</p>
        <div className="secondary-button v5-search-hint">
          Refine from the search button above
          <Icon name="search" width="17" />
        </div>
      </section>

      {mode === "ai" ? (
        <section className="search-intent-card">
          <span>
            <Icon name="wand" width="22" />
          </span>
          <div>
            <strong>How Yoru interpreted your request</strong>
            <p>
              Keyword, category, partner, description, tag, and service-area matching for “{query}”.
              Transaction facts still come from product and booking APIs.
            </p>
          </div>
        </section>
      ) : null}

      {mode === "image" ? (
        <section className="search-intent-card search-intent-card--image">
          <span>
            <Icon name="sparkle" width="22" />
          </span>
          <div>
            <strong>Visual-search integration preview</strong>
            <p>
              These results use the visual category intent. Production similarity requires an
              image-embedding endpoint, moderation, and vector retrieval.
            </p>
          </div>
        </section>
      ) : null}

      <nav className="search-category-links" aria-label="Search shortcuts">
        <Link href="/products">All products</Link>
        <Link href="/search?q=skincare">Skincare</Link>
        <Link href="/search?q=fashion">Fashion</Link>
        <Link href="/search?q=facial">Facial</Link>
        <Link href="/services">Home service</Link>
      </nav>

      {productResults.length > 0 ? (
        <section className="search-section">
          <div className="section-heading-row">
            <div>
              <p className="section-eyebrow">Commerce</p>
              <h2>Products</h2>
            </div>
            <span>{productResults.length} results</span>
          </div>
          <div className="catalog-grid">
            {productResults.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </section>
      ) : null}

      {serviceResults.length > 0 ? (
        <section className="search-section">
          <div className="section-heading-row">
            <div>
              <p className="section-eyebrow">At home</p>
              <h2>Home services</h2>
            </div>
            <span>{serviceResults.length} results</span>
          </div>
          <div className="catalog-grid">
            {serviceResults.map((service) => (
              <ServiceCard key={service.id} service={service} />
            ))}
          </div>
        </section>
      ) : null}

      {count === 0 ? (
        <section className="empty-state inline-empty-state v5-empty-state">
          <span>
            <Icon name="search" width="25" />
          </span>
          <h2>Nothing close enough yet.</h2>
          <p>Try skincare, facial, hair, makeup, fashion, grooming, a partner name, or an area.</p>
          <div>
            <Link className="primary-button" href="/products">
              Browse products
            </Link>
            <Link className="secondary-button" href="/services">
              Browse services
            </Link>
          </div>
        </section>
      ) : null}
    </main>
  );
}
