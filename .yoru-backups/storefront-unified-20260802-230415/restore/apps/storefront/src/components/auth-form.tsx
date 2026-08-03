"use client";

import type { AuthSession } from "@yoru/contracts";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";

type AuthMode = "login" | "register";

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const payload =
      mode === "register"
        ? {
            email: String(data.get("email") ?? ""),
            full_name: String(data.get("full_name") ?? ""),
            password: String(data.get("password") ?? ""),
          }
        : {
            email: String(data.get("email") ?? ""),
            password: String(data.get("password") ?? ""),
          };
    try {
      await apiRequest<AuthSession>(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      router.replace("/account");
      router.refresh();
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Koneksi ke layanan Yoru gagal. Silakan coba kembali.",
      );
    } finally {
      setPending(false);
    }
  }

  const isRegister = mode === "register";
  return (
    <form className="auth-form" onSubmit={submit}>
      {isRegister ? (
        <label>
          Nama lengkap
          <input autoComplete="name" maxLength={150} minLength={2} name="full_name" required />
        </label>
      ) : null}
      <label>
        Email
        <input autoComplete="email" name="email" required type="email" />
      </label>
      <label>
        Password
        <input
          autoComplete={isRegister ? "new-password" : "current-password"}
          maxLength={128}
          minLength={isRegister ? 12 : 1}
          name="password"
          required
          type="password"
        />
      </label>
      {isRegister ? (
        <p className="field-hint">
          Minimal 12 karakter dan gunakan sedikitnya tiga kombinasi huruf kecil, huruf besar, angka,
          atau simbol.
        </p>
      ) : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <button className="primary-action auth-submit" disabled={pending} type="submit">
        {pending ? "Memproses..." : isRegister ? "Buat akun customer" : "Masuk ke Yoru"}
      </button>
      <p className="auth-switch">
        {isRegister ? "Sudah memiliki akun?" : "Belum memiliki akun?"}{" "}
        <Link href={isRegister ? "/login" : "/register"}>
          {isRegister ? "Masuk" : "Daftar sebagai customer"}
        </Link>
      </p>
    </form>
  );
}
