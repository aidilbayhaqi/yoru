export default function StorefrontLoading() {
  return (
    <main aria-busy="true" aria-label="Memuat halaman" className="v7-page-skeleton" role="status">
      <section className="v7-page-skeleton__hero">
        <span className="v7-page-skeleton__eyebrow skeleton-shimmer" />
        <span className="v7-page-skeleton__title skeleton-shimmer" />
        <span className="v7-page-skeleton__copy skeleton-shimmer" />
      </section>
      <section className="v7-page-skeleton__grid">
        {Array.from({ length: 4 }, (_, index) => (
          <article className="v7-page-skeleton__card" key={index}>
            <span className="v7-page-skeleton__media skeleton-shimmer" />
            <span className="v7-page-skeleton__line skeleton-shimmer" />
            <span className="v7-page-skeleton__line v7-page-skeleton__line--short skeleton-shimmer" />
          </article>
        ))}
      </section>
      <span className="visually-hidden">Menyiapkan halaman Yoru</span>
    </main>
  );
}
