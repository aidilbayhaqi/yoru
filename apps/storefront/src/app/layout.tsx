import type { Metadata } from "next";
import type { ReactNode } from "react";

import { CommerceOverlays } from "@/components/commerce-overlays";
import { StorefrontProvider } from "@/lib/storefront-store";

import "./globals.css";
import "./experience.css";

export const metadata: Metadata = {
  title: {
    default: "Yoru — Curated commerce & trusted home service",
    template: "%s — Yoru",
  },
  description:
    "Belanja produk terkurasi, pesan home service, dan temukan pilihan yang cocok bersama Yoru.",
};

const themeScript = `
  try {
    const stored = localStorage.getItem("yoru-theme");
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    document.documentElement.dataset.theme = stored === "dark" || stored === "light" ? stored : preferred;
  } catch {
    document.documentElement.dataset.theme = "light";
  }
`;

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <StorefrontProvider>
          {children}
          <CommerceOverlays />
        </StorefrontProvider>
      </body>
    </html>
  );
}
