"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "@/components/icons";
import { ProductCard } from "@/components/product-card";
import { products } from "@/lib/storefront-data";
import { formatMoney } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";
import type { Product } from "@/lib/storefront-types";

export function ProductDetail({ product }: { product: Product }) {
  const router = useRouter();
  const { addProduct, setBuyNowProduct, state, toggleFavorite } = useStorefront();
  const [variantId, setVariantId] = useState(product.variants[0]!.id);
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);
  const [shared, setShared] = useState(false);
  const [mediaView, setMediaView] = useState<"hero" | "detail" | "texture">("hero");
  const [postalCode, setPostalCode] = useState("");
  const [deliveryMessage, setDeliveryMessage] = useState("");
  const addedTimerRef = useRef<number | null>(null);
  const sharedTimerRef = useRef<number | null>(null);

  const variant = useMemo(
    () => (product.variants.find((item) => item.id === variantId) ?? product.variants[0])!,
    [product.variants, variantId],
  );
  const favorite = state.favorites.includes(product.id);
  const related = useMemo(
    () =>
      products
        .filter((item) => item.id !== product.id && item.category === product.category)
        .slice(0, 4),
    [product.category, product.id],
  );

  useEffect(
    () => () => {
      if (addedTimerRef.current !== null) window.clearTimeout(addedTimerRef.current);
      if (sharedTimerRef.current !== null) window.clearTimeout(sharedTimerRef.current);
    },
    [],
  );

  function addToCart() {
    addProduct(product.id, variant.id, quantity);
    setAdded(true);
    if (addedTimerRef.current !== null) window.clearTimeout(addedTimerRef.current);
    addedTimerRef.current = window.setTimeout(() => {
      setAdded(false);
      addedTimerRef.current = null;
    }, 1800);
  }

  function buyNow() {
    setBuyNowProduct(product.id, variant.id, quantity);
    router.push("/checkout?mode=buy-now");
  }

  async function shareProduct() {
    const url = window.location.href;
    try {
      if (navigator.share) {
        await navigator.share({ title: product.name, text: product.description, url });
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
      }
      setShared(true);
      if (sharedTimerRef.current !== null) window.clearTimeout(sharedTimerRef.current);
      sharedTimerRef.current = window.setTimeout(() => {
        setShared(false);
        sharedTimerRef.current = null;
      }, 1600);
    } catch {
      // Native share can be dismissed by the user; no error state is needed.
    }
  }

  function estimateDelivery() {
    const normalized = postalCode.trim();
    if (!/^\d{5}$/.test(normalized)) {
      setDeliveryMessage("Masukkan kode pos 5 digit.");
      return;
    }
    setDeliveryMessage(`${product.shippingEta}. Estimasi final dihitung ulang saat checkout.`);
  }

  return (
    <main className="v5-product-page">
      <div className="breadcrumb">
        <Link href="/">Home</Link>
        <span>/</span>
        <Link href="/products">Products</Link>
        <span>/</span>
        <span>{product.name}</span>
      </div>

      <section className="detail-layout v5-detail-layout">
        <div className="v5-product-gallery">
          <div className={`detail-media v5-detail-media v5-detail-media--${mediaView}`}>
            <Image
              alt={product.name}
              fill
              priority
              sizes="(max-width: 900px) 92vw, 52vw"
              src={product.image}
            />
            {product.badge ? <span className="detail-badge">{product.badge}</span> : null}
            <button className="gallery-share-button" onClick={shareProduct} type="button">
              {shared ? "Link copied" : "Share"}
            </button>
          </div>
          <div className="gallery-thumbnails" aria-label="Product views">
            {[
              ["hero", "Full view"],
              ["detail", "Close-up"],
              ["texture", "Texture"],
            ].map(([value, label]) => (
              <button
                className={mediaView === value ? "is-active" : ""}
                key={value}
                onClick={() => setMediaView(value as typeof mediaView)}
                type="button"
              >
                <span className={`gallery-thumb gallery-thumb--${value}`}>
                  <Image alt="" fill sizes="90px" src={product.image} />
                </span>
                <small>{label}</small>
              </button>
            ))}
          </div>
        </div>

        <div className="detail-panel v5-detail-panel">
          <div className="product-kicker-row">
            <p className="detail-partner">{product.partner}</p>
            <span className="verified-label">
              <Icon name="shield" width="15" /> Verified partner
            </span>
          </div>
          <h1>{product.name}</h1>
          <div className="rating-row detail-rating">
            <Icon name="star" width="16" />
            <strong>{product.rating}</strong>
            <a href="#reviews">{product.reviewCount} verified reviews</a>
          </div>

          <div className="detail-price">
            <strong>{formatMoney(variant.priceMinor)}</strong>
            {product.compareAtMinor ? <span>{formatMoney(product.compareAtMinor)}</span> : null}
          </div>
          <p className="detail-description">{product.description}</p>

          <div className="v5-payment-note">
            <span>Pay in full</span>
            <strong>Secure checkout</strong>
            <small>Payment status and final total are verified by the server.</small>
          </div>

          <div className="detail-option">
            <span className="option-label">Choose variant</span>
            <div className="variant-grid">
              {product.variants.map((item) => (
                <button
                  className={item.id === variant.id ? "is-selected" : ""}
                  disabled={item.stock <= 0}
                  key={item.id}
                  onClick={() => {
                    setVariantId(item.id);
                    setQuantity(1);
                  }}
                  type="button"
                >
                  <strong>{item.name}</strong>
                  <span>{item.stock > 0 ? `${item.stock} available` : "Out of stock"}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="detail-purchase-controls">
            <div>
              <span className="option-label">Quantity</span>
              <div className="quantity-control">
                <button
                  aria-label="Kurangi jumlah"
                  onClick={() => setQuantity((value) => Math.max(1, value - 1))}
                  type="button"
                >
                  <Icon name="minus" width="17" />
                </button>
                <span>{quantity}</span>
                <button
                  aria-label="Tambah jumlah"
                  onClick={() =>
                    setQuantity((value) => Math.min(Math.max(1, variant.stock), value + 1))
                  }
                  type="button"
                >
                  <Icon name="plus" width="17" />
                </button>
              </div>
            </div>
            <button
              aria-label={favorite ? "Hapus dari wishlist" : "Tambah ke wishlist"}
              className={`secondary-button detail-favorite ${favorite ? "is-active" : ""}`}
              onClick={() => toggleFavorite(product.id)}
              type="button"
            >
              <Icon name="heart" width="19" />
              {favorite ? "Saved" : "Wishlist"}
            </button>
          </div>

          <div className="detail-primary-actions">
            <button
              className="secondary-button detail-cart-button"
              disabled={variant.stock <= 0}
              onClick={addToCart}
              type="button"
            >
              {added ? "Added to cart" : "Add to cart"}
              <Icon name={added ? "check" : "bag"} width="18" />
            </button>
            <button
              className="primary-button buy-now-button"
              disabled={variant.stock <= 0}
              onClick={buyNow}
              type="button"
            >
              Buy now
              <Icon name="arrow" width="18" />
            </button>
          </div>

          <p className="buy-now-note">
            Buy now membawa varian ini langsung ke checkout. Cart yang sudah ada tidak dihapus.
          </p>

          <div className="delivery-estimator">
            <div>
              <Icon name="truck" width="20" />
              <span>
                <strong>Delivery estimate</strong>
                <small>From {product.partnerLocation}</small>
              </span>
            </div>
            <div className="delivery-estimator__form">
              <input
                aria-label="Kode pos"
                inputMode="numeric"
                maxLength={5}
                onChange={(event) => setPostalCode(event.target.value)}
                placeholder="Postal code"
                value={postalCode}
              />
              <button onClick={estimateDelivery} type="button">
                Check
              </button>
            </div>
            {deliveryMessage ? <p>{deliveryMessage}</p> : null}
          </div>

          <div className="detail-accordions">
            <details open>
              <summary>
                Product highlights <span>+</span>
              </summary>
              <ul>
                {product.highlights.map((highlight) => (
                  <li key={highlight}>
                    <Icon name="check" width="16" />
                    {highlight}
                  </li>
                ))}
              </ul>
            </details>
            <details>
              <summary>
                Shipping & returns <span>+</span>
              </summary>
              <p>
                {product.shippingEta}. Return eligibility should be verified against category, item
                condition, and partner policy.
              </p>
            </details>
            <details>
              <summary>
                Authenticity & partner <span>+</span>
              </summary>
              <p>
                Published through {product.partner}. Partner identity and product state are checked
                before the item is shown as active.
              </p>
            </details>
          </div>
        </div>
      </section>

      <section className="v5-review-section" id="reviews">
        <div className="v5-review-summary">
          <p className="section-eyebrow">Verified feedback</p>
          <strong>{product.rating}</strong>
          <div>
            <Icon name="star" width="18" />
            <span>Based on {product.reviewCount} reviews</span>
          </div>
          <p>
            Review distribution shown here is an interface preview until review aggregates are
            served by the API.
          </p>
        </div>
        <div className="v5-review-cards">
          <article>
            <div>
              <strong>Packaging felt considered.</strong>
              <span>5.0</span>
            </div>
            <p>Produk datang aman dan varian sesuai. Tekstur terasa nyaman dipakai harian.</p>
            <small>Verified purchase · 12 days ago</small>
          </article>
          <article>
            <div>
              <strong>Easy addition to my routine.</strong>
              <span>4.8</span>
            </div>
            <p>Detail produknya jelas dan proses checkout cepat. Estimasi pengiriman sesuai.</p>
            <small>Verified purchase · 3 weeks ago</small>
          </article>
        </div>
      </section>

      {related.length > 0 ? (
        <section className="home-section v5-related-section">
          <div className="section-heading-row">
            <div>
              <p className="section-eyebrow">Complete the edit</p>
              <h2>You may also like.</h2>
            </div>
            <Link className="text-link" href={`/search?q=${encodeURIComponent(product.category)}`}>
              View category <Icon name="arrow" width="18" />
            </Link>
          </div>
          <div className="catalog-grid">
            {related.map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
          </div>
        </section>
      ) : null}

      <div className="mobile-buy-bar">
        <div>
          <small>{variant.name}</small>
          <strong>{formatMoney(variant.priceMinor)}</strong>
        </div>
        <button className="secondary-button" onClick={addToCart} type="button">
          <Icon name="bag" width="18" />
        </button>
        <button className="primary-button" onClick={buyNow} type="button">
          Buy now
        </button>
      </div>
    </main>
  );
}
