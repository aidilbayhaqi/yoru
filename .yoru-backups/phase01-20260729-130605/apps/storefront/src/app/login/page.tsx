import Link from "next/link";

import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  return (
    <main className="auth-shell">
      <section className="auth-intro">
        <Link className="brand" href="/">
          <span className="brand-mark">Y</span>
          <span>Yoru</span>
        </Link>
        <div>
          <p className="eyebrow">Secure customer session</p>
          <h1>Masuk untuk melanjutkan perjalananmu.</h1>
          <p className="lead">
            Token akses tidak disimpan di local storage. Yoru menggunakan session cookie HttpOnly
            dan proteksi CSRF.
          </p>
        </div>
      </section>
      <section className="auth-card">
        <p className="card-kicker">Customer access</p>
        <h2>Selamat datang kembali</h2>
        <AuthForm mode="login" />
      </section>
    </main>
  );
}
