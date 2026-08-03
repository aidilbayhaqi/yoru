"use client";

import Image from "next/image";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { formatMoney } from "@/lib/storefront-domain";
import { useStorefront } from "@/lib/storefront-store";
import type { Service } from "@/lib/storefront-types";

export function ServiceCard({ service }: { service: Service }) {
  const { state, toggleFavorite } = useStorefront();
  const favorite = state.favorites.includes(service.id);

  return (
    <article className="catalog-card service-card">
      <div className="catalog-card__media">
        <Link href={`/services/${service.slug}`}>
          <Image alt={service.name} height={640} src={service.image} width={640} />
        </Link>
        {service.badge ? <span className="catalog-badge service-badge">{service.badge}</span> : null}
        <button
          aria-label={favorite ? "Hapus dari favorit" : "Tambah ke favorit"}
          className={`favorite-button ${favorite ? "is-active" : ""}`}
          onClick={() => toggleFavorite(service.id)}
          type="button"
        >
          <Icon name="heart" width="18" />
        </button>
      </div>
      <div className="catalog-card__body">
        <p className="catalog-card__partner">{service.partner}</p>
        <Link href={`/services/${service.slug}`}>
          <h3>{service.name}</h3>
        </Link>
        <div className="service-meta">
          <span>
            <Icon name="clock" width="15" />
            {service.durationMin} menit
          </span>
          <span>
            <Icon name="star" width="15" />
            {service.rating}
          </span>
        </div>
        <div className="service-price-row">
          <span>Mulai</span>
          <strong>{formatMoney(service.priceMinor)}</strong>
        </div>
        <Link className="primary-button card-book-button" href={`/services/${service.slug}/book`}>
          Pilih jadwal
          <Icon name="calendar" width="17" />
        </Link>
      </div>
    </article>
  );
}
