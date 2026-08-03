"use client";

import type { AuthSession } from "@yoru/contracts";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";

import styles from "./auth-shell.module.css";

type PartnerResponse = { id: string; display_name: string; status: string };

export function ConsoleRegistrationForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);
  const [accountCreated, setAccountCreated] = useState(false);

  function nextStep(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password") ?? "");
    const confirmation = String(data.get("password_confirmation") ?? "");
    if (password !== confirmation) {
      setError("Konfirmasi password belum sama.");
      return;
    }
    setError("");
    setStep(2);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const root = event.currentTarget.closest("main");
    const accountForm = root?.querySelector<HTMLFormElement>("#partner-account-form");
    const account = accountForm ? new FormData(accountForm) : new FormData();
    const business = new FormData(event.currentTarget);
    setError("");
    setPending(true);

    try {
      if (!accountCreated) {
        await apiRequest<AuthSession>("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            full_name: String(account.get("full_name") ?? ""),
            email: String(account.get("email") ?? ""),
            password: String(account.get("password") ?? ""),
          }),
        });
        setAccountCreated(true);
      }

      const partner = await apiRequest<PartnerResponse>("/partners", {
        method: "POST",
        body: JSON.stringify({
          display_name: String(business.get("display_name") ?? ""),
          legal_name: String(business.get("legal_name") ?? ""),
          partner_type: String(business.get("partner_type") ?? "service_provider"),
          contact_email: String(account.get("email") ?? ""),
          contact_phone: String(business.get("contact_phone") ?? ""),
          address_line: String(business.get("address_line") ?? ""),
          city: String(business.get("city") ?? ""),
          province: String(business.get("province") ?? ""),
          postal_code: String(business.get("postal_code") ?? "") || null,
          description: String(business.get("description") ?? "") || null,
        }),
      });

      await apiRequest<AuthSession>("/auth/active-partner", {
        method: "PATCH",
        body: JSON.stringify({ partner_id: partner.id }),
      });
      router.replace("/dashboard");
      router.refresh();
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Pendaftaran belum dapat diproses. Silakan coba kembali.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <div className={styles.steps} aria-label="Tahap pendaftaran">
        <span className={step >= 1 ? styles.stepActive : ""}><b>1</b> Akun</span>
        <i />
        <span className={step >= 2 ? styles.stepActive : ""}><b>2</b> Bisnis</span>
      </div>

      <form className={`${styles.form} ${step === 1 ? "" : styles.hidden}`} id="partner-account-form" onSubmit={nextStep}>
        <label className={styles.field}><span>Nama lengkap</span><input autoComplete="name" minLength={2} name="full_name" placeholder="Nama penanggung jawab" required /></label>
        <label className={styles.field}><span>Email kerja</span><input autoComplete="email" name="email" placeholder="nama@perusahaan.id" required type="email" /></label>
        <div className={styles.twoColumns}>
          <label className={styles.field}><span>Password</span><input autoComplete="new-password" minLength={12} name="password" placeholder="Minimal 12 karakter" required type="password" /></label>
          <label className={styles.field}><span>Konfirmasi</span><input autoComplete="new-password" minLength={12} name="password_confirmation" placeholder="Ulangi password" required type="password" /></label>
        </div>
        <p className={styles.helper}>Gunakan minimal tiga kategori karakter: huruf besar, huruf kecil, angka, atau simbol.</p>
        {error && step === 1 ? <p className={styles.error} role="alert">{error}</p> : null}
        <button className={styles.submit} type="submit">Lanjutkan data bisnis</button>
      </form>

      <form className={`${styles.form} ${step === 2 ? "" : styles.hidden}`} onSubmit={submit}>
        <div className={styles.twoColumns}>
          <label className={styles.field}><span>Nama brand</span><input minLength={2} name="display_name" placeholder="Contoh: HomeCare Jakarta" required /></label>
          <label className={styles.field}><span>Nama legal</span><input minLength={2} name="legal_name" placeholder="PT / CV / nama usaha" required /></label>
        </div>
        <div className={styles.twoColumns}>
          <label className={styles.field}><span>Jenis mitra</span><select defaultValue="service_provider" name="partner_type"><option value="service_provider">Penyedia home service</option><option value="company">Perusahaan</option><option value="store">Toko / merchant</option><option value="clinic">Klinik</option><option value="individual">Profesional individu</option></select></label>
          <label className={styles.field}><span>Nomor telepon</span><input minLength={7} name="contact_phone" placeholder="08xxxxxxxxxx" required /></label>
        </div>
        <label className={styles.field}><span>Alamat operasional</span><input minLength={5} name="address_line" placeholder="Jalan, nomor, kecamatan" required /></label>
        <div className={styles.threeColumns}>
          <label className={styles.field}><span>Kota</span><input minLength={2} name="city" required /></label>
          <label className={styles.field}><span>Provinsi</span><input minLength={2} name="province" required /></label>
          <label className={styles.field}><span>Kode pos</span><input name="postal_code" /></label>
        </div>
        <label className={styles.field}><span>Deskripsi usaha</span><textarea maxLength={2000} name="description" placeholder="Jelaskan produk atau layanan utama." rows={3} /></label>
        <label className={styles.checkbox}><input required type="checkbox" /> <span>Saya menyetujui proses verifikasi dan kebijakan kemitraan Yoru.</span></label>
        {error && step === 2 ? <p className={styles.error} role="alert">{error}</p> : null}
        <div className={styles.actionRow}><button className={styles.secondary} disabled={pending} onClick={() => setStep(1)} type="button">Kembali</button><button className={styles.submit} disabled={pending} type="submit">{pending ? "Membuat workspace..." : "Daftar sebagai mitra"}</button></div>
      </form>
      <p className={styles.switchText}>Sudah punya akun? <Link href="/login">Masuk ke dashboard</Link></p>
    </div>
  );
}
