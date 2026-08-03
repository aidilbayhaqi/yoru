import type { Metadata } from "next";
import { CustomerAccount } from "@/components/customer-account";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
export const metadata: Metadata = { title: "Akun Saya" };
export default function AccountPage() { return <><SiteHeader /><CustomerAccount /><SiteFooter /></>; }
