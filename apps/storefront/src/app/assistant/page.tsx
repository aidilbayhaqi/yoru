import type { Metadata } from "next";
import { AssistantPanel } from "@/components/assistant-panel";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
export const metadata: Metadata = { title: "Yoru Advisor" };
export default function AssistantPage() { return <><SiteHeader /><AssistantPanel /><SiteFooter /></>; }
