"use client";

import Image from "next/image";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { ProductCard } from "@/components/product-card";
import { ServiceCard } from "@/components/service-card";
import { products, services } from "@/lib/storefront-data";

function openSearch(mode: "query" | "ai" | "image") {
  window.dispatchEvent(new CustomEvent("yoru:open-search", { detail: { mode } }));
}

export function HomeExperience() {
  const featuredProduct = products[3]!;
  const featuredService = services[0]!;
  const editorialService = services[1]!;

  return (
    <>
      <section className="v5-home-hero">
        <div className="v5-home-hero__copy">
          <p className="section-eyebrow">Curated commerce · Trusted at-home service</p>
          <h1>Style, care, and service. Designed around your day.</h1>
          <p className="v5-home-hero__lead">
            Produk terkurasi, profesional terverifikasi, dan discovery tools yang membantu kamu
            memilih tanpa bikin proses belanja terasa ribet.
          </p>
          <div className="hero-cta-row">
            <Link className="primary-button large-button" href="/products">
              Shop the edit
              <Icon name="arrow" width="19" />
            </Link>
            <Link className="secondary-button large-button" href="/services">
              Book home service
            </Link>
          </div>
          <button className="hero-discovery-trigger" onClick={() => openSearch("ai")} type="button">
            <span>
              <Icon name="wand" width="20" />
            </span>
            <div>
              <strong>Not sure where to start?</strong>
              <small>Describe your need and let Yoru narrow it down.</small>
            </div>
            <Icon name="arrow" width="18" />
          </button>
          <div className="hero-trust">
            <span>
              <Icon name="shield" width="18" />
              Verified partners
            </span>
            <span>
              <Icon name="sparkle" width="18" />
              Curated selection
            </span>
            <span>
              <Icon name="pin" width="18" />
              Area-aware service
            </span>
          </div>
        </div>

        <div className="v5-home-hero__visual" aria-label="Yoru featured edit">
          <article className="v5-editorial-card v5-editorial-card--main">
            <Image
              alt={featuredProduct.name}
              fill
              priority
              sizes="(max-width: 800px) 92vw, 38vw"
              src={featuredProduct.image}
            />
            <div className="v5-editorial-card__caption">
              <span>THE EVERYDAY EDIT</span>
              <strong>{featuredProduct.name}</strong>
              <Link href={`/products/${featuredProduct.slug}`}>
                Discover <Icon name="arrow" width="16" />
              </Link>
            </div>
          </article>
          <article className="v5-editorial-card v5-editorial-card--small">
            <Image
              alt={featuredService.name}
              fill
              sizes="(max-width: 800px) 44vw, 18vw"
              src={featuredService.image}
            />
            <div className="v5-editorial-card__caption">
              <span>AT HOME</span>
              <strong>{featuredService.name}</strong>
            </div>
          </article>
          <button
            className="v5-visual-search-card"
            onClick={() => openSearch("image")}
            type="button"
          >
            <Icon name="sparkle" width="22" />
            <span>
              <strong>See it. Find it.</strong>
              <small>Upload a visual reference</small>
            </span>
            <Icon name="arrow" width="18" />
          </button>
        </div>
      </section>

      <section className="v5-category-rail" aria-label="Shop by category">
        {[
          ["Skincare", "Barrier-first essentials", "/search?q=skincare"],
          ["Fashion", "Quiet statement pieces", "/search?q=fashion"],
          ["Home facial", "Reset without leaving home", "/search?q=facial"],
          ["Hair", "Care, styling, and ritual", "/search?q=hair"],
        ].map(([title, detail, href], index) => (
          <Link
            className={`v5-category-tile v5-category-tile--${index + 1}`}
            href={href}
            key={title}
          >
            <span>0{index + 1}</span>
            <div>
              <strong>{title}</strong>
              <small>{detail}</small>
            </div>
            <Icon name="arrow" width="18" />
          </Link>
        ))}
      </section>

      <section className="home-section v5-home-section">
        <div className="section-heading-row">
          <div>
            <p className="section-eyebrow">The Yoru edit</p>
            <h2>Objects worth making room for.</h2>
            <p className="section-support">
              Pilihan dengan kombinasi rating, detail produk, dan stok yang paling relevan.
            </p>
          </div>
          <Link className="text-link" href="/products">
            Shop all <Icon name="arrow" width="18" />
          </Link>
        </div>
        <div className="catalog-grid">
          {products.slice(0, 4).map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>

      <section className="v5-editorial-split">
        <div className="v5-editorial-split__copy">
          <p className="section-eyebrow">At-home, not improvised</p>
          <h2>Professional care with a clear service journey.</h2>
          <p>
            Pilih area dan jadwal, lihat profesional, pahami apa yang termasuk, lalu pantau status
            booking dari akunmu.
          </p>
          <div className="process-list">
            {[
              ["01", "Check your area", "Cakupan layanan divalidasi sebelum slot dikunci."],
              [
                "02",
                "Choose a real slot",
                "Profesional dan jadwal ditampilkan sebagai satu keputusan.",
              ],
              ["03", "Track the journey", "Status, OTP, dan lifecycle booking tetap transparan."],
            ].map(([number, title, detail]) => (
              <div key={number}>
                <span>{number}</span>
                <div>
                  <strong>{title}</strong>
                  <p>{detail}</p>
                </div>
              </div>
            ))}
          </div>
          <Link className="primary-button" href="/services">
            Explore services <Icon name="arrow" width="18" />
          </Link>
        </div>
        <div className="v5-editorial-split__media">
          <Image
            alt={editorialService.name}
            fill
            sizes="(max-width: 800px) 92vw, 45vw"
            src={editorialService.image}
          />
          <div className="service-status-card">
            <span className="status-dot" />
            <div>
              <strong>Professional confirmed</strong>
              <span>Area and slot verified</span>
            </div>
          </div>
        </div>
      </section>

      <section className="home-section v5-home-section">
        <div className="section-heading-row">
          <div>
            <p className="section-eyebrow">Bookable now</p>
            <h2>Care that comes to you.</h2>
          </div>
          <Link className="text-link" href="/services">
            View all services <Icon name="arrow" width="18" />
          </Link>
        </div>
        <div className="catalog-grid">
          {services.slice(0, 4).map((service) => (
            <ServiceCard key={service.id} service={service} />
          ))}
        </div>
      </section>

      <section className="v5-member-banner">
        <div>
          <p className="section-eyebrow">Yoru membership preview</p>
          <h2>Save your edit, track every order, keep every booking in one place.</h2>
        </div>
        <div className="v5-member-banner__actions">
          <Link className="primary-button" href="/register">
            Create account <Icon name="arrow" width="18" />
          </Link>
          <Link className="secondary-button" href="/wishlist">
            View wishlist
          </Link>
        </div>
      </section>

      <section className="trust-grid v5-trust-grid">
        {[
          [
            "shield",
            "Verified ecosystem",
            "Partner dan profesional melewati onboarding dan review.",
          ],
          [
            "truck",
            "Transparent lifecycle",
            "Order, delivery, booking, dan tracking punya status yang jelas.",
          ],
          [
            "check",
            "Server-verified totals",
            "Harga final, payment state, dan inventory tidak dipercaya dari browser.",
          ],
          [
            "sparkle",
            "AI with boundaries",
            "AI membantu discovery, bukan menjadi sumber kebenaran transaksi.",
          ],
        ].map(([icon, title, detail]) => (
          <article key={title}>
            <span className="trust-icon">
              <Icon name={icon as "shield"} width="22" />
            </span>
            <h3>{title}</h3>
            <p>{detail}</p>
          </article>
        ))}
      </section>
    </>
  );
}
