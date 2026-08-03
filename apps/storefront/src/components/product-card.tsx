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
  const canAdd = Boolean(defaultVariant && defaultVariant.stock > 0);

  return (
    <article className="catalog-card product-card">
      <div className="catalog-card__media">
        <Link aria-label={`Lihat ${product.name}`} href={`/products/${product.slug}`}>
          <Image alt={product.name} height={720} src={product.image} width={640} />
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
        <div className="catalog-card__heading">
          <div>
            <p className="catalog-card__partner">{product.partner}</p>
            <Link href={`/products/${product.slug}`}>
              <h3>{product.name}</h3>
            </Link>
          </div>
          <div className="rating-row" aria-label={`Rating ${product.rating}`}>
            <Icon name="star" width="14" />
            <span>{product.rating}</span>
          </div>
        </div>

        <div className="catalog-card__footer">
          <div className="price-row">
            <strong>{formatMoney(product.priceMinor)}</strong>
            {product.compareAtMinor ? <span>{formatMoney(product.compareAtMinor)}</span> : null}
          </div>
          <button
            aria-label={`Tambah ${product.name} ke cart`}
            className="card-quick-action"
            disabled={!canAdd}
            onClick={() => {
              if (defaultVariant) addProduct(product.id, defaultVariant.id);
            }}
            type="button"
          >
            <Icon name={canAdd ? "plus" : "close"} width="17" />
          </button>
        </div>
      </div>
    </article>
  );
}
