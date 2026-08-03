export type ConsoleRole = "partner" | "superadmin";

export type DashboardSection =
  | "overview"
  | "products"
  | "inventory"
  | "orders"
  | "bookings"
  | "professionals"
  | "finance"
  | "copilot"
  | "partner-verification"
  | "partners"
  | "transactions"
  | "operations"
  | "ledger"
  | "risk"
  | "ai-governance"
  | "security"
  | "audit";

export interface SessionLike {
  platform_roles: string[];
  memberships: Array<{
    partner_id: string;
    role: string;
    partner_status: string;
    membership_status: string;
  }>;
  active_partner_id: string | null;
}

export interface NavigationItem {
  id: DashboardSection;
  label: string;
  icon: IconName;
  badge?: string;
}

export interface NavigationGroup {
  label: string;
  items: NavigationItem[];
}

export type IconName =
  | "grid"
  | "box"
  | "layers"
  | "receipt"
  | "calendar"
  | "users"
  | "wallet"
  | "sparkles"
  | "shield"
  | "store"
  | "activity"
  | "bank"
  | "alert"
  | "brain"
  | "lock"
  | "history";

const PLATFORM_ROLES = new Set([
  "super_admin",
  "superadmin",
  "platform_admin",
  "platform_operations",
  "platform_finance",
  "platform_support",
]);

export function resolveConsoleRole(session: SessionLike): ConsoleRole {
  const hasPlatformRole = session.platform_roles.some((role) =>
    PLATFORM_ROLES.has(role.toLowerCase()),
  );
  return hasPlatformRole ? "superadmin" : "partner";
}

export const partnerNavigation: NavigationGroup[] = [
  {
    label: "Workspace",
    items: [{ id: "overview", label: "Ringkasan bisnis", icon: "grid" }],
  },
  {
    label: "Commerce",
    items: [
      { id: "products", label: "Produk & layanan", icon: "box" },
      { id: "inventory", label: "Stok & inventori", icon: "layers", badge: "8" },
      { id: "orders", label: "Pesanan", icon: "receipt", badge: "12" },
      { id: "bookings", label: "Booking & operasional", icon: "calendar", badge: "5" },
    ],
  },
  {
    label: "Organisasi",
    items: [
      { id: "professionals", label: "Tim & profesional", icon: "users" },
      { id: "finance", label: "Keuangan", icon: "wallet" },
      { id: "copilot", label: "Partner Copilot", icon: "sparkles" },
    ],
  },
];

export const superAdminNavigation: NavigationGroup[] = [
  {
    label: "Command center",
    items: [{ id: "overview", label: "Platform overview", icon: "grid" }],
  },
  {
    label: "Marketplace control",
    items: [
      {
        id: "partner-verification",
        label: "Verifikasi mitra",
        icon: "shield",
        badge: "17",
      },
      { id: "partners", label: "Partner directory", icon: "store" },
      { id: "transactions", label: "Order & pembayaran", icon: "receipt" },
      { id: "operations", label: "Booking operations", icon: "activity" },
    ],
  },
  {
    label: "Finance & governance",
    items: [
      { id: "ledger", label: "Ledger & payout", icon: "bank" },
      { id: "risk", label: "Dispute & refund", icon: "alert", badge: "4" },
      { id: "ai-governance", label: "AI governance", icon: "brain" },
      { id: "security", label: "Security & ops", icon: "lock" },
      { id: "audit", label: "Audit log", icon: "history" },
    ],
  },
];

export function navigationForRole(role: ConsoleRole): NavigationGroup[] {
  return role === "superadmin" ? superAdminNavigation : partnerNavigation;
}

export function sectionLabel(role: ConsoleRole, section: DashboardSection): string {
  const item = navigationForRole(role)
    .flatMap((group) => group.items)
    .find((entry) => entry.id === section);
  return item?.label ?? "Dashboard";
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatCompact(value: number): string {
  return new Intl.NumberFormat("id-ID", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export const partnerMetrics = [
  { label: "Pendapatan bulan ini", value: 186_450_000, delta: 12.4, kind: "currency" },
  { label: "Pesanan selesai", value: 428, delta: 8.1, kind: "number" },
  { label: "Booking aktif", value: 64, delta: -3.2, kind: "number" },
  { label: "Saldo tersedia", value: 74_820_000, delta: 5.7, kind: "currency" },
] as const;

export const platformMetrics = [
  { label: "GMV bulan ini", value: 4_860_000_000, delta: 18.7, kind: "currency" },
  { label: "Partner aktif", value: 284, delta: 6.4, kind: "number" },
  { label: "Order hari ini", value: 1_842, delta: 11.2, kind: "number" },
  { label: "Net platform revenue", value: 486_000_000, delta: 14.9, kind: "currency" },
] as const;

export const partnerRevenueSeries = [32, 39, 35, 48, 45, 58, 62, 55, 69, 74, 71, 86];
export const platformRevenueSeries = [42, 51, 48, 57, 63, 70, 76, 71, 82, 88, 91, 96];

export const initialProducts = [
  {
    id: "PRD-1024",
    name: "Deep Cleaning Premium",
    category: "Home service",
    price: 475_000,
    stock: 24,
    status: "Published",
    sales: 128,
  },
  {
    id: "PRD-1028",
    name: "AC Service 1 PK",
    category: "Maintenance",
    price: 185_000,
    stock: 8,
    status: "Published",
    sales: 94,
  },
  {
    id: "PRD-1031",
    name: "Paket Detailing Sofa",
    category: "Cleaning",
    price: 650_000,
    stock: 4,
    status: "Low stock",
    sales: 72,
  },
  {
    id: "PRD-1037",
    name: "Filter HEPA Replacement",
    category: "Product",
    price: 320_000,
    stock: 0,
    status: "Draft",
    sales: 41,
  },
];

export const partnerOrders = [
  { id: "YR-240812", customer: "Nadia Prameswari", amount: 1_275_000, status: "Diproses", time: "8 menit lalu" },
  { id: "YR-240811", customer: "Ari Wibowo", amount: 650_000, status: "Selesai", time: "24 menit lalu" },
  { id: "YR-240810", customer: "Maya Kurnia", amount: 475_000, status: "Menunggu", time: "41 menit lalu" },
  { id: "YR-240809", customer: "Dimas Saputra", amount: 940_000, status: "Selesai", time: "1 jam lalu" },
];

export const bookingSchedule = [
  { time: "08:00", customer: "Rani", service: "Deep Cleaning", professional: "Raka", status: "On the way" },
  { time: "10:30", customer: "Kevin", service: "AC Service", professional: "Dimas", status: "Confirmed" },
  { time: "13:00", customer: "Sinta", service: "Sofa Detailing", professional: "Raka", status: "Assigned" },
  { time: "15:30", customer: "Andre", service: "Deep Cleaning", professional: "Alya", status: "Requested" },
];

export const verificationQueue = [
  { partner: "PT Bersih Selalu", type: "Home service", submitted: "12 menit lalu", risk: "Low", completeness: 100 },
  { partner: "Klinik Senyum Cerah", type: "Healthcare", submitted: "27 menit lalu", risk: "Medium", completeness: 92 },
  { partner: "CV Teknik Prima", type: "Maintenance", submitted: "44 menit lalu", risk: "Low", completeness: 100 },
  { partner: "Glow House Indonesia", type: "Beauty", submitted: "1 jam lalu", risk: "High", completeness: 84 },
];

export const partnerDirectory = [
  { name: "HomeCare Jakarta", category: "Home service", gmv: 428_000_000, orders: 982, health: 96, status: "Healthy" },
  { name: "Klinik Senyum Cerah", category: "Healthcare", gmv: 286_000_000, orders: 481, health: 88, status: "Review" },
  { name: "Teknik Prima", category: "Maintenance", gmv: 194_000_000, orders: 722, health: 92, status: "Healthy" },
  { name: "Glow House", category: "Beauty", gmv: 167_000_000, orders: 538, health: 71, status: "At risk" },
];

export const platformTransactions = [
  { id: "PAY-839102", partner: "HomeCare Jakarta", amount: 2_450_000, provider: "MockPay", status: "Settled" },
  { id: "PAY-839101", partner: "Teknik Prima", amount: 875_000, provider: "MockPay", status: "Pending" },
  { id: "PAY-839100", partner: "Glow House", amount: 1_280_000, provider: "MockPay", status: "Review" },
  { id: "PAY-839099", partner: "Klinik Senyum Cerah", amount: 3_150_000, provider: "MockPay", status: "Settled" },
];

export const financeBalances = [
  { label: "Pending settlement", value: 22_480_000 },
  { label: "Available balance", value: 74_820_000 },
  { label: "Held by dispute", value: 3_260_000 },
  { label: "Paid out MTD", value: 96_550_000 },
];

export const auditEvents = [
  { actor: "admin@yoru.id", action: "PARTNER_VERIFIED", target: "PT Bersih Selalu", time: "3 menit lalu" },
  { actor: "finance@yoru.id", action: "PAYOUT_APPROVED", target: "PO-48211", time: "11 menit lalu" },
  { actor: "system", action: "SECURITY_EVENT_RESOLVED", target: "SEC-2104", time: "18 menit lalu" },
  { actor: "ops@yoru.id", action: "BOOKING_REASSIGNED", target: "BK-72112", time: "26 menit lalu" },
];
