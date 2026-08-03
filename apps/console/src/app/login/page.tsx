import Link from "next/link";

import { ConsoleLoginForm } from "@/components/console-login-form";
import styles from "@/components/auth-shell.module.css";

export default function ConsoleLoginPage() {
  return (
    <main className={styles.shell}>
      <section className={styles.brandPanel}>
        <Link className={styles.logo} href="/login"><span className={styles.logoMark}>Y</span><span><strong>Yoru</strong><small>Commerce & Service OS</small></span></Link>
        <div className={styles.brandCopy}>
          <span className={styles.eyebrow}>Operational intelligence</span>
          <h1>Satu sistem untuk commerce, home service, dan finance.</h1>
          <p>Kelola katalog, booking, tenaga lapangan, transaksi, settlement, serta pengawasan platform dengan akses yang dipisahkan secara ketat.</p>
          <div className={styles.featureGrid}><div className={styles.feature}><b>Partner OS</b><span>Katalog, stok, order, booking, tim, dan cashflow.</span></div><div className={styles.feature}><b>Platform control</b><span>Verifikasi, monitoring, ledger, dispute, security, dan audit.</span></div><div className={styles.feature}><b>RBAC native</b><span>Menu dan aksi berasal dari role serta permission server.</span></div></div>
        </div>
        <span className={styles.brandFooter}>Yoru Platform · secure operational console</span>
      </section>
      <section className={styles.formPanel}>
        <div className={styles.card}>
          <span className={styles.statusPill}>Identity service operational</span>
          <header className={styles.cardHeader}><span>Secure sign in</span><h2>Selamat datang kembali</h2><p>Masuk menggunakan akun kemitraan atau super admin yang sudah terverifikasi.</p></header>
          <ConsoleLoginForm />
          <div className={styles.demoNote}><strong>Super admin tidak dapat didaftarkan dari web.</strong> Gunakan bootstrap terkontrol agar role sensitif tidak terekspos melalui public registration.</div>
        </div>
      </section>
    </main>
  );
}
