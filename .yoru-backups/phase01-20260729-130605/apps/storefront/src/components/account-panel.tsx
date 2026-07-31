"use client";

import type { AuthSession } from "@yoru/contracts";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";

export function AccountPanel() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiRequest<AuthSession>("/auth/me")
      .then((value) => {
        if (active) setSession(value);
      })
      .catch((reason) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 401) {
          router.replace("/login");
          return;
        }
        setError("Data akun belum dapat dimuat.");
      });
    return () => {
      active = false;
    };
  }, [router]);

  async function logout() {
    try {
      await apiRequest<{ message: string }>("/auth/logout", { method: "POST" });
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  if (error) {
    return (
      <div className="account-state">
        <p>{error}</p>
        <Link href="/">Kembali ke beranda</Link>
      </div>
    );
  }
  if (!session) {
    return <div className="account-state">Memuat session aman...</div>;
  }

  return (
    <section className="account-card">
      <div>
        <p className="eyebrow">Customer account</p>
        <h1>{session.user.full_name}</h1>
        <p className="lead">{session.user.email}</p>
      </div>
      <dl className="account-details">
        <div>
          <dt>Status</dt>
          <dd>{session.user.status}</dd>
        </div>
        <div>
          <dt>Tenant aktif</dt>
          <dd>{session.active_partner_id ?? "Akun customer"}</dd>
        </div>
        <div>
          <dt>Capability</dt>
          <dd>{session.permissions.join(", ")}</dd>
        </div>
      </dl>
      <div className="account-actions">
        <Link className="secondary-action" href="/">
          Beranda
        </Link>
        <button className="danger-action" onClick={logout} type="button">
          Keluar
        </button>
      </div>
    </section>
  );
}
