import Link from "next/link";

import { AuthForm } from "@/components/auth-form";

export default function RegisterPage() {
  return (
    <main className="auth-shell">
      <section className="auth-intro">
        <Link className="brand" href="/">
          <span className="brand-mark">Y</span>
          <span>Yoru</span>
        </Link>
        <div>
          <p className="eyebrow">Customer registration</p>
          <h1>Satu akun untuk commerce dan home service.</h1>
          <p className="lead">
            Registrasi publik hanya membuat akun customer. Akun partner dan admin melalui proses
            onboarding terkontrol.
          </p>
        </div>
      </section>
      <section className="auth-card">
        <p className="card-kicker">Create account</p>
        <h2>Daftar sebagai customer</h2>
        <AuthForm mode="register" />
      </section>
    </main>
  );
}
