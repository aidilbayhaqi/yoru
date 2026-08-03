import { ApiError, type ApiFieldErrors } from "@/lib/api";

export type AuthErrorPresentation = {
  message: string;
  fieldErrors: Record<string, string>;
};

const knownMessages: Record<string, string> = {
  ACCOUNT_EXISTS:
    "Email ini sudah terdaftar. Silakan masuk atau gunakan alamat email lain.",
  INVALID_CREDENTIALS: "Email atau password tidak cocok.",
  AUTH_RATE_LIMITED:
    "Terlalu banyak percobaan. Tunggu beberapa saat sebelum mencoba kembali.",
  AUTH_PROTECTION_UNAVAILABLE:
    "Layanan perlindungan autentikasi sedang tidak tersedia. Coba kembali nanti.",
  ORIGIN_DENIED:
    "Alamat storefront belum diizinkan oleh API. Periksa konfigurasi CORS.",
  CSRF_VALIDATION_FAILED:
    "Sesi keamanan tidak valid. Muat ulang halaman lalu coba kembali.",
  REQUEST_VALIDATION_FAILED: "Periksa kembali data yang disorot.",
  AUTHENTICATION_REQUIRED: "Silakan masuk untuk melanjutkan.",
  INVALID_SESSION: "Sesi sudah berakhir. Silakan masuk kembali.",
};

function firstMessage(errors: ApiFieldErrors, field: string): string | undefined {
  return errors[field]?.[0];
}

function translateFieldMessage(field: string, message: string): string {
  const value = message.toLowerCase();

  if (field === "email") {
    if (value.includes("valid email") || value.includes("email address")) {
      return "Masukkan alamat email yang valid.";
    }
  }

  if (field === "full_name") {
    if (value.includes("at least 2") || value.includes("too short")) {
      return "Nama lengkap minimal 2 karakter.";
    }
    if (value.includes("at most 150") || value.includes("too long")) {
      return "Nama lengkap maksimal 150 karakter.";
    }
  }

  if (field === "password") {
    if (value.includes("at least 12") || value.includes("too short")) {
      return "Password minimal 12 karakter.";
    }
    if (value.includes("at most 128") || value.includes("too long")) {
      return "Password maksimal 128 karakter.";
    }
    if (value.includes("three character categories")) {
      return "Password harus memakai sedikitnya 3 kategori: huruf kecil, huruf besar, angka, atau simbol.";
    }
  }

  if (value.includes("field required")) {
    return "Kolom ini wajib diisi.";
  }

  return message;
}

export function presentAuthError(
  reason: unknown,
  mode: "login" | "register",
): AuthErrorPresentation {
  if (!(reason instanceof ApiError)) {
    return {
      message:
        "Tidak dapat terhubung ke layanan Yoru. Periksa koneksi dan status API.",
      fieldErrors: {},
    };
  }

  const fieldErrors: Record<string, string> = {};
  for (const field of ["full_name", "email", "password"]) {
    const message = firstMessage(reason.fieldErrors, field);
    if (message) {
      fieldErrors[field] = translateFieldMessage(field, message);
    }
  }

  if (reason.code === "ACCOUNT_EXISTS") {
    fieldErrors.email = knownMessages.ACCOUNT_EXISTS;
  }

  if (reason.code === "INVALID_CREDENTIALS") {
    fieldErrors.email = "Periksa kembali email yang digunakan.";
    fieldErrors.password = "Periksa kembali password yang digunakan.";
  }

  const fallback =
    reason.status === 422
      ? "Periksa kembali data registrasi yang disorot."
      : reason.status === 409 && mode === "register"
        ? knownMessages.ACCOUNT_EXISTS
        : reason.status === 429
          ? knownMessages.AUTH_RATE_LIMITED
          : reason.status >= 500
            ? "Layanan Yoru sedang mengalami gangguan. Coba kembali nanti."
            : reason.message;

  const requestSuffix = reason.requestId
    ? ` Kode permintaan: ${reason.requestId}.`
    : "";

  return {
    message: `${knownMessages[reason.code] ?? fallback}${requestSuffix}`,
    fieldErrors,
  };
}


export function validateLogin(input: {
  email: string;
  password: string;
}): Record<string, string> {
  const errors: Record<string, string> = {};
  const email = input.email.trim();

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Masukkan alamat email yang valid.";
  }

  if (!input.password) {
    errors.password = "Password wajib diisi.";
  } else if (input.password.length > 128) {
    errors.password = "Password maksimal 128 karakter.";
  }

  return errors;
}

export function validateRegistration(input: {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
  acceptedTerms: boolean;
}): Record<string, string> {
  const errors: Record<string, string> = {};
  const fullName = input.fullName.trim();
  const email = input.email.trim();

  if (fullName.length < 2) {
    errors.full_name = "Nama lengkap minimal 2 karakter.";
  } else if (fullName.length > 150) {
    errors.full_name = "Nama lengkap maksimal 150 karakter.";
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Masukkan alamat email yang valid.";
  }

  if (input.password.length < 12) {
    errors.password = "Password minimal 12 karakter.";
  } else if (input.password.length > 128) {
    errors.password = "Password maksimal 128 karakter.";
  } else {
    const categoryCount = [
      /[a-z]/.test(input.password),
      /[A-Z]/.test(input.password),
      /\d/.test(input.password),
      /[^A-Za-z0-9]/.test(input.password),
    ].filter(Boolean).length;

    if (categoryCount < 3) {
      errors.password =
        "Gunakan sedikitnya 3 kategori: huruf kecil, huruf besar, angka, atau simbol.";
    }
  }

  if (!input.confirmPassword) {
    errors.confirm_password = "Ulangi password untuk memastikan tidak salah ketik.";
  } else if (input.password !== input.confirmPassword) {
    errors.confirm_password = "Konfirmasi password tidak sama.";
  }

  if (!input.acceptedTerms) {
    errors.terms = "Persetujuan syarat dan kebijakan privasi wajib diberikan.";
  }

  return errors;
}
