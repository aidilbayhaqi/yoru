import Link from "next/link";

import { AuthForm } from "@/components/auth-form";
import { Icon } from "@/components/icons";

type Props = { searchParams: Promise<{ next?: string | string[] }> };

export default async function RegisterPage({ searchParams }: Props) {
  const values = await searchParams;
  const nextPath = Array.isArray(values.next) ? values.next[0] : values.next;

  return (
    <main className="storefront-auth-page">
      <div className="storefront-auth-shell storefront-auth-shell--register">
        <section className="storefront-auth-visual storefront-auth-visual--register">
          <Link className="commerce-brand auth-brand" href="/">
            <span className="commerce-brand__mark">Y</span>
            <span>Yoru</span>
          </Link>

          <div className="auth-visual-copy">
            <p className="section-eyebrow">Customer registration</p>
            <h1>One account for commerce and home service.</h1>
            <p>
              Buat akun customer untuk menyimpan pilihan, mengikuti order, dan mengelola booking
              dalam satu tempat.
            </p>
          </div>

          <div className="auth-benefits" aria-label="Yoru account benefits">
            <span>
              <Icon name="heart" width="19" />
              <span>
                <strong>Simpan favorit</strong>
                <small>Bangun wishlist produk dan layananmu.</small>
              </span>
            </span>
            <span>
              <Icon name="truck" width="19" />
              <span>
                <strong>Pantau transaksi</strong>
                <small>Order dan pengiriman punya status jelas.</small>
              </span>
            </span>
            <span>
              <Icon name="user" width="19" />
              <span>
                <strong>Kelola booking</strong>
                <small>Lihat profesional, slot, OTP, dan lifecycle.</small>
              </span>
            </span>
          </div>
        </section>

        <section className="storefront-auth-card">
          <div className="storefront-auth-card__topline">
            <Link className="auth-back-link" href="/">
              <Icon name="arrow" width="16" />
              Kembali ke storefront
            </Link>
            <span>Customer account</span>
          </div>

          <div className="storefront-auth-card__heading">
            <p className="section-eyebrow">Create account</p>
            <h2>Mulai perjalananmu.</h2>
            <p>
              Gunakan email aktif dan password kuat. Registrasi publik hanya membuat akun customer.
            </p>
          </div>

          <AuthForm mode="register" nextPath={nextPath} />

          <div className="auth-security-note">
            <Icon name="shield" width="17" />
            <span>
              Partner dan admin tetap melalui onboarding terkontrol. Role tidak dapat dipilih dari
              formulir registrasi publik.
            </span>
          </div>
        </section>
      </div>
    </main>
  );
}
