type CatalogGridSkeletonProps = {
  count?: number;
  label?: string;
  view?: "grid" | "list";
};

export function CatalogGridSkeleton({
  count = 6,
  label = "Memuat katalog",
  view = "grid",
}: CatalogGridSkeletonProps) {
  return (
    <div
      aria-busy="true"
      aria-label={label}
      className={`catalog-grid catalog-grid--filtered catalog-skeleton-grid ${view === "list" ? "is-list" : ""}`}
      role="status"
    >
      {Array.from({ length: count }, (_, index) => (
        <article className="catalog-skeleton-card" key={index}>
          <div className="catalog-skeleton-media skeleton-shimmer" />
          <div className="catalog-skeleton-copy">
            <span className="catalog-skeleton-kicker skeleton-shimmer" />
            <span className="catalog-skeleton-title skeleton-shimmer" />
            <span className="catalog-skeleton-line skeleton-shimmer" />
            <div className="catalog-skeleton-footer">
              <span className="catalog-skeleton-price skeleton-shimmer" />
              <span className="catalog-skeleton-action skeleton-shimmer" />
            </div>
          </div>
        </article>
      ))}
      <span className="visually-hidden">{label}</span>
    </div>
  );
}

export function CatalogRouteSkeleton({ kind }: { kind: "product" | "service" }) {
  return (
    <main aria-busy="true" aria-label={`Memuat katalog ${kind === "product" ? "produk" : "layanan"}`}>
      <section className="catalog-hero v6-route-skeleton-hero">
        <div>
          <span className="v6-route-skeleton-eyebrow skeleton-shimmer" />
          <span className="v6-route-skeleton-heading skeleton-shimmer" />
          <span className="v6-route-skeleton-copy skeleton-shimmer" />
        </div>
        <span className="v6-route-skeleton-stat skeleton-shimmer" />
      </section>
      <section className="catalog-browser v5-catalog-browser">
        <aside className="desktop-filter filter-panel v6-filter-skeleton">
          {Array.from({ length: 6 }, (_, index) => (
            <span className="v6-filter-skeleton-line skeleton-shimmer" key={index} />
          ))}
        </aside>
        <div className="catalog-results">
          <div className="v6-toolbar-skeleton skeleton-shimmer" />
          <CatalogGridSkeleton label="Menyiapkan hasil katalog" />
        </div>
      </section>
    </main>
  );
}

export function DetailRouteSkeleton({ kind }: { kind: "product" | "service" }) {
  return (
    <main
      aria-busy="true"
      aria-label={`Memuat detail ${kind === "product" ? "produk" : "layanan"}`}
      className="v6-detail-route-skeleton"
    >
      <div className="v6-detail-media-skeleton skeleton-shimmer" />
      <div className="v6-detail-copy-skeleton">
        <span className="v6-route-skeleton-eyebrow skeleton-shimmer" />
        <span className="v6-detail-title-skeleton skeleton-shimmer" />
        <span className="v6-route-skeleton-copy skeleton-shimmer" />
        <span className="v6-route-skeleton-copy skeleton-shimmer" />
        <div className="v6-detail-action-skeleton">
          <span className="skeleton-shimmer" />
          <span className="skeleton-shimmer" />
        </div>
      </div>
    </main>
  );
}
