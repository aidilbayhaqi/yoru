"use client";

import Link from "next/link";
import { Icon } from "@/components/icons";
import { formatMoney, productById } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";

export function OrderDetailScreen({ orderId }: { orderId: string }) {
  const { hydrated, state } = useStorefront();
  const order = state.orders.find((item) => item.id === orderId);
  if (!hydrated) return <div className="page-state">Memuat detail pesanan...</div>;
  if (!order) return <section className="empty-state"><h1>Pesanan tidak ditemukan.</h1><Link className="primary-button" href="/orders">Kembali ke pesanan</Link></section>;

  return (
    <main className="record-detail-page">
      <div className="record-detail-heading"><div><p className="section-eyebrow">Product order</p><h1>{order.number}</h1><p>Dibuat {new Intl.DateTimeFormat("id-ID", { dateStyle: "full", timeStyle: "short" }).format(new Date(order.createdAt))}</p></div><span className={`record-status status-${order.status}`}>Diproses</span></div>
      <div className="record-detail-grid">
        <section className="record-detail-main">
          <article className="record-card"><h2>Status pesanan</h2><div className="timeline">{order.timeline.map((item) => <div className={item.completed ? "is-complete" : ""} key={item.label}><span className="timeline-marker">{item.completed ? <Icon name="check" width="14" /> : null}</span><div><strong>{item.label}</strong><p>{item.detail}</p></div></div>)}</div></article>
          <article className="record-card"><h2>Produk</h2><div className="detail-item-list">{order.items.map((line) => {
            const product = productById(line.productId);
            const variant = product?.variants.find((item) => item.id === line.variantId);
            return <div key={line.lineId}><div><strong>{product?.name}</strong><span>{variant?.name} · {line.quantity} item</span></div><strong>{formatMoney((variant?.priceMinor ?? 0) * line.quantity)}</strong></div>;
          })}</div></article>
        </section>
        <aside className="record-detail-side">
          <article className="record-card"><h2>Pengiriman</h2><strong>{order.address.recipientName}</strong><p>{order.address.phone}</p><p>{order.address.addressLine}, {order.address.city} {order.address.postalCode}</p></article>
          <article className="record-card"><h2>Pembayaran</h2><div className="summary-row"><span>Subtotal</span><span>{formatMoney(order.subtotalMinor)}</span></div><div className="summary-row"><span>Pengiriman</span><span>{formatMoney(order.shippingMinor)}</span></div><div className="summary-row"><span>Biaya layanan</span><span>{formatMoney(order.serviceFeeMinor)}</span></div><div className="summary-total"><span>Total</span><strong>{formatMoney(order.totalMinor)}</strong></div><p className="record-payment-method">{order.paymentMethod.replaceAll("_", " ")}</p></article>
        </aside>
      </div>
    </main>
  );
}
