"use client";

import { useState } from "react";

import { Icon } from "@/components/icons";
import { ServiceCard } from "@/components/service-card";
import { serviceCategories, services } from "@/lib/storefront-data";
import {
  filterServices,
  type ServiceFilters,
  type ServiceSort,
} from "@/lib/storefront-filters";

const defaultFilters: ServiceFilters = {
  query: "",
  category: "Semua",
  maxPriceMinor: null,
  maxDurationMin: null,
  minRating: 0,
  sort: "recommended",
};

export function ServiceCatalog() {
  const [filters, setFilters] = useState<ServiceFilters>(defaultFilters);
  const results = filterServices(services, filters);
  const activeCount = [
    filters.query.trim().length > 0,
    filters.category !== "Semua",
    filters.maxPriceMinor !== null,
    filters.maxDurationMin !== null,
    filters.minRating > 0,
  ].filter(Boolean).length;

  function update<Key extends keyof ServiceFilters>(
    key: Key,
    value: ServiceFilters[Key],
  ) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <>
      <section className="catalog-hero catalog-hero--service">
        <p className="section-eyebrow">Trusted home service</p>
        <h1>Layanan profesional, datang sesuai jadwalmu.</h1>
        <p>
          Saring layanan berdasarkan kategori, budget, durasi, rating, dan kata pencarian.
        </p>
      </section>

      <section className="catalog-browser">
        <aside className="filter-panel filter-panel--service" aria-label="Filter home service">
          <div className="filter-panel__heading">
            <div>
              <p className="section-eyebrow">Filter layanan</p>
              <h2>Temukan yang cocok</h2>
            </div>
            {activeCount > 0 ? <span>{activeCount} aktif</span> : null}
          </div>

          <label className="filter-search">
            <span>Cari layanan</span>
            <div>
              <Icon name="search" width="17" />
              <input
                onChange={(event) => update("query", event.target.value)}
                placeholder="Facial, hair spa, area..."
                type="search"
                value={filters.query}
              />
            </div>
          </label>

          <label className="filter-field">
            <span>Kategori</span>
            <select
              onChange={(event) => update("category", event.target.value)}
              value={filters.category}
            >
              {serviceCategories.map((category) => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Budget maksimum</span>
            <select
              onChange={(event) =>
                update(
                  "maxPriceMinor",
                  event.target.value ? Number(event.target.value) : null,
                )
              }
              value={filters.maxPriceMinor ?? ""}
            >
              <option value="">Semua budget</option>
              <option value="20000000">Sampai Rp200 ribu</option>
              <option value="25000000">Sampai Rp250 ribu</option>
              <option value="35000000">Sampai Rp350 ribu</option>
              <option value="50000000">Sampai Rp500 ribu</option>
            </select>
          </label>

          <label className="filter-field">
            <span>Durasi maksimum</span>
            <select
              onChange={(event) =>
                update(
                  "maxDurationMin",
                  event.target.value ? Number(event.target.value) : null,
                )
              }
              value={filters.maxDurationMin ?? ""}
            >
              <option value="">Semua durasi</option>
              <option value="60">Maksimal 60 menit</option>
              <option value="75">Maksimal 75 menit</option>
              <option value="90">Maksimal 90 menit</option>
              <option value="120">Maksimal 120 menit</option>
            </select>
          </label>

          <label className="filter-field">
            <span>Rating minimum</span>
            <select
              onChange={(event) => update("minRating", Number(event.target.value))}
              value={filters.minRating}
            >
              <option value="0">Semua rating</option>
              <option value="4.7">4,7 ke atas</option>
              <option value="4.8">4,8 ke atas</option>
              <option value="4.9">4,9</option>
            </select>
          </label>

          <div className="filter-information">
            <Icon name="pin" width="18" />
            <p>
              Area layanan tetap diverifikasi ulang pada tahap booking sebelum slot dikunci.
            </p>
          </div>

          <button
            className="filter-reset"
            disabled={activeCount === 0}
            onClick={() => setFilters(defaultFilters)}
            type="button"
          >
            Reset semua filter
          </button>
        </aside>

        <div className="catalog-results">
          <div className="catalog-results__toolbar">
            <div>
              <strong>{results.length} layanan</strong>
              <span>dari {services.length} layanan tersedia</span>
            </div>
            <label>
              <span>Urutkan</span>
              <select
                onChange={(event) => update("sort", event.target.value as ServiceSort)}
                value={filters.sort}
              >
                <option value="recommended">Rekomendasi</option>
                <option value="price_asc">Harga terendah</option>
                <option value="price_desc">Harga tertinggi</option>
                <option value="rating_desc">Rating tertinggi</option>
                <option value="duration_asc">Durasi tercepat</option>
              </select>
            </label>
          </div>

          {results.length > 0 ? (
            <div className="catalog-grid catalog-grid--filtered">
              {results.map((service) => (
                <ServiceCard key={service.id} service={service} />
              ))}
            </div>
          ) : (
            <section className="filter-empty-state">
              <span><Icon name="calendar" width="25" /></span>
              <h2>Layanan belum ditemukan.</h2>
              <p>Coba ubah kategori, budget, durasi, rating, atau kata pencarian.</p>
              <button
                className="secondary-button"
                onClick={() => setFilters(defaultFilters)}
                type="button"
              >
                Reset filter
              </button>
            </section>
          )}
        </div>
      </section>
    </>
  );
}
