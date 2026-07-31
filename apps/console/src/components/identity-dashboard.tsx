"use client";

import type { AuthSession } from "@yoru/contracts";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";

export function IdentityDashboard() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiRequest<AuthSession>("/auth/me")
      .then((value) => {
        if (!active) return;
        if (value.platform_roles.length === 0 && value.memberships.length === 0) {
          setError("Akun ini tidak memiliki akses operational console.");
          return;
        }
        setSession(value);
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

  async function selectPartner(partnerId: string) {
    const value = await apiRequest<AuthSession>("/auth/active-partner", {
      method: "PATCH",
      body: JSON.stringify({ partner_id: partnerId }),
    });
    setSession(value);
  }

  async function logout() {
    await apiRequest<{ message: string }>("/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  if (error) return <div className="identity-state identity-error">{error}</div>;
  if (!session) return <div className="identity-state">Memuat authorization context...</div>;

  return (
    <div className="identity-dashboard">
      <header>
        <div>
          <p className="kicker">Authenticated operator</p>
          <h1>{session.user.full_name}</h1>
          <p>{session.user.email}</p>
        </div>
        <button className="console-logout" onClick={logout} type="button">
          Keluar
        </button>
      </header>

      <section className="identity-grid">
        <article>
          <span>Platform role</span>
          <strong>{session.platform_roles.join(", ") || "Partner member"}</strong>
        </article>
        <article>
          <span>Tenant aktif</span>
          <strong>{session.active_partner_id ?? "Platform scope"}</strong>
        </article>
        <article>
          <span>Capability</span>
          <strong>{session.permissions.length}</strong>
        </article>
      </section>

      <section className="identity-panel">
        <div>
          <p className="kicker">Tenant boundary</p>
          <h2>Partner memberships</h2>
        </div>
        {session.memberships.length ? (
          <div className="membership-list">
            {session.memberships.map((membership) => (
              <article key={membership.partner_id}>
                <div>
                  <strong>{membership.role}</strong>
                  <span>
                    {membership.partner_status} · {membership.membership_status}
                  </span>
                </div>
                <button
                  disabled={session.active_partner_id === membership.partner_id}
                  onClick={() => selectPartner(membership.partner_id)}
                  type="button"
                >
                  {session.active_partner_id === membership.partner_id
                    ? "Tenant aktif"
                    : "Pilih tenant"}
                </button>
              </article>
            ))}
          </div>
        ) : (
          <p className="identity-empty">
            Platform role bekerja tanpa memilih tenant partner. Resource sensitif tetap membutuhkan
            capability dan step-up yang sesuai.
          </p>
        )}
      </section>
    </div>
  );
}
