"use client";

import { useMemo, useState } from "react";

import { Icon } from "@/components/icons";
import { CatalogGridSkeleton } from "@/components/catalog-skeleton";
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
    () => area === "Semua area"
      ? baseResults
      : baseResults.filter((service) => service.serviceArea === area),
    [area, baseResults],
  );
  const visibleResults = useMemo(
    () => results.slice(0, visibleCount),
    [results, visibleCount],
  );
  const isFiltering = searchInput.trim() !== debouncedQuery.trim();
  const activeCount = useMemo(() => [
    searchInput.trim().length > 0,
    filters.category !== "Semua",
    filters.maxPriceMinor !== null,
    filters.maxDurationMin !== null,
    filters.minRating > 0,
    area !== "Semua area",
  ].filter(Boolean).length, [area, filters, searchInput]);

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
    <aside className="filter-panel filter-panel--service v5-filter-panel" aria-label="Filter home service">
      <div className="filter-panel__heading">
        <div><p className="section-eyebrow">Refine</p><h2>Filter layanan</h2></div>
        {activeCount > 0 ? <span>{activeCount} aktif</span> : null}
      </div>

      <label className="filter-search">
        <span>Cari layanan</span>
        <div>
          <Icon name="search" width="17" />
          <input
            onChange={(event) => {
              setSearchInput(event.target.value);
              setVisibleCount(PAGE_SIZE);
            }}
            placeholder="Facial, hair, partner..."
            type="search"
            value={searchInput}
          />
        </div>
      </label>

      <label className="filter-field">
        <span>Kategori</span>
        <select onChange={(event) => update("category", event.target.value)} value={filters.category}>
          {serviceCategories.map((category) => <option key={category} value={category}>{category}</option>)}
        </select>
      </label>

      <label className="filter-field">
        <span>Service area</span>
        <select onChange={(event) => updateArea(event.target.value)} value={area}>
          {serviceAreas.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </label>

      <label className="filter-field">
        <span>Budget maksimum</span>
        <select onChange={(event) => update("maxPriceMinor", event.target.value ? Number(event.target.value) : null)} value={filters.maxPriceMinor ?? ""}>
          <option value="">Semua budget</option>
          <option value="20000000">Sampai Rp200 ribu</option>
          <option value="25000000">Sampai Rp250 ribu</option>
          <option value="35000000">Sampai Rp350 ribu</option>
          <option value="50000000">Sampai Rp500 ribu</option>
        </select>
      </label>

      <label className="filter-field">
        <span>Durasi maksimum</span>
        <select onChange={(event) => update("maxDurationMin", event.target.value ? Number(event.target.value) : null)} value={filters.maxDurationMin ?? ""}>
          <option value="">Semua durasi</option>
          <option value="60">Up to 60 minutes</option>
          <option value="75">Up to 75 minutes</option>
          <option value="90">Up to 90 minutes</option>
          <option value="120">Up to 120 minutes</option>
        </select>
      </label>

      <label className="filter-field">
        <span>Rating minimum</span>
        <select onChange={(event) => update("minRating", Number(event.target.value))} value={filters.minRating}>
          <option value="0">Semua rating</option>
          <option value="4.7">4,7 ke atas</option>
          <option value="4.8">4,8 ke atas</option>
          <option value="4.9">4,9</option>
        </select>
      </label>

      <div className="filter-information">
        <Icon name="pin" width="18" />
        <p>Alamat lengkap dan serviceability tetap diverifikasi ulang sebelum slot booking dikunci.</p>
      </div>
      <button className="filter-reset" disabled={activeCount === 0} onClick={reset} type="button">Reset all filters</button>
    </aside>
  );

  return (
    <>
      <section className="catalog-hero catalog-hero--service v5-catalog-hero">
        <div>
          <p className="section-eyebrow">Trusted home service</p>
          <h1>Professional care, scheduled around your life.</h1>
          <p>Filter berdasarkan area, kategori, durasi, budget, rating, dan preferensi layanan.</p>
        </div>
        <div className="v5-catalog-hero__stat"><strong>{services.length}</strong><span>bookable services</span></div>
      </section>

      <div className="quick-filter-rail">
        {serviceCategories.map((category) => (
          <button className={filters.category === category ? "is-active" : ""} key={category} onClick={() => update("category", category)} type="button">{category}</button>
        ))}
        <button className={filters.maxDurationMin === 60 ? "is-active" : ""} onClick={() => update("maxDurationMin", filters.maxDurationMin === 60 ? null : 60)} type="button">60 min or less</button>
        <button className={filters.minRating === 4.8 ? "is-active" : ""} onClick={() => update("minRating", filters.minRating === 4.8 ? 0 : 4.8)} type="button">Rated 4.8+</button>
      </div>

      <section className="catalog-browser v5-catalog-browser">
        <div className="desktop-filter">{filterPanel}</div>
        <div className="catalog-results">
          <div className="catalog-results__toolbar v5-results-toolbar">
            <div><strong>{results.length} services</strong><span>from {services.length} available treatments</span></div>
            <div className="v5-toolbar-actions">
              <button className="mobile-filter-button" onClick={() => setFilterOpen(true)} type="button"><Icon name="menu" width="17" /> Filters {activeCount > 0 ? `(${activeCount})` : ""}</button>
              <label>
                <span>Sort</span>
                <select onChange={(event) => update("sort", event.target.value as ServiceSort)} value={filters.sort}>
                  <option value="recommended">Recommended</option>
                  <option value="price_asc">Price: low to high</option>
                  <option value="price_desc">Price: high to low</option>
                  <option value="rating_desc">Top rated</option>
                  <option value="duration_asc">Shortest duration</option>
                </select>
              </label>
              <div className="view-switcher" aria-label="Tampilan katalog">
                <button className={view === "grid" ? "is-active" : ""} onClick={() => setView("grid")} type="button">▦</button>
                <button className={view === "list" ? "is-active" : ""} onClick={() => setView("list")} type="button">☷</button>
              </div>
            </div>
          </div>

          {activeCount > 0 ? (
            <div className="active-filter-row">
              {searchInput.trim() ? <button onClick={() => setSearchInput("")} type="button">“{searchInput.trim()}” ×</button> : null}
              {filters.category !== "Semua" ? <button onClick={() => update("category", "Semua")} type="button">{filters.category} ×</button> : null}
              {area !== "Semua area" ? <button onClick={() => updateArea("Semua area")} type="button">{area} ×</button> : null}
              {filters.maxDurationMin ? <button onClick={() => update("maxDurationMin", null)} type="button">≤ {filters.maxDurationMin} min ×</button> : null}
              {filters.minRating > 0 ? <button onClick={() => update("minRating", 0)} type="button">Rating {filters.minRating}+ ×</button> : null}
              <button className="active-filter-reset" onClick={reset} type="button">Clear all</button>
            </div>
          ) : null}

          {isFiltering ? (
            <CatalogGridSkeleton label="Menyaring home service" view={view} />
          ) : results.length > 0 ? (
            <>
              <div className={`catalog-grid catalog-grid--filtered ${view === "list" ? "is-list" : ""}`}>
                {visibleResults.map((service) => <ServiceCard key={service.id} service={service} />)}
              </div>
              {visibleCount < results.length ? (
                <button className="secondary-button load-more-button" onClick={() => setVisibleCount((value) => value + PAGE_SIZE)} type="button">
                  Load more services
                  <Icon name="plus" width="17" />
                </button>
              ) : null}
            </>
          ) : (
            <section className="filter-empty-state">
              <span><Icon name="calendar" width="25" /></span>
              <h2>No services found.</h2>
              <p>Try changing area, category, budget, duration, rating, or keywords.</p>
              <button className="secondary-button" onClick={reset} type="button">Reset filters</button>
            </section>
          )}
        </div>
      </section>

      {filterOpen ? (
        <div className="filter-drawer-backdrop" onMouseDown={() => setFilterOpen(false)}>
          <div className="filter-drawer" onMouseDown={(event) => event.stopPropagation()}>
            <div className="filter-drawer__heading">
              <strong>Service filters</strong>
              <button aria-label="Tutup filter" className="icon-button" onClick={() => setFilterOpen(false)} type="button"><Icon name="close" width="19" /></button>
            </div>
            {filterPanel}
            <button className="primary-button filter-apply-button" onClick={() => setFilterOpen(false)} type="button">Show {results.length} services</button>
          </div>
        </div>
      ) : null}
    </>
  );
}
