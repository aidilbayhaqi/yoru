"use client";

import Link from "next/link";
import { Icon } from "@/components/icons";
import { formatMoney, productById } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";

const labels = {
  awaiting_payment: "Menunggu pembayaran",
  processing: "Diproses",
  shipped: "Dikirim",
  delivered: "Selesai",
  cancelled: "Dibatalkan",
};

export function OrdersScreen() {
  const { hydrated, state } = useStorefront();
  if (!hydrated) return <div className="page-state">Memuat pesanan...</div>;

  return (
    <main className="customer-list-page">
      <div className="page-heading">
        <p className="section-eyebrow">Customer account</p>
        <h1>Pesanan produk</h1>
        <p>Order produk memiliki lifecycle terpisah dari booking layanan.</p>
      </div>
      {state.orders.length === 0 ? (
        <section className="empty-state inline-empty-state">
          <span className="empty-state__icon">
            <Icon name="bag" width="32" />
          </span>
          <h2>Belum ada pesanan.</h2>
          <p>Checkout produk pertamamu untuk melihat tracking di sini.</p>
          <Link className="primary-button" href="/products">
            Mulai belanja
          </Link>
        </section>
      ) : (
        <div className="customer-record-list">
          {state.orders.map((order) => (
            <article key={order.id}>
              <div className="record-header">
                <div>
                  <span>Nomor pesanan</span>
                  <strong>{order.number}</strong>
                </div>
                <span className={`record-status status-${order.status}`}>
                  {labels[order.status]}
                </span>
              </div>
              <div className="record-body">
                <div className="record-products">
                  {order.items.slice(0, 3).map((line) => {
                    const product = productById(line.productId);
                    return (
                      <div key={line.lineId}>
                        <strong>{product?.name ?? "Produk"}</strong>
                        <span>{line.quantity} item</span>
                      </div>
                    );
                  })}
                </div>
                <div className="record-total">
                  <span>Total</span>
                  <strong>{formatMoney(order.totalMinor)}</strong>
                </div>
              </div>
              <div className="record-footer">
                <span>
                  {new Intl.DateTimeFormat("id-ID", {
                    dateStyle: "medium",
                    timeStyle: "short",
                  }).format(new Date(order.createdAt))}
                </span>
                <Link className="text-link" href={`/orders/${order.id}`}>
                  Lihat detail
                  <Icon name="arrow" width="17" />
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
