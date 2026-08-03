import type { Metadata } from "next";
import type { ReactNode } from "react";

import { StorefrontProvider } from "@/lib/storefront-store";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Yoru — Commerce & Home Service", template: "%s · Yoru" },
  description: "Belanja produk terkurasi dan pesan layanan profesional di rumah dalam satu pengalaman Yoru.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="id"><body><StorefrontProvider>{children}</StorefrontProvider></body></html>;
}
