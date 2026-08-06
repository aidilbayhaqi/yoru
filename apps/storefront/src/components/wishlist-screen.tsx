"use client";

import Link from "next/link";

import { Icon } from "@/components/icons";
import { ProductCard } from "@/components/product-card";
import { ServiceCard } from "@/components/service-card";
import { products, services } from "@/lib/storefront-data";
import { useStorefront } from "@/lib/storefront-store";

export function WishlistScreen() {
  const { hydrated, state } = useStorefront();
  const savedProducts = products.filter((item) => state.favorites.includes(item.id));
  const savedServices = services.filter((item) => state.favorites.includes(item.id));
  const count = savedProducts.length + savedServices.length;

  if (!hydrated) {
    return (
      <main className="page-state" role="status">
        Loading your wishlist...
      </main>
    );
  }

  return (
    <main className="v5-content-page">
      <section className="v5-page-hero">
        <p className="section-eyebrow">Saved edit</p>
        <h1>Your wishlist.</h1>
        <p>
          {count} saved item{count === 1 ? "" : "s"} across commerce and home service.
        </p>
      </section>

      {savedProducts.length > 0 ? (
        <section className="home-section">
          <div className="section-heading-row">
            <div>
              <h2>Products</h2>
            </div>
            <span>{savedProducts.length} saved</span>
          </div>
          <div className="catalog-grid">
            {savedProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </section>
      ) : null}

      {savedServices.length > 0 ? (
        <section className="home-section">
          <div className="section-heading-row">
            <div>
              <h2>Home services</h2>
            </div>
            <span>{savedServices.length} saved</span>
          </div>
          <div className="catalog-grid">
            {savedServices.map((service) => (
              <ServiceCard key={service.id} service={service} />
            ))}
          </div>
        </section>
      ) : null}

      {count === 0 ? (
        <section className="empty-state inline-empty-state v5-empty-state">
          <span>
            <Icon name="heart" width="25" />
          </span>
          <h2>Your edit is still empty.</h2>
          <p>Save products and services to compare them before checkout or booking.</p>
          <div>
            <Link className="primary-button" href="/products">
              Explore products
            </Link>
            <Link className="secondary-button" href="/services">
              Explore services
            </Link>
          </div>
        </section>
      ) : null}
    </main>
  );
}
