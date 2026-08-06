import type { Metadata } from "next";
import { BookingsScreen } from "@/components/bookings-screen";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
export const metadata: Metadata = { title: "Booking" };
export default function BookingsPage() {
  return (
    <>
      <SiteHeader />
      <BookingsScreen />
      <SiteFooter />
    </>
  );
}
