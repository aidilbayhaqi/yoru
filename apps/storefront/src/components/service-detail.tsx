import Image from "next/image";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { ServiceCard } from "@/components/service-card";
import { services } from "@/lib/storefront-data";
import { formatMoney } from "@/lib/storefront-domain";
import type { Service } from "@/lib/storefront-types";

export function ServiceDetail({ service }: { service: Service }) {
  const related = services
    .filter(
      (item) =>
        item.id !== service.id &&
        (item.category === service.category || item.partner === service.partner),
    )
    .slice(0, 3);

  return (
    <main className="v5-service-page">
      <div className="breadcrumb">
        <Link href="/">Home</Link>
        <span>/</span>
        <Link href="/services">Home service</Link>
        <span>/</span>
        <span>{service.name}</span>
      </div>

      <section className="detail-layout service-detail-layout v5-service-detail-layout">
        <div className="detail-media service-detail-media v5-service-detail-media">
          <Image
            alt={service.name}
            fill
            priority
            sizes="(max-width: 900px) 92vw, 54vw"
            src={service.image}
          />
          {service.badge ? (
            <span className="detail-badge service-detail-badge">{service.badge}</span>
          ) : null}
          <div className="v5-service-media-note">
            <span className="status-dot" />
            <div>
              <strong>Serviceability checked before booking</strong>
              <small>{service.serviceArea}</small>
            </div>
          </div>
        </div>

        <div className="detail-panel v5-service-detail-panel">
          <div className="product-kicker-row">
            <p className="detail-partner">{service.partner}</p>
            <span className="verified-label">
              <Icon name="shield" width="15" /> Verified provider
            </span>
          </div>
          <h1>{service.name}</h1>
          <div className="service-detail-meta">
            <span>
              <Icon name="star" width="16" />
              {service.rating} ({service.reviewCount} reviews)
            </span>
            <span>
              <Icon name="clock" width="16" />
              {service.durationMin} minutes
            </span>
          </div>
          <div className="detail-price service-detail-price">
            <span>Starting from</span>
            <strong>{formatMoney(service.priceMinor)}</strong>
          </div>
          <p className="detail-description">{service.description}</p>

          <div className="service-area-card">
            <Icon name="pin" width="22" />
            <div>
              <strong>Advertised service area</strong>
              <span>{service.serviceArea}</span>
              <small>Exact address is revalidated before slot confirmation.</small>
            </div>
          </div>

          <Link className="primary-button service-book-cta" href={`/services/${service.slug}/book`}>
            Check schedule & book
            <Icon name="calendar" width="19" />
          </Link>

          <div className="v5-service-assurance">
            <div>
              <Icon name="shield" width="19" />
              <span>
                <strong>Verified professional</strong>
                <small>Assignment follows skill, availability, and area.</small>
              </span>
            </div>
            <div>
              <Icon name="check" width="19" />
              <span>
                <strong>Clear service scope</strong>
                <small>Review inclusions before confirming a slot.</small>
              </span>
            </div>
          </div>

          <div className="detail-accordions">
            <details open>
              <summary>
                What is included <span>+</span>
              </summary>
              <ul>
                {service.includes.map((item) => (
                  <li key={item}>
                    <Icon name="check" width="16" />
                    {item}
                  </li>
                ))}
              </ul>
            </details>
            <details>
              <summary>
                Before your appointment <span>+</span>
              </summary>
              <p>
                Prepare access to the service location, review notes, and keep your phone reachable.
                Specific preparation should be confirmed by the partner.
              </p>
            </details>
            <details>
              <summary>
                Reschedule & cancellation <span>+</span>
              </summary>
              <p>
                Eligibility depends on booking state, timing, payment state, and the active
                cancellation policy. The server remains the source of truth.
              </p>
            </details>
          </div>
        </div>
      </section>

      <section className="v5-service-journey">
        <div>
          <p className="section-eyebrow">The booking journey</p>
          <h2>Clear from selection to completion.</h2>
        </div>
        <div className="v5-service-journey__steps">
          {[
            ["01", "Confirm area", "Enter the actual address so coverage can be verified."],
            ["02", "Choose slot", "Select a real schedule and preferred professional."],
            ["03", "Review total", "Price and payment state are verified before confirmation."],
            ["04", "Track service", "Follow assignment, arrival, OTP, and completion status."],
          ].map(([number, title, detail]) => (
            <article key={number}>
              <span>{number}</span>
              <h3>{title}</h3>
              <p>{detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="professional-section v5-professional-section">
        <div className="section-heading-row">
          <div>
            <p className="section-eyebrow">Available professionals</p>
            <h2>Experience you can inspect before booking.</h2>
          </div>
        </div>
        <div className="professional-grid">
          {service.professionals.map((professional) => (
            <article key={professional.id}>
              <span className="professional-avatar">{professional.avatar}</span>
              <div>
                <h3>{professional.name}</h3>
                <p>{professional.title}</p>
                <span>
                  <Icon name="star" width="15" />
                  {professional.rating} · {professional.completedJobs} completed jobs
                </span>
              </div>
              <span className="verified-label">
                <Icon name="shield" width="14" /> Verified
              </span>
            </article>
          ))}
        </div>
      </section>

      <section className="v5-service-faq">
        <div>
          <p className="section-eyebrow">Before you book</p>
          <h2>Useful questions.</h2>
        </div>
        <div>
          <details>
            <summary>
              Is the displayed price final?<span>+</span>
            </summary>
            <p>
              It is the starting catalog price. Transport, selected options, discounts, and the
              final total must be calculated by the booking API.
            </p>
          </details>
          <details>
            <summary>
              Can I choose the professional?<span>+</span>
            </summary>
            <p>
              You can submit a preference when the booking flow supports it. Final assignment
              depends on availability, area, and operational rules.
            </p>
          </details>
          <details>
            <summary>
              How does arrival verification work?<span>+</span>
            </summary>
            <p>
              The booking lifecycle can use OTP and status transitions. Never share an OTP before
              the professional is physically present.
            </p>
          </details>
        </div>
      </section>

      {related.length > 0 ? (
        <section className="home-section v5-related-section">
          <div className="section-heading-row">
            <div>
              <p className="section-eyebrow">Continue exploring</p>
              <h2>Related home services.</h2>
            </div>
            <Link className="text-link" href="/services">
              All services <Icon name="arrow" width="18" />
            </Link>
          </div>
          <div className="catalog-grid">
            {related.map((item) => (
              <ServiceCard key={item.id} service={item} />
            ))}
          </div>
        </section>
      ) : null}

      <div className="mobile-buy-bar mobile-service-book-bar">
        <div>
          <small>{service.durationMin} minutes</small>
          <strong>{formatMoney(service.priceMinor)}</strong>
        </div>
        <Link className="primary-button" href={`/services/${service.slug}/book`}>
          Check slots
        </Link>
      </div>
    </main>
  );
}
