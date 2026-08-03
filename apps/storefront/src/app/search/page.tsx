import type { Metadata } from "next";
import { SearchResults } from "@/components/search-results";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
type Props = { searchParams: Promise<{ q?: string | string[] }> };
export const metadata: Metadata = { title: "Pencarian" };
export default async function SearchPage({ searchParams }: Props) {
  const values = await searchParams;
  const query = Array.isArray(values.q) ? values.q[0] ?? "" : values.q ?? "";
  return <><SiteHeader /><SearchResults query={query} /><SiteFooter /></>;
}
