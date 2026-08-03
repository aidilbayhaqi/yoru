import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="commerce-footer">
      <div className="commerce-footer__grid">
        <div className="footer-brand">
          <Link className="commerce-brand" href="/">
            <span className="commerce-brand__mark">Y</span><span>Yoru</span>
          </Link>
          <p>Curated commerce and trusted home service, designed as one connected customer journey.</p>
          <span className="footer-edition">Yoru Storefront · Phase 9 experience</span>
        </div>
        <div>
          <h3>Shop</h3>
          <Link href="/products">All products</Link>
          <Link href="/collections">Collections</Link>
          <Link href="/deals">Deals</Link>
          <Link href="/wishlist">Wishlist</Link>
        </div>
        <div>
          <h3>Services</h3>
          <Link href="/services">Home service</Link>
          <Link href="/service-areas">Service areas</Link>
          <Link href="/assistant">Yoru Advisor</Link>
          <Link href="/bookings">My bookings</Link>
        </div>
        <div>
          <h3>Support</h3>
          <Link href="/help">Help center</Link>
          <Link href="/history">Transaction history</Link>
          <Link href="/orders">My orders</Link>
          <Link href="/account">Account</Link>
        </div>
      </div>
      <div className="commerce-footer__bottom">
        <span>© 2026 Yoru Platform</span>
        <span>Prices, stock, serviceability, and payment states are verified at transaction time.</span>
      </div>
    </footer>
  );
}
