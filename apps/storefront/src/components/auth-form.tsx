"use client";

import type { AuthSession } from "@yoru/contracts";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Icon } from "@/components/icons";
import { apiRequest } from "@/lib/api";
import {
  presentAuthError,
  validateLogin,
  validateRegistration,
} from "@/lib/auth-errors";
import { safeReturnPath } from "@/lib/storefront-auth";

type AuthMode = "login" | "register";

function FieldError({ message }: { message?: string }) {
  return message ? (
    <small className="field-error" role="alert">
      {message}
    </small>
  ) : null;
}

export function AuthForm({
  mode,
  nextPath,
}: {
  mode: AuthMode;
  nextPath?: string;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [formError, setFormError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") ?? "").trim().toLowerCase();
    const password = String(data.get("password") ?? "");
    const fullName = String(data.get("full_name") ?? "").trim();
    const confirmPassword = String(data.get("confirm_password") ?? "");
    const acceptedTerms = data.get("terms") === "on";

    setFormError("");
    setFieldErrors({});

    const validationErrors =
      mode === "register"
        ? validateRegistration({
            fullName,
            email,
            password,
            confirmPassword,
            acceptedTerms,
          })
        : validateLogin({ email, password });

    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setFormError(
        mode === "register"
          ? "Periksa kembali data registrasi yang disorot."
          : "Periksa kembali email dan password.",
      );
      return;
    }

    setPending(true);

    const payload =
      mode === "register"
        ? {
            email,
            full_name: fullName,
            password,
          }
        : {
            email,
            password,
          };

    try {
      await apiRequest<AuthSession>(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      router.replace(safeReturnPath(nextPath, "/account"));
      router.refresh();
    } catch (reason) {
      const presented = presentAuthError(reason, mode);
      setFormError(presented.message);
      setFieldErrors(presented.fieldErrors);
    } finally {
      setPending(false);
    }
  }

  const isRegister = mode === "register";

  return (
    <form className="auth-form storefront-auth-form" noValidate onSubmit={submit}>
      {isRegister ? (
        <label>
          Nama lengkap
          <input
            aria-invalid={Boolean(fieldErrors.full_name)}
            autoComplete="name"
            maxLength={150}
            minLength={2}
            name="full_name"
            placeholder="Nama sesuai identitas"
            required
          />
          <FieldError message={fieldErrors.full_name} />
        </label>
      ) : null}

      <label>
        Email
        <input
          aria-invalid={Boolean(fieldErrors.email)}
          autoComplete="email"
          name="email"
          placeholder="nama@email.com"
          required
          type="email"
        />
        <FieldError message={fieldErrors.email} />
      </label>

      <label>
        Password
        <input
          aria-invalid={Boolean(fieldErrors.password)}
          autoComplete={isRegister ? "new-password" : "current-password"}
          maxLength={128}
          minLength={isRegister ? 12 : 1}
          name="password"
          placeholder={isRegister ? "Minimal 12 karakter" : "Masukkan password"}
          required
          type="password"
        />
        <FieldError message={fieldErrors.password} />
      </label>

      {isRegister ? (
        <>
          <label>
            Konfirmasi password
            <input
              aria-invalid={Boolean(fieldErrors.confirm_password)}
              autoComplete="new-password"
              maxLength={128}
              minLength={12}
              name="confirm_password"
              placeholder="Ulangi password"
              required
              type="password"
            />
            <FieldError message={fieldErrors.confirm_password} />
          </label>

          <div className="password-rules">
            <strong>Syarat password</strong>
            <span>12–128 karakter</span>
            <span>Sedikitnya 3 dari: huruf kecil, huruf besar, angka, simbol</span>
          </div>

          <label className="terms-field">
            <input name="terms" type="checkbox" />
            <span>
              Saya menyetujui syarat penggunaan dan kebijakan privasi Yoru.
            </span>
          </label>
          <FieldError message={fieldErrors.terms} />
        </>
      ) : null}

      {formError ? (
        <div className="form-error auth-error-summary" role="alert">
          <Icon name="shield" width="18" />
          <span>{formError}</span>
        </div>
      ) : null}

      <button
        className="primary-button auth-submit"
        disabled={pending}
        type="submit"
      >
        {pending
          ? "Memproses..."
          : isRegister
            ? "Buat akun customer"
            : "Masuk ke Yoru"}
        <Icon name="arrow" width="18" />
      </button>

      <p className="auth-switch">
        {isRegister ? "Sudah memiliki akun?" : "Belum memiliki akun?"}{" "}
        <Link
          href={
            isRegister
              ? `/login${nextPath ? `?next=${encodeURIComponent(nextPath)}` : ""}`
              : `/register${nextPath ? `?next=${encodeURIComponent(nextPath)}` : ""}`
          }
        >
          {isRegister ? "Masuk" : "Daftar sekarang"}
        </Link>
      </p>
    </form>
  );
}
