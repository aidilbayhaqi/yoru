"use client";

import type { AuthSession } from "@yoru/contracts";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useMemo, useState } from "react";

import { Icon } from "@/components/icons";
import { apiRequest } from "@/lib/api";
import {
  presentAuthError,
  validateLogin,
  validateRegistration,
} from "@/lib/auth-errors";
import { safeReturnPath } from "@/lib/storefront-auth";

type AuthMode = "login" | "register";

function FieldError({ id, message }: { id: string; message?: string }) {
  return message ? (
    <small className="field-error" id={id} role="alert">
      {message}
    </small>
  ) : null;
}

function focusFirstInvalid(form: HTMLFormElement): void {
  window.requestAnimationFrame(() => {
    form.querySelector<HTMLElement>("[aria-invalid='true']")?.focus();
  });
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
  const [requestId, setRequestId] = useState<string>();
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const isRegister = mode === "register";
  const passwordChecks = useMemo(
    () => ({
      length: password.length >= 12 && password.length <= 128,
      categories:
        [
          /[a-z]/.test(password),
          /[A-Z]/.test(password),
          /\d/.test(password),
          /[^A-Za-z0-9]/.test(password),
        ].filter(Boolean).length >= 3,
      boundary: password.length > 0 && password === password.trim(),
    }),
    [password],
  );

  function clearFieldError(field: string) {
    setFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const email = String(data.get("email") ?? "").trim().toLowerCase();
    const fullName = String(data.get("full_name") ?? "")
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .join(" ");
    const confirmPassword = String(data.get("confirm_password") ?? "");
    const acceptedTerms = data.get("terms") === "on";

    setFormError("");
    setRequestId(undefined);
    setFieldErrors({});

    const validationErrors = isRegister
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
        isRegister
          ? "Akun belum dibuat. Perbaiki kolom yang ditandai sebelum melanjutkan."
          : "Login belum berhasil. Periksa email dan password.",
      );
      focusFirstInvalid(form);
      return;
    }

    setPending(true);
    try {
      await apiRequest<AuthSession>(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify(
          isRegister
            ? { email, full_name: fullName, password }
            : { email, password },
        ),
      });
      router.replace(safeReturnPath(nextPath, "/account"));
      router.refresh();
    } catch (reason) {
      const presented = presentAuthError(reason, mode);
      setFormError(presented.message);
      setFieldErrors(presented.fieldErrors);
      setRequestId(presented.requestId);
      focusFirstInvalid(form);
    } finally {
      setPending(false);
    }
  }

  return (
    <form
      aria-busy={pending}
      className="auth-form storefront-auth-form"
      noValidate
      onSubmit={submit}
    >
      {isRegister ? (
        <label>
          Nama lengkap
          <input
            aria-describedby={fieldErrors.full_name ? "full-name-error" : undefined}
            aria-invalid={Boolean(fieldErrors.full_name)}
            autoComplete="name"
            disabled={pending}
            maxLength={150}
            minLength={2}
            name="full_name"
            onInput={() => clearFieldError("full_name")}
            placeholder="Nama sesuai identitas"
            required
          />
          <FieldError id="full-name-error" message={fieldErrors.full_name} />
        </label>
      ) : null}

      <label>
        Email
        <input
          aria-describedby={fieldErrors.email ? "email-error" : undefined}
          aria-invalid={Boolean(fieldErrors.email)}
          autoCapitalize="none"
          autoComplete="email"
          disabled={pending}
          inputMode="email"
          name="email"
          onInput={() => clearFieldError("email")}
          placeholder="nama@email.com"
          required
          spellCheck={false}
          type="email"
        />
        <FieldError id="email-error" message={fieldErrors.email} />
      </label>

      <label>
        Password
        <span className="password-input-wrap">
          <input
            aria-describedby={
              isRegister
                ? fieldErrors.password
                  ? "password-error password-rules"
                  : "password-rules"
                : fieldErrors.password
                  ? "password-error"
                  : undefined
            }
            aria-invalid={Boolean(fieldErrors.password)}
            autoComplete={isRegister ? "new-password" : "current-password"}
            disabled={pending}
            maxLength={128}
            minLength={isRegister ? 12 : 1}
            name="password"
            onChange={(event) => {
              setPassword(event.target.value);
              clearFieldError("password");
            }}
            placeholder={isRegister ? "Minimal 12 karakter" : "Masukkan password"}
            required
            type={showPassword ? "text" : "password"}
            value={password}
          />
          <button
            aria-label={showPassword ? "Sembunyikan password" : "Tampilkan password"}
            className="password-toggle"
            onClick={() => setShowPassword((value) => !value)}
            type="button"
          >
            {showPassword ? "Sembunyikan" : "Tampilkan"}
          </button>
        </span>
        <FieldError id="password-error" message={fieldErrors.password} />
      </label>

      {isRegister ? (
        <>
          <div className="password-rules" id="password-rules">
            <strong>Syarat password</strong>
            <span data-valid={passwordChecks.length}>12–128 karakter</span>
            <span data-valid={passwordChecks.categories}>
              Sedikitnya 3 dari: huruf kecil, huruf besar, angka, simbol
            </span>
            <span data-valid={passwordChecks.boundary}>
              Tidak diawali atau diakhiri spasi
            </span>
          </div>

          <label>
            Konfirmasi password
            <span className="password-input-wrap">
              <input
                aria-describedby={
                  fieldErrors.confirm_password ? "confirm-password-error" : undefined
                }
                aria-invalid={Boolean(fieldErrors.confirm_password)}
                autoComplete="new-password"
                disabled={pending}
                maxLength={128}
                minLength={12}
                name="confirm_password"
                onInput={() => clearFieldError("confirm_password")}
                placeholder="Ulangi password"
                required
                type={showPassword ? "text" : "password"}
              />
            </span>
            <FieldError
              id="confirm-password-error"
              message={fieldErrors.confirm_password}
            />
          </label>

          <label className="terms-field">
            <input
              aria-describedby={fieldErrors.terms ? "terms-error" : undefined}
              aria-invalid={Boolean(fieldErrors.terms)}
              disabled={pending}
              name="terms"
              onChange={() => clearFieldError("terms")}
              type="checkbox"
            />
            <span>
              Saya menyetujui syarat penggunaan dan kebijakan privasi Yoru.
            </span>
          </label>
          <FieldError id="terms-error" message={fieldErrors.terms} />
        </>
      ) : null}

      {fieldErrors._form ? (
        <FieldError id="form-field-error" message={fieldErrors._form} />
      ) : null}

      {formError ? (
        <div className="form-error auth-error-summary" role="alert">
          <Icon name="shield" width="18" />
          <span>
            <strong>{formError}</strong>
            {requestId ? (
              <small>
                Kode permintaan: <code>{requestId}</code>
              </small>
            ) : null}
          </span>
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
