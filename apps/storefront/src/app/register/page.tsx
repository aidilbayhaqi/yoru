import Link from "next/link";

import { AuthForm } from "@/components/auth-form";
import { Icon } from "@/components/icons";

type Props = { searchParams: Promise<{ next?: string | string[] }> };

export default async function RegisterPage({ searchParams }: Props) {
  const values = await searchParams;
  const nextPath = Array.isArray(values.next) ? values.next[0] : values.next;

  return (
    <main className="storefront-auth-shell">
      <section className="storefront-auth-visual auth-visual-register">
        <Link className="commerce-brand auth-brand" href="/">
          <span className="commerce-brand__mark">Y</span>
          <span>Yoru</span>
        </Link>
        <div className="auth-visual-copy">
          <p className="section-eyebrow">Customer registration</p>
          <h1>Satu akun untuk belanja dan home service.</h1>
          <p>
            Registrasi publik hanya membuat akun customer. Akses partner dan
            superadmin tetap diberikan melalui onboarding serta approval yang
            terkontrol.
          </p>
        </div>
        <div className="auth-benefits">
          <span>
            <Icon name="heart" width="18" /> Simpan favorit
          </span>
          <span>
            <Icon name="truck" width="18" /> Pantau order
          </span>
          <span>
            <Icon name="user" width="18" /> Kelola booking
          </span>
          <span>
            <Icon name="shield" width="18" /> Session aman
          </span>
        </div>
      </section>

      <section className="storefront-auth-card">
        <div>
          <p className="section-eyebrow">Create customer account</p>
          <h2>Buat akun Yoru.</h2>
          <p>
            Gunakan email aktif. Setiap kesalahan validasi akan ditampilkan pada
            kolom yang perlu diperbaiki, tanpa mengirim ulang password ke layar.
          </p>
        </div>
        <AuthForm mode="register" nextPath={nextPath} />
      </section>
    </main>
  );
}
