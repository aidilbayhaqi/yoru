import { StatusBadge } from "@yoru/ui";
import Link from "next/link";

import { getPublicApiBaseUrl } from "@/lib/config";

const capabilities = [
  {
    title: "Beauty commerce",
    body: "Skincare, fashion, dan aksesori styling dalam pengalaman belanja yang terkurasi.",
    status: "Planned",
  },
  {
    title: "Trusted home service",
    body: "Treatment, salon, barber, dan layanan profesional dengan verifikasi serta tracking.",
    status: "Planned",
  },
  {
    title: "AI customer advisor",
    body: "Rekomendasi berbasis kebutuhan dan budget, dengan consent serta safety guardrail.",
    status: "Design locked",
  },
];

export default function StorefrontHome() {
  const apiBaseUrl = getPublicApiBaseUrl();

  return (
    <main>
      <header className="site-header">
        <Link className="brand" href="/" aria-label="Yoru home">
          <span className="brand-mark">Y</span>
          <span>Yoru</span>
        </Link>
        <nav aria-label="Primary navigation">
          <a href="#foundation">Foundation</a>
          <a href="#architecture">Architecture</a>
          <Link href="/login">Masuk</Link>
        </nav>
        <StatusBadge label="Identity ready" tone="ready" />
      </header>

      <section className="hero" id="foundation">
        <div className="hero-copy">
          <p className="eyebrow">Beauty commerce · Home service · AI guidance</p>
          <h1>Fondasi Yoru siap untuk dibangun dengan benar.</h1>
          <p className="lead">
            Storefront ini sengaja belum menampilkan transaksi palsu. Sprint 1 menambahkan identity,
            session aman, dan tenant authorization sebelum fitur bisnis masuk.
          </p>
          <div className="hero-actions">
            <Link className="primary-action" href="/register">
              Buat akun customer
            </Link>
            <span className="quiet-label">API contract: {apiBaseUrl}</span>
          </div>
        </div>

        <aside className="foundation-card" aria-label="Foundation gate status">
          <p className="card-kicker">Foundation gate</p>
          <h2>Core before features</h2>
          <ul>
            <li>
              <span>01</span> Monorepo dan quality tooling
            </li>
            <li>
              <span>02</span> FastAPI, worker, migration
            </li>
            <li>
              <span>03</span> Health dan structured logs
            </li>
            <li>
              <span>04</span> CI, test, dan security baseline
            </li>
          </ul>
        </aside>
      </section>

      <section className="capabilities" aria-labelledby="capabilities-title">
        <div className="section-heading">
          <p className="eyebrow">Product direction</p>
          <h2 id="capabilities-title">Satu ekosistem, tiga pengalaman utama.</h2>
        </div>
        <div className="card-grid">
          {capabilities.map((capability, index) => (
            <article key={capability.title}>
              <span className="card-index">{String(index + 1).padStart(2, "0")}</span>
              <h3>{capability.title}</h3>
              <p>{capability.body}</p>
              <StatusBadge label={capability.status} />
            </article>
          ))}
        </div>
      </section>

      <section className="architecture" id="architecture" aria-labelledby="architecture-title">
        <div>
          <p className="eyebrow">System boundary</p>
          <h2 id="architecture-title">Teknologi punya peran yang tegas.</h2>
        </div>
        <dl>
          <div>
            <dt>Next.js</dt>
            <dd>Storefront dan console</dd>
          </div>
          <div>
            <dt>FastAPI</dt>
            <dd>Business rules dan API</dd>
          </div>
          <div>
            <dt>PostgreSQL</dt>
            <dd>System of record</dd>
          </div>
          <div>
            <dt>Redis</dt>
            <dd>Ephemeral state dan coordination</dd>
          </div>
          <div>
            <dt>Qdrant</dt>
            <dd>AI semantic retrieval</dd>
          </div>
        </dl>
      </section>

      <footer>
        <span>Yoru Engineering Foundation</span>
        <span>Version 0.2.1</span>
      </footer>
    </main>
  );
}
