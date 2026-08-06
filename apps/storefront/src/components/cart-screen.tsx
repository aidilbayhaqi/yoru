"use client";

import Image from "next/image";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { cartSubtotal, formatMoney, productById } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";

export function CartScreen() {
  const { hydrated, removeCartLine, state, updateCartQuantity } = useStorefront();
  const subtotal = cartSubtotal(state.cart);

  if (!hydrated) return <div className="page-state">Memuat cart...</div>;

  if (state.cart.length === 0) {
    return (
      <section className="empty-state">
        <span className="empty-state__icon">
          <Icon name="bag" width="34" />
        </span>
        <p className="section-eyebrow">Cart masih kosong</p>
        <h1>Temukan produk untuk rutinitasmu.</h1>
        <p>
          Produk dan layanan memiliki alur transaksi berbeda. Layanan dapat dipesan langsung dari
          halaman layanan.
        </p>
        <Link className="primary-button" href="/products">
          Jelajahi produk
          <Icon name="arrow" width="18" />
        </Link>
      </section>
    );
  }

  return (
    <main className="cart-layout">
      <section className="cart-main">
        <div className="page-heading">
          <p className="section-eyebrow">Product order</p>
          <h1>Cart kamu</h1>
          <p>{state.cart.length} varian siap diperiksa sebelum checkout.</p>
        </div>
        <div className="cart-lines">
          {state.cart.map((line) => {
            const product = productById(line.productId);
            const variant = product?.variants.find((item) => item.id === line.variantId);
            if (!product || !variant) return null;

            return (
              <article className="cart-line" key={line.lineId}>
                <Image alt={product.name} height={220} src={product.image} width={220} />
                <div className="cart-line__content">
                  <p>{product.partner}</p>
                  <Link href={`/products/${product.slug}`}>
                    <h2>{product.name}</h2>
                  </Link>
                  <span>{variant.name}</span>
                  <strong>{formatMoney(variant.priceMinor)}</strong>
                </div>
                <div className="cart-line__actions">
                  <div className="quantity-control">
                    <button
                      aria-label="Kurangi jumlah"
                      onClick={() => updateCartQuantity(line.lineId, line.quantity - 1)}
                      type="button"
                    >
                      <Icon name="minus" width="16" />
                    </button>
                    <span>{line.quantity}</span>
                    <button
                      aria-label="Tambah jumlah"
                      onClick={() => updateCartQuantity(line.lineId, line.quantity + 1)}
                      type="button"
                    >
                      <Icon name="plus" width="16" />
                    </button>
                  </div>
                  <button
                    className="text-danger"
                    onClick={() => removeCartLine(line.lineId)}
                    type="button"
                  >
                    Hapus
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
      <aside className="summary-card">
        <p className="summary-kicker">Ringkasan</p>
        <h2>Subtotal produk</h2>
        <div className="summary-row">
          <span>Subtotal</span>
          <strong>{formatMoney(subtotal)}</strong>
        </div>
        <div className="summary-row">
          <span>Pengiriman</span>
          <span>Dihitung di checkout</span>
        </div>
        <div className="summary-note">
          <Icon name="shield" width="18" />
          <span>Harga dan stok akan divalidasi ulang oleh server saat checkout.</span>
        </div>
        <Link className="primary-button summary-button" href="/checkout">
          Lanjut checkout
          <Icon name="arrow" width="18" />
        </Link>
        <Link className="text-link centered-link" href="/products">
          Lanjut belanja
        </Link>
      </aside>
    </main>
  );
}
