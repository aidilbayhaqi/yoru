import Link from "next/link";

import { AuthForm } from "@/components/auth-form";
import { Icon } from "@/components/icons";

type Props = { searchParams: Promise<{ next?: string | string[] }> };

export default async function LoginPage({ searchParams }: Props) {
  const values = await searchParams;
  const nextPath = Array.isArray(values.next) ? values.next[0] : values.next;

  return (
    <main className="storefront-auth-page">
      <div className="storefront-auth-shell storefront-auth-shell--login">
        <section className="storefront-auth-visual storefront-auth-visual--login">
          <Link className="commerce-brand auth-brand" href="/">
            <span className="commerce-brand__mark">Y</span>
            <span>Yoru</span>
          </Link>

          <div className="auth-visual-copy">
            <p className="section-eyebrow">One secure customer session</p>
            <h1>Welcome back to your curated routine.</h1>
            <p>
              Masuk untuk melanjutkan cart, wishlist, order, dan booking dari
              satu akun yang sama.
            </p>
          </div>

          <div className="auth-benefits" aria-label="Yoru account benefits">
            <span>
              <Icon name="bag" width="19" />
              <span><strong>Cart tetap tersimpan</strong><small>Lanjutkan pilihanmu tanpa mulai ulang.</small></span>
            </span>
            <span>
              <Icon name="heart" width="19" />
              <span><strong>Wishlist personal</strong><small>Simpan produk dan layanan yang relevan.</small></span>
            </span>
            <span>
              <Icon name="shield" width="19" />
              <span><strong>Session terlindungi</strong><small>Cookie HttpOnly dan proteksi CSRF.</small></span>
            </span>
          </div>
        </section>

        <section className="storefront-auth-card">
          <div className="storefront-auth-card__topline">
            <Link className="auth-back-link" href="/">
              <Icon name="arrow" width="16" />
              Kembali ke storefront
            </Link>
            <span>Customer sign in</span>
          </div>

          <div className="storefront-auth-card__heading">
            <p className="section-eyebrow">Sign in</p>
            <h2>Selamat datang kembali.</h2>
            <p>Gunakan email dan password akun Yoru milikmu.</p>
          </div>

          <AuthForm mode="login" nextPath={nextPath} />

          <div className="auth-security-note">
            <Icon name="shield" width="17" />
            <span>Token akses tidak disimpan di local storage. Yoru memakai session cookie HttpOnly dan proteksi CSRF.</span>
          </div>
        </section>
      </div>
    </main>
  );
}
