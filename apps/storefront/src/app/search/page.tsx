import type { Metadata } from "next";

import { SearchResults } from "@/components/search-results";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

type SearchMode = "query" | "ai" | "image";
type Props = {
  searchParams: Promise<{
    q?: string | string[];
    mode?: string | string[];
  }>;
};

export const metadata: Metadata = { title: "Search" };

export default async function SearchPage({ searchParams }: Props) {
  const values = await searchParams;
  const query = Array.isArray(values.q) ? (values.q[0] ?? "") : (values.q ?? "");
  const rawMode = Array.isArray(values.mode) ? values.mode[0] : values.mode;
  const mode: SearchMode = rawMode === "ai" || rawMode === "image" ? rawMode : "query";

  return (
    <>
      <SiteHeader />
      <SearchResults mode={mode} query={query} />
      <SiteFooter />
    </>
  );
}
