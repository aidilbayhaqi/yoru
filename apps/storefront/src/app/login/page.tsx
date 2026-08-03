import Link from "next/link";

import { AuthForm } from "@/components/auth-form";
import { Icon } from "@/components/icons";

type Props = { searchParams: Promise<{ next?: string | string[] }> };

export default async function LoginPage({ searchParams }: Props) {
  const values = await searchParams;
  const nextPath = Array.isArray(values.next) ? values.next[0] : values.next;

  return (
    <main className="storefront-auth-shell">
      <section className="storefront-auth-visual auth-visual-login">
        <Link className="commerce-brand auth-brand" href="/">
          <span className="commerce-brand__mark">Y</span><span>Yoru</span>
        </Link>
        <div className="auth-visual-copy">
          <p className="section-eyebrow">One account, two experiences</p>
          <h1>Belanja dan booking dengan satu akun.</h1>
          <p>Pantau produk, pembayaran, jadwal, profesional, dan layanan dari halaman akun yang sama.</p>
        </div>
        <div className="auth-benefits">
          <span><Icon name="shield" width="18" />Secure browser session</span>
          <span><Icon name="bag" width="18" />Order history</span>
          <span><Icon name="calendar" width="18" />Booking tracking</span>
        </div>
      </section>
      <section className="storefront-auth-card">
        <div><p className="section-eyebrow">Customer sign in</p><h2>Selamat datang kembali.</h2><p>Masuk untuk melanjutkan checkout, booking, dan mengakses riwayat transaksi.</p></div>
        <AuthForm mode="login" nextPath={nextPath} />
      </section>
    </main>
  );
}
