import { ApiError } from "@/lib/api";

export type AuthErrorPresentation = {
  message: string;
  fieldErrors: Record<string, string>;
  requestId?: string;
};

const knownMessages: Record<string, string> = {
  ACCOUNT_EXISTS:
    "Email ini sudah terdaftar. Masuk dengan akun tersebut atau gunakan alamat email lain.",
  INVALID_CREDENTIALS: "Email atau password tidak cocok.",
  AUTH_RATE_LIMITED:
    "Terlalu banyak percobaan. Tunggu beberapa saat sebelum mencoba kembali.",
  AUTH_PROTECTION_UNAVAILABLE:
    "Layanan perlindungan autentikasi sedang tidak tersedia. Coba kembali nanti.",
  ORIGIN_DENIED:
    "Alamat storefront belum diizinkan oleh API. Periksa CORS_ALLOWED_ORIGINS pada backend.",
  CSRF_VALIDATION_FAILED:
    "Sesi keamanan tidak valid. Muat ulang halaman lalu coba kembali.",
  AUTHENTICATION_REQUIRED: "Silakan masuk untuk melanjutkan.",
  INVALID_SESSION: "Sesi sudah berakhir. Silakan masuk kembali.",
};

const fieldLabels: Record<string, string> = {
  full_name: "nama lengkap",
  email: "email",
  password: "password",
  confirm_password: "konfirmasi password",
  terms: "persetujuan syarat",
};


function translateFieldMessage(field: string, message: string): string {
  const value = message.toLowerCase();

  if (field === "email") {
    if (value.includes("valid email") || value.includes("email address")) {
      return "Masukkan alamat email yang valid, misalnya nama@domain.com.";
    }
  }
  if (field === "full_name") {
    if (value.includes("at least 2") || value.includes("too short")) {
      return "Nama lengkap minimal 2 karakter setelah spasi kosong dibuang.";
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
      return "Gunakan sedikitnya 3 kategori: huruf kecil, huruf besar, angka, atau simbol.";
    }
    if (value.includes("start or end with whitespace")) {
      return "Password tidak boleh diawali atau diakhiri spasi.";
    }
  }
  if (value.includes("field required") || value.includes("missing")) {
    return "Kolom ini wajib diisi.";
  }
  if (value.includes("extra inputs are not permitted")) {
    return "Aplikasi mengirim field yang tidak dikenali API. Perbarui kontrak FE–BE.";
  }
  return message;
}

function invalidFieldSummary(fieldErrors: Record<string, string>): string | undefined {
  const labels = Object.keys(fieldErrors)
    .filter((field) => field !== "_form")
    .map((field) => fieldLabels[field] ?? field.replaceAll("_", " "));
  if (labels.length === 0) return undefined;
  if (labels.length === 1) return labels[0];
  return `${labels.slice(0, -1).join(", ")}, dan ${labels.at(-1)}`;
}

export function presentAuthError(
  reason: unknown,
  mode: "login" | "register",
): AuthErrorPresentation {
  if (!(reason instanceof ApiError)) {
    return {
      message:
        "Tidak dapat terhubung ke layanan Yoru. Pastikan API aktif dan koneksi jaringan tersedia.",
      fieldErrors: {},
    };
  }

  const fieldErrors: Record<string, string> = {};
  for (const [field, messages] of Object.entries(reason.fieldErrors)) {
    const message = messages[0];
    if (message) fieldErrors[field] = translateFieldMessage(field, message);
  }

  if (reason.code === "ACCOUNT_EXISTS") {
    fieldErrors.email = knownMessages.ACCOUNT_EXISTS;
  }
  if (reason.code === "INVALID_CREDENTIALS") {
    fieldErrors.email = "Periksa kembali alamat email yang digunakan.";
    fieldErrors.password = "Periksa kembali password yang digunakan.";
  }

  const invalidFields = invalidFieldSummary(fieldErrors);
  const validationMessage = invalidFields
    ? `${mode === "register" ? "Akun belum dibuat" : "Login belum berhasil"}. Perbaiki ${invalidFields}.`
    : mode === "register"
      ? "Akun belum dibuat karena data registrasi belum valid. Periksa kembali seluruh kolom."
      : "Login belum berhasil karena data yang dikirim belum valid.";

  const fallback =
    reason.status === 422
      ? validationMessage
      : reason.status === 409 && mode === "register"
        ? knownMessages.ACCOUNT_EXISTS
        : reason.status === 429
          ? knownMessages.AUTH_RATE_LIMITED
          : reason.status >= 500
            ? "Layanan Yoru sedang mengalami gangguan. Coba kembali nanti."
            : reason.message;

  return {
    message: knownMessages[reason.code] ?? fallback,
    fieldErrors,
    requestId: reason.requestId,
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
  const fullName = input.fullName.trim().split(/\s+/).filter(Boolean).join(" ");
  const email = input.email.trim();

  if (fullName.length < 2) {
    errors.full_name = "Nama lengkap minimal 2 karakter.";
  } else if (fullName.length > 150) {
    errors.full_name = "Nama lengkap maksimal 150 karakter.";
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Masukkan alamat email yang valid.";
  }

  if (input.password !== input.password.trim()) {
    errors.password = "Password tidak boleh diawali atau diakhiri spasi.";
  } else if (input.password.length < 12) {
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
