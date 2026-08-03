import type { Metadata } from "next";
import Link from "next/link";

import { Icon } from "@/components/icons";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = { title: "Help Center" };

const topics = [
  ["Orders & delivery", "Track an order, understand fulfillment states, or review delivery details.", "/orders"],
  ["Bookings & professionals", "Review schedules, professional assignment, OTP, and service status.", "/bookings"],
  ["Payments & refunds", "Understand payment status, retry rules, refunds, and dispute entry points.", "/history"],
  ["Account & security", "Manage your identity session, active account, and access history.", "/account"],
];

export default function HelpPage() {
  return (
    <>
      <SiteHeader />
      <main className="v5-content-page">
        <section className="v5-page-hero">
          <p className="section-eyebrow">Help center</p><h1>Find the next action, not another dead end.</h1>
          <p>Support content should eventually map to real policy versions and support tickets. This page creates the navigational foundation.</p>
        </section>
        <div className="help-topic-grid">
          {topics.map(([title, detail, href], index) => (
            <Link href={href} key={title}>
              <span>0{index + 1}</span><div><h2>{title}</h2><p>{detail}</p></div><Icon name="arrow" width="18" />
            </Link>
          ))}
        </div>
        <section className="help-contact-card">
          <span><Icon name="sparkle" width="22" /></span>
          <div><h2>Need help choosing?</h2><p>Use Yoru Assistant for discovery questions. Transaction and dispute decisions must follow server state and support policy.</p></div>
          <Link className="primary-button" href="/assistant">Open advisor</Link>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
