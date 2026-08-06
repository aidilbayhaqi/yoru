"use client";

import Link from "next/link";
import { Icon } from "@/components/icons";
import { formatMoney } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";

export function BookingDetailScreen({ bookingId }: { bookingId: string }) {
  const { hydrated, state } = useStorefront();
  const booking = state.bookings.find((item) => item.id === bookingId);
  if (!hydrated) return <div className="page-state">Memuat detail booking...</div>;
  if (!booking)
    return (
      <section className="empty-state">
        <h1>Booking tidak ditemukan.</h1>
        <Link className="primary-button" href="/bookings">
          Kembali ke booking
        </Link>
      </section>
    );

  return (
    <main className="record-detail-page">
      <div className="record-detail-heading">
        <div>
          <p className="section-eyebrow">Home service booking</p>
          <h1>{booking.number}</h1>
          <p>{booking.serviceName}</p>
        </div>
        <span className={`record-status status-${booking.status}`}>Dikonfirmasi</span>
      </div>
      <div className="record-detail-grid">
        <section className="record-detail-main">
          <article className="record-card booking-focus-card">
            <div>
              <span className="professional-avatar">
                {booking.professionalName
                  .split(" ")
                  .map((item) => item[0])
                  .join("")
                  .slice(0, 2)}
              </span>
              <div>
                <span>Profesional</span>
                <h2>{booking.professionalName}</h2>
              </div>
            </div>
            <div>
              <span>Jadwal</span>
              <strong>
                {new Intl.DateTimeFormat("id-ID", { dateStyle: "full", timeStyle: "short" }).format(
                  new Date(booking.scheduledAt),
                )}
              </strong>
            </div>
          </article>
          <article className="record-card">
            <h2>Status booking</h2>
            <div className="timeline">
              {booking.timeline.map((item) => (
                <div className={item.completed ? "is-complete" : ""} key={item.label}>
                  <span className="timeline-marker">
                    {item.completed ? <Icon name="check" width="14" /> : null}
                  </span>
                  <div>
                    <strong>{item.label}</strong>
                    <p>{item.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </article>
        </section>
        <aside className="record-detail-side">
          <article className="record-card otp-card">
            <p className="section-eyebrow">Service check-in</p>
            <h2>OTP layanan</h2>
            <strong>{booking.otp}</strong>
            <p>Berikan OTP hanya setelah profesional tiba di lokasi.</p>
          </article>
          <article className="record-card">
            <h2>Lokasi</h2>
            <strong>{booking.address.recipientName}</strong>
            <p>{booking.address.phone}</p>
            <p>
              {booking.address.addressLine}, {booking.address.city} {booking.address.postalCode}
            </p>
          </article>
          <article className="record-card">
            <h2>Pembayaran</h2>
            <div className="summary-row">
              <span>Layanan</span>
              <span>{formatMoney(booking.serviceSubtotalMinor)}</span>
            </div>
            <div className="summary-row">
              <span>Transport</span>
              <span>{formatMoney(booking.transportMinor)}</span>
            </div>
            <div className="summary-row">
              <span>Biaya platform</span>
              <span>{formatMoney(booking.platformFeeMinor)}</span>
            </div>
            <div className="summary-total">
              <span>Total</span>
              <strong>{formatMoney(booking.totalMinor)}</strong>
            </div>
          </article>
        </aside>
      </div>
    </main>
  );
}
