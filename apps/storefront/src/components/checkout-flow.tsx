"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Icon } from "@/components/icons";
import { formatMoney, productById, productCheckoutTotals } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";
import type { ShippingAddress } from "@/lib/storefront-types";

const steps = ["Alamat", "Pengiriman", "Pembayaran"];

export function CheckoutFlow() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { createOrder, hydrated, state } = useStorefront();
  const buyNowMode = searchParams.get("mode") === "buy-now";
  const checkoutLines =
    buyNowMode && state.buyNow ? [state.buyNow] : state.cart;
  const [step, setStep] = useState(0);
  const [pending, setPending] = useState(false);
  const [deliveryMethod, setDeliveryMethod] = useState("regular");
  const [paymentMethod, setPaymentMethod] = useState("virtual_account");
  const [address, setAddress] = useState<ShippingAddress>({
    recipientName: "", phone: "", addressLine: "", city: "Jakarta Selatan", postalCode: "", notes: "",
  });

  const totals = productCheckoutTotals(checkoutLines, deliveryMethod);

  if (!hydrated) return <div className="page-state">Menyiapkan checkout...</div>;
  if (checkoutLines.length === 0) {
    return (
      <section className="empty-state">
        <span className="empty-state__icon"><Icon name="bag" width="34" /></span>
        <h1>Tidak ada produk untuk di-checkout.</h1>
        <button className="primary-button" onClick={() => router.replace("/products")} type="button">Kembali ke katalog</button>
      </section>
    );
  }

  function submitAddress(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setAddress({
      recipientName: String(data.get("recipientName") ?? ""),
      phone: String(data.get("phone") ?? ""),
      addressLine: String(data.get("addressLine") ?? ""),
      city: String(data.get("city") ?? ""),
      postalCode: String(data.get("postalCode") ?? ""),
      notes: String(data.get("notes") ?? ""),
    });
    setStep(1);
  }

  function confirmOrder() {
    setPending(true);
    const order = createOrder({
      address,
      deliveryMethod,
      paymentMethod,
      lines: buyNowMode ? checkoutLines : undefined,
    });
    router.replace(`/orders/${order.id}?new=1`);
  }

  return (
    <main className="checkout-shell">
      <section className="checkout-main">
        <div className="page-heading compact-heading"><p className="section-eyebrow">Secure product checkout</p><h1>Selesaikan pesanan</h1></div>
        <div className="stepper">
          {steps.map((label, index) => (
            <div className={index <= step ? "is-active" : ""} key={label}>
              <span>{index < step ? <Icon name="check" width="15" /> : index + 1}</span><strong>{label}</strong>
            </div>
          ))}
        </div>

        {step === 0 ? (
          <form className="checkout-card form-grid" onSubmit={submitAddress}>
            <div className="checkout-card__heading form-span-2"><span className="checkout-icon"><Icon name="pin" width="21" /></span><div><h2>Alamat pengiriman</h2><p>Pastikan nomor telepon aktif untuk koordinasi kurir.</p></div></div>
            <label>Nama penerima<input defaultValue={address.recipientName} name="recipientName" required /></label>
            <label>Nomor telepon<input defaultValue={address.phone} name="phone" required type="tel" /></label>
            <label className="form-span-2">Alamat lengkap<textarea defaultValue={address.addressLine} name="addressLine" required rows={4} /></label>
            <label>Kota<input defaultValue={address.city} name="city" required /></label>
            <label>Kode pos<input defaultValue={address.postalCode} name="postalCode" required /></label>
            <label className="form-span-2">Catatan kurir<input defaultValue={address.notes} name="notes" placeholder="Opsional" /></label>
            <button className="primary-button form-next-button" type="submit">Pilih pengiriman<Icon name="arrow" width="18" /></button>
          </form>
        ) : null}

        {step === 1 ? (
          <section className="checkout-card">
            <div className="checkout-card__heading"><span className="checkout-icon"><Icon name="truck" width="21" /></span><div><h2>Metode pengiriman</h2><p>Estimasi final mengikuti alamat dan partner fulfillment.</p></div></div>
            <div className="selection-list">
              {[
                ["regular", "Regular", "Tiba 2–4 hari", 1800000],
                ["express", "Express", "Tiba 1–2 hari", 3500000],
                ["pickup", "Ambil di partner", "Jadwal pickup akan dikonfirmasi", 0],
              ].map(([id, label, detail, price]) => (
                <button className={deliveryMethod === id ? "is-selected" : ""} key={String(id)} onClick={() => setDeliveryMethod(String(id))} type="button">
                  <span className="selection-radio" /><div><strong>{label}</strong><span>{detail}</span></div><strong>{Number(price) === 0 ? "Gratis" : formatMoney(Number(price))}</strong>
                </button>
              ))}
            </div>
            <div className="checkout-navigation"><button className="secondary-button" onClick={() => setStep(0)} type="button">Kembali</button><button className="primary-button" onClick={() => setStep(2)} type="button">Pilih pembayaran<Icon name="arrow" width="18" /></button></div>
          </section>
        ) : null}

        {step === 2 ? (
          <section className="checkout-card">
            <div className="checkout-card__heading"><span className="checkout-icon"><Icon name="shield" width="21" /></span><div><h2>Pembayaran</h2><p>Demo frontend menandai pembayaran berhasil agar seluruh flow dapat diuji.</p></div></div>
            <div className="selection-list payment-selection">
              {[
                ["virtual_account", "Virtual account", "BCA, Mandiri, BNI, dan BRI"],
                ["ewallet", "E-wallet", "GoPay, OVO, DANA, atau ShopeePay"],
                ["card", "Kartu debit/kredit", "Diproses melalui payment provider"],
              ].map(([id, label, detail]) => (
                <button className={paymentMethod === id ? "is-selected" : ""} key={id} onClick={() => setPaymentMethod(id)} type="button">
                  <span className="selection-radio" /><div><strong>{label}</strong><span>{detail}</span></div>
                </button>
              ))}
            </div>
            <div className="checkout-navigation"><button className="secondary-button" onClick={() => setStep(1)} type="button">Kembali</button><button className="primary-button" disabled={pending} onClick={confirmOrder} type="button">{pending ? "Memproses..." : "Bayar dan buat pesanan"}<Icon name="check" width="18" /></button></div>
          </section>
        ) : null}
      </section>

      <aside className="summary-card checkout-summary">
        <p className="summary-kicker">
          {buyNowMode ? "Buy now summary" : "Order summary"}
        </p>
        <div className="checkout-items">
          {checkoutLines.map((line) => {
            const product = productById(line.productId);
            const variant = product?.variants.find((item) => item.id === line.variantId);
            if (!product || !variant) return null;
            return <div key={line.lineId}><span>{line.quantity}×</span><div><strong>{product.name}</strong><span>{variant.name}</span></div><strong>{formatMoney(variant.priceMinor * line.quantity)}</strong></div>;
          })}
        </div>
        <div className="summary-divider" />
        <div className="summary-row"><span>Subtotal</span><span>{formatMoney(totals.subtotalMinor)}</span></div>
        <div className="summary-row"><span>Pengiriman</span><span>{formatMoney(totals.shippingMinor)}</span></div>
        <div className="summary-row"><span>Biaya layanan</span><span>{formatMoney(totals.serviceFeeMinor)}</span></div>
        {totals.discountMinor > 0 ? <div className="summary-row discount-row"><span>Promo otomatis</span><span>-{formatMoney(totals.discountMinor)}</span></div> : null}
        <div className="summary-total"><span>Total</span><strong>{formatMoney(totals.totalMinor)}</strong></div>
        <div className="summary-note"><Icon name="shield" width="18" /><span>Total production harus berasal dari quote server yang belum kedaluwarsa.</span></div>
      </aside>
    </main>
  );
}
