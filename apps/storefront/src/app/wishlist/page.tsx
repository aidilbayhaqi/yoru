import type { Metadata } from "next";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { WishlistScreen } from "@/components/wishlist-screen";

export const metadata: Metadata = { title: "Wishlist" };

export default function WishlistPage() {
  return (
    <>
      <SiteHeader />
      <WishlistScreen />
      <SiteFooter />
    </>
  );
}
