"use client";

import type { AuthSession } from "@yoru/contracts";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/icons";
import { ApiError, apiRequest } from "@/lib/api";
import { useStorefront } from "@/lib/storefront-store";

const navigation = [
  { href: "/products", label: "Belanja" },
  { href: "/services", label: "Home service" },
  { href: "/collections", label: "Koleksi" },
  { href: "/deals", label: "Deals" },
];

function openSearch(mode: "query" | "ai" | "image" = "query") {
  window.dispatchEvent(new CustomEvent("yoru:open-search", { detail: { mode } }));
}

export function SiteHeader() {
  const pathname = usePathname();
  const { cartCount } = useStorefront();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
    });

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
      window.cancelAnimationFrame(frame);
    };
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    window.localStorage.setItem("yoru-theme", next);
    setTheme(next);
  }

  return (
    <>
      <div className="announcement-bar">
        <span>Gratis pengiriman untuk pilihan tertentu</span>
        <Link href="/deals">Lihat penawaran hari ini</Link>
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
                className={pathname === item.href || pathname.startsWith(`${item.href}/`) ? "is-active" : ""}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <button className="header-search header-search--button" onClick={() => openSearch("query")} type="button">
            <Icon name="search" width="18" />
            <span>Cari produk, layanan, atau gambar</span>
            <kbd>⌘K</kbd>
          </button>

          <div className="header-actions">
            <button
              aria-label={`Gunakan mode ${theme === "dark" ? "terang" : "gelap"}`}
              aria-pressed={theme === "dark"}
              className="theme-toggle"
              onClick={toggleTheme}
              title={`Mode ${theme === "dark" ? "terang" : "gelap"}`}
              type="button"
            >
              <span className="theme-toggle__track" aria-hidden="true"><span /></span>
              <span className="visually-hidden">{theme === "dark" ? "Mode gelap aktif" : "Mode terang aktif"}</span>
            </button>

            <Link aria-label="Wishlist" className="icon-button header-action-secondary" href="/wishlist">
              <Icon name="heart" width="19" />
            </Link>

            <Link
              aria-label={session ? `Akun ${session.user.full_name}` : "Masuk ke akun"}
              className="icon-button header-action-secondary"
              href={session ? "/account" : "/login"}
            >
              <Icon name="user" width="19" />
            </Link>

            <Link aria-label={`Keranjang berisi ${cartCount} item`} className="icon-button" href="/cart">
              <Icon name="bag" width="19" />
              {cartCount > 0 ? <span className="cart-count">{cartCount}</span> : null}
            </Link>

            <button
              aria-expanded={mobileOpen}
              aria-label="Buka navigasi"
              className="icon-button mobile-menu-button"
              onClick={() => setMobileOpen((value) => !value)}
              type="button"
            >
              <Icon name={mobileOpen ? "close" : "menu"} width="20" />
            </button>
          </div>
        </div>

        {mobileOpen ? (
          <div className="mobile-menu">
            <button
              className="mobile-search-trigger"
              onClick={() => {
                setMobileOpen(false);
                openSearch("query");
              }}
              type="button"
            >
              <Icon name="search" width="18" />
              Cari di Yoru
              <Icon name="arrow" width="18" />
            </button>
            {navigation.map((item) => (
              <Link href={item.href} key={item.href} onClick={() => setMobileOpen(false)}>
                {item.label}
                <Icon name="arrow" width="18" />
              </Link>
            ))}
            <Link href="/wishlist" onClick={() => setMobileOpen(false)}>Wishlist <Icon name="arrow" width="18" /></Link>
            <Link href="/history" onClick={() => setMobileOpen(false)}>Riwayat transaksi <Icon name="arrow" width="18" /></Link>
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
