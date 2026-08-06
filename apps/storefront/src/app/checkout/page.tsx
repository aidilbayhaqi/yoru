import type { Metadata } from "next";
import { Suspense } from "react";
import { CheckoutFlow } from "@/components/checkout-flow";
import { SiteHeader } from "@/components/site-header";
export const metadata: Metadata = { title: "Checkout" };
export default function CheckoutPage() {
  return (
    <>
      <SiteHeader />
      <Suspense
        fallback={
          <div className="page-state" role="status" aria-live="polite">
            Menyiapkan checkout...
          </div>
        }
      >
        <CheckoutFlow />
      </Suspense>
    </>
  );
}
