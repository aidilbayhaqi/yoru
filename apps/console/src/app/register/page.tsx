import Link from "next/link";

import { ConsoleRegistrationForm } from "@/components/console-registration-form";
import styles from "@/components/auth-shell.module.css";

export default function PartnerRegistrationPage() {
  return (
    <main className={styles.shell}>
      <section className={styles.brandPanel}>
        <Link className={styles.logo} href="/login"><span className={styles.logoMark}>Y</span><span><strong>Yoru</strong><small>Partner onboarding</small></span></Link>
        <div className={styles.brandCopy}>
          <span className={styles.eyebrow}>Grow with Yoru</span>
          <h1>Bangun operasi bisnis dalam satu workspace.</h1>
          <p>Pendaftaran ini membuat akun owner dan draft aplikasi partner. Setelah masuk, lengkapi dokumen, area layanan, katalog, serta data operasional untuk proses verifikasi.</p>
          <div className={styles.featureGrid}><div className={styles.feature}><b>Commerce</b><span>Produk, layanan, stok, harga, dan media katalog.</span></div><div className={styles.feature}><b>Home service</b><span>Availability, booking, assignment, OTP, dan tracking.</span></div><div className={styles.feature}><b>Finance</b><span>Settlement, payout, refund, ledger, dan analitik.</span></div></div>
        </div>
        <span className={styles.brandFooter}>Pendaftaran publik hanya untuk kemitraan · role admin dibuat terkontrol</span>
      </section>
      <section className={styles.formPanel}><div className={styles.card}><header className={styles.cardHeader}><span>Partner registration</span><h2>Daftarkan bisnis Anda</h2><p>Isi akun penanggung jawab dan profil usaha. Password minimal 12 karakter.</p></header><ConsoleRegistrationForm /></div></section>
    </main>
  );
}
