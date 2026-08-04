"use client";

import { useMemo, useState } from "react";

import { CatalogGridSkeleton } from "@/components/catalog-skeleton";
import { Icon } from "@/components/icons";
import { ServiceCard } from "@/components/service-card";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
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

const serviceAreas = ["Semua area", ...new Set(services.map((service) => service.serviceArea))];
const PAGE_SIZE = 6;

export function ServiceCatalog() {
  const [filters, setFilters] = useState<ServiceFilters>(defaultFilters);
  const [searchInput, setSearchInput] = useState("");
  const [area, setArea] = useState("Semua area");
  const [filterOpen, setFilterOpen] = useState(false);
  const [view, setView] = useState<"grid" | "list">("grid");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const debouncedQuery = useDebouncedValue(searchInput, 280);
  const effectiveFilters = useMemo<ServiceFilters>(
    () => ({ ...filters, query: debouncedQuery }),
    [debouncedQuery, filters],
  );
  const baseResults = useMemo(
    () => filterServices(services, effectiveFilters),
    [effectiveFilters],
  );
  const results = useMemo(
    () => area === "Semua area" ? baseResults : baseResults.filter((service) => service.serviceArea === area),
    [area, baseResults],
  );
  const visibleResults = useMemo(
    () => results.slice(0, visibleCount),
    [results, visibleCount],
  );
  const isFiltering = searchInput.trim() !== debouncedQuery.trim();
  const activeCount = useMemo(
    () =>
      [
        searchInput.trim().length > 0,
        filters.category !== "Semua",
        filters.maxPriceMinor !== null,
        filters.maxDurationMin !== null,
        filters.minRating > 0,
        area !== "Semua area",
      ].filter(Boolean).length,
    [area, filters, searchInput],
  );

  function update<Key extends keyof ServiceFilters>(key: Key, value: ServiceFilters[Key]) {
    setFilters((current) => ({ ...current, [key]: value }));
    setVisibleCount(PAGE_SIZE);
  }

  function updateArea(value: string) {
    setArea(value);
    setVisibleCount(PAGE_SIZE);
  }

  function reset() {
    setSearchInput("");
    setFilters(defaultFilters);
    setArea("Semua area");
    setVisibleCount(PAGE_SIZE);
  }

  const filterPanel = (
    <aside className="filter-panel filter-panel--clean filter-panel--service" aria-label="Filter home service">
      <div className="filter-panel__heading">
        <div>
          <p className="section-eyebrow">Filter</p>
          <h2>Pilih layananmu</h2>
        </div>
        {activeCount > 0 ? <span>{activeCount}</span> : null}
      </div>

      <label className="filter-search">
        <span className="filter-label">Cari layanan</span>
        <div>
          <Icon name="search" width="17" />
          <input
            onChange={(event) => {
              setSearchInput(event.target.value);
              setVisibleCount(PAGE_SIZE);
            }}
            placeholder="Facial, hair, partner"
            type="search"
            value={searchInput}
          />
          {isFiltering ? <span className="filter-search__loading" aria-label="Menyaring" /> : null}
        </div>
      </label>

      <div className="filter-section">
        <div className="filter-section__heading">
          <span>Kategori</span>
          {filters.category !== "Semua" ? (
            <button onClick={() => update("category", "Semua")} type="button">Reset</button>
          ) : null}
        </div>
        <div className="filter-choice-grid">
          {serviceCategories.map((category) => (
            <button
              aria-pressed={filters.category === category}
              className={filters.category === category ? "is-active" : ""}
              key={category}
              onClick={() => update("category", category)}
              type="button"
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-section filter-section--stacked">
        <label className="filter-field">
          <span className="filter-label">Area layanan</span>
          <select onChange={(event) => updateArea(event.target.value)} value={area}>
            {serviceAreas.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>

        <label className="filter-field">
          <span className="filter-label">Budget maksimum</span>
          <select onChange={(event) => update("maxPriceMinor", event.target.value ? Number(event.target.value) : null)} value={filters.maxPriceMinor ?? ""}>
            <option value="">Semua budget</option>
            <option value="20000000">Sampai Rp200 ribu</option>
            <option value="25000000">Sampai Rp250 ribu</option>
            <option value="35000000">Sampai Rp350 ribu</option>
            <option value="50000000">Sampai Rp500 ribu</option>
          </select>
        </label>

        <label className="filter-field">
          <span className="filter-label">Durasi maksimum</span>
          <select onChange={(event) => update("maxDurationMin", event.target.value ? Number(event.target.value) : null)} value={filters.maxDurationMin ?? ""}>
            <option value="">Semua durasi</option>
            <option value="60">60 menit</option>
            <option value="75">75 menit</option>
            <option value="90">90 menit</option>
            <option value="120">120 menit</option>
          </select>
        </label>
      </div>

      <div className="filter-section">
        <span className="filter-label">Rating minimum</span>
        <div className="filter-segmented">
          {[0, 4.7, 4.8, 4.9].map((rating) => (
            <button
              aria-pressed={filters.minRating === rating}
              className={filters.minRating === rating ? "is-active" : ""}
              key={rating}
              onClick={() => update("minRating", rating)}
              type="button"
            >
              {rating === 0 ? "Semua" : `${rating}+`}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-information">
        <Icon name="pin" width="18" />
        <p>Alamat lengkap dan ketersediaan slot diverifikasi lagi sebelum booking dikunci.</p>
      </div>

      <button className="filter-reset" disabled={activeCount === 0} onClick={reset} type="button">Reset semua filter</button>
    </aside>
  );

  return (
    <>
      <section className="catalog-hero catalog-hero--service v5-catalog-hero">
        <div>
          <p className="section-eyebrow">Trusted home service</p>
          <h1>Perawatan profesional, dijadwalkan sesuai harimu.</h1>
          <p>Saring berdasarkan area, kategori, durasi, budget, dan rating.</p>
        </div>
        <div className="v5-catalog-hero__stat"><strong>{services.length}</strong><span>layanan tersedia</span></div>
      </section>

      <section className="catalog-browser v5-catalog-browser">
        <div className="desktop-filter">{filterPanel}</div>

        <div className="catalog-results">
          <div className="catalog-results__toolbar v5-results-toolbar">
            <div className="catalog-results__summary">
              <strong>{results.length} layanan</strong>
              <span>{activeCount > 0 ? `${activeCount} filter aktif` : "Semua layanan"}</span>
            </div>
            <div className="v5-toolbar-actions">
              <button className="mobile-filter-button" onClick={() => setFilterOpen(true)} type="button">
                <Icon name="menu" width="17" /> Filter
                {activeCount > 0 ? <span>{activeCount}</span> : null}
              </button>
              <label className="catalog-sort">
                <span className="visually-hidden">Urutkan layanan</span>
                <select aria-label="Urutkan layanan" onChange={(event) => update("sort", event.target.value as ServiceSort)} value={filters.sort}>
                  <option value="recommended">Paling relevan</option>
                  <option value="price_asc">Harga terendah</option>
                  <option value="price_desc">Harga tertinggi</option>
                  <option value="rating_desc">Rating tertinggi</option>
                  <option value="duration_asc">Durasi tercepat</option>
                </select>
              </label>
              <div className="view-switcher" aria-label="Tampilan katalog">
                <button aria-label="Tampilan grid" className={view === "grid" ? "is-active" : ""} onClick={() => setView("grid")} type="button">▦</button>
                <button aria-label="Tampilan daftar" className={view === "list" ? "is-active" : ""} onClick={() => setView("list")} type="button">☷</button>
              </div>
            </div>
          </div>

          {activeCount > 0 ? (
            <div className="active-filter-row" aria-label="Filter aktif">
              {searchInput.trim() ? <button onClick={() => setSearchInput("")} type="button">“{searchInput.trim()}” <span>×</span></button> : null}
              {filters.category !== "Semua" ? <button onClick={() => update("category", "Semua")} type="button">{filters.category} <span>×</span></button> : null}
              {area !== "Semua area" ? <button onClick={() => updateArea("Semua area")} type="button">{area} <span>×</span></button> : null}
              {filters.maxPriceMinor !== null ? <button onClick={() => update("maxPriceMinor", null)} type="button">Batas budget <span>×</span></button> : null}
              {filters.maxDurationMin !== null ? <button onClick={() => update("maxDurationMin", null)} type="button">≤ {filters.maxDurationMin} menit <span>×</span></button> : null}
              {filters.minRating > 0 ? <button onClick={() => update("minRating", 0)} type="button">Rating {filters.minRating}+ <span>×</span></button> : null}
              <button className="active-filter-reset" onClick={reset} type="button">Hapus semua</button>
            </div>
          ) : null}

          {isFiltering ? (
            <CatalogGridSkeleton label="Menyaring layanan" view={view} />
          ) : results.length > 0 ? (
            <>
              <div className={`catalog-grid catalog-grid--filtered ${view === "list" ? "is-list" : ""}`}>
                {visibleResults.map((service) => <ServiceCard key={service.id} service={service} />)}
              </div>
              {visibleCount < results.length ? (
                <button className="secondary-button load-more-button" onClick={() => setVisibleCount((value) => value + PAGE_SIZE)} type="button">
                  Tampilkan lebih banyak
                  <Icon name="plus" width="17" />
                </button>
              ) : null}
            </>
          ) : (
            <section className="filter-empty-state">
              <span><Icon name="search" width="24" /></span>
              <h2>Belum ada layanan yang cocok</h2>
              <p>Coba ubah area, kategori, durasi, budget, rating, atau kata pencarian.</p>
              <button className="secondary-button" onClick={reset} type="button">Reset filter</button>
            </section>
          )}
        </div>
      </section>

      {filterOpen ? (
        <div className="filter-drawer-backdrop" onMouseDown={() => setFilterOpen(false)}>
          <div className="filter-drawer" onMouseDown={(event) => event.stopPropagation()}>
            <div className="filter-drawer__heading">
              <div><span>Filter layanan</span><small>{results.length} hasil</small></div>
              <button aria-label="Tutup filter" className="icon-button" onClick={() => setFilterOpen(false)} type="button"><Icon name="close" width="19" /></button>
            </div>
            <div className="filter-drawer__body">{filterPanel}</div>
            <div className="filter-drawer__footer">
              <button className="secondary-button" disabled={activeCount === 0} onClick={reset} type="button">Reset</button>
              <button className="primary-button filter-apply-button" onClick={() => setFilterOpen(false)} type="button">Lihat {results.length} layanan</button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
