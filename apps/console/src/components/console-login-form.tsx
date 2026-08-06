"use client";

import type { AuthSession } from "@yoru/contracts";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import { resolveConsoleAccess, safeDashboardReturnPath } from "@/lib/console-auth";

import styles from "./auth-shell.module.css";

const loginMessages: Record<string, string> = {
  authentication_required: "Silakan masuk untuk membuka dashboard.",
  session_expired: "Sesi Anda telah berakhir. Silakan masuk kembali.",
  console_access_denied: "Akun ini belum memiliki akses kemitraan atau super admin.",
  identity_unavailable: "Layanan identity sedang tidak tersedia. Coba masuk kembali.",
  registered: "Akun kemitraan berhasil dibuat. Silakan masuk.",
};

export function ConsoleLoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      const reason = new URLSearchParams(window.location.search).get("reason") ?? "";
      setNotice(loginMessages[reason] ?? "");
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError("");
    setPending(true);

    try {
      const session = await apiRequest<AuthSession>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: String(data.get("email") ?? ""),
          password: String(data.get("password") ?? ""),
        }),
      });

      if (!resolveConsoleAccess(session)) {
        await apiRequest<{ message: string }>("/auth/logout", { method: "POST" });
        throw new ApiError(
          "Akun ini tidak memiliki role partner aktif atau super_admin.",
          403,
          "CONSOLE_ACCESS_DENIED",
        );
      }

      const nextPath = safeDashboardReturnPath(
        new URLSearchParams(window.location.search).get("next"),
      );
      router.replace(nextPath);
      router.refresh();
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Console belum dapat terhubung ke layanan identity.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      {notice && !error ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}
      <label className={styles.field}>
        <span>Email kerja</span>
        <input
          autoComplete="email"
          name="email"
          placeholder="nama@perusahaan.id"
          required
          type="email"
        />
      </label>
      <label className={styles.field}>
        <span>Password</span>
        <input
          autoComplete="current-password"
          maxLength={128}
          name="password"
          placeholder="Masukkan password"
          required
          type="password"
        />
      </label>
      <div className={styles.formMeta}>
        <label className={styles.checkbox}>
          <input type="checkbox" /> <span>Ingat perangkat ini</span>
        </label>
        <button className={styles.linkButton} type="button">
          Lupa password?
        </button>
      </div>
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
      <button className={styles.submit} disabled={pending} type="submit">
        {pending ? "Memverifikasi akses..." : "Masuk ke dashboard"}
      </button>
      <p className={styles.switchText}>
        Belum punya akun kemitraan? <Link href="/register">Daftar sekarang</Link>
      </p>
    </form>
  );
}
