"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useMemo, useState } from "react";

import { Icon } from "@/components/icons";
import { formatMoney, serviceBookingTotals } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";
import type { Service, ShippingAddress } from "@/lib/storefront-types";

const steps = ["Jadwal", "Profesional", "Lokasi", "Pembayaran"];

function dateOptions(): Array<{ iso: string; day: string; date: string }> {
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date();
    date.setDate(date.getDate() + index + 1);
    return {
      iso: date.toISOString().slice(0, 10),
      day: new Intl.DateTimeFormat("id-ID", { weekday: "short" }).format(date),
      date: new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short" }).format(date),
    };
  });
}

const timeOptions = ["09:00", "11:00", "13:30", "16:00", "18:30"];

export function ServiceBookingFlow({ service }: { service: Service }) {
  const router = useRouter();
  const { createBooking } = useStorefront();
  const dates = useMemo(() => dateOptions(), []);
  const totals = serviceBookingTotals(service);
  const [step, setStep] = useState(0);
  const [selectedDate, setSelectedDate] = useState(dates[0].iso);
  const [selectedTime, setSelectedTime] = useState(timeOptions[0]);
  const [professionalId, setProfessionalId] = useState(service.professionals[0].id);
  const [paymentMethod, setPaymentMethod] = useState("virtual_account");
  const [notes, setNotes] = useState("");
  const [pending, setPending] = useState(false);
  const [address, setAddress] = useState<ShippingAddress>({
    recipientName: "",
    phone: "",
    addressLine: "",
    city: "",
    postalCode: "",
    notes: "",
  });

  function saveLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setAddress({
      recipientName: String(data.get("recipientName") ?? ""),
      phone: String(data.get("phone") ?? ""),
      addressLine: String(data.get("addressLine") ?? ""),
      city: String(data.get("city") ?? ""),
      postalCode: String(data.get("postalCode") ?? ""),
      notes: String(data.get("locationNotes") ?? ""),
    });
    setNotes(String(data.get("serviceNotes") ?? ""));
    setStep(3);
  }

  function confirmBooking() {
    setPending(true);
    const scheduledAt = new Date(`${selectedDate}T${selectedTime}:00+07:00`).toISOString();
    const booking = createBooking({
      service,
      address,
      scheduledAt,
      professionalId,
      paymentMethod,
      notes,
    });
    router.replace(`/bookings/${booking.id}?new=1`);
  }

  return (
    <main className="booking-shell">
      <section className="booking-main">
        <div className="page-heading compact-heading">
          <p className="section-eyebrow">Home service booking</p>
          <h1>{service.name}</h1>
          <p>
            {service.partner} · {service.durationMin} menit
          </p>
        </div>

        <div className="stepper booking-stepper">
          {steps.map((label, index) => (
            <div className={index <= step ? "is-active" : ""} key={label}>
              <span>{index < step ? <Icon name="check" width="15" /> : index + 1}</span>
              <strong>{label}</strong>
            </div>
          ))}
        </div>

        {step === 0 ? (
          <section className="checkout-card">
            <div className="checkout-card__heading">
              <span className="checkout-icon">
                <Icon name="calendar" width="21" />
              </span>
              <div>
                <h2>Pilih tanggal dan waktu</h2>
                <p>Slot demo tersedia untuk tujuh hari ke depan.</p>
              </div>
            </div>
            <div className="date-grid">
              {dates.map((date) => (
                <button
                  className={selectedDate === date.iso ? "is-selected" : ""}
                  key={date.iso}
                  onClick={() => setSelectedDate(date.iso)}
                  type="button"
                >
                  <span>{date.day}</span>
                  <strong>{date.date}</strong>
                </button>
              ))}
            </div>
            <div className="time-grid">
              {timeOptions.map((time) => (
                <button
                  className={selectedTime === time ? "is-selected" : ""}
                  key={time}
                  onClick={() => setSelectedTime(time)}
                  type="button"
                >
                  {time}
                </button>
              ))}
            </div>
            <div className="checkout-navigation">
              <span />
              <button className="primary-button" onClick={() => setStep(1)} type="button">
                Pilih profesional
                <Icon name="arrow" width="18" />
              </button>
            </div>
          </section>
        ) : null}

        {step === 1 ? (
          <section className="checkout-card">
            <div className="checkout-card__heading">
              <span className="checkout-icon">
                <Icon name="user" width="21" />
              </span>
              <div>
                <h2>Pilih profesional</h2>
                <p>Semua profesional di bawah tersedia untuk slot pilihanmu.</p>
              </div>
            </div>
            <div className="professional-selection">
              {service.professionals.map((professional) => (
                <button
                  className={professionalId === professional.id ? "is-selected" : ""}
                  key={professional.id}
                  onClick={() => setProfessionalId(professional.id)}
                  type="button"
                >
                  <span className="professional-avatar">{professional.avatar}</span>
                  <div>
                    <strong>{professional.name}</strong>
                    <span>{professional.title}</span>
                    <small>
                      <Icon name="star" width="14" />
                      {professional.rating} · {professional.completedJobs} pekerjaan
                    </small>
                  </div>
                  <span className="selection-radio" />
                </button>
              ))}
            </div>
            <div className="checkout-navigation">
              <button className="secondary-button" onClick={() => setStep(0)} type="button">
                Kembali
              </button>
              <button className="primary-button" onClick={() => setStep(2)} type="button">
                Isi lokasi
                <Icon name="arrow" width="18" />
              </button>
            </div>
          </section>
        ) : null}

        {step === 2 ? (
          <form className="checkout-card form-grid" onSubmit={saveLocation}>
            <div className="checkout-card__heading form-span-2">
              <span className="checkout-icon">
                <Icon name="pin" width="21" />
              </span>
              <div>
                <h2>Lokasi layanan</h2>
                <p>Yoru akan memvalidasi ulang area layanan sebelum booking production dibuat.</p>
              </div>
            </div>
            <label>
              Nama customer
              <input defaultValue={address.recipientName} name="recipientName" required />
            </label>
            <label>
              Nomor telepon
              <input defaultValue={address.phone} name="phone" required type="tel" />
            </label>
            <label className="form-span-2">
              Alamat lengkap
              <textarea defaultValue={address.addressLine} name="addressLine" required rows={4} />
            </label>
            <label>
              Kota
              <input defaultValue={address.city} name="city" required />
            </label>
            <label>
              Kode pos
              <input defaultValue={address.postalCode} name="postalCode" required />
            </label>
            <label className="form-span-2">
              Petunjuk lokasi
              <input
                defaultValue={address.notes}
                name="locationNotes"
                placeholder="Patokan, lantai, unit"
              />
            </label>
            <label className="form-span-2">
              Catatan untuk profesional
              <textarea
                defaultValue={notes}
                name="serviceNotes"
                placeholder="Preferensi atau kebutuhan khusus"
                rows={3}
              />
            </label>
            <div className="checkout-navigation form-span-2">
              <button className="secondary-button" onClick={() => setStep(1)} type="button">
                Kembali
              </button>
              <button className="primary-button" type="submit">
                Pilih pembayaran
                <Icon name="arrow" width="18" />
              </button>
            </div>
          </form>
        ) : null}

        {step === 3 ? (
          <section className="checkout-card">
            <div className="checkout-card__heading">
              <span className="checkout-icon">
                <Icon name="shield" width="21" />
              </span>
              <div>
                <h2>Pembayaran dan konfirmasi</h2>
                <p>Booking production wajib memakai idempotency key dan slot lock server.</p>
              </div>
            </div>
            <div className="selection-list payment-selection">
              {[
                ["virtual_account", "Virtual account", "BCA, Mandiri, BNI, atau BRI"],
                ["ewallet", "E-wallet", "GoPay, OVO, DANA, atau ShopeePay"],
                ["card", "Kartu debit/kredit", "Diproses oleh payment provider"],
              ].map(([id, label, detail]) => (
                <button
                  className={paymentMethod === id ? "is-selected" : ""}
                  key={id}
                  onClick={() => setPaymentMethod(id)}
                  type="button"
                >
                  <span className="selection-radio" />
                  <div>
                    <strong>{label}</strong>
                    <span>{detail}</span>
                  </div>
                </button>
              ))}
            </div>
            <div className="booking-consent">
              <Icon name="check" width="18" />
              <p>
                Dengan melanjutkan, kamu menyetujui jadwal, kebijakan pembatalan, dan penggunaan OTP
                untuk check-in layanan.
              </p>
            </div>
            <div className="checkout-navigation">
              <button className="secondary-button" onClick={() => setStep(2)} type="button">
                Kembali
              </button>
              <button
                className="primary-button"
                disabled={pending}
                onClick={confirmBooking}
                type="button"
              >
                {pending ? "Memproses..." : "Bayar dan buat booking"}
                <Icon name="check" width="18" />
              </button>
            </div>
          </section>
        ) : null}
      </section>

      <aside className="summary-card booking-summary">
        <p className="summary-kicker">Booking summary</p>
        <h2>{service.name}</h2>
        <div className="booking-summary__meta">
          <span>
            <Icon name="calendar" width="17" />
            {new Intl.DateTimeFormat("id-ID", {
              day: "numeric",
              month: "long",
              year: "numeric",
            }).format(new Date(`${selectedDate}T00:00:00+07:00`))}
          </span>
          <span>
            <Icon name="clock" width="17" />
            {selectedTime} · {service.durationMin} menit
          </span>
          <span>
            <Icon name="user" width="17" />
            {service.professionals.find((item) => item.id === professionalId)?.name}
          </span>
        </div>
        <div className="summary-divider" />
        <div className="summary-row">
          <span>Layanan</span>
          <span>{formatMoney(totals.serviceSubtotalMinor)}</span>
        </div>
        <div className="summary-row">
          <span>Transport</span>
          <span>{formatMoney(totals.transportMinor)}</span>
        </div>
        <div className="summary-row">
          <span>Biaya platform</span>
          <span>{formatMoney(totals.platformFeeMinor)}</span>
        </div>
        <div className="summary-total">
          <span>Total</span>
          <strong>{formatMoney(totals.totalMinor)}</strong>
        </div>
        <div className="summary-note">
          <Icon name="pin" width="18" />
          <span>{service.serviceArea}</span>
        </div>
      </aside>
    </main>
  );
}
