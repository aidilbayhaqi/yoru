import type { Metadata } from "next";
import { ServiceCard } from "@/components/service-card";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { serviceCategories, services } from "@/lib/storefront-data";

export const metadata: Metadata = { title: "Home Service" };

export default function ServicesPage() {
  return (
    <><SiteHeader /><main className="catalog-page">
      <section className="catalog-hero catalog-hero--service"><p className="section-eyebrow">Trusted home service</p><h1>Layanan profesional, datang sesuai jadwalmu.</h1><p>Pilih layanan, area, slot, dan profesional. Booking memiliki lifecycle sendiri agar jadwal, OTP, dan tracking tetap aman.</p></section>
      <div className="category-chips service-category-chips" aria-label="Kategori layanan">{serviceCategories.map((category, index) => <span className={index === 0 ? "is-active" : ""} key={category}>{category}</span>)}</div>
      <div className="catalog-toolbar"><span>{services.length} layanan</span><span>Area: Semua lokasi</span></div>
      <div className="catalog-grid catalog-grid--page">{services.map((service) => <ServiceCard key={service.id} service={service} />)}</div>
    </main><SiteFooter /></>
  );
}
