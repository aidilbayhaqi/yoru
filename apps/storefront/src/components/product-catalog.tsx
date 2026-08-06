"use client";

import { useMemo, useState } from "react";

import { CatalogGridSkeleton } from "@/components/catalog-skeleton";
import { Icon } from "@/components/icons";
import { ProductCard } from "@/components/product-card";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { Product } from "@/lib/storefront-types";
import { filterProducts, type ProductFilters, type ProductSort } from "@/lib/storefront-filters";

const defaultFilters: ProductFilters = {
  query: "",
  category: "Semua",
  partner: "Semua",
  maxPriceMinor: null,
  minRating: 0,
  onlyInStock: false,
  sort: "recommended",
};

const PAGE_SIZE = 6;

export function ProductCatalog({ items }: { items: Product[] }) {
  const [filters, setFilters] = useState<ProductFilters>(defaultFilters);
  const productCategories = useMemo(
    () => ["Semua", ...new Set(items.map((product) => product.category))],
    [items],
  );
  const partners = useMemo(
    () => ["Semua", ...new Set(items.map((product) => product.partner))],
    [items],
  );
  const [searchInput, setSearchInput] = useState("");
  const [filterOpen, setFilterOpen] = useState(false);
  const [view, setView] = useState<"grid" | "list">("grid");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const debouncedQuery = useDebouncedValue(searchInput, 280);
  const effectiveFilters = useMemo<ProductFilters>(
    () => ({ ...filters, query: debouncedQuery }),
    [debouncedQuery, filters],
  );
  const results = useMemo(() => filterProducts(items, effectiveFilters), [effectiveFilters, items]);
  const visibleResults = useMemo(() => results.slice(0, visibleCount), [results, visibleCount]);
  const isFiltering = searchInput.trim() !== debouncedQuery.trim();
  const activeCount = useMemo(
    () =>
      [
        searchInput.trim().length > 0,
        filters.category !== "Semua",
        filters.partner !== "Semua",
        filters.maxPriceMinor !== null,
        filters.minRating > 0,
        filters.onlyInStock,
      ].filter(Boolean).length,
    [filters, searchInput],
  );

  function update<Key extends keyof ProductFilters>(key: Key, value: ProductFilters[Key]) {
    setFilters((current) => ({ ...current, [key]: value }));
    setVisibleCount(PAGE_SIZE);
  }

  function reset() {
    setSearchInput("");
    setFilters(defaultFilters);
    setVisibleCount(PAGE_SIZE);
  }

  const filterPanel = (
    <aside className="filter-panel filter-panel--clean" aria-label="Filter produk">
      <div className="filter-panel__heading">
        <div>
          <p className="section-eyebrow">Filter</p>
          <h2>Temukan yang cocok</h2>
        </div>
        {activeCount > 0 ? <span>{activeCount}</span> : null}
      </div>

      <label className="filter-search">
        <span className="filter-label">Cari katalog</span>
        <div>
          <Icon name="search" width="17" />
          <input
            onChange={(event) => {
              setSearchInput(event.target.value);
              setVisibleCount(PAGE_SIZE);
            }}
            placeholder="Nama produk atau partner"
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
            <button onClick={() => update("category", "Semua")} type="button">
              Reset
            </button>
          ) : null}
        </div>
        <div className="filter-choice-grid">
          {productCategories.map((category) => (
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
          <span className="filter-label">Partner</span>
          <select
            onChange={(event) => update("partner", event.target.value)}
            value={filters.partner}
          >
            {partners.map((partner) => (
              <option key={partner} value={partner}>
                {partner}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span className="filter-label">Harga maksimum</span>
          <select
            onChange={(event) =>
              update("maxPriceMinor", event.target.value ? Number(event.target.value) : null)
            }
            value={filters.maxPriceMinor ?? ""}
          >
            <option value="">Semua harga</option>
            <option value="10000000">Sampai Rp100 ribu</option>
            <option value="15000000">Sampai Rp150 ribu</option>
            <option value="20000000">Sampai Rp200 ribu</option>
            <option value="30000000">Sampai Rp300 ribu</option>
          </select>
        </label>
      </div>

      <div className="filter-section">
        <span className="filter-label">Rating minimum</span>
        <div className="filter-segmented">
          {[0, 4.5, 4.8, 4.9].map((rating) => (
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

      <label className="filter-toggle-row">
        <span>
          <strong>Hanya ready stock</strong>
          <small>Sembunyikan item yang belum tersedia.</small>
        </span>
        <input
          checked={filters.onlyInStock}
          onChange={(event) => update("onlyInStock", event.target.checked)}
          type="checkbox"
        />
        <span className="filter-toggle" aria-hidden="true" />
      </label>

      <button className="filter-reset" disabled={activeCount === 0} onClick={reset} type="button">
        Reset semua filter
      </button>
    </aside>
  );

  return (
    <>
      <section className="catalog-hero catalog-hero--product v5-catalog-hero">
        <div>
          <p className="section-eyebrow">Curated commerce</p>
          <h1>Produk terpilih, tanpa katalog yang terasa penuh.</h1>
          <p>Gunakan pencarian dan filter untuk mempersempit pilihan berdasarkan kebutuhanmu.</p>
        </div>
        <div className="v5-catalog-hero__stat">
          <strong>{items.length}</strong>
          <span>produk terkurasi</span>
        </div>
      </section>

      <section className="catalog-browser v5-catalog-browser">
        <div className="desktop-filter">{filterPanel}</div>

        <div className="catalog-results">
          <div className="catalog-results__toolbar v5-results-toolbar">
            <div className="catalog-results__summary">
              <strong>{results.length} produk</strong>
              <span>{activeCount > 0 ? `${activeCount} filter aktif` : "Semua koleksi"}</span>
            </div>
            <div className="v5-toolbar-actions">
              <button
                className="mobile-filter-button"
                onClick={() => setFilterOpen(true)}
                type="button"
              >
                <Icon name="menu" width="17" /> Filter
                {activeCount > 0 ? <span>{activeCount}</span> : null}
              </button>
              <label className="catalog-sort">
                <span className="visually-hidden">Urutkan produk</span>
                <select
                  aria-label="Urutkan produk"
                  onChange={(event) => update("sort", event.target.value as ProductSort)}
                  value={filters.sort}
                >
                  <option value="recommended">Paling relevan</option>
                  <option value="price_asc">Harga terendah</option>
                  <option value="price_desc">Harga tertinggi</option>
                  <option value="rating_desc">Rating tertinggi</option>
                </select>
              </label>
              <div className="view-switcher" aria-label="Tampilan katalog">
                <button
                  aria-label="Tampilan grid"
                  className={view === "grid" ? "is-active" : ""}
                  onClick={() => setView("grid")}
                  type="button"
                >
                  ▦
                </button>
                <button
                  aria-label="Tampilan daftar"
                  className={view === "list" ? "is-active" : ""}
                  onClick={() => setView("list")}
                  type="button"
                >
                  ☷
                </button>
              </div>
            </div>
          </div>

          {activeCount > 0 ? (
            <div className="active-filter-row" aria-label="Filter aktif">
              {searchInput.trim() ? (
                <button onClick={() => setSearchInput("")} type="button">
                  “{searchInput.trim()}” <span>×</span>
                </button>
              ) : null}
              {filters.category !== "Semua" ? (
                <button onClick={() => update("category", "Semua")} type="button">
                  {filters.category} <span>×</span>
                </button>
              ) : null}
              {filters.partner !== "Semua" ? (
                <button onClick={() => update("partner", "Semua")} type="button">
                  {filters.partner} <span>×</span>
                </button>
              ) : null}
              {filters.maxPriceMinor !== null ? (
                <button onClick={() => update("maxPriceMinor", null)} type="button">
                  Batas harga <span>×</span>
                </button>
              ) : null}
              {filters.minRating > 0 ? (
                <button onClick={() => update("minRating", 0)} type="button">
                  Rating {filters.minRating}+ <span>×</span>
                </button>
              ) : null}
              {filters.onlyInStock ? (
                <button onClick={() => update("onlyInStock", false)} type="button">
                  Ready stock <span>×</span>
                </button>
              ) : null}
              <button className="active-filter-reset" onClick={reset} type="button">
                Hapus semua
              </button>
            </div>
          ) : null}

          {isFiltering ? (
            <CatalogGridSkeleton label="Menyaring produk" view={view} />
          ) : results.length > 0 ? (
            <>
              <div
                className={`catalog-grid catalog-grid--filtered ${view === "list" ? "is-list" : ""}`}
              >
                {visibleResults.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
              {visibleCount < results.length ? (
                <button
                  className="secondary-button load-more-button"
                  onClick={() => setVisibleCount((value) => value + PAGE_SIZE)}
                  type="button"
                >
                  Tampilkan lebih banyak
                  <Icon name="plus" width="17" />
                </button>
              ) : null}
            </>
          ) : (
            <section className="filter-empty-state">
              <span>
                <Icon name="search" width="24" />
              </span>
              <h2>Belum ada hasil yang cocok</h2>
              <p>Coba longgarkan kategori, harga, rating, partner, atau kata pencarian.</p>
              <button className="secondary-button" onClick={reset} type="button">
                Reset filter
              </button>
            </section>
          )}
        </div>
      </section>

      {filterOpen ? (
        <div className="filter-drawer-backdrop" onMouseDown={() => setFilterOpen(false)}>
          <div className="filter-drawer" onMouseDown={(event) => event.stopPropagation()}>
            <div className="filter-drawer__heading">
              <div>
                <span>Filter produk</span>
                <small>{results.length} hasil</small>
              </div>
              <button
                aria-label="Tutup filter"
                className="icon-button"
                onClick={() => setFilterOpen(false)}
                type="button"
              >
                <Icon name="close" width="19" />
              </button>
            </div>
            <div className="filter-drawer__body">{filterPanel}</div>
            <div className="filter-drawer__footer">
              <button
                className="secondary-button"
                disabled={activeCount === 0}
                onClick={reset}
                type="button"
              >
                Reset
              </button>
              <button
                className="primary-button filter-apply-button"
                onClick={() => setFilterOpen(false)}
                type="button"
              >
                Lihat {results.length} produk
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
