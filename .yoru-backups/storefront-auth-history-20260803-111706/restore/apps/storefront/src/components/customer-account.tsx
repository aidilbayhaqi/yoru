"use client";

import type { AuthSession } from "@yoru/contracts";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/icons";
import { ApiError, apiRequest } from "@/lib/api";
import { useStorefront } from "@/lib/storefront-store";

export function CustomerAccount() {
  const router = useRouter();
  const { state } = useStorefront();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiRequest<AuthSession>("/auth/me")
      .then((value) => {
        if (active) setSession(value);
      })
      .catch((reason) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 401) {
          router.replace("/login?next=%2Faccount");
          return;
        }
        setError("Data akun belum dapat dimuat.");
      });

    return () => {
      active = false;
    };
  }, [router]);

  async function logout() {
    try {
      await apiRequest<{ message: string }>("/auth/logout", { method: "POST" });
    } finally {
      router.replace("/");
      router.refresh();
    }
  }

  if (error) return <div className="page-state">{error}</div>;
  if (!session) return <div className="page-state">Memuat akun...</div>;

  return (
    <main className="account-page">
      <section className="account-hero">
        <div className="account-avatar">{session.user.full_name.slice(0, 2).toUpperCase()}</div>
        <div><p className="section-eyebrow">Customer account</p><h1>Halo, {session.user.full_name.split(" ")[0]}.</h1><p>{session.user.email}</p></div>
        <button className="secondary-button" onClick={logout} type="button">Keluar</button>
      </section>
      <section className="account-dashboard-grid">
        <Link href="/orders"><span className="account-tile-icon"><Icon name="bag" width="22" /></span><div><strong>Pesanan</strong><span>{state.orders.length} order tersimpan</span></div><Icon name="arrow" width="18" /></Link>
        <Link href="/bookings"><span className="account-tile-icon"><Icon name="calendar" width="22" /></span><div><strong>Booking</strong><span>{state.bookings.length} layanan tersimpan</span></div><Icon name="arrow" width="18" /></Link>
        <Link href="/assistant"><span className="account-tile-icon"><Icon name="wand" width="22" /></span><div><strong>Yoru Advisor</strong><span>Bantu pilih produk dan layanan</span></div><Icon name="arrow" width="18" /></Link>
        <Link href="/products"><span className="account-tile-icon"><Icon name="heart" width="22" /></span><div><strong>Favorit</strong><span>{state.favorites.length} item disimpan</span></div><Icon name="arrow" width="18" /></Link>
      </section>
      <section className="account-information">
        <div><h2>Informasi akun</h2><dl><div><dt>Status</dt><dd>{session.user.status}</dd></div><div><dt>Role storefront</dt><dd>Customer</dd></div><div><dt>Session</dt><dd>Secure HttpOnly cookie</dd></div></dl></div>
        <div className="account-security-card"><Icon name="shield" width="28" /><h2>Akun dan transaksi tetap terpisah dari console partner.</h2><p>Storefront hanya memberi akses customer. Otorisasi partner dan super admin tetap berada di console dan API.</p></div>
      </section>
    </main>
  );
}
