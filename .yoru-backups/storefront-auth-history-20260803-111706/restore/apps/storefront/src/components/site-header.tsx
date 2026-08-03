"use client";

import type { AuthSession } from "@yoru/contracts";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { Icon } from "@/components/icons";
import { ApiError, apiRequest } from "@/lib/api";
import { useStorefront } from "@/lib/storefront-store";

const navigation = [
  { href: "/products", label: "Belanja" },
  { href: "/services", label: "Home service" },
  { href: "/assistant", label: "Yoru Advisor" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { cartCount } = useStorefront();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    let active = true;
    apiRequest<AuthSession>("/auth/me")
      .then((value) => {
        if (active) setSession(value);
      })
      .catch((reason) => {
        if (active && reason instanceof ApiError && reason.status !== 401) {
          console.warn("Storefront session lookup failed", reason.code);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const query = String(data.get("q") ?? "").trim();
    if (query) {
      router.push(`/search?q=${encodeURIComponent(query)}`);
    }
  }

  return (
    <>
      <div className="announcement-bar">
        <span>Gratis ongkir produk mulai Rp500 ribu</span>
        <span>Profesional terverifikasi untuk layanan di rumah</span>
      </div>
      <header className="commerce-header">
        <div className="commerce-header__inner">
          <Link className="commerce-brand" href="/" aria-label="Yoru home">
            <span className="commerce-brand__mark">Y</span>
            <span>Yoru</span>
          </Link>

          <nav className="commerce-nav" aria-label="Navigasi utama">
            {navigation.map((item) => (
              <Link
                className={
                  pathname === item.href || pathname.startsWith(`${item.href}/`) ? "is-active" : ""
                }
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <form className="header-search" onSubmit={submitSearch} role="search">
            <Icon name="search" width="18" />
            <input
              aria-label="Cari produk atau layanan"
              name="q"
              placeholder="Cari serum, facial, hair spa..."
              type="search"
            />
          </form>

          <div className="header-actions">
            <Link
              aria-label={session ? `Akun ${session.user.full_name}` : "Masuk ke akun"}
              className="icon-button"
              href={session ? "/account" : "/login"}
            >
              <Icon name="user" width="20" />
            </Link>
            <Link aria-label={`Keranjang berisi ${cartCount} item`} className="icon-button" href="/cart">
              <Icon name="bag" width="20" />
              {cartCount > 0 ? <span className="cart-count">{cartCount}</span> : null}
            </Link>
            <button
              aria-expanded={mobileOpen}
              aria-label="Buka navigasi"
              className="icon-button mobile-menu-button"
              onClick={() => setMobileOpen((value) => !value)}
              type="button"
            >
              <Icon name={mobileOpen ? "close" : "menu"} width="21" />
            </button>
          </div>
        </div>

        {mobileOpen ? (
          <div className="mobile-menu">
            <form className="header-search mobile-search" onSubmit={submitSearch} role="search">
              <Icon name="search" width="18" />
              <input name="q" placeholder="Cari di Yoru" type="search" />
            </form>
            {navigation.map((item) => (
              <Link href={item.href} key={item.href} onClick={() => setMobileOpen(false)}>
                {item.label}
                <Icon name="arrow" width="18" />
              </Link>
            ))}
            <Link href={session ? "/account" : "/login"} onClick={() => setMobileOpen(false)}>
              {session ? "Akun saya" : "Masuk"}
              <Icon name="arrow" width="18" />
            </Link>
          </div>
        ) : null}
      </header>
    </>
  );
}
