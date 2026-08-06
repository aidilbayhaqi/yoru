import type { Metadata } from "next";
import { CartScreen } from "@/components/cart-screen";
import { SiteHeader } from "@/components/site-header";
export const metadata: Metadata = { title: "Cart" };
export default function CartPage() {
  return (
    <>
      <SiteHeader />
      <CartScreen />
    </>
  );
}
