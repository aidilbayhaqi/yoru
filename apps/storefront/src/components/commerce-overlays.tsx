"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  type ChangeEvent,
  type FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { Icon } from "@/components/icons";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { products, services } from "@/lib/storefront-data";
import { formatMoney } from "@/lib/storefront-domain";

type SearchMode = "query" | "ai" | "image";
type AssistantMessage = {
  id: number;
  role: "assistant" | "user";
  text: string;
};

const quickPrompts = [
  "Skincare untuk skin barrier",
  "Home facial di Jakarta",
  "Hadiah di bawah Rp300 ribu",
  "Grooming paling cepat",
];

function inferVisualQuery(fileName: string, fallback: string): string {
  const normalized = fileName.toLowerCase();
  const keywordMap = [
    ["serum", "serum skincare"],
    ["cream", "moisturizer skincare"],
    ["bag", "fashion tote"],
    ["tote", "fashion tote"],
    ["lip", "lip tint makeup"],
    ["hair", "hair care"],
    ["nail", "nail care"],
    ["facial", "facial"],
  ] as const;

  return keywordMap.find(([keyword]) => normalized.includes(keyword))?.[1] ?? fallback;
}

function assistantReply(prompt: string): string {
  const value = prompt.toLowerCase();
  if (value.includes("barrier") || value.includes("skincare")) {
    return "Mulai dari Barrier Cloud Moisturizer untuk rutinitas sederhana. Kalau kulitmu sedang sensitif, hindari menambah terlalu banyak active sekaligus.";
  }
  if (value.includes("facial") || value.includes("jakarta")) {
    return "Home Facial Reset tersedia untuk Jakarta Selatan, Jakarta Pusat, dan Depok. Cek alamat dan slot sebelum pembayaran supaya serviceability tervalidasi.";
  }
  if (value.includes("hadiah") || value.includes("300")) {
    return "Everyday Satin Tote dan Glow Reset Serum masuk rentang pilihan hadiah di bawah Rp300 ribu. Aku sarankan cek preferensi penerima dulu.";
  }
  if (value.includes("grooming") || value.includes("cepat")) {
    return "Men Grooming Home Visit berdurasi sekitar 60 menit. Waktu kedatangan tetap bergantung area, profesional, dan slot aktif.";
  }
  return "Aku bisa bantu mempersempit pilihan berdasarkan kebutuhan, budget, area, waktu, dan preferensi. Rekomendasi ini panduan awal; harga, stok, serta slot final tetap diverifikasi sistem.";
}

export function CommerceOverlays() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [mode, setMode] = useState<SearchMode>("query");
  const [query, setQuery] = useState("");
  const [visualCategory, setVisualCategory] = useState("fashion");
  const [fileName, setFileName] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [visualError, setVisualError] = useState("");
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantLoading, setAssistantLoading] = useState(false);
  const assistantTimerRef = useRef<number | null>(null);
  const nextMessageIdRef = useRef(2);
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      id: 1,
      role: "assistant",
      text: "Hai, aku Yoru Assistant. Ceritakan kebutuhan, budget, area, atau jadwalmu. Aku bantu menyaring pilihan tanpa menggantikan keputusanmu.",
    },
  ]);

  useEffect(() => {
    function handleOpenSearch(event: Event) {
      const custom = event as CustomEvent<{ mode?: SearchMode }>;
      setMode(custom.detail?.mode ?? "query");
      setSearchOpen(true);
    }
    function handleKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
      if (event.key === "Escape") {
        setSearchOpen(false);
        setAssistantOpen(false);
      }
    }

    window.addEventListener("yoru:open-search", handleOpenSearch);
    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("yoru:open-search", handleOpenSearch);
      window.removeEventListener("keydown", handleKey);
    };
  }, []);

  useEffect(() => {
    const locked = searchOpen || assistantOpen;
    const previous = document.body.style.overflow;
    if (locked) document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [assistantOpen, searchOpen]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    return () => {
      if (assistantTimerRef.current !== null) {
        window.clearTimeout(assistantTimerRef.current);
      }
    };
  }, []);

  const debouncedQuery = useDebouncedValue(query, 240);
  const suggestionsLoading = query.trim() !== debouncedQuery.trim();

  const suggestions = useMemo(() => {
    const source = [
      ...products.slice(0, 3).map((product) => ({
        href: `/products/${product.slug}`,
        label: product.name,
        meta: `${product.category} · ${formatMoney(product.priceMinor)}`,
      })),
      ...services.slice(0, 2).map((service) => ({
        href: `/services/${service.slug}`,
        label: service.name,
        meta: `${service.category} · ${service.durationMin} menit`,
      })),
    ];
    if (!debouncedQuery.trim()) return source;
    const normalized = debouncedQuery.toLowerCase();
    return source.filter((item) => `${item.label} ${item.meta}`.toLowerCase().includes(normalized));
  }, [debouncedQuery]);

  function closeSearch() {
    setSearchOpen(false);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = query.trim();
    if (!normalized) return;
    router.push(`/search?q=${encodeURIComponent(normalized)}&mode=${mode}`);
    closeSearch();
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setVisualError("File terlalu besar. Gunakan gambar maksimal 10 MB.");
      event.target.value = "";
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setVisualError("Format belum didukung. Gunakan JPG, PNG, atau WEBP.");
      event.target.value = "";
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setVisualError("");
    setFileName(file.name);
    setPreviewUrl(URL.createObjectURL(file));
  }

  function runVisualSearch() {
    if (!fileName) {
      fileInputRef.current?.click();
      return;
    }
    const visualQuery = inferVisualQuery(fileName, visualCategory);
    router.push(`/search?q=${encodeURIComponent(visualQuery)}&mode=image`);
    closeSearch();
  }

  function sendAssistant(text = assistantInput) {
    const normalized = text.trim();
    if (!normalized || assistantLoading) return;
    const userMessageId = nextMessageIdRef.current;
    const assistantMessageId = userMessageId + 1;
    nextMessageIdRef.current += 2;
    setMessages((current) => [
      ...current,
      { id: userMessageId, role: "user", text: normalized },
    ]);
    setAssistantInput("");
    setAssistantLoading(true);

    assistantTimerRef.current = window.setTimeout(() => {
      setMessages((current) => [
        ...current,
        { id: assistantMessageId, role: "assistant", text: assistantReply(normalized) },
      ]);
      setAssistantLoading(false);
      assistantTimerRef.current = null;
    }, 520);
  }

  return (
    <>
      {!assistantOpen ? (
        <button
          aria-expanded={assistantOpen}
          aria-label="Buka Yoru AI"
          className="ai-fab"
          onClick={() => setAssistantOpen(true)}
          type="button"
        >
          <span className="ai-fab__orb"><Icon name="sparkle" width="18" /></span>
          <span className="ai-fab__label">Yoru AI</span>
        </button>
      ) : null}

      {searchOpen ? (
        <div className="overlay-backdrop" onMouseDown={closeSearch}>
          <section
            aria-labelledby="search-dialog-title"
            aria-modal="true"
            className="search-dialog"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="overlay-heading">
              <div>
                <p className="section-eyebrow">Pencarian Yoru</p>
                <h2 id="search-dialog-title">Cari lebih cepat.</h2>
              </div>
              <button aria-label="Tutup pencarian" className="icon-button" onClick={closeSearch} type="button">
                <Icon name="close" width="20" />
              </button>
            </div>

            <div className="search-mode-tabs" role="tablist" aria-label="Mode pencarian">
              {[
                ["query", "Kata kunci", "Nama, kategori, atau partner"],
                ["ai", "Dengan AI", "Ceritakan kebutuhanmu"],
                ["image", "Dengan gambar", "Upload referensi visual"],
              ].map(([value, title, detail]) => (
                <button
                  aria-selected={mode === value}
                  className={mode === value ? "is-active" : ""}
                  key={value}
                  onClick={() => setMode(value as SearchMode)}
                  role="tab"
                  type="button"
                >
                  <Icon name={value === "image" ? "sparkle" : value === "ai" ? "wand" : "search"} width="18" />
                  <span><strong>{title}</strong><small>{detail}</small></span>
                </button>
              ))}
            </div>

            {mode !== "image" ? (
              <form className="discovery-form" onSubmit={submitSearch}>
                <div className="discovery-input">
                  <Icon name={mode === "ai" ? "wand" : "search"} width="21" />
                  <textarea
                    aria-label={mode === "ai" ? "Jelaskan kebutuhan" : "Kata pencarian"}
                    autoFocus
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={
                      mode === "ai"
                        ? "Contoh: aku butuh skincare simpel untuk barrier, budget maksimal Rp350 ribu..."
                        : "Cari nama produk, kategori, partner, layanan, atau area..."
                    }
                    rows={mode === "ai" ? 3 : 1}
                    value={query}
                  />
                  <button className="primary-button" disabled={!query.trim()} type="submit">
                    Cari
                    <Icon name="arrow" width="17" />
                  </button>
                </div>
                {mode === "ai" ? (
                  <p className="ai-disclaimer">
                    AI menyusun intent pencarian. Harga, stok, cakupan area, dan slot final tetap diverifikasi sistem.
                  </p>
                ) : null}

                <div className="search-suggestion-list">
                  <div className="search-suggestion-heading">
                    <span>{query.trim() ? "Quick matches" : "Sedang populer"}</span>
                    <small>{suggestions.length} pilihan</small>
                  </div>
                  {suggestionsLoading ? (
                    <div aria-label="Mencari saran" className="search-suggestion-skeleton" role="status">
                      {Array.from({ length: 3 }, (_, index) => (
                        <span className="skeleton-shimmer" key={index} />
                      ))}
                    </div>
                  ) : suggestions.length > 0 ? suggestions.map((item) => (
                    <Link href={item.href} key={item.href} onClick={closeSearch}>
                      <span><Icon name="search" width="17" /></span>
                      <div><strong>{item.label}</strong><small>{item.meta}</small></div>
                      <Icon name="arrow" width="17" />
                    </Link>
                  )) : (
                    <p className="search-no-suggestion">Tekan Cari untuk melihat hasil lebih luas.</p>
                  )}
                </div>
              </form>
            ) : (
              <div className="visual-search-panel">
                <button
                  className={`visual-dropzone ${previewUrl ? "has-preview" : ""}`}
                  onClick={() => fileInputRef.current?.click()}
                  style={previewUrl ? { backgroundImage: `url(${previewUrl})` } : undefined}
                  type="button"
                >
                  {!previewUrl ? (
                    <>
                      <span><Icon name="sparkle" width="28" /></span>
                      <strong>Upload foto referensi</strong>
                      <small>JPG, PNG, atau WEBP. Maksimal 10 MB.</small>
                    </>
                  ) : (
                    <span className="visual-preview-label">
                      <strong>{fileName}</strong>
                      <small>Klik untuk mengganti foto</small>
                    </span>
                  )}
                </button>
                <input
                  accept="image/jpeg,image/png,image/webp"
                  className="visually-hidden"
                  onChange={chooseFile}
                  ref={fileInputRef}
                  type="file"
                />

                <div className="visual-category-picker">
                  <span>Fokus pencarian</span>
                  <div>
                    {["fashion", "skincare", "makeup", "hair care", "home service"].map((category) => (
                      <button
                        className={visualCategory === category ? "is-active" : ""}
                        key={category}
                        onClick={() => setVisualCategory(category)}
                        type="button"
                      >
                        {category}
                      </button>
                    ))}
                  </div>
                </div>

                {visualError ? <p className="visual-error" role="alert">{visualError}</p> : null}
                <button className="primary-button visual-search-action" onClick={runVisualSearch} type="button">
                  {fileName ? "Cari barang serupa" : "Pilih media"}
                  <Icon name="arrow" width="18" />
                </button>
                <p className="ai-disclaimer">
                  Preview ini membuat intent dari nama file dan kategori. Production visual matching membutuhkan endpoint image embedding dan similarity search.
                </p>
              </div>
            )}
          </section>
        </div>
      ) : null}

      {assistantOpen ? (
        <div className="assistant-backdrop" onMouseDown={() => setAssistantOpen(false)}>
          <aside
            aria-labelledby="assistant-title"
            aria-modal="true"
            className="assistant-drawer"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="assistant-heading">
              <div className="assistant-avatar"><Icon name="sparkle" width="22" /></div>
              <div><strong id="assistant-title">Yoru Assistant</strong><span>Commerce & home service guide</span></div>
              <button aria-label="Tutup assistant" className="icon-button" onClick={() => setAssistantOpen(false)} type="button">
                <Icon name="close" width="19" />
              </button>
            </div>

            <div className="assistant-messages" aria-live="polite">
              {messages.map((message) => (
                <div className={`assistant-message assistant-message--${message.role}`} key={message.id}>
                  {message.text}
                </div>
              ))}
              {assistantLoading ? (
                <div aria-label="Yoru Assistant sedang mengetik" className="assistant-typing" role="status">
                  <span className="skeleton-shimmer" />
                  <span className="skeleton-shimmer" />
                  <span className="skeleton-shimmer" />
                </div>
              ) : null}
            </div>

            <div className="assistant-quick-prompts">
              {quickPrompts.map((prompt) => (
                <button key={prompt} onClick={() => sendAssistant(prompt)} type="button">{prompt}</button>
              ))}
            </div>

            <form
              className="assistant-composer"
              onSubmit={(event) => {
                event.preventDefault();
                sendAssistant();
              }}
            >
              <textarea
                aria-label="Pesan untuk Yoru Assistant"
                onChange={(event) => setAssistantInput(event.target.value)}
                placeholder="Ceritakan kebutuhanmu..."
                rows={2}
                value={assistantInput}
              />
              <button aria-label="Kirim pesan" className="primary-button" disabled={!assistantInput.trim() || assistantLoading} type="submit">
                <Icon name="arrow" width="18" />
              </button>
            </form>
            <Link className="assistant-full-link" href="/assistant" onClick={() => setAssistantOpen(false)}>
              Buka advisor lengkap
              <Icon name="arrow" width="16" />
            </Link>
          </aside>
        </div>
      ) : null}
    </>
  );
}
