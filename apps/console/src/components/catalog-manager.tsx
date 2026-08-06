"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { ApiError, apiRequest } from "@/lib/api";
import styles from "./catalog-manager.module.css";

type Category = {
  id: string;
  code: string;
  name: string;
  description: string | null;
};

type Inventory = {
  id: string;
  product_id: string;
  on_hand: number;
  reserved: number;
  available: number;
  reorder_level: number;
  version: number;
  updated_at: string;
};

type Product = {
  id: string;
  partner_id: string;
  category_id: string;
  sku: string | null;
  name: string;
  slug: string;
  description: string;
  unit_price: string | number;
  currency: string;
  stock_tracked: boolean;
  status: "draft" | "pending_review" | "published" | "revision_required" | "rejected" | "archived";
  review_reason: string | null;
  submitted_at: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  available_quantity: number | null;
  inventory: Inventory | null;
  media: Array<{ id: string; object_key: string; content_type: string; status: string }>;
};

type ProductListResponse = { data: Product[] };
type CatalogSnapshot = { categories: Category[]; products: Product[] };
type ViewMode = "products" | "inventory";

type ProductForm = {
  category_id: string;
  sku: string;
  name: string;
  description: string;
  unit_price: string;
  initial_stock: string;
  reorder_level: string;
  stock_tracked: boolean;
  media_object_key: string;
  media_content_type: string;
  submit_after_save: boolean;
};

const emptyForm: ProductForm = {
  category_id: "",
  sku: "",
  name: "",
  description: "",
  unit_price: "",
  initial_stock: "0",
  reorder_level: "0",
  stock_tracked: true,
  media_object_key: "",
  media_content_type: "image/webp",
  submit_after_save: false,
};

async function fetchCatalogSnapshot(): Promise<CatalogSnapshot> {
  const [categories, productData] = await Promise.all([
    apiRequest<Category[]>("/catalog/categories"),
    apiRequest<ProductListResponse>("/partner/catalog/products?limit=200"),
  ]);
  return { categories, products: productData.data };
}

function formatCurrency(value: string | number, currency = "IDR"): string {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function describeError(error: unknown): { message: string; requestId?: string } {
  if (!(error instanceof ApiError)) {
    return { message: "Tidak dapat terhubung ke API katalog Yoru." };
  }
  const firstFieldMessage = Object.values(error.fieldErrors).flat()[0];
  return { message: firstFieldMessage ?? error.message, requestId: error.requestId };
}

function CatalogManagerSkeleton({ view }: { view: ViewMode }) {
  return (
    <section
      aria-busy="true"
      aria-label="Memuat katalog partner"
      className={styles.panel}
      role="status"
    >
      <header className={styles.toolbar}>
        <div className={styles.skeletonHeading}>
          <span className={styles.skeletonLineSmall} />
          <span className={styles.skeletonLineTitle} />
        </div>
        <span className={styles.skeletonButton} />
      </header>
      {view === "products" ? (
        <>
          <div className={styles.skeletonFilters}>
            <span className={styles.skeletonInput} />
            <span className={styles.skeletonInput} />
          </div>
          <div className={styles.skeletonTable}>
            {Array.from({ length: 6 }, (_, index) => (
              <div className={styles.skeletonTableRow} key={index}>
                <span className={styles.skeletonProduct} />
                <span className={styles.skeletonCell} />
                <span className={styles.skeletonCell} />
                <span className={styles.skeletonCell} />
                <span className={styles.skeletonBadge} />
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className={styles.inventoryGrid}>
          {Array.from({ length: 4 }, (_, index) => (
            <div className={styles.skeletonInventoryCard} key={index}>
              <span className={styles.skeletonLineTitle} />
              <div className={styles.skeletonInventoryStats}>
                {Array.from({ length: 4 }, (_, item) => (
                  <span key={item} />
                ))}
              </div>
              <span className={styles.skeletonInput} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function CatalogManager({
  view,
  onMessage,
}: {
  view: ViewMode;
  onMessage?: (message: string) => void;
}) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busyId, setBusyId] = useState<string>();
  const [error, setError] = useState<{ message: string; requestId?: string }>();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product>();
  const [form, setForm] = useState<ProductForm>(emptyForm);

  const debouncedSearch = useDebouncedValue(search, 280);
  const isFiltering = search.trim() !== debouncedSearch.trim();

  const applySnapshot = useCallback((snapshot: CatalogSnapshot) => {
    setCategories(snapshot.categories);
    setProducts(snapshot.products);
    setForm((current) => ({
      ...current,
      category_id: current.category_id || snapshot.categories[0]?.id || "",
    }));
  }, []);

  const load = useCallback(async () => {
    setRefreshing(true);
    setError(undefined);
    try {
      applySnapshot(await fetchCatalogSnapshot());
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [applySnapshot]);

  useEffect(() => {
    let active = true;

    void fetchCatalogSnapshot()
      .then((snapshot) => {
        if (active) applySnapshot(snapshot);
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
  }, [applySnapshot]);

  const filteredProducts = useMemo(() => {
    const query = debouncedSearch.trim().toLowerCase();
    return products.filter((product) => {
      const matchesSearch =
        !query ||
        product.name.toLowerCase().includes(query) ||
        product.sku?.toLowerCase().includes(query) ||
        product.slug.toLowerCase().includes(query);
      const matchesStatus = status === "all" || product.status === status;
      return matchesSearch && matchesStatus;
    });
  }, [debouncedSearch, products, status]);

  const trackedProducts = useMemo(
    () => products.filter((product) => product.stock_tracked),
    [products],
  );

  function openCreate() {
    setEditing(undefined);
    setForm({ ...emptyForm, category_id: categories[0]?.id ?? "" });
    setModalOpen(true);
  }

  function openEdit(product: Product) {
    setEditing(product);
    setForm({
      category_id: product.category_id,
      sku: product.sku ?? "",
      name: product.name,
      description: product.description,
      unit_price: String(product.unit_price),
      initial_stock: String(product.inventory?.on_hand ?? 0),
      reorder_level: String(product.inventory?.reorder_level ?? 0),
      stock_tracked: product.stock_tracked,
      media_object_key: "",
      media_content_type: "image/webp",
      submit_after_save: false,
    });
    setModalOpen(true);
  }

  async function saveProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setBusyId(editing?.id ?? "create");
    try {
      const payload = {
        category_id: form.category_id,
        sku: form.sku.trim() || null,
        name: form.name.trim(),
        description: form.description.trim(),
        unit_price: form.unit_price,
        currency: "IDR",
        stock_tracked: form.stock_tracked,
      };

      let saved: Product;
      if (editing) {
        saved = await apiRequest<Product>(`/partner/catalog/products/${editing.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        saved = await apiRequest<Product>("/partner/catalog/products", {
          method: "POST",
          body: JSON.stringify({
            ...payload,
            initial_stock: Number(form.initial_stock || 0),
            reorder_level: Number(form.reorder_level || 0),
          }),
        });
      }

      if (form.media_object_key.trim()) {
        await apiRequest<unknown>(`/partner/catalog/products/${saved.id}/media`, {
          method: "POST",
          body: JSON.stringify({
            object_key: form.media_object_key.trim(),
            content_type: form.media_content_type.trim(),
            alt_text: saved.name,
            sort_order: 0,
          }),
        });
      }

      if (form.submit_after_save && saved.status !== "published") {
        await apiRequest<Product>(`/partner/catalog/products/${saved.id}/submit`, {
          method: "POST",
        });
      }

      setModalOpen(false);
      onMessage?.(
        form.submit_after_save
          ? "Produk tersimpan dan dikirim untuk review."
          : "Draft produk tersimpan di API.",
      );
      await load();
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setBusyId(undefined);
    }
  }

  async function runAction(product: Product, action: "submit" | "archive") {
    setBusyId(product.id);
    setError(undefined);
    try {
      await apiRequest<Product>(`/partner/catalog/products/${product.id}/${action}`, {
        method: "POST",
      });
      onMessage?.(
        action === "submit" ? "Produk dikirim ke antrean review." : "Produk berhasil diarsipkan.",
      );
      await load();
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setBusyId(undefined);
    }
  }

  async function updateInventory(product: Product, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusyId(product.id);
    setError(undefined);
    try {
      await apiRequest<Inventory>(`/partner/catalog/products/${product.id}/inventory`, {
        method: "PUT",
        body: JSON.stringify({
          on_hand: Number(data.get("on_hand") ?? 0),
          reorder_level: Number(data.get("reorder_level") ?? 0),
          expected_version: product.inventory?.version ?? undefined,
        }),
      });
      onMessage?.(`Stok ${product.name} berhasil diperbarui.`);
      await load();
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setBusyId(undefined);
    }
  }

  if (loading) return <CatalogManagerSkeleton view={view} />;

  return (
    <div className={styles.shell}>
      {refreshing ? (
        <div aria-label="Memperbarui katalog" className={styles.refreshBar} role="status">
          <span />
        </div>
      ) : null}
      {error ? (
        <div className={styles.error} role="alert">
          <strong>Operasi katalog gagal</strong>
          <span>{error.message}</span>
          {error.requestId ? (
            <small>
              Kode permintaan: <code>{error.requestId}</code>
            </small>
          ) : null}
        </div>
      ) : null}

      {view === "products" ? (
        <section className={styles.panel}>
          <header className={styles.toolbar}>
            <div>
              <span className={styles.eyebrow}>LIVE CATALOG API</span>
              <h2>{products.length} produk partner</h2>
            </div>
            <div className={styles.actions}>
              <button
                className={styles.buttonQuiet}
                disabled={refreshing}
                onClick={() => void load()}
                type="button"
              >
                {refreshing ? "Memuat…" : "Muat ulang"}
              </button>
              <button
                className={styles.button}
                disabled={categories.length === 0 || refreshing}
                onClick={openCreate}
                type="button"
              >
                Tambah produk
              </button>
            </div>
          </header>
          <div className={styles.filters}>
            <input
              className={styles.input}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Cari nama, SKU, atau slug…"
              value={search}
            />
            <select
              className={styles.select}
              onChange={(event) => setStatus(event.target.value)}
              value={status}
            >
              <option value="all">Semua status</option>
              <option value="draft">Draft</option>
              <option value="pending_review">Menunggu review</option>
              <option value="published">Published</option>
              <option value="revision_required">Perlu revisi</option>
              <option value="rejected">Ditolak</option>
              <option value="archived">Diarsipkan</option>
            </select>
          </div>
          {isFiltering ? (
            <div className={styles.skeletonTable} aria-label="Menyaring produk" role="status">
              {Array.from({ length: 5 }, (_, index) => (
                <div className={styles.skeletonTableRow} key={index}>
                  <span className={styles.skeletonProduct} />
                  <span className={styles.skeletonCell} />
                  <span className={styles.skeletonCell} />
                  <span className={styles.skeletonCell} />
                  <span className={styles.skeletonBadge} />
                </div>
              ))}
            </div>
          ) : filteredProducts.length === 0 ? (
            <div className={styles.state}>Belum ada produk yang cocok dengan filter.</div>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Produk</th>
                    <th>Harga</th>
                    <th>Stok</th>
                    <th>Media</th>
                    <th>Status</th>
                    <th>Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProducts.map((product) => (
                    <tr key={product.id}>
                      <td>
                        <div className={styles.product}>
                          <strong>{product.name}</strong>
                          <span className={styles.meta}>
                            {product.sku ?? "Tanpa SKU"} · {product.slug}
                          </span>
                          {product.review_reason ? (
                            <span className={styles.meta}>Review: {product.review_reason}</span>
                          ) : null}
                        </div>
                      </td>
                      <td>{formatCurrency(product.unit_price, product.currency)}</td>
                      <td>
                        {product.stock_tracked
                          ? (product.inventory?.available ?? 0)
                          : "Tidak dilacak"}
                      </td>
                      <td>{product.media.length}</td>
                      <td>
                        <span className={styles.badge} data-status={product.status}>
                          {product.status.replaceAll("_", " ")}
                        </span>
                      </td>
                      <td>
                        <div className={styles.rowActions}>
                          <button
                            disabled={busyId === product.id}
                            onClick={() => openEdit(product)}
                            type="button"
                          >
                            Edit
                          </button>
                          {["draft", "revision_required"].includes(product.status) ? (
                            <button
                              disabled={busyId === product.id}
                              onClick={() => void runAction(product, "submit")}
                              type="button"
                            >
                              {busyId === product.id ? "Memproses…" : "Kirim review"}
                            </button>
                          ) : null}
                          {product.status !== "archived" ? (
                            <button
                              disabled={busyId === product.id}
                              onClick={() => void runAction(product, "archive")}
                              type="button"
                            >
                              Arsipkan
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : (
        <section className={styles.panel}>
          <header className={styles.toolbar}>
            <div>
              <span className={styles.eyebrow}>OPTIMISTIC INVENTORY CONTROL</span>
              <h2>Stok produk partner</h2>
            </div>
            <button
              className={styles.buttonQuiet}
              disabled={refreshing}
              onClick={() => void load()}
              type="button"
            >
              {refreshing ? "Memuat…" : "Muat ulang"}
            </button>
          </header>
          <div className={styles.inventoryGrid}>
            {trackedProducts.length === 0 ? (
              <div className={styles.state}>Belum ada produk dengan pelacakan stok aktif.</div>
            ) : null}
            {trackedProducts.map((product) => (
              <article className={styles.inventoryCard} key={product.id}>
                <div className={styles.inventoryHead}>
                  <div className={styles.product}>
                    <strong>{product.name}</strong>
                    <span className={styles.meta}>{product.sku ?? product.slug}</span>
                  </div>
                  <span className={styles.badge} data-status={product.status}>
                    {product.status.replaceAll("_", " ")}
                  </span>
                </div>
                <div className={styles.inventoryStats}>
                  <div>
                    <span>On hand</span>
                    <strong>{product.inventory?.on_hand ?? 0}</strong>
                  </div>
                  <div>
                    <span>Reserved</span>
                    <strong>{product.inventory?.reserved ?? 0}</strong>
                  </div>
                  <div>
                    <span>Available</span>
                    <strong>{product.inventory?.available ?? 0}</strong>
                  </div>
                  <div>
                    <span>Version</span>
                    <strong>{product.inventory?.version ?? 1}</strong>
                  </div>
                </div>
                <form
                  className={styles.inventoryForm}
                  onSubmit={(event) => void updateInventory(product, event)}
                >
                  <label>
                    Jumlah fisik
                    <input
                      className={styles.input}
                      defaultValue={product.inventory?.on_hand ?? 0}
                      min="0"
                      name="on_hand"
                      required
                      type="number"
                    />
                  </label>
                  <label>
                    Batas restock
                    <input
                      className={styles.input}
                      defaultValue={product.inventory?.reorder_level ?? 0}
                      min="0"
                      name="reorder_level"
                      required
                      type="number"
                    />
                  </label>
                  <button className={styles.button} disabled={busyId === product.id} type="submit">
                    {busyId === product.id ? "Menyimpan…" : "Simpan stok"}
                  </button>
                </form>
              </article>
            ))}
          </div>
        </section>
      )}

      {modalOpen ? (
        <div className={styles.modalBackdrop} role="presentation">
          <div
            aria-labelledby="catalog-form-title"
            aria-modal="true"
            className={styles.modal}
            role="dialog"
          >
            <div className={styles.modalHeader}>
              <div>
                <span className={styles.eyebrow}>CATALOG WORKFLOW</span>
                <h3 id="catalog-form-title">{editing ? "Edit produk" : "Buat produk"}</h3>
              </div>
              <button
                className={styles.buttonQuiet}
                onClick={() => setModalOpen(false)}
                type="button"
              >
                Tutup
              </button>
            </div>
            <form className={styles.form} onSubmit={(event) => void saveProduct(event)}>
              <div className={styles.grid}>
                <label>
                  Kategori
                  <select
                    className={styles.select}
                    onChange={(event) => setForm({ ...form, category_id: event.target.value })}
                    required
                    value={form.category_id}
                  >
                    {categories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  SKU
                  <input
                    className={styles.input}
                    maxLength={80}
                    onChange={(event) => setForm({ ...form, sku: event.target.value })}
                    placeholder="Opsional"
                    value={form.sku}
                  />
                </label>
              </div>
              <label>
                Nama produk
                <input
                  className={styles.input}
                  maxLength={180}
                  minLength={2}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  required
                  value={form.name}
                />
              </label>
              <label>
                Deskripsi
                <textarea
                  className={styles.textarea}
                  maxLength={10000}
                  minLength={10}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                  required
                  value={form.description}
                />
              </label>
              <div className={styles.grid}>
                <label>
                  Harga IDR
                  <input
                    className={styles.input}
                    min="0"
                    onChange={(event) => setForm({ ...form, unit_price: event.target.value })}
                    required
                    step="0.01"
                    type="number"
                    value={form.unit_price}
                  />
                </label>
                <label className={styles.check}>
                  <input
                    checked={form.stock_tracked}
                    onChange={(event) => setForm({ ...form, stock_tracked: event.target.checked })}
                    type="checkbox"
                  />{" "}
                  Lacak stok
                </label>
              </div>
              {!editing && form.stock_tracked ? (
                <div className={styles.grid}>
                  <label>
                    Stok awal
                    <input
                      className={styles.input}
                      min="0"
                      onChange={(event) => setForm({ ...form, initial_stock: event.target.value })}
                      type="number"
                      value={form.initial_stock}
                    />
                  </label>
                  <label>
                    Batas restock
                    <input
                      className={styles.input}
                      min="0"
                      onChange={(event) => setForm({ ...form, reorder_level: event.target.value })}
                      type="number"
                      value={form.reorder_level}
                    />
                  </label>
                </div>
              ) : null}
              <div className={styles.grid}>
                <label>
                  Object key media
                  <input
                    className={styles.input}
                    onChange={(event) => setForm({ ...form, media_object_key: event.target.value })}
                    placeholder="catalog/partner/product.webp"
                    value={form.media_object_key}
                  />
                </label>
                <label>
                  Content type
                  <input
                    className={styles.input}
                    onChange={(event) =>
                      setForm({ ...form, media_content_type: event.target.value })
                    }
                    value={form.media_content_type}
                  />
                </label>
              </div>
              <label className={styles.check}>
                <input
                  checked={form.submit_after_save}
                  onChange={(event) =>
                    setForm({ ...form, submit_after_save: event.target.checked })
                  }
                  type="checkbox"
                />{" "}
                Kirim untuk review setelah disimpan
              </label>
              <div className={styles.notice}>
                Media object key hanya mendaftarkan objek yang sudah diunggah ke storage. UI ini
                tidak memalsukan upload file. Bila policy publish mensyaratkan media, isi object key
                yang valid sebelum mengirim review.
              </div>
              <div className={styles.footer}>
                <button
                  className={styles.buttonQuiet}
                  onClick={() => setModalOpen(false)}
                  type="button"
                >
                  Batal
                </button>
                <button className={styles.button} disabled={Boolean(busyId)} type="submit">
                  {busyId ? "Menyimpan…" : "Simpan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
