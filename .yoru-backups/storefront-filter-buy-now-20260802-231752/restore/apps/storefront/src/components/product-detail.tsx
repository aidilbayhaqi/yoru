"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { Icon } from "@/components/icons";
import { formatMoney } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";
import type { Product } from "@/lib/storefront-types";

export function ProductDetail({ product }: { product: Product }) {
  const { addProduct, state, toggleFavorite } = useStorefront();
  const [variantId, setVariantId] = useState(product.variants[0].id);
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);
  const variant = product.variants.find((item) => item.id === variantId) ?? product.variants[0];
  const favorite = state.favorites.includes(product.id);

  function addToCart() {
    addProduct(product.id, variant.id, quantity);
    setAdded(true);
    window.setTimeout(() => setAdded(false), 1800);
  }

  return (
    <main>
      <div className="breadcrumb">
        <Link href="/">Beranda</Link><span>/</span><Link href="/products">Produk</Link><span>/</span><span>{product.name}</span>
      </div>
      <section className="detail-layout">
        <div className="detail-media">
          <Image alt={product.name} height={960} priority src={product.image} width={960} />
          {product.badge ? <span className="detail-badge">{product.badge}</span> : null}
        </div>
        <div className="detail-panel">
          <p className="detail-partner">{product.partner}</p>
          <h1>{product.name}</h1>
          <div className="rating-row detail-rating"><Icon name="star" width="16" /><strong>{product.rating}</strong><span>{product.reviewCount} ulasan</span></div>
          <div className="detail-price"><strong>{formatMoney(variant.priceMinor)}</strong>{product.compareAtMinor ? <span>{formatMoney(product.compareAtMinor)}</span> : null}</div>
          <p className="detail-description">{product.description}</p>

          <div className="detail-option">
            <span className="option-label">Pilih varian</span>
            <div className="variant-grid">
              {product.variants.map((item) => (
                <button className={item.id === variant.id ? "is-selected" : ""} key={item.id} onClick={() => setVariantId(item.id)} type="button">
                  <strong>{item.name}</strong><span>{item.stock} tersedia</span>
                </button>
              ))}
            </div>
          </div>

          <div className="detail-buy-row">
            <div className="quantity-control">
              <button aria-label="Kurangi jumlah" onClick={() => setQuantity((value) => Math.max(1, value - 1))} type="button"><Icon name="minus" width="17" /></button>
              <span>{quantity}</span>
              <button aria-label="Tambah jumlah" onClick={() => setQuantity((value) => Math.min(20, value + 1))} type="button"><Icon name="plus" width="17" /></button>
            </div>
            <button className="primary-button detail-add-button" onClick={addToCart} type="button">
              {added ? "Sudah masuk cart" : "Tambah ke cart"}<Icon name={added ? "check" : "bag"} width="18" />
            </button>
            <button aria-label={favorite ? "Hapus dari favorit" : "Tambah ke favorit"} className={`secondary-button detail-favorite ${favorite ? "is-active" : ""}`} onClick={() => toggleFavorite(product.id)} type="button"><Icon name="heart" width="19" /></button>
          </div>

          <div className="detail-information">
            <div><Icon name="truck" width="20" /><div><strong>{product.shippingEta}</strong><span>Dari {product.partnerLocation}</span></div></div>
            <div><Icon name="shield" width="20" /><div><strong>Partner terverifikasi</strong><span>Produk dipublish setelah pengecekan partner.</span></div></div>
          </div>
          <div className="detail-highlights">
            <h2>Kenapa kamu mungkin suka</h2>
            <ul>{product.highlights.map((highlight) => <li key={highlight}><Icon name="check" width="16" />{highlight}</li>)}</ul>
          </div>
        </div>
      </section>
    </main>
  );
}
