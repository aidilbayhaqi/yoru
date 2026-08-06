import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ProductDetail } from "@/components/product-detail";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { productBySlug } from "@/lib/storefront-domain";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  return { title: productBySlug(slug)?.name ?? "Produk" };
}

export default async function ProductPage({ params }: Props) {
  const { slug } = await params;
  const product = productBySlug(slug);
  if (!product) notFound();
  return (
    <>
      <SiteHeader />
      <ProductDetail product={product} />
      <SiteFooter />
    </>
  );
}
