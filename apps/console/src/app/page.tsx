import { StatusBadge } from "@yoru/ui";
import Link from "next/link";

import { getPublicApiBaseUrl } from "@/lib/config";

const services = [
  { name: "Storefront", owner: "Frontend", state: "Ready", tone: "ready" as const },
  { name: "Console", owner: "Frontend", state: "Ready", tone: "ready" as const },
  { name: "FastAPI", owner: "Backend", state: "Ready", tone: "ready" as const },
  { name: "Worker", owner: "Backend", state: "Ready", tone: "ready" as const },
  { name: "Authentication", owner: "Platform", state: "Ready", tone: "ready" as const },
  { name: "Commerce", owner: "Product", state: "Blocked by gate", tone: "blocked" as const },
];

const gates = [
  "Environment validation",
  "Migration baseline",
  "Request correlation",
  "Structured logging",
  "Automated tests",
  "CI and dependency review",
];

export default function ConsoleHome() {
  const apiBaseUrl = getPublicApiBaseUrl();

  return (
    <main className="console-shell">
      <aside className="sidebar">
        <div className="logo">
          <span>Y</span>
          <strong>Yoru</strong>
        </div>
        <p className="sidebar-label">Engineering</p>
        <nav aria-label="Console navigation">
          <a className="active" href="#overview">
            Overview
          </a>
          <a href="#services">Services</a>
          <a href="#gates">Quality gates</a>
          <Link href="/login">Sign in</Link>
        </nav>
        <div className="sidebar-footer">
          <StatusBadge label="Identity foundation" tone="ready" />
          <p>Business modules remain locked until authorization acceptance passes.</p>
        </div>
      </aside>

      <section className="workspace" id="overview">
        <header className="topbar">
          <div>
            <p>Yoru Platform</p>
            <h1>Engineering foundation</h1>
          </div>
          <div className="environment">
            <span className="status-dot" aria-hidden="true" />
            Local environment
          </div>
        </header>

        <div className="overview-grid">
          <article className="headline-card">
            <p className="kicker">Sprint 1</p>
            <h2>Identity and tenant control before business complexity.</h2>
            <p>
              Opaque session, capability, partner membership, audit, dan PostgreSQL RLS kini menjadi
              fondasi console.
            </p>
            <code>{apiBaseUrl}</code>
          </article>

          <article className="metric-card">
            <span>Foundation services</span>
            <strong>7</strong>
            <p>2 web apps · API · worker · PostgreSQL · Redis · Qdrant</p>
          </article>

          <article className="metric-card">
            <span>Tenant model</span>
            <strong>1</strong>
            <p>`partner_id` menjadi boundary lintas data plane pada Sprint 1.</p>
          </article>
        </div>

        <section className="panel" id="services" aria-labelledby="services-title">
          <div className="panel-heading">
            <div>
              <p className="kicker">Platform map</p>
              <h2 id="services-title">Service readiness</h2>
            </div>
            <StatusBadge label="No mock business data" tone="planned" />
          </div>
          <div className="service-table" role="table" aria-label="Platform service readiness">
            <div className="table-row table-header" role="row">
              <span role="columnheader">Service</span>
              <span role="columnheader">Owner</span>
              <span role="columnheader">State</span>
            </div>
            {services.map((service) => (
              <div className="table-row" role="row" key={service.name}>
                <strong role="cell">{service.name}</strong>
                <span role="cell">{service.owner}</span>
                <span role="cell">
                  <StatusBadge label={service.state} tone={service.tone} />
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel" id="gates" aria-labelledby="gates-title">
          <div className="panel-heading">
            <div>
              <p className="kicker">Release policy</p>
              <h2 id="gates-title">Foundation gates</h2>
            </div>
          </div>
          <ol className="gate-list">
            {gates.map((gate, index) => (
              <li key={gate}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{gate}</strong>
                <StatusBadge label="Implemented" tone="ready" />
              </li>
            ))}
          </ol>
        </section>
      </section>
    </main>
  );
}
