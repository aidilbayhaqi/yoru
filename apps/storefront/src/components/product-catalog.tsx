"use client";

import { useMemo, useState } from "react";

import { Icon } from "@/components/icons";
import { CatalogGridSkeleton } from "@/components/catalog-skeleton";
import { ProductCard } from "@/components/product-card";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { productCategories, products } from "@/lib/storefront-data";
import {
  filterProducts,
  type ProductFilters,
  type ProductSort,
} from "@/lib/storefront-filters";

const defaultFilters: ProductFilters = {
  query: "",
  category: "Semua",
  partner: "Semua",
  maxPriceMinor: null,
  minRating: 0,
  onlyInStock: false,
  sort: "recommended",
};

const partners = ["Semua", ...new Set(products.map((product) => product.partner))];
const PAGE_SIZE = 6;

export function ProductCatalog() {
  const [filters, setFilters] = useState<ProductFilters>(defaultFilters);
  const [searchInput, setSearchInput] = useState("");
  const [filterOpen, setFilterOpen] = useState(false);
  const [view, setView] = useState<"grid" | "list">("grid");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const debouncedQuery = useDebouncedValue(searchInput, 280);
  const effectiveFilters = useMemo<ProductFilters>(
    () => ({ ...filters, query: debouncedQuery }),
    [debouncedQuery, filters],
  );
  const results = useMemo(
    () => filterProducts(products, effectiveFilters),
    [effectiveFilters],
  );
  const visibleResults = useMemo(
    () => results.slice(0, visibleCount),
    [results, visibleCount],
  );
  const isFiltering = searchInput.trim() !== debouncedQuery.trim();
  const activeCount = useMemo(() => [
    searchInput.trim().length > 0,
    filters.category !== "Semua",
    filters.partner !== "Semua",
    filters.maxPriceMinor !== null,
    filters.minRating > 0,
    filters.onlyInStock,
  ].filter(Boolean).length, [filters, searchInput]);

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
    <aside className="filter-panel v5-filter-panel" aria-label="Filter produk">
      <div className="filter-panel__heading">
        <div><p className="section-eyebrow">Refine</p><h2>Filter produk</h2></div>
        {activeCount > 0 ? <span>{activeCount} aktif</span> : null}
      </div>

      <label className="filter-search">
        <span>Cari katalog</span>
        <div>
          <Icon name="search" width="17" />
          <input
            onChange={(event) => {
              setSearchInput(event.target.value);
              setVisibleCount(PAGE_SIZE);
            }}
            placeholder="Nama, kategori, partner..."
            type="search"
            value={searchInput}
          />
        </div>
      </label>

      <label className="filter-field">
        <span>Kategori</span>
        <select onChange={(event) => update("category", event.target.value)} value={filters.category}>
          {productCategories.map((category) => <option key={category} value={category}>{category}</option>)}
        </select>
      </label>

      <label className="filter-field">
        <span>Partner</span>
        <select onChange={(event) => update("partner", event.target.value)} value={filters.partner}>
          {partners.map((partner) => <option key={partner} value={partner}>{partner}</option>)}
        </select>
      </label>

      <label className="filter-field">
        <span>Harga maksimum</span>
        <select
          onChange={(event) => update("maxPriceMinor", event.target.value ? Number(event.target.value) : null)}
          value={filters.maxPriceMinor ?? ""}
        >
          <option value="">Semua harga</option>
          <option value="10000000">Sampai Rp100 ribu</option>
          <option value="15000000">Sampai Rp150 ribu</option>
          <option value="20000000">Sampai Rp200 ribu</option>
          <option value="30000000">Sampai Rp300 ribu</option>
        </select>
      </label>

      <label className="filter-field">
        <span>Rating minimum</span>
        <select onChange={(event) => update("minRating", Number(event.target.value))} value={filters.minRating}>
          <option value="0">Semua rating</option>
          <option value="4.5">4,5 ke atas</option>
          <option value="4.7">4,7 ke atas</option>
          <option value="4.8">4,8 ke atas</option>
          <option value="4.9">4,9</option>
        </select>
      </label>

      <label className="filter-checkbox">
        <input
          checked={filters.onlyInStock}
          onChange={(event) => update("onlyInStock", event.target.checked)}
          type="checkbox"
        />
        <span><strong>Ready stock only</strong><small>Sembunyikan produk yang semua variannya habis.</small></span>
      </label>

      <button className="filter-reset" disabled={activeCount === 0} onClick={reset} type="button">
        Reset all filters
      </button>
    </aside>
  );

  return (
    <>
      <section className="catalog-hero catalog-hero--product v5-catalog-hero">
        <div>
          <p className="section-eyebrow">Yoru commerce edit</p>
          <h1>Curated pieces for rituals, workdays, and everything after.</h1>
          <p>Gunakan filter detail atau pilih quick edit untuk mempersempit katalog.</p>
        </div>
        <div className="v5-catalog-hero__stat"><strong>{products.length}</strong><span>curated products</span></div>
      </section>

      <div className="quick-filter-rail">
        {productCategories.map((category) => (
          <button
            className={filters.category === category ? "is-active" : ""}
            key={category}
            onClick={() => update("category", category)}
            type="button"
          >
            {category}
          </button>
        ))}
        <button
          className={filters.onlyInStock ? "is-active" : ""}
          onClick={() => update("onlyInStock", !filters.onlyInStock)}
          type="button"
        >
          Ready stock
        </button>
        <button
          className={filters.minRating === 4.8 ? "is-active" : ""}
          onClick={() => update("minRating", filters.minRating === 4.8 ? 0 : 4.8)}
          type="button"
        >
          Rated 4.8+
        </button>
      </div>

      <section className="catalog-browser v5-catalog-browser">
        <div className="desktop-filter">{filterPanel}</div>

        <div className="catalog-results">
          <div className="catalog-results__toolbar v5-results-toolbar">
            <div>
              <strong>{results.length} products</strong>
              <span>from {products.length} curated items</span>
            </div>
            <div className="v5-toolbar-actions">
              <button className="mobile-filter-button" onClick={() => setFilterOpen(true)} type="button">
                <Icon name="menu" width="17" /> Filters {activeCount > 0 ? `(${activeCount})` : ""}
              </button>
              <label>
                <span>Sort</span>
                <select
                  onChange={(event) => update("sort", event.target.value as ProductSort)}
                  value={filters.sort}
                >
                  <option value="recommended">Recommended</option>
                  <option value="price_asc">Price: low to high</option>
                  <option value="price_desc">Price: high to low</option>
                  <option value="rating_desc">Top rated</option>
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
              {filters.partner !== "Semua" ? <button onClick={() => update("partner", "Semua")} type="button">{filters.partner} ×</button> : null}
              {filters.minRating > 0 ? <button onClick={() => update("minRating", 0)} type="button">Rating {filters.minRating}+ ×</button> : null}
              {filters.onlyInStock ? <button onClick={() => update("onlyInStock", false)} type="button">Ready stock ×</button> : null}
              <button className="active-filter-reset" onClick={reset} type="button">Clear all</button>
            </div>
          ) : null}

          {isFiltering ? (
            <CatalogGridSkeleton label="Menyaring produk" view={view} />
          ) : results.length > 0 ? (
            <>
              <div className={`catalog-grid catalog-grid--filtered ${view === "list" ? "is-list" : ""}`}>
                {visibleResults.map((product) => <ProductCard key={product.id} product={product} />)}
              </div>
              {visibleCount < results.length ? (
                <button className="secondary-button load-more-button" onClick={() => setVisibleCount((value) => value + PAGE_SIZE)} type="button">
                  Load more products
                  <Icon name="plus" width="17" />
                </button>
              ) : null}
            </>
          ) : (
            <section className="filter-empty-state">
              <span><Icon name="search" width="25" /></span>
              <h2>No products found.</h2>
              <p>Try changing category, price, rating, partner, or search keywords.</p>
              <button className="secondary-button" onClick={reset} type="button">Reset filters</button>
            </section>
          )}
        </div>
      </section>

      {filterOpen ? (
        <div className="filter-drawer-backdrop" onMouseDown={() => setFilterOpen(false)}>
          <div className="filter-drawer" onMouseDown={(event) => event.stopPropagation()}>
            <div className="filter-drawer__heading">
              <strong>Product filters</strong>
              <button aria-label="Tutup filter" className="icon-button" onClick={() => setFilterOpen(false)} type="button"><Icon name="close" width="19" /></button>
            </div>
            {filterPanel}
            <button className="primary-button filter-apply-button" onClick={() => setFilterOpen(false)} type="button">
              Show {results.length} products
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}
