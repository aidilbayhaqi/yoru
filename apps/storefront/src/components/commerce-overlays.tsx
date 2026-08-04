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

const searchModes: Array<{
  value: SearchMode;
  title: string;
  detail: string;
  icon: "search" | "wand" | "sparkle";
}> = [
  { value: "query", title: "Kata kunci", detail: "Cari langsung", icon: "search" },
  { value: "ai", title: "Dengan AI", detail: "Jelaskan kebutuhan", icon: "wand" },
  { value: "image", title: "Dengan gambar", detail: "Upload referensi", icon: "sparkle" },
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
    return "Mulai dari Barrier Cloud Moisturizer untuk rutinitas sederhana. Kalau kulit sedang sensitif, hindari menambah terlalu banyak active sekaligus.";
  }
  if (value.includes("facial") || value.includes("jakarta")) {
    return "Home Facial Reset tersedia untuk Jakarta Selatan, Jakarta Pusat, dan Depok. Cek alamat dan slot sebelum pembayaran supaya cakupan layanan tervalidasi.";
  }
  if (value.includes("hadiah") || value.includes("300")) {
    return "Everyday Satin Tote dan Glow Reset Serum masuk pilihan hadiah di bawah Rp300 ribu. Kamu bisa lanjutkan dengan preferensi warna atau kebutuhan penerima.";
  }
  if (value.includes("grooming") || value.includes("cepat")) {
    return "Men Grooming Home Visit berdurasi sekitar 60 menit. Waktu kedatangan tetap bergantung area, profesional, dan slot aktif.";
  }
  return "Aku bisa mempersempit pilihan berdasarkan kebutuhan, budget, area, waktu, dan preferensi. Harga, stok, serta slot final tetap diverifikasi sistem.";
}

export function CommerceOverlays() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const assistantEndRef = useRef<HTMLDivElement>(null);
  const assistantTimerRef = useRef<number | null>(null);
  const nextMessageIdRef = useRef(2);

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
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      id: 1,
      role: "assistant",
      text: "Hai, aku Yoru Assistant. Ceritakan kebutuhan, budget, area, atau jadwalmu—aku bantu menyaring pilihan yang relevan.",
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
    const locked = searchOpen;
    const previous = document.body.style.overflow;
    if (locked) document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [searchOpen]);

  useEffect(() => {
    assistantEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [assistantLoading, assistantOpen, messages]);

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
      ...products.slice(0, 4).map((product) => ({
        href: `/products/${product.slug}`,
        label: product.name,
        meta: `${product.category} · ${formatMoney(product.priceMinor)}`,
        kind: "Produk",
      })),
      ...services.slice(0, 3).map((service) => ({
        href: `/services/${service.slug}`,
        label: service.name,
        meta: `${service.category} · ${service.durationMin} menit`,
        kind: "Layanan",
      })),
    ];

    if (!debouncedQuery.trim()) return source.slice(0, 5);
    const normalized = debouncedQuery.toLowerCase();
    return source
      .filter((item) => `${item.label} ${item.meta} ${item.kind}`.toLowerCase().includes(normalized))
      .slice(0, 6);
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
          <span className="ai-fab__orb"><Icon name="sparkle" width="17" /></span>
          <span className="ai-fab__label"><strong>Yoru AI</strong><small>Tanya apa saja</small></span>
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
                <p className="section-eyebrow">Discovery</p>
                <h2 id="search-dialog-title">Apa yang sedang kamu cari?</h2>
                <p>Pilih cara pencarian yang paling nyaman.</p>
              </div>
              <button aria-label="Tutup pencarian" className="icon-button" onClick={closeSearch} type="button">
                <Icon name="close" width="20" />
              </button>
            </div>

            <div className="search-mode-tabs" role="tablist" aria-label="Mode pencarian">
              {searchModes.map((item) => (
                <button
                  aria-selected={mode === item.value}
                  className={mode === item.value ? "is-active" : ""}
                  key={item.value}
                  onClick={() => setMode(item.value)}
                  role="tab"
                  type="button"
                >
                  <Icon name={item.icon} width="18" />
                  <span><strong>{item.title}</strong><small>{item.detail}</small></span>
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
                        ? "Contoh: skincare simpel untuk barrier, budget maksimal Rp350 ribu"
                        : "Cari produk, kategori, partner, layanan, atau area"
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
                    AI membantu menyusun intent. Harga, stok, area, dan slot final tetap diverifikasi sistem.
                  </p>
                ) : null}

                <div className="search-suggestion-list">
                  <div className="search-suggestion-heading">
                    <span>{query.trim() ? "Hasil cepat" : "Pilihan populer"}</span>
                    <small>{suggestions.length} rekomendasi</small>
                  </div>
                  {suggestionsLoading ? (
                    <div aria-label="Mencari saran" className="search-suggestion-skeleton" role="status">
                      {Array.from({ length: 4 }, (_, index) => <span className="skeleton-shimmer" key={index} />)}
                    </div>
                  ) : suggestions.length > 0 ? suggestions.map((item) => (
                    <Link href={item.href} key={item.href} onClick={closeSearch}>
                      <span className="search-suggestion-icon"><Icon name="search" width="16" /></span>
                      <div><strong>{item.label}</strong><small>{item.kind} · {item.meta}</small></div>
                      <Icon name="arrow" width="16" />
                    </Link>
                  )) : (
                    <p className="search-no-suggestion">Tekan Cari untuk melihat hasil yang lebih luas.</p>
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
                      <span><Icon name="sparkle" width="25" /></span>
                      <strong>Upload foto referensi</strong>
                      <small>JPG, PNG, atau WEBP · maksimal 10 MB</small>
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
                  Preview membuat intent dari nama file dan kategori. Similarity production tetap membutuhkan image embedding API.
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
            className="assistant-drawer"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="assistant-heading">
              <div className="assistant-avatar"><Icon name="sparkle" width="20" /></div>
              <div className="assistant-heading__copy">
                <div><strong id="assistant-title">Yoru Assistant</strong><span className="assistant-presence">Online</span></div>
                <span>Belanja dan home service</span>
              </div>
              <button aria-label="Tutup assistant" className="icon-button" onClick={() => setAssistantOpen(false)} type="button">
                <Icon name="close" width="18" />
              </button>
            </div>

            <div className="assistant-context-bar">
              <span><Icon name="shield" width="15" /> Rekomendasi terarah</span>
              <button onClick={() => {
                setAssistantOpen(false);
                setMode("image");
                setSearchOpen(true);
              }} type="button">
                <Icon name="sparkle" width="15" /> Cari dengan gambar
              </button>
            </div>

            <div className="assistant-messages" aria-live="polite">
              {messages.map((message) => (
                <div className={`assistant-message-row assistant-message-row--${message.role}`} key={message.id}>
                  {message.role === "assistant" ? <span className="assistant-message-avatar"><Icon name="sparkle" width="14" /></span> : null}
                  <div className={`assistant-message assistant-message--${message.role}`}>{message.text}</div>
                </div>
              ))}
              {assistantLoading ? (
                <div className="assistant-message-row assistant-message-row--assistant">
                  <span className="assistant-message-avatar"><Icon name="sparkle" width="14" /></span>
                  <div aria-label="Yoru Assistant sedang mengetik" className="assistant-typing" role="status">
                    <span /><span /><span />
                  </div>
                </div>
              ) : null}
              <div ref={assistantEndRef} />
            </div>

            <div className="assistant-quick-prompts" aria-label="Pertanyaan cepat">
              {quickPrompts.map((prompt) => (
                <button disabled={assistantLoading} key={prompt} onClick={() => sendAssistant(prompt)} type="button">{prompt}</button>
              ))}
            </div>

            <div className="assistant-composer-shell">
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
                  placeholder="Tulis kebutuhanmu..."
                  rows={2}
                  value={assistantInput}
                />
                <button aria-label="Kirim pesan" className="primary-button" disabled={!assistantInput.trim() || assistantLoading} type="submit">
                  <Icon name="arrow" width="18" />
                </button>
              </form>
              <div className="assistant-footer-row">
                <span>AI dapat keliru. Verifikasi detail transaksi.</span>
                <Link href="/assistant" onClick={() => setAssistantOpen(false)}>Buka penuh <Icon name="arrow" width="14" /></Link>
              </div>
            </div>
          </aside>
        </div>
      ) : null}
    </>
  );
}
