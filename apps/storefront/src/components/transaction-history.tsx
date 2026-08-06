"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Icon } from "@/components/icons";
import { formatMoney, productById } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";
import type { DemoBooking, DemoOrder } from "@/lib/storefront-types";

type HistoryFilter = "all" | "orders" | "bookings";

function paymentLabel(status: DemoOrder["paymentStatus"]): string {
  return {
    pending: "Menunggu pembayaran",
    paid: "Sudah dibayar",
    failed: "Pembayaran gagal",
    refunded: "Sudah direfund",
  }[status];
}

function fulfillmentLabel(order: DemoOrder): string {
  const status = order.fulfillmentStatus ?? order.status;
  return (
    {
      unfulfilled: "Belum diproses",
      packing: "Sedang dikemas",
      processing: "Sedang diproses",
      shipped: "Dalam pengiriman",
      delivered: "Sudah diterima",
      cancelled: "Dibatalkan",
      awaiting_payment: "Menunggu pembayaran",
    }[status] ?? status
  );
}

function bookingLabel(status: DemoBooking["status"]): string {
  return {
    requested: "Menunggu konfirmasi",
    confirmed: "Jadwal dikonfirmasi",
    assigned: "Profesional ditugaskan",
    en_route: "Menuju lokasi",
    arrived: "Sudah tiba",
    in_service: "Layanan berlangsung",
    completed: "Selesai",
    cancelled: "Dibatalkan",
  }[status];
}

function Progress({ completed, total }: { completed: number; total: number }) {
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
  return (
    <div
      aria-label={`Progres ${percentage}%`}
      className="history-progress"
      role="progressbar"
      aria-valuemax={100}
      aria-valuemin={0}
      aria-valuenow={percentage}
    >
      <span style={{ width: `${percentage}%` }} />
    </div>
  );
}

export function TransactionHistory() {
  const {
    hydrated,
    state,
    loadDemoHistory,
    retryOrderPayment,
    cancelOrder,
    confirmOrderReceived,
    requestOrderRefund,
    cancelBooking,
    rescheduleBooking,
  } = useStorefront();

  const [filter, setFilter] = useState<HistoryFilter>("all");
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");

  const records = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const orderRecords = state.orders.map((order) => ({
      kind: "order" as const,
      occurredAt: order.updatedAt ?? order.createdAt,
      record: order,
      searchable: [
        order.number,
        order.status,
        order.paymentStatus,
        order.fulfillmentStatus ?? "",
        order.trackingNumber ?? "",
        ...order.items.map((line) => productById(line.productId)?.name ?? line.productId),
      ]
        .join(" ")
        .toLowerCase(),
    }));
    const bookingRecords = state.bookings.map((booking) => ({
      kind: "booking" as const,
      occurredAt: booking.updatedAt ?? booking.createdAt,
      record: booking,
      searchable: [
        booking.number,
        booking.status,
        booking.paymentStatus,
        booking.serviceName,
        booking.professionalName,
      ]
        .join(" ")
        .toLowerCase(),
    }));

    return [...orderRecords, ...bookingRecords]
      .filter((item) => {
        const matchesType =
          filter === "all" ||
          (filter === "orders" && item.kind === "order") ||
          (filter === "bookings" && item.kind === "booking");
        return matchesType && (!normalized || item.searchable.includes(normalized));
      })
      .sort(
        (left, right) => new Date(right.occurredAt).getTime() - new Date(left.occurredAt).getTime(),
      );
  }, [filter, query, state.bookings, state.orders]);

  if (!hydrated) {
    return <div className="page-state">Memuat riwayat transaksi...</div>;
  }

  function announce(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2600);
  }

  function handleCancelOrder(order: DemoOrder) {
    const reason = window.prompt(
      "Alasan pembatalan pesanan:",
      "Berubah pikiran sebelum pengiriman.",
    );
    if (!reason?.trim()) return;
    cancelOrder(order.id, reason.trim());
    announce("Pesanan dibatalkan. Status refund diperbarui bila pembayaran sudah berhasil.");
  }

  function handleRefund(order: DemoOrder) {
    const reason = window.prompt(
      "Jelaskan alasan refund atau dispute:",
      "Produk tidak sesuai atau mengalami kerusakan.",
    );
    if (!reason?.trim()) return;
    requestOrderRefund(order.id, reason.trim());
    announce("Permintaan refund dan dispute berhasil dibuat.");
  }

  function handleCancelBooking(booking: DemoBooking) {
    const reason = window.prompt("Alasan pembatalan booking:", "Jadwal tidak lagi sesuai.");
    if (!reason?.trim()) return;
    cancelBooking(booking.id, reason.trim());
    announce("Booking dibatalkan dan status refund diperbarui.");
  }

  return (
    <main className="history-page">
      <section className="history-hero">
        <div>
          <p className="section-eyebrow">Customer transaction center</p>
          <h1>Riwayat dan tracking.</h1>
          <p>
            Pantau pembayaran, proses partner, pengiriman, booking, profesional, refund, serta
            dispute dari satu halaman.
          </p>
        </div>
        <div className="history-summary">
          <div>
            <span>Order produk</span>
            <strong>{state.orders.length}</strong>
          </div>
          <div>
            <span>Booking layanan</span>
            <strong>{state.bookings.length}</strong>
          </div>
          <div>
            <span>Butuh tindakan</span>
            <strong>
              {
                [
                  ...state.orders.filter(
                    (order) => order.paymentStatus === "pending" || order.status === "shipped",
                  ),
                  ...state.bookings.filter((booking) => booking.status === "requested"),
                ].length
              }
            </strong>
          </div>
        </div>
      </section>

      {notice ? (
        <div className="history-notice" role="status">
          <Icon name="check" width="18" />
          {notice}
        </div>
      ) : null}

      <section className="history-controls">
        <div className="history-tabs" role="tablist">
          {[
            ["all", "Semua"],
            ["orders", "Produk"],
            ["bookings", "Home service"],
          ].map(([value, label]) => (
            <button
              aria-selected={filter === value}
              className={filter === value ? "is-active" : ""}
              key={value}
              onClick={() => setFilter(value as HistoryFilter)}
              role="tab"
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <label className="history-search">
          <Icon name="search" width="17" />
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Cari nomor, produk, layanan, resi..."
            type="search"
            value={query}
          />
        </label>
      </section>

      {state.orders.length === 0 && state.bookings.length === 0 ? (
        <section className="history-empty">
          <span>
            <Icon name="clock" width="30" />
          </span>
          <h2>Belum ada riwayat transaksi.</h2>
          <p>
            Lakukan checkout atau booking pertama. Untuk menguji seluruh status sekarang, muat
            contoh riwayat development.
          </p>
          <div>
            <button
              className="primary-button"
              onClick={() => {
                loadDemoHistory();
                announce("Contoh riwayat berhasil dimuat.");
              }}
              type="button"
            >
              Muat contoh riwayat
              <Icon name="sparkle" width="18" />
            </button>
            <Link className="secondary-button" href="/products">
              Mulai belanja
            </Link>
          </div>
        </section>
      ) : records.length === 0 ? (
        <section className="history-empty compact-history-empty">
          <h2>Tidak ada transaksi yang cocok.</h2>
          <p>Ubah tab atau kata pencarian.</p>
        </section>
      ) : (
        <section className="history-list">
          {records.map((item) => {
            if (item.kind === "order") {
              const order = item.record;
              const completed = order.timeline.filter((timeline) => timeline.completed).length;
              const canCancel =
                ["awaiting_payment", "processing"].includes(order.status) &&
                order.fulfillmentStatus !== "shipped";
              const canConfirm =
                order.status === "shipped" || order.fulfillmentStatus === "shipped";
              const canRefund =
                order.paymentStatus === "paid" &&
                !["cancelled"].includes(order.status) &&
                order.refundStatus !== "requested";

              return (
                <article className="history-card" key={`order-${order.id}`}>
                  <div className="history-card__header">
                    <div>
                      <span>Order produk</span>
                      <h2>{order.number}</h2>
                    </div>
                    <span className={`history-state state-${order.status}`}>
                      {fulfillmentLabel(order)}
                    </span>
                  </div>

                  <div className="history-card__status-grid">
                    <div>
                      <span>Status pembayaran</span>
                      <strong>{paymentLabel(order.paymentStatus)}</strong>
                      {order.paymentExpiresAt && order.paymentStatus === "pending" ? (
                        <small>
                          Batas{" "}
                          {new Intl.DateTimeFormat("id-ID", {
                            dateStyle: "medium",
                            timeStyle: "short",
                          }).format(new Date(order.paymentExpiresAt))}
                        </small>
                      ) : null}
                    </div>
                    <div>
                      <span>Status pengantaran</span>
                      <strong>{fulfillmentLabel(order)}</strong>
                      <small>
                        {order.courier && order.trackingNumber
                          ? `${order.courier} · ${order.trackingNumber}`
                          : "Resi belum tersedia"}
                      </small>
                    </div>
                    <div>
                      <span>Estimasi tiba</span>
                      <strong>
                        {order.estimatedDeliveryAt
                          ? new Intl.DateTimeFormat("id-ID", {
                              dateStyle: "medium",
                            }).format(new Date(order.estimatedDeliveryAt))
                          : "Belum tersedia"}
                      </strong>
                      <small>{order.deliveryMethod}</small>
                    </div>
                    <div>
                      <span>Total</span>
                      <strong>{formatMoney(order.totalMinor)}</strong>
                      <small>
                        Refund: {order.refundStatus ?? "none"} · Dispute:{" "}
                        {order.disputeStatus ?? "none"}
                      </small>
                    </div>
                  </div>

                  <Progress completed={completed} total={order.timeline.length} />

                  <div className="history-card__items">
                    {order.items.map((line) => (
                      <span key={line.lineId}>
                        {line.quantity}× {productById(line.productId)?.name ?? "Produk Yoru"}
                      </span>
                    ))}
                  </div>

                  <div className="history-card__actions">
                    <Link className="secondary-button" href={`/orders/${order.id}`}>
                      Detail dan timeline
                    </Link>
                    {order.paymentStatus === "pending" ? (
                      <button
                        className="primary-button"
                        onClick={() => {
                          retryOrderPayment(order.id);
                          announce("Pembayaran ulang demo berhasil.");
                        }}
                        type="button"
                      >
                        Bayar ulang
                      </button>
                    ) : null}
                    {canConfirm ? (
                      <button
                        className="primary-button"
                        onClick={() => {
                          confirmOrderReceived(order.id);
                          announce("Paket dikonfirmasi sudah diterima.");
                        }}
                        type="button"
                      >
                        Konfirmasi diterima
                      </button>
                    ) : null}
                    {canCancel ? (
                      <button
                        className="history-danger-button"
                        onClick={() => handleCancelOrder(order)}
                        type="button"
                      >
                        Batalkan pesanan
                      </button>
                    ) : null}
                    {canRefund ? (
                      <button
                        className="history-text-button"
                        onClick={() => handleRefund(order)}
                        type="button"
                      >
                        Refund atau dispute
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            }

            const booking = item.record;
            const completed = booking.timeline.filter((timeline) => timeline.completed).length;
            const canModify = ![
              "en_route",
              "arrived",
              "in_service",
              "completed",
              "cancelled",
            ].includes(booking.status);

            return (
              <article className="history-card history-card--booking" key={`booking-${booking.id}`}>
                <div className="history-card__header">
                  <div>
                    <span>Home service</span>
                    <h2>{booking.number}</h2>
                  </div>
                  <span className={`history-state state-${booking.status}`}>
                    {bookingLabel(booking.status)}
                  </span>
                </div>

                <div className="history-card__status-grid">
                  <div>
                    <span>Status pembayaran</span>
                    <strong>{paymentLabel(booking.paymentStatus)}</strong>
                    <small>Refund: {booking.refundStatus ?? "none"}</small>
                  </div>
                  <div>
                    <span>Jadwal layanan</span>
                    <strong>
                      {new Intl.DateTimeFormat("id-ID", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      }).format(new Date(booking.scheduledAt))}
                    </strong>
                    <small>Reschedule {booking.rescheduleCount ?? 0} kali</small>
                  </div>
                  <div>
                    <span>Profesional</span>
                    <strong>{booking.professionalName}</strong>
                    <small>{bookingLabel(booking.status)}</small>
                  </div>
                  <div>
                    <span>Total</span>
                    <strong>{formatMoney(booking.totalMinor)}</strong>
                    <small>{booking.serviceName}</small>
                  </div>
                </div>

                <Progress completed={completed} total={booking.timeline.length} />

                <div className="history-card__actions">
                  <Link className="secondary-button" href={`/bookings/${booking.id}`}>
                    Detail, OTP, dan tracking
                  </Link>
                  {canModify ? (
                    <button
                      className="primary-button"
                      onClick={() => {
                        rescheduleBooking(booking.id);
                        announce("Jadwal demo dipindahkan satu hari.");
                      }}
                      type="button"
                    >
                      Reschedule +1 hari
                    </button>
                  ) : null}
                  {canModify ? (
                    <button
                      className="history-danger-button"
                      onClick={() => handleCancelBooking(booking)}
                      type="button"
                    >
                      Batalkan booking
                    </button>
                  ) : null}
                </div>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}
