import type { Metadata } from "next";
import type { ReactNode } from "react";

import { CommerceOverlays } from "@/components/commerce-overlays";
import { StorefrontProvider } from "@/lib/storefront-store";

import "./globals.css";
import "./experience.css";
import "./polish-v8.css";

import "./system-v9.css";
import "./visual-repair-v9.2.css";
import "./gold-design-system-v9.5.css";
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
