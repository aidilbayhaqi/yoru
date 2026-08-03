"use client";

import Image from "next/image";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { formatMoney } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";
import type { Product } from "@/lib/storefront-types";

export function ProductCard({ product }: { product: Product }) {
  const { addProduct, state, toggleFavorite } = useStorefront();
  const favorite = state.favorites.includes(product.id);
  const defaultVariant = product.variants[0];

  return (
    <article className="catalog-card product-card">
      <div className="catalog-card__media">
        <Link href={`/products/${product.slug}`}>
          <Image alt={product.name} height={640} src={product.image} width={640} />
        </Link>
        {product.badge ? <span className="catalog-badge">{product.badge}</span> : null}
        <button
          aria-label={favorite ? "Hapus dari favorit" : "Tambah ke favorit"}
          className={`favorite-button ${favorite ? "is-active" : ""}`}
          onClick={() => toggleFavorite(product.id)}
          type="button"
        >
          <Icon name="heart" width="18" />
        </button>
      </div>
      <div className="catalog-card__body">
        <p className="catalog-card__partner">{product.partner}</p>
        <Link href={`/products/${product.slug}`}>
          <h3>{product.name}</h3>
        </Link>
        <div className="rating-row">
          <Icon name="star" width="15" />
          <span>{product.rating}</span>
          <span className="muted">({product.reviewCount})</span>
        </div>
        <div className="price-row">
          <strong>{formatMoney(product.priceMinor)}</strong>
          {product.compareAtMinor ? <span>{formatMoney(product.compareAtMinor)}</span> : null}
        </div>
        <button
          className="secondary-button card-add-button"
          onClick={() => addProduct(product.id, defaultVariant.id)}
          type="button"
        >
          Tambah ke cart
          <Icon name="plus" width="17" />
        </button>
      </div>
    </article>
  );
}
