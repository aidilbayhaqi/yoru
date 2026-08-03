import type { Metadata } from "next";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { TransactionHistory } from "@/components/transaction-history";

export const metadata: Metadata = {
  title: "Riwayat Transaksi",
};

export default function HistoryPage() {
  return (
    <>
      <SiteHeader />
      <TransactionHistory />
      <SiteFooter />
    </>
  );
}
