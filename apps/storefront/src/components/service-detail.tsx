import Image from "next/image";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { formatMoney } from "@/lib/storefront-domain";
import type { Service } from "@/lib/storefront-types";

export function ServiceDetail({ service }: { service: Service }) {
  return (
    <main>
      <div className="breadcrumb">
        <Link href="/">Beranda</Link><span>/</span><Link href="/services">Home service</Link><span>/</span><span>{service.name}</span>
      </div>
      <section className="detail-layout service-detail-layout">
        <div className="detail-media service-detail-media">
          <Image alt={service.name} height={960} priority src={service.image} width={960} />
          {service.badge ? <span className="detail-badge service-detail-badge">{service.badge}</span> : null}
        </div>
        <div className="detail-panel">
          <p className="detail-partner">{service.partner}</p>
          <h1>{service.name}</h1>
          <div className="service-detail-meta">
            <span><Icon name="star" width="16" />{service.rating} ({service.reviewCount} ulasan)</span>
            <span><Icon name="clock" width="16" />{service.durationMin} menit</span>
          </div>
          <div className="detail-price service-detail-price"><span>Mulai</span><strong>{formatMoney(service.priceMinor)}</strong></div>
          <p className="detail-description">{service.description}</p>
          <div className="service-area-card"><Icon name="pin" width="22" /><div><strong>Area layanan</strong><span>{service.serviceArea}</span></div></div>
          <Link className="primary-button service-book-cta" href={`/services/${service.slug}/book`}>
            Pilih jadwal dan booking<Icon name="calendar" width="19" />
          </Link>
          <div className="detail-highlights">
            <h2>Yang termasuk dalam layanan</h2>
            <ul>{service.includes.map((item) => <li key={item}><Icon name="check" width="16" />{item}</li>)}</ul>
          </div>
        </div>
      </section>
      <section className="professional-section">
        <div className="section-heading-row"><div><p className="section-eyebrow">Profesional tersedia</p><h2>Dipilih berdasarkan skill dan area.</h2></div></div>
        <div className="professional-grid">
          {service.professionals.map((professional) => (
            <article key={professional.id}>
              <span className="professional-avatar">{professional.avatar}</span>
              <div><h3>{professional.name}</h3><p>{professional.title}</p><span><Icon name="star" width="15" />{professional.rating} · {professional.completedJobs} pekerjaan</span></div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
