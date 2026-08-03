"use client";

import type { AuthSession } from "@yoru/contracts";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import { safeDashboardReturnPath } from "@/lib/console-auth";

const loginMessages: Record<string, string> = {
  authentication_required: "Silakan masuk untuk membuka dashboard.",
  session_expired: "Sesi Anda telah berakhir. Silakan masuk kembali.",
  console_access_denied: "Akun ini belum memiliki akses ke Yoru Console.",
  identity_unavailable: "Layanan identity sedang tidak tersedia. Coba masuk kembali.",
};

export function ConsoleLoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const reason = new URLSearchParams(window.location.search).get("reason") ?? "";
    setNotice(loginMessages[reason] ?? "");
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

      if (session.platform_roles.length === 0 && session.memberships.length === 0) {
        await apiRequest<{ message: string }>("/auth/logout", { method: "POST" });
        throw new ApiError(
          "Akun customer tidak memiliki akses ke operational console.",
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
    <form className="console-login-form" onSubmit={submit}>
      {notice && !error ? (
        <p className="console-auth-note" role="status">
          {notice}
        </p>
      ) : null}
      <label>
        Email
        <input autoComplete="email" name="email" required type="email" />
      </label>
      <label>
        Password
        <input
          autoComplete="current-password"
          maxLength={128}
          name="password"
          required
          type="password"
        />
      </label>
      {error ? (
        <p className="console-form-error" role="alert">
          {error}
        </p>
      ) : null}
      <button disabled={pending} type="submit">
        {pending ? "Memverifikasi..." : "Masuk ke console"}
      </button>
    </form>
  );
}
