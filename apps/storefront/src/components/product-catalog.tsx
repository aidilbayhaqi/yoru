"use client";

import { useState } from "react";

import { Icon } from "@/components/icons";
import { ProductCard } from "@/components/product-card";
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

export function ProductCatalog() {
  const [filters, setFilters] = useState<ProductFilters>(defaultFilters);
  const results = filterProducts(products, filters);
  const activeCount = [
    filters.query.trim().length > 0,
    filters.category !== "Semua",
    filters.partner !== "Semua",
    filters.maxPriceMinor !== null,
    filters.minRating > 0,
    filters.onlyInStock,
  ].filter(Boolean).length;

  function update<Key extends keyof ProductFilters>(
    key: Key,
    value: ProductFilters[Key],
  ) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <>
      <section className="catalog-hero catalog-hero--product">
        <p className="section-eyebrow">Yoru commerce</p>
        <h1>Produk terkurasi untuk rutinitas dan gayamu.</h1>
        <p>
          Temukan produk berdasarkan kategori, partner, harga, rating, dan ketersediaan stok.
        </p>
      </section>

      <section className="catalog-browser">
        <aside className="filter-panel" aria-label="Filter produk">
          <div className="filter-panel__heading">
            <div>
              <p className="section-eyebrow">Filter produk</p>
              <h2>Atur pencarian</h2>
            </div>
            {activeCount > 0 ? <span>{activeCount} aktif</span> : null}
          </div>

          <label className="filter-search">
            <span>Cari produk</span>
            <div>
              <Icon name="search" width="17" />
              <input
                onChange={(event) => update("query", event.target.value)}
                placeholder="Nama, kategori, atau partner"
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
              {productCategories.map((category) => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Partner</span>
            <select
              onChange={(event) => update("partner", event.target.value)}
              value={filters.partner}
            >
              {partners.map((partner) => (
                <option key={partner} value={partner}>{partner}</option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Harga maksimum</span>
            <select
              onChange={(event) =>
                update(
                  "maxPriceMinor",
                  event.target.value ? Number(event.target.value) : null,
                )
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

          <label className="filter-field">
            <span>Rating minimum</span>
            <select
              onChange={(event) => update("minRating", Number(event.target.value))}
              value={filters.minRating}
            >
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
            <span>
              <strong>Hanya stok tersedia</strong>
              <small>Sembunyikan varian yang seluruh stoknya habis.</small>
            </span>
          </label>

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
              <strong>{results.length} produk</strong>
              <span>dari {products.length} item katalog</span>
            </div>
            <label>
              <span>Urutkan</span>
              <select
                onChange={(event) => update("sort", event.target.value as ProductSort)}
                value={filters.sort}
              >
                <option value="recommended">Rekomendasi</option>
                <option value="price_asc">Harga terendah</option>
                <option value="price_desc">Harga tertinggi</option>
                <option value="rating_desc">Rating tertinggi</option>
              </select>
            </label>
          </div>

          {results.length > 0 ? (
            <div className="catalog-grid catalog-grid--filtered">
              {results.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          ) : (
            <section className="filter-empty-state">
              <span><Icon name="search" width="25" /></span>
              <h2>Produk belum ditemukan.</h2>
              <p>Coba ubah kategori, batas harga, rating, atau kata pencarian.</p>
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
