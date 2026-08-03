"use client";

import Link from "next/link";
import { Icon } from "@/components/icons";
import { formatMoney } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";

const labels = {
  requested: "Menunggu konfirmasi",
  confirmed: "Dikonfirmasi",
  assigned: "Profesional ditugaskan",
  en_route: "Menuju lokasi",
  arrived: "Sudah tiba",
  in_service: "Sedang berlangsung",
  completed: "Selesai",
  cancelled: "Dibatalkan",
};

export function BookingsScreen() {
  const { hydrated, state } = useStorefront();
  if (!hydrated) return <div className="page-state">Memuat booking...</div>;

  return (
    <main className="customer-list-page">
      <div className="page-heading"><p className="section-eyebrow">Customer account</p><h1>Booking layanan</h1><p>Pantau jadwal, profesional, OTP, dan status layanan di rumah.</p></div>
      {state.bookings.length === 0 ? (
        <section className="empty-state inline-empty-state"><span className="empty-state__icon"><Icon name="calendar" width="32" /></span><h2>Belum ada booking.</h2><p>Pilih layanan dan jadwal yang paling sesuai.</p><Link className="primary-button" href="/services">Cari layanan</Link></section>
      ) : (
        <div className="customer-record-list">
          {state.bookings.map((booking) => (
            <article key={booking.id}>
              <div className="record-header"><div><span>Nomor booking</span><strong>{booking.number}</strong></div><span className={`record-status status-${booking.status}`}>{labels[booking.status]}</span></div>
              <div className="booking-record-body"><div><p>{booking.serviceName}</p><h2>{booking.professionalName}</h2><span><Icon name="calendar" width="16" />{new Intl.DateTimeFormat("id-ID", { dateStyle: "full", timeStyle: "short" }).format(new Date(booking.scheduledAt))}</span></div><div className="record-total"><span>Total</span><strong>{formatMoney(booking.totalMinor)}</strong></div></div>
              <div className="record-footer"><span>{booking.address.city}</span><Link className="text-link" href={`/bookings/${booking.id}`}>Lihat detail<Icon name="arrow" width="17" /></Link></div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
