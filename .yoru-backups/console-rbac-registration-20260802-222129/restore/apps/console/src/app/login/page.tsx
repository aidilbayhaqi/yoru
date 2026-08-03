import Link from "next/link";

import { ConsoleLoginForm } from "@/components/console-login-form";

export default function ConsoleLoginPage() {
  return (
    <main className="console-auth-shell">
      <section className="console-auth-brand">
        <Link className="logo" href="/login">
          <span>Y</span>
          <strong>Yoru</strong>
        </Link>
        <div>
          <p className="kicker">Operational access</p>
          <h1>Satu console, akses sesuai tanggung jawab.</h1>
          <p>
            Partner dan platform operator hanya melihat capability serta tenant yang diberikan oleh
            server.
          </p>
        </div>
      </section>
      <section className="console-auth-card">
        <p className="kicker">Secure sign in</p>
        <h2>Masuk ke Yoru Console</h2>
        <ConsoleLoginForm />
        <p className="console-auth-note">
          Akun admin dibuat melalui bootstrap terkontrol. Tidak tersedia public admin registration.
        </p>
      </section>
    </main>
  );
}
