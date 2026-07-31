"use client";

import type { AuthSession } from "@yoru/contracts";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";

export function ConsoleLoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

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
      router.replace("/dashboard");
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
