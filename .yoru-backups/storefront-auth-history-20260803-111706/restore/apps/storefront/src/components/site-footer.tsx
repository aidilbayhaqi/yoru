import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="commerce-footer">
      <div className="commerce-footer__grid">
        <div className="footer-brand">
          <Link className="commerce-brand" href="/">
            <span className="commerce-brand__mark">Y</span>
            <span>Yoru</span>
          </Link>
          <p>
            Satu tempat untuk menemukan produk terkurasi dan layanan profesional yang datang ke
            rumah.
          </p>
        </div>
        <div>
          <h3>Jelajahi</h3>
          <Link href="/products">Produk</Link>
          <Link href="/services">Home service</Link>
          <Link href="/assistant">Yoru Advisor</Link>
        </div>
        <div>
          <h3>Akun</h3>
          <Link href="/account">Profil</Link>
          <Link href="/orders">Pesanan</Link>
          <Link href="/bookings">Booking</Link>
        </div>
        <div>
          <h3>Kepercayaan</h3>
          <span>Partner terverifikasi</span>
          <span>Pembayaran aman</span>
          <span>Dukungan dan dispute</span>
        </div>
      </div>
      <div className="commerce-footer__bottom">
        <span>© 2026 Yoru Platform</span>
        <span>Commerce dan home service dalam satu pengalaman.</span>
      </div>
    </footer>
  );
}
