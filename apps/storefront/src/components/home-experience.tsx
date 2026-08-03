import Image from "next/image";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { ProductCard } from "@/components/product-card";
import { ServiceCard } from "@/components/service-card";
import { products, services } from "@/lib/storefront-data";

export function HomeExperience() {
  return (
    <>
      <section className="home-hero">
        <div className="home-hero__copy">
          <p className="section-eyebrow">Beauty commerce · Trusted home service</p>
          <h1>Belanja yang kamu suka. Panggil ahli saat kamu perlu.</h1>
          <p>
            Yoru menyatukan produk terkurasi dan layanan profesional di rumah, dengan partner
            terverifikasi, harga transparan, serta status transaksi yang mudah dipantau.
          </p>
          <div className="hero-cta-row">
            <Link className="primary-button large-button" href="/products">
              Belanja produk
              <Icon name="arrow" width="19" />
            </Link>
            <Link className="secondary-button large-button" href="/services">
              Pesan home service
            </Link>
          </div>
          <div className="hero-trust">
            <span><Icon name="shield" width="18" />Partner terverifikasi</span>
            <span><Icon name="sparkle" width="18" />Pilihan terkurasi</span>
            <span><Icon name="pin" width="18" />Layanan sesuai area</span>
          </div>
        </div>
        <div className="home-hero__visual" aria-label="Produk dan layanan unggulan Yoru">
          <div className="hero-visual-card hero-product-card">
            <Image alt="Glow Reset Serum" height={720} src="/yoru-media/product-serum.svg" width={720} />
            <div><span>Beauty essential</span><strong>Glow Reset Serum</strong></div>
          </div>
          <div className="hero-visual-card hero-service-card">
            <Image alt="Home Facial Reset" height={720} src="/yoru-media/service-facial.svg" width={720} />
            <div><span>Available today</span><strong>Home Facial Reset</strong></div>
          </div>
          <div className="hero-floating-note">
            <Icon name="wand" width="22" />
            <div><strong>Belum yakin pilih apa?</strong><Link href="/assistant">Tanya Yoru Advisor</Link></div>
          </div>
        </div>
      </section>

      <section className="experience-switch">
        <Link className="experience-card experience-card--commerce" href="/products">
          <span className="experience-number">01</span>
          <div>
            <p>Commerce</p>
            <h2>Produk pilihan untuk rutinitas dan gayamu.</h2>
            <span className="experience-link">Lihat katalog<Icon name="arrow" width="18" /></span>
          </div>
        </Link>
        <Link className="experience-card experience-card--service" href="/services">
          <span className="experience-number">02</span>
          <div>
            <p>Home service</p>
            <h2>Profesional terverifikasi datang sesuai jadwal.</h2>
            <span className="experience-link">Cari layanan<Icon name="arrow" width="18" /></span>
          </div>
        </Link>
      </section>

      <section className="home-section">
        <div className="section-heading-row">
          <div><p className="section-eyebrow">Pilihan minggu ini</p><h2>Produk yang sedang disukai.</h2></div>
          <Link className="text-link" href="/products">Semua produk<Icon name="arrow" width="18" /></Link>
        </div>
        <div className="catalog-grid">
          {products.slice(0, 4).map((product) => <ProductCard key={product.id} product={product} />)}
        </div>
      </section>

      <section className="service-highlight">
        <div className="service-highlight__copy">
          <p className="section-eyebrow">Home service, without the guesswork</p>
          <h2>Pilih layanan, cek slot, dan pantau profesional dari satu tempat.</h2>
          <div className="process-list">
            {[
              ["01", "Pilih layanan dan area", "Yoru memeriksa serviceability sebelum booking."],
              ["02", "Pilih jadwal dan profesional", "Slot aktif dikunci saat konfirmasi."],
              ["03", "Bayar dan pantau", "Status booking, OTP, dan tracking tersedia di akun."],
            ].map(([number, title, detail]) => (
              <div key={number}><span>{number}</span><div><strong>{title}</strong><p>{detail}</p></div></div>
            ))}
          </div>
          <Link className="primary-button" href="/services">Temukan layanan<Icon name="arrow" width="18" /></Link>
        </div>
        <div className="service-highlight__image">
          <Image alt="Profesional home service Yoru" height={900} src="/yoru-media/service-hair.svg" width={900} />
          <div className="service-status-card">
            <span className="status-dot" />
            <div><strong>Profesional dikonfirmasi</strong><span>Estimasi tiba 14.20</span></div>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="section-heading-row">
          <div><p className="section-eyebrow">Layanan populer</p><h2>Perawatan datang ke rumahmu.</h2></div>
          <Link className="text-link" href="/services">Semua layanan<Icon name="arrow" width="18" /></Link>
        </div>
        <div className="catalog-grid">
          {services.slice(0, 4).map((service) => <ServiceCard key={service.id} service={service} />)}
        </div>
      </section>

      <section className="trust-grid">
        {[
          ["shield", "Partner terverifikasi", "Partner dan profesional melewati proses onboarding."],
          ["truck", "Status transparan", "Pantau order, shipment, booking, dan perjalanan profesional."],
          ["check", "Pembayaran terkontrol", "Total final dan state pembayaran diverifikasi server."],
          ["sparkle", "Rekomendasi bertanggung jawab", "AI membantu memilih, bukan menjadi sumber kebenaran."],
        ].map(([icon, title, detail]) => (
          <article key={title}>
            <span className="trust-icon"><Icon name={icon as "shield"} width="22" /></span>
            <h3>{title}</h3><p>{detail}</p>
          </article>
        ))}
      </section>
    </>
  );
}
