"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { ApiError, apiRequest } from "@/lib/api";
import styles from "./catalog-manager.module.css";

type ReviewProduct = {
  id: string;
  partner_id: string;
  sku: string | null;
  name: string;
  slug: string;
  description: string;
  unit_price: string | number;
  currency: string;
  status: string;
  media: Array<{ id: string; object_key: string; status: string }>;
};

type ProductListResponse = { data: ReviewProduct[] };
type Decision = "publish" | "revision_required" | "reject";

async function fetchReviewQueue(): Promise<ReviewProduct[]> {
  const response = await apiRequest<ProductListResponse>(
    "/admin/catalog/products?status=pending_review&limit=200",
  );
  return response.data;
}

function describeError(error: unknown): { message: string; requestId?: string } {
  if (!(error instanceof ApiError)) {
    return { message: "Tidak dapat terhubung ke antrean moderasi katalog." };
  }
  const fieldMessage = Object.values(error.fieldErrors).flat()[0];
  return { message: fieldMessage ?? error.message, requestId: error.requestId };
}

function ModerationSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div aria-label="Memuat antrean moderasi" className={styles.moderationGrid} role="status">
      {Array.from({ length: count }, (_, index) => (
        <article className={styles.skeletonModerationCard} key={index}>
          <span className={styles.skeletonLineSmall} />
          <span className={styles.skeletonLineTitle} />
          <span className={styles.skeletonParagraph} />
          <span className={styles.skeletonTextarea} />
          <div className={styles.skeletonActions}>
            <span />
            <span />
            <span />
          </div>
        </article>
      ))}
    </div>
  );
}

export function CatalogModeration({ onMessage }: { onMessage?: (message: string) => void }) {
  const [products, setProducts] = useState<ReviewProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busyId, setBusyId] = useState<string>();
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [error, setError] = useState<{ message: string; requestId?: string }>();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 280);
  const isFiltering = search.trim() !== debouncedSearch.trim();

  const load = useCallback(async () => {
    setRefreshing(true);
    setError(undefined);
    try {
      setProducts(await fetchReviewQueue());
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    void fetchReviewQueue()
      .then((data) => {
        if (active) setProducts(data);
      })
      .catch((reason: unknown) => {
        if (active) setError(describeError(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const filteredProducts = useMemo(() => {
    const query = debouncedSearch.trim().toLowerCase();
    if (!query) return products;
    return products.filter((product) =>
      [product.name, product.sku ?? "", product.slug, product.partner_id]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }, [debouncedSearch, products]);

  async function moderate(product: ReviewProduct, decision: Decision) {
    const reason = reasons[product.id]?.trim() ?? "";
    if (decision !== "publish" && !reason) {
      setError({ message: "Alasan wajib diisi untuk keputusan revisi atau penolakan." });
      return;
    }

    setBusyId(product.id);
    setError(undefined);
    try {
      await apiRequest<ReviewProduct>(`/admin/catalog/products/${product.id}/moderate`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          reason: decision === "publish" ? null : reason,
        }),
      });
      setProducts((current) => current.filter((item) => item.id !== product.id));
      setReasons((current) => {
        const next = { ...current };
        delete next[product.id];
        return next;
      });
      onMessage?.(
        decision === "publish"
          ? `${product.name} berhasil dipublikasikan.`
          : decision === "revision_required"
            ? `${product.name} dikembalikan untuk revisi.`
            : `${product.name} ditolak.`,
      );
    } catch (reasonValue) {
      setError(describeError(reasonValue));
    } finally {
      setBusyId(undefined);
    }
  }

  return (
    <section className={styles.panel}>
      {refreshing ? (
        <div aria-label="Memperbarui antrean" className={styles.refreshBar} role="status">
          <span />
        </div>
      ) : null}
      <header className={styles.toolbar}>
        <div>
          <span className={styles.eyebrow}>LIVE CATALOG MODERATION</span>
          <h2>{products.length} produk menunggu review</h2>
        </div>
        <button
          className={styles.buttonQuiet}
          disabled={loading || refreshing}
          onClick={() => void load()}
          type="button"
        >
          {refreshing ? "Memuat…" : "Muat ulang"}
        </button>
      </header>

      <div className={styles.moderationFilters}>
        <input
          className={styles.input}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Cari nama, SKU, slug, atau partner…"
          type="search"
          value={search}
        />
        <span>
          {filteredProducts.length} dari {products.length} antrean
        </span>
      </div>

      {error ? (
        <div className={styles.error} role="alert">
          <strong>Moderasi katalog gagal</strong>
          <span>{error.message}</span>
          {error.requestId ? (
            <small>
              Kode permintaan: <code>{error.requestId}</code>
            </small>
          ) : null}
        </div>
      ) : null}

      {loading || isFiltering ? (
        <ModerationSkeleton count={loading ? 4 : 3} />
      ) : filteredProducts.length === 0 ? (
        <div className={styles.state}>
          {products.length === 0
            ? "Tidak ada produk yang menunggu moderasi."
            : "Tidak ada produk yang cocok dengan pencarian."}
        </div>
      ) : (
        <div className={styles.moderationGrid}>
          {filteredProducts.map((product) => (
            <article className={styles.moderationCard} key={product.id}>
              <div className={styles.product}>
                <strong>{product.name}</strong>
                <span className={styles.meta}>
                  Partner {product.partner_id.slice(0, 8)} · {product.sku ?? product.slug}
                </span>
                <span className={styles.meta}>
                  {new Intl.NumberFormat("id-ID", {
                    style: "currency",
                    currency: product.currency,
                    maximumFractionDigits: 0,
                  }).format(Number(product.unit_price))}
                  {" · "}
                  {product.media.length} media
                </span>
              </div>
              <p className={styles.description}>{product.description}</p>
              <label className={styles.reasonField}>
                Alasan revisi atau penolakan
                <textarea
                  className={styles.textarea}
                  disabled={busyId === product.id}
                  maxLength={2000}
                  onChange={(event) =>
                    setReasons((current) => ({ ...current, [product.id]: event.target.value }))
                  }
                  placeholder="Wajib untuk revisi atau penolakan"
                  value={reasons[product.id] ?? ""}
                />
              </label>
              <div className={styles.actions}>
                <button
                  className={styles.button}
                  disabled={busyId === product.id}
                  onClick={() => void moderate(product, "publish")}
                  type="button"
                >
                  {busyId === product.id ? "Memproses…" : "Publish"}
                </button>
                <button
                  className={styles.buttonQuiet}
                  disabled={busyId === product.id}
                  onClick={() => void moderate(product, "revision_required")}
                  type="button"
                >
                  Minta revisi
                </button>
                <button
                  className={styles.buttonDanger}
                  disabled={busyId === product.id}
                  onClick={() => void moderate(product, "reject")}
                  type="button"
                >
                  Tolak
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
