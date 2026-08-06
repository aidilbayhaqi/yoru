"use client";

import type { AuthSession } from "@yoru/contracts";
import { useRouter } from "next/navigation";
import type { ChangeEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { CatalogManager } from "@/components/catalog-manager";
import { CatalogModeration } from "@/components/catalog-moderation";
import { ApiError, apiRequest } from "@/lib/api";
import { activePartnerMembership, eligiblePartnerMemberships } from "@/lib/console-auth";
import {
  auditEvents,
  bookingSchedule,
  financeBalances,
  formatCompact,
  formatCurrency,
  navigationForRole,
  partnerDirectory,
  partnerMetrics,
  partnerOrders,
  partnerRevenueSeries,
  platformMetrics,
  platformRevenueSeries,
  platformTransactions,
  resolveConsoleRole,
  sectionBelongsToRole,
  sectionLabel,
  verificationQueue,
  type ConsoleRole,
  type DashboardSection,
  type IconName,
} from "@/lib/console-dashboard";

import styles from "./operations-dashboard.module.css";

function Icon({
  name,
  size = 18,
}: {
  name:
    | IconName
    | "search"
    | "bell"
    | "plus"
    | "chevron"
    | "menu"
    | "trend"
    | "more"
    | "close"
    | "check"
    | "download";
  size?: number;
}) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  const paths: Record<string, ReactNode> = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="2" />
        <rect x="14" y="3" width="7" height="7" rx="2" />
        <rect x="3" y="14" width="7" height="7" rx="2" />
        <rect x="14" y="14" width="7" height="7" rx="2" />
      </>
    ),
    box: (
      <>
        <path d="m21 8-9 5-9-5" />
        <path d="m3 8 9-5 9 5v8l-9 5-9-5Z" />
        <path d="M12 13v8" />
      </>
    ),
    layers: (
      <>
        <path d="m12 2 9 5-9 5-9-5 9-5Z" />
        <path d="m3 12 9 5 9-5" />
        <path d="m3 17 9 5 9-5" />
      </>
    ),
    receipt: (
      <>
        <path d="M6 2h12v20l-3-2-3 2-3-2-3 2V2Z" />
        <path d="M9 7h6M9 11h6M9 15h3" />
      </>
    ),
    calendar: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M16 3v4M8 3v4M3 10h18" />
      </>
    ),
    users: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
      </>
    ),
    wallet: (
      <>
        <path d="M20 7V5a2 2 0 0 0-2-2H5a3 3 0 0 0 0 6h15v12H5a3 3 0 0 1-3-3V6" />
        <path d="M16 13h4" />
      </>
    ),
    sparkles: (
      <>
        <path d="m12 3-1.4 3.6L7 8l3.6 1.4L12 13l1.4-3.6L17 8l-3.6-1.4L12 3Z" />
        <path d="m5 14-.8 2.2L2 17l2.2.8L5 20l.8-2.2L8 17l-2.2-.8L5 14ZM19 13l-.7 1.8-1.8.7 1.8.7L19 18l.7-1.8 1.8-.7-1.8-.7L19 13Z" />
      </>
    ),
    shield: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    store: (
      <>
        <path d="M3 9l2-6h14l2 6" />
        <path d="M5 13v8h14v-8" />
        <path d="M9 21v-6h6v6" />
        <path d="M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0" />
      </>
    ),
    activity: (
      <>
        <path d="M3 12h4l2-7 4 14 2-7h6" />
      </>
    ),
    bank: (
      <>
        <path d="m3 10 9-7 9 7" />
        <path d="M5 10v8M9 10v8M15 10v8M19 10v8M3 21h18M2 18h20" />
      </>
    ),
    alert: (
      <>
        <path d="M10.3 3.6 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.6a2 2 0 0 0-3.4 0Z" />
        <path d="M12 9v4M12 17h.01" />
      </>
    ),
    brain: (
      <>
        <path d="M9.5 4A2.5 2.5 0 0 0 7 6.5v.2A3 3 0 0 0 5 12a3 3 0 0 0 2 5.3v.2A2.5 2.5 0 0 0 11.5 19V5.5A1.5 1.5 0 0 0 10 4h-.5ZM14.5 4A2.5 2.5 0 0 1 17 6.5v.2a3 3 0 0 1 2 5.3 3 3 0 0 1-2 5.3v.2A2.5 2.5 0 0 1 12.5 19V5.5A1.5 1.5 0 0 1 14 4h.5Z" />
        <path d="M7 9.5h2M15 9.5h2M7 15h2M15 15h2" />
      </>
    ),
    lock: (
      <>
        <rect x="4" y="10" width="16" height="11" rx="2" />
        <path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" />
      </>
    ),
    history: (
      <>
        <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
        <path d="M3 3v5h5M12 7v5l3 2" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
      </>
    ),
    bell: (
      <>
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
      </>
    ),
    plus: (
      <>
        <path d="M12 5v14M5 12h14" />
      </>
    ),
    chevron: <path d="m9 18 6-6-6-6" />,
    menu: (
      <>
        <path d="M4 6h16M4 12h16M4 18h16" />
      </>
    ),
    trend: (
      <>
        <path d="m3 17 6-6 4 4 8-9" />
        <path d="M15 6h6v6" />
      </>
    ),
    more: (
      <>
        <circle cx="5" cy="12" r="1" fill="currentColor" stroke="none" />
        <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
        <circle cx="19" cy="12" r="1" fill="currentColor" stroke="none" />
      </>
    ),
    close: (
      <>
        <path d="M18 6 6 18M6 6l12 12" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    download: (
      <>
        <path d="M12 3v12M7 10l5 5 5-5M5 21h14" />
      </>
    ),
  };
  return <svg {...common}>{paths[name]}</svg>;
}

function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}) {
  return <span className={`${styles.badge} ${styles[`badge_${tone}`]}`}>{children}</span>;
}

function StatusBadge({ value }: { value: string }) {
  const lower = value.toLowerCase();
  const tone =
    lower.includes("healthy") ||
    lower.includes("selesai") ||
    lower.includes("settled") ||
    lower.includes("published") ||
    lower.includes("confirmed")
      ? "success"
      : lower.includes("risk") ||
          lower.includes("high") ||
          lower.includes("review") ||
          lower.includes("low stock")
        ? "danger"
        : lower.includes("pending") || lower.includes("menunggu") || lower.includes("requested")
          ? "warning"
          : "info";
  return <Badge tone={tone}>{value}</Badge>;
}

function TrendChart({ values, label }: { values: number[]; label: string }) {
  const width = 720;
  const height = 220;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / Math.max(max - min, 1)) * (height - 36) - 18;
      return `${x},${y}`;
    })
    .join(" ");
  const area = `0,${height} ${points} ${width},${height}`;
  return (
    <div className={styles.chartWrap} aria-label={label} role="img">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="areaGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.23" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[40, 90, 140, 190].map((y) => (
          <line key={y} x1="0" x2={width} y1={y} y2={y} className={styles.chartGrid} />
        ))}
        <polygon points={area} fill="url(#areaGradient)" className={styles.chartArea} />
        <polyline points={points} className={styles.chartLine} />
      </svg>
      <div className={styles.chartLabels}>
        {["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"].map(
          (month) => (
            <span key={month}>{month}</span>
          ),
        )}
      </div>
    </div>
  );
}

function MetricCards({ role }: { role: ConsoleRole }) {
  const data = role === "superadmin" ? platformMetrics : partnerMetrics;
  return (
    <section className={styles.metricGrid}>
      {data.map((item, index) => (
        <article className={styles.metricCard} key={item.label}>
          <div className={styles.metricHeader}>
            <span>{item.label}</span>
            <span className={styles.metricIndex}>0{index + 1}</span>
          </div>
          <strong>
            {item.kind === "currency" ? formatCurrency(item.value) : formatCompact(item.value)}
          </strong>
          <div className={`${styles.delta} ${item.delta < 0 ? styles.deltaDown : ""}`}>
            <Icon name="trend" size={15} />
            {Math.abs(item.delta)}% <span>vs bulan lalu</span>
          </div>
        </article>
      ))}
    </section>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon}>
        <Icon name="layers" size={22} />
      </div>
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}

export function OperationsDashboard() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [error, setError] = useState("");
  const [role, setRole] = useState<ConsoleRole | null>(null);
  const [section, setSection] = useState<DashboardSection>("overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    let active = true;
    apiRequest<AuthSession>("/auth/me")
      .then((value) => {
        if (!active) return;
        try {
          const resolvedRole = resolveConsoleRole(value);
          setSession(value);
          setRole(resolvedRole);
        } catch {
          setError("Akun ini tidak memiliki role partner aktif atau super_admin.");
        }
      })
      .catch((reason) => {
        if (reason instanceof ApiError && reason.status === 401) {
          router.replace("/login");
          return;
        }
        setError("Identity context belum dapat dimuat.");
      });
    return () => {
      active = false;
    };
  }, [router]);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(""), 2600);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const navigation = useMemo(() => (role ? navigationForRole(role) : []), [role]);
  const partnerMemberships = useMemo(
    () => (session ? eligiblePartnerMemberships(session) : []),
    [session],
  );
  const activeMembership = session ? activePartnerMembership(session) : null;

  async function selectPartner(partnerId: string) {
    const value = await apiRequest<AuthSession>("/auth/active-partner", {
      method: "PATCH",
      body: JSON.stringify({ partner_id: partnerId }),
    });
    setSession(value);
    setToast("Workspace partner berhasil diganti.");
  }

  async function logout() {
    await apiRequest<{ message: string }>("/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  function navigate(next: DashboardSection) {
    if (!role || !sectionBelongsToRole(role, next)) {
      setToast("Akses ditolak oleh RBAC. Section ini bukan milik role Anda.");
      return;
    }
    setSection(next);
    setSidebarOpen(false);
  }

  if (error)
    return (
      <main className={styles.loadingState}>
        <div>
          <h1>Akses tidak tersedia</h1>
          <p>{error}</p>
        </div>
      </main>
    );
  if (!session || !role)
    return (
      <main className={styles.loadingState}>
        <div className={styles.loader} />
        <p>Memuat Yoru Operations...</p>
      </main>
    );

  const pageTitle = sectionLabel(role, section);

  return (
    <div className={styles.shell}>
      <aside className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ""}`}>
        <div className={styles.brand}>
          <div className={styles.brandMark}>Y</div>
          <div>
            <strong>Yoru</strong>
            <span>Commerce & Service OS</span>
          </div>
          <button
            className={styles.mobileClose}
            onClick={() => setSidebarOpen(false)}
            type="button"
          >
            <Icon name="close" />
          </button>
        </div>
        <div className={styles.workspaceCard}>
          <span className={styles.workspaceLabel}>
            {role === "superadmin" ? "Platform workspace" : "Partner workspace"}
          </span>
          <div className={styles.workspaceValue}>
            <div className={styles.avatarSmall}>
              {role === "superadmin"
                ? "YO"
                : (activeMembership?.role?.slice(0, 2).toUpperCase() ?? "PT")}
            </div>
            <div>
              <strong>
                {role === "superadmin"
                  ? "Yoru Indonesia"
                  : activeMembership
                    ? `Partner ${activeMembership.partner_id.slice(0, 8)}`
                    : "Partner workspace"}
              </strong>
              <span>
                {role === "superadmin"
                  ? "Production control"
                  : (activeMembership?.partner_status ?? "Verified partner")}
              </span>
            </div>
            <Icon name="chevron" size={14} />
          </div>
          {role === "partner" && partnerMemberships.length > 1 ? (
            <select
              value={activeMembership?.partner_id ?? partnerMemberships[0]?.partner_id}
              onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                selectPartner(event.target.value)
              }
            >
              {partnerMemberships.map((membership) => (
                <option key={membership.partner_id} value={membership.partner_id}>
                  {membership.role} · {membership.partner_status}
                </option>
              ))}
            </select>
          ) : null}
        </div>
        <nav className={styles.navigation} aria-label="Navigasi utama">
          {navigation.map((group) => (
            <div className={styles.navGroup} key={group.label}>
              <span className={styles.navLabel}>{group.label}</span>
              {group.items.map((item) => (
                <button
                  className={`${styles.navItem} ${section === item.id ? styles.navItemActive : ""}`}
                  key={item.id}
                  onClick={() => navigate(item.id)}
                  type="button"
                >
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                  {item.badge ? <em>{item.badge}</em> : null}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className={styles.systemCard}>
          <div>
            <span className={styles.liveDot} />
            <strong>All systems operational</strong>
          </div>
          <span>API · Worker · Database</span>
        </div>
        <div className={styles.sidebarUser}>
          <div className={styles.userAvatar}>
            {session.user.full_name
              .split(" ")
              .map((part) => part[0])
              .slice(0, 2)
              .join("")}
          </div>
          <div>
            <strong>{session.user.full_name}</strong>
            <span>{role === "superadmin" ? "Super Admin" : "Partner Operator"}</span>
          </div>
          <button onClick={logout} title="Keluar" type="button">
            <Icon name="chevron" />
          </button>
        </div>
      </aside>
      {sidebarOpen ? (
        <button
          className={styles.backdrop}
          onClick={() => setSidebarOpen(false)}
          type="button"
          aria-label="Tutup navigasi"
        />
      ) : null}

      <main className={styles.main}>
        <header className={styles.topbar}>
          <div className={styles.topbarLeft}>
            <button
              className={styles.menuButton}
              onClick={() => setSidebarOpen(true)}
              type="button"
            >
              <Icon name="menu" />
            </button>
            <div className={styles.breadcrumb}>
              <span>{role === "superadmin" ? "Platform" : "Kemitraan"}</span>
              <Icon name="chevron" size={13} />
              <strong>{pageTitle}</strong>
            </div>
          </div>
          <div className={styles.topbarActions}>
            <label className={styles.searchBox}>
              <Icon name="search" size={17} />
              <input
                placeholder="Cari order, booking, partner..."
                value={search}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setSearch(event.target.value)}
              />
              <kbd>⌘ K</kbd>
            </label>
            <span className={styles.rolePill}>
              {role === "superadmin" ? "Super Admin" : "Kemitraan"}
            </span>
            <button className={styles.iconButton} type="button">
              <Icon name="bell" />
              <span className={styles.notificationDot} />
            </button>
            <button
              className={styles.primaryButton}
              onClick={() =>
                role === "partner" ? navigate("products") : navigate("partner-verification")
              }
              type="button"
            >
              <Icon name="plus" size={17} />
              {role === "partner" ? "Kelola katalog" : "Review partner"}
            </button>
          </div>
        </header>

        <div className={styles.content}>
          <section className={styles.pageHeader}>
            <div>
              <span className={styles.eyebrow}>
                {role === "superadmin" ? "PLATFORM COMMAND CENTER" : "PARTNER OPERATING SYSTEM"}
              </span>
              <h1>{pageTitle}</h1>
              <p>
                {role === "superadmin"
                  ? "Kendalikan pertumbuhan, risiko, transaksi, dan operasional seluruh ekosistem Yoru."
                  : "Kelola commerce, home service, tim lapangan, dan arus kas dalam satu workspace."}
              </p>
              {role === "superadmin" ? (
                <span className={styles.demoBadge}>Demo dataset · khusus development</span>
              ) : null}
            </div>
            <div className={styles.headerMeta}>
              <span>Data diperbarui</span>
              <strong>Baru saja</strong>
              <button type="button">
                <Icon name="download" size={16} /> Export
              </button>
            </div>
          </section>

          {section === "overview" ? <Overview role={role} /> : null}
          {role === "partner" && section === "products" ? (
            <CatalogManager view="products" onMessage={setToast} />
          ) : null}
          {role === "partner" && section === "inventory" ? (
            <CatalogManager view="inventory" onMessage={setToast} />
          ) : null}
          {role === "partner" && section === "orders" ? <Orders /> : null}
          {role === "partner" && section === "bookings" ? <Bookings /> : null}
          {role === "partner" && section === "professionals" ? <Professionals /> : null}
          {role === "partner" && section === "finance" ? <PartnerFinance /> : null}
          {role === "partner" && section === "copilot" ? <Copilot /> : null}
          {role === "superadmin" && section === "partner-verification" ? <Verification /> : null}
          {role === "superadmin" && section === "partners" ? <Partners /> : null}
          {role === "superadmin" && section === "transactions" ? <Transactions /> : null}
          {role === "superadmin" && section === "operations" ? (
            <>
              <PlatformOperations />
              <CatalogModeration onMessage={setToast} />
            </>
          ) : null}
          {role === "superadmin" && section === "ledger" ? <PlatformFinance /> : null}
          {role === "superadmin" && section === "risk" ? <Risk /> : null}
          {role === "superadmin" && section === "ai-governance" ? <AIGovernance /> : null}
          {role === "superadmin" && section === "security" ? <SecurityOps /> : null}
          {role === "superadmin" && section === "audit" ? <AuditLog /> : null}
        </div>
      </main>

      {toast ? (
        <div className={styles.toast}>
          <div>
            <Icon name="check" size={17} />
          </div>
          <span>{toast}</span>
        </div>
      ) : null}
    </div>
  );
}

function Overview({ role }: { role: ConsoleRole }) {
  const series = role === "superadmin" ? platformRevenueSeries : partnerRevenueSeries;
  return (
    <>
      <MetricCards role={role} />
      <section className={styles.dashboardGrid}>
        <article className={`${styles.panel} ${styles.chartPanel}`}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.panelEyebrow}>
                {role === "superadmin" ? "PLATFORM GROWTH" : "REVENUE PERFORMANCE"}
              </span>
              <h2>{role === "superadmin" ? "GMV & net revenue" : "Pendapatan dan transaksi"}</h2>
            </div>
            <select aria-label="Rentang waktu">
              <option>12 bulan</option>
              <option>30 hari</option>
              <option>7 hari</option>
            </select>
          </div>
          <div className={styles.chartSummary}>
            <strong>
              {role === "superadmin" ? formatCurrency(4_860_000_000) : formatCurrency(186_450_000)}
            </strong>
            <Badge tone="success">+{role === "superadmin" ? "18.7" : "12.4"}%</Badge>
          </div>
          <TrendChart values={series} label="Grafik performa 12 bulan" />
        </article>
        <article className={`${styles.panel} ${styles.sidePanel}`}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.panelEyebrow}>PRIORITY QUEUE</span>
              <h2>Butuh perhatian</h2>
            </div>
            <button type="button">
              <Icon name="more" />
            </button>
          </div>
          {role === "superadmin" ? (
            <div className={styles.taskList}>
              <Task
                title="17 partner menunggu verifikasi"
                meta="SLA terlama 3 jam 24 menit"
                tone="warning"
              />
              <Task
                title="4 dispute bernilai tinggi"
                meta="Total exposure Rp18,4 juta"
                tone="danger"
              />
              <Task
                title="2 layanan mengalami error spike"
                meta="Payment webhook dan tracking"
                tone="danger"
              />
              <Task
                title="Launch gate perlu evaluasi"
                meta="Backup drill belum diperbarui"
                tone="info"
              />
            </div>
          ) : (
            <div className={styles.taskList}>
              <Task
                title="8 SKU mendekati habis"
                meta="Potensi kehilangan 14 order"
                tone="warning"
              />
              <Task title="5 booking belum diassign" meta="Jadwal hari ini" tone="danger" />
              <Task title="Payout siap diajukan" meta="Saldo tersedia Rp74,8 juta" tone="success" />
              <Task title="Rating layanan turun 0,2" meta="Deep Cleaning Premium" tone="info" />
            </div>
          )}
        </article>
      </section>
      <section className={styles.dashboardGrid}>
        <article className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.panelEyebrow}>
                {role === "superadmin" ? "MARKETPLACE ACTIVITY" : "RECENT ORDERS"}
              </span>
              <h2>{role === "superadmin" ? "Transaksi terbaru" : "Pesanan terbaru"}</h2>
            </div>
            <button className={styles.textButton} type="button">
              Lihat semua <Icon name="chevron" size={14} />
            </button>
          </div>
          {role === "superadmin" ? <TransactionTable /> : <OrderTable />}
        </article>
        <article className={`${styles.panel} ${styles.sidePanel}`}>
          <div className={styles.aiCard}>
            <div className={styles.aiIcon}>
              <Icon name="sparkles" size={20} />
            </div>
            <span className={styles.panelEyebrow}>
              {role === "superadmin" ? "YORU INTELLIGENCE" : "PARTNER COPILOT"}
            </span>
            <h2>
              {role === "superadmin"
                ? "Platform tumbuh sehat, tetapi dispute meningkat."
                : "Ada peluang tambahan omzet Rp12,8 juta."}
            </h2>
            <p>
              {role === "superadmin"
                ? "Dispute naik 21% pada kategori beauty. Fokuskan review pada partner dengan fulfillment di bawah 85%."
                : "Tambahkan kapasitas Deep Cleaning pada Jumat–Minggu dan naikkan safety stock filter HEPA menjadi 12 unit."}
            </p>
            <button type="button">
              Buka analisis lengkap <Icon name="chevron" size={14} />
            </button>
          </div>
        </article>
      </section>
    </>
  );
}

function Task({
  title,
  meta,
  tone,
}: {
  title: string;
  meta: string;
  tone: "warning" | "danger" | "success" | "info";
}) {
  return (
    <div className={styles.task}>
      <span className={`${styles.taskDot} ${styles[`taskDot_${tone}`]}`} />
      <div>
        <strong>{title}</strong>
        <span>{meta}</span>
      </div>
      <Icon name="chevron" size={14} />
    </div>
  );
}

function Orders() {
  return (
    <section className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <span className={styles.panelEyebrow}>ORDER MANAGEMENT</span>
          <h2>Order fulfillment</h2>
        </div>
        <div className={styles.segmented}>
          <button className={styles.segmentActive} type="button">
            Semua
          </button>
          <button type="button">Menunggu</button>
          <button type="button">Diproses</button>
          <button type="button">Selesai</button>
        </div>
      </div>
      <OrderTable />
    </section>
  );
}
function Bookings() {
  return (
    <section className={styles.dashboardGrid}>
      <article className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.panelEyebrow}>TODAY’S OPERATIONS</span>
            <h2>Jadwal booking hari ini</h2>
          </div>
          <button className={styles.primaryButton} type="button">
            Tambah booking
          </button>
        </div>
        <div className={styles.schedule}>
          {bookingSchedule.map((booking) => (
            <div className={styles.scheduleRow} key={`${booking.time}-${booking.customer}`}>
              <time>{booking.time}</time>
              <div className={styles.scheduleLine}>
                <span />
              </div>
              <div>
                <strong>{booking.customer}</strong>
                <span>
                  {booking.service} · {booking.professional}
                </span>
              </div>
              <StatusBadge value={booking.status} />
              <button type="button">
                <Icon name="more" />
              </button>
            </div>
          ))}
        </div>
      </article>
      <article className={`${styles.panel} ${styles.sidePanel}`}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.panelEyebrow}>FIELD TEAM</span>
            <h2>Operasional lapangan</h2>
          </div>
        </div>
        <div className={styles.radarCard}>
          <div className={styles.radar}>
            <span />
            <i />
            <b />
          </div>
          <strong>3 profesional aktif</strong>
          <span>2 on the way · 1 in progress</span>
        </div>
        <div className={styles.taskList}>
          <Task title="OTP check-in menunggu" meta="BK-72118 · Raka" tone="warning" />
          <Task title="Tracking aktif" meta="BK-72112 · 18 menit" tone="success" />
          <Task title="Potensi keterlambatan" meta="BK-72122 · ETA +14 menit" tone="danger" />
        </div>
      </article>
    </section>
  );
}
function Professionals() {
  const people = [
    { name: "Raka Aditya", role: "Cleaning specialist", jobs: 48, rating: 4.9, status: "On duty" },
    {
      name: "Alya Prameswari",
      role: "Home care specialist",
      jobs: 41,
      rating: 4.8,
      status: "Available",
    },
    { name: "Dimas Nugraha", role: "AC technician", jobs: 37, rating: 4.9, status: "On duty" },
    {
      name: "Sari Wulandari",
      role: "Quality supervisor",
      jobs: 29,
      rating: 4.7,
      status: "Off duty",
    },
  ];
  return (
    <section className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <span className={styles.panelEyebrow}>WORKFORCE MANAGEMENT</span>
          <h2>Tim profesional</h2>
        </div>
        <button className={styles.primaryButton} type="button">
          <Icon name="plus" size={16} /> Tambah anggota
        </button>
      </div>
      <div className={styles.peopleGrid}>
        {people.map((person) => (
          <article key={person.name}>
            <div className={styles.personAvatar}>
              {person.name
                .split(" ")
                .map((value) => value[0])
                .join("")}
            </div>
            <div>
              <strong>{person.name}</strong>
              <span>{person.role}</span>
            </div>
            <dl>
              <div>
                <dt>Job selesai</dt>
                <dd>{person.jobs}</dd>
              </div>
              <div>
                <dt>Rating</dt>
                <dd>{person.rating}</dd>
              </div>
            </dl>
            <StatusBadge value={person.status} />
          </article>
        ))}
      </div>
    </section>
  );
}
function PartnerFinance() {
  return (
    <>
      <section className={styles.financeGrid}>
        {financeBalances.map((item) => (
          <article key={item.label}>
            <span>{item.label}</span>
            <strong>{formatCurrency(item.value)}</strong>
            <button type="button">
              Lihat detail <Icon name="chevron" size={13} />
            </button>
          </article>
        ))}
      </section>
      <section className={styles.dashboardGrid}>
        <article className={`${styles.panel} ${styles.chartPanel}`}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.panelEyebrow}>CASHFLOW</span>
              <h2>Arus masuk dan payout</h2>
            </div>
            <select>
              <option>12 bulan</option>
            </select>
          </div>
          <TrendChart values={partnerRevenueSeries} label="Grafik cashflow" />
        </article>
        <article className={`${styles.panel} ${styles.sidePanel}`}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.panelEyebrow}>NEXT PAYOUT</span>
              <h2>Jadwal pencairan</h2>
            </div>
          </div>
          <div className={styles.payoutCard}>
            <span>Estimasi cair</span>
            <strong>{formatCurrency(24_850_000)}</strong>
            <p>Senin, 10 Agustus 2026</p>
            <button className={styles.primaryButton} type="button">
              Ajukan payout
            </button>
          </div>
        </article>
      </section>
    </>
  );
}
function Copilot() {
  return (
    <section className={styles.copilotLayout}>
      <article className={styles.copilotHero}>
        <div className={styles.aiIcon}>
          <Icon name="sparkles" size={22} />
        </div>
        <span className={styles.eyebrow}>PARTNER COPILOT</span>
        <h1>Apa yang ingin kamu pahami dari bisnismu hari ini?</h1>
        <p>
          Copilot menggunakan data order, booking, inventory, dan ledger milik tenant aktif untuk
          memberikan jawaban berbasis bukti.
        </p>
        <div className={styles.copilotInput}>
          <input placeholder="Contoh: Kenapa booking saya turun minggu ini?" />
          <button type="button">
            Analisis <Icon name="chevron" size={14} />
          </button>
        </div>
      </article>
      <div className={styles.insightGrid}>
        <Insight
          title="Potensi revenue"
          value="Rp12,8 jt"
          body="Tambahkan 6 slot akhir pekan untuk layanan Deep Cleaning."
        />
        <Insight
          title="Inventory risk"
          value="3 SKU"
          body="Restock sebelum Jumat untuk mencegah potensi lost order."
        />
        <Insight
          title="Customer quality"
          value="4.82"
          body="Rating stabil, tetapi response time meningkat 18 menit."
        />
      </div>
    </section>
  );
}
function Insight({ title, value, body }: { title: string; value: string; body: string }) {
  return (
    <article className={styles.insightCard}>
      <span>{title}</span>
      <strong>{value}</strong>
      <p>{body}</p>
      <button type="button">
        Lihat evidence <Icon name="chevron" size={13} />
      </button>
    </article>
  );
}

function Verification() {
  return (
    <section className={styles.panel}>
      <div className={styles.tableToolbar}>
        <div>
          <span className={styles.panelEyebrow}>PARTNER ONBOARDING</span>
          <h2>17 aplikasi menunggu review</h2>
        </div>
        <div>
          <button className={styles.secondaryButton} type="button">
            Atur SLA
          </button>
          <button className={styles.primaryButton} type="button">
            Mulai review berikutnya
          </button>
        </div>
      </div>
      <div className={styles.tableWrap}>
        <table>
          <thead>
            <tr>
              <th>Partner</th>
              <th>Tipe bisnis</th>
              <th>Dikirim</th>
              <th>Kelengkapan</th>
              <th>Risk</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {verificationQueue.map((item) => (
              <tr key={item.partner}>
                <td>
                  <div className={styles.productCell}>
                    <div className={styles.productThumb}>
                      {item.partner.slice(0, 2).toUpperCase()}
                    </div>
                    <strong>{item.partner}</strong>
                  </div>
                </td>
                <td>{item.type}</td>
                <td>{item.submitted}</td>
                <td>
                  <div className={styles.progressCell}>
                    <span>
                      <i style={{ width: `${item.completeness}%` }} />
                    </span>
                    <strong>{item.completeness}%</strong>
                  </div>
                </td>
                <td>
                  <StatusBadge value={item.risk} />
                </td>
                <td>
                  <button className={styles.rowPrimary} type="button">
                    Review
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
function Partners() {
  return (
    <section className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <span className={styles.panelEyebrow}>PARTNER DIRECTORY</span>
          <h2>284 partner aktif</h2>
        </div>
        <button className={styles.secondaryButton} type="button">
          <Icon name="download" size={15} /> Export directory
        </button>
      </div>
      <div className={styles.tableWrap}>
        <table>
          <thead>
            <tr>
              <th>Partner</th>
              <th>Kategori</th>
              <th>GMV MTD</th>
              <th>Order</th>
              <th>Health score</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {partnerDirectory.map((partner) => (
              <tr key={partner.name}>
                <td>
                  <strong>{partner.name}</strong>
                </td>
                <td>{partner.category}</td>
                <td>{formatCurrency(partner.gmv)}</td>
                <td>{partner.orders}</td>
                <td>
                  <div className={styles.score}>
                    <strong>{partner.health}</strong>
                    <span>
                      <i style={{ width: `${partner.health}%` }} />
                    </span>
                  </div>
                </td>
                <td>
                  <StatusBadge value={partner.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
function Transactions() {
  return (
    <section className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <span className={styles.panelEyebrow}>TRANSACTION MONITOR</span>
          <h2>Order dan payment real-time</h2>
        </div>
        <div className={styles.liveStatus}>
          <span className={styles.liveDot} /> Live feed
        </div>
      </div>
      <TransactionTable />
    </section>
  );
}
function PlatformOperations() {
  return (
    <>
      <section className={styles.metricGrid}>
        <article className={styles.metricCard}>
          <span>Booking aktif</span>
          <strong>482</strong>
          <p>Across 129 partner</p>
        </article>
        <article className={styles.metricCard}>
          <span>On the way</span>
          <strong>117</strong>
          <p>Tracking session aktif</p>
        </article>
        <article className={styles.metricCard}>
          <span>SLA at risk</span>
          <strong>23</strong>
          <p>Butuh intervensi ops</p>
        </article>
        <article className={styles.metricCard}>
          <span>Completion rate</span>
          <strong>94.8%</strong>
          <p>30 hari terakhir</p>
        </article>
      </section>
      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.panelEyebrow}>OPERATIONS MAP</span>
            <h2>Home-service command center</h2>
          </div>
        </div>
        <div className={styles.opsMap}>
          <div className={styles.mapGrid} />
          {["Jakarta Pusat", "Jakarta Selatan", "Tangerang", "Bekasi"].map((area, index) => (
            <div
              className={styles.mapNode}
              key={area}
              style={{ left: `${18 + index * 21}%`, top: `${28 + (index % 2) * 30}%` }}
            >
              <span>{32 + index * 17}</span>
              <strong>{area}</strong>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
function PlatformFinance() {
  return (
    <>
      <section className={styles.financeGrid}>
        <article>
          <span>Clearing balance</span>
          <strong>{formatCurrency(286_450_000)}</strong>
          <button type="button">Reconcile</button>
        </article>
        <article>
          <span>Pending payout</span>
          <strong>{formatCurrency(142_800_000)}</strong>
          <button type="button">Review queue</button>
        </article>
        <article>
          <span>Platform commission</span>
          <strong>{formatCurrency(486_000_000)}</strong>
          <button type="button">View journal</button>
        </article>
        <article>
          <span>Ledger health</span>
          <strong>Balanced</strong>
          <button type="button">Run check</button>
        </article>
      </section>
      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.panelEyebrow}>PAYOUT CONTROL</span>
            <h2>Approval queue</h2>
          </div>
        </div>
        <EmptyState
          title="Semua payout prioritas sudah diproses"
          body="Queue reguler berikutnya dijadwalkan pukul 16.00 WIB."
        />
      </section>
    </>
  );
}
function Risk() {
  return (
    <section className={styles.dashboardGrid}>
      <article className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.panelEyebrow}>DISPUTE CENTER</span>
            <h2>4 kasus membutuhkan keputusan</h2>
          </div>
        </div>
        <div className={styles.taskList}>
          <Task
            title="Customer menyatakan layanan tidak selesai"
            meta="DSP-7821 · Rp4,8 juta · Evidence lengkap"
            tone="danger"
          />
          <Task
            title="Refund parsial melebihi batas otomatis"
            meta="DSP-7818 · Rp2,1 juta"
            tone="warning"
          />
          <Task
            title="Partner contesting no-show"
            meta="DSP-7812 · Booking BK-72102"
            tone="warning"
          />
          <Task title="Payment duplicate claim" meta="DSP-7809 · Rp1,4 juta" tone="info" />
        </div>
      </article>
      <article className={`${styles.panel} ${styles.sidePanel}`}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.panelEyebrow}>EXPOSURE</span>
            <h2>Financial risk</h2>
          </div>
        </div>
        <div className={styles.riskValue}>
          <strong>{formatCurrency(18_420_000)}</strong>
          <span>Total dana ditahan</span>
        </div>
        <div className={styles.riskMeter}>
          <span style={{ width: "38%" }} />
        </div>
        <p className={styles.muted}>38% dari monthly dispute threshold.</p>
      </article>
    </section>
  );
}
function AIGovernance() {
  return (
    <>
      <section className={styles.metricGrid}>
        <article className={styles.metricCard}>
          <span>Advisor sessions</span>
          <strong>12.4K</strong>
          <p>+24% month over month</p>
        </article>
        <article className={styles.metricCard}>
          <span>Grounded answer rate</span>
          <strong>96.8%</strong>
          <p>Target ≥95%</p>
        </article>
        <article className={styles.metricCard}>
          <span>Safety blocked</span>
          <strong>84</strong>
          <p>0.68% dari session</p>
        </article>
        <article className={styles.metricCard}>
          <span>Partner Copilot CSAT</span>
          <strong>4.72</strong>
          <p>Dari 1.920 feedback</p>
        </article>
      </section>
      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.panelEyebrow}>AI EVALUATION</span>
            <h2>Model quality dan safety gates</h2>
          </div>
        </div>
        <div className={styles.evaluationGrid}>
          <Insight
            title="Groundedness"
            value="96.8%"
            body="Jawaban memiliki evidence dari katalog atau metric snapshot."
          />
          <Insight
            title="Safety precision"
            value="98.1%"
            body="Blocked response telah direview oleh platform AI ops."
          />
          <Insight
            title="Cost per session"
            value="Rp148"
            body="Local ranker menangani 72% request tanpa provider eksternal."
          />
        </div>
      </section>
    </>
  );
}
function SecurityOps() {
  return (
    <section className={styles.dashboardGrid}>
      <article className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.panelEyebrow}>SYSTEM READINESS</span>
            <h2>Production health</h2>
          </div>
          <Badge tone="success">All green</Badge>
        </div>
        <div className={styles.healthList}>
          {[
            "API & OpenAPI",
            "PostgreSQL & migrations",
            "Redis & rate limiter",
            "Worker & outbox",
            "Qdrant retrieval",
            "Backup & restore drill",
          ].map((item) => (
            <div key={item}>
              <span className={styles.healthCheck}>
                <Icon name="check" size={14} />
              </span>
              <strong>{item}</strong>
              <span>Operational</span>
            </div>
          ))}
        </div>
      </article>
      <article className={`${styles.panel} ${styles.sidePanel}`}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.panelEyebrow}>SECURITY EVENTS</span>
            <h2>24 jam terakhir</h2>
          </div>
        </div>
        <div className={styles.riskValue}>
          <strong>3</strong>
          <span>Open events</span>
        </div>
        <div className={styles.taskList}>
          <Task
            title="Refresh token reuse blocked"
            meta="Severity high · resolved"
            tone="success"
          />
          <Task title="Login rate limit triggered" meta="14 source IP" tone="warning" />
          <Task title="Invalid webhook signature" meta="Provider mock" tone="info" />
        </div>
      </article>
    </section>
  );
}
function AuditLog() {
  return (
    <section className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <span className={styles.panelEyebrow}>IMMUTABLE AUDIT TRAIL</span>
          <h2>Aktivitas platform</h2>
        </div>
        <button className={styles.secondaryButton} type="button">
          <Icon name="download" size={15} /> Export CSV
        </button>
      </div>
      <div className={styles.timeline}>
        {auditEvents.map((event) => (
          <div key={`${event.action}-${event.time}`}>
            <span className={styles.timelineDot} />
            <time>{event.time}</time>
            <strong>{event.action}</strong>
            <p>
              <b>{event.actor}</b> pada <b>{event.target}</b>
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

function OrderTable() {
  return (
    <div className={styles.tableWrap}>
      <table>
        <thead>
          <tr>
            <th>Order</th>
            <th>Customer</th>
            <th>Nilai</th>
            <th>Status</th>
            <th>Waktu</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {partnerOrders.map((order) => (
            <tr key={order.id}>
              <td>
                <strong>{order.id}</strong>
              </td>
              <td>{order.customer}</td>
              <td>{formatCurrency(order.amount)}</td>
              <td>
                <StatusBadge value={order.status} />
              </td>
              <td>{order.time}</td>
              <td>
                <button className={styles.rowPrimary} type="button">
                  Detail
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function TransactionTable() {
  return (
    <div className={styles.tableWrap}>
      <table>
        <thead>
          <tr>
            <th>Payment</th>
            <th>Partner</th>
            <th>Nilai</th>
            <th>Provider</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {platformTransactions.map((transaction) => (
            <tr key={transaction.id}>
              <td>
                <strong>{transaction.id}</strong>
              </td>
              <td>{transaction.partner}</td>
              <td>{formatCurrency(transaction.amount)}</td>
              <td>{transaction.provider}</td>
              <td>
                <StatusBadge value={transaction.status} />
              </td>
              <td>
                <button className={styles.rowPrimary} type="button">
                  Inspect
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
