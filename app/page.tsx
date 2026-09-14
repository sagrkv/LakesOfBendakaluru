import type { Metadata } from "next";
import { connection } from "next/server";
import NoOpener from "@/components/home/NoOpener";
import { pickOpener } from "@/components/home/opener";
import Opening from "@/components/home/Opening";
import SiteFooter from "@/components/SiteFooter";

export const metadata: Metadata = {
  title: { absolute: "Lakes of Bendakaluru" },
  description:
    "A different Bangalore lake every visit, cut out at its real shape: how big it is, who looks after it, how clean the water is and how much is built over.",
};

export default async function HomePage() {
  // A new random lake on every request, never one frozen at build time.
  await connection();
  const opener = pickOpener();

  return (
    <>
      <main>{opener ? <Opening opener={opener} /> : <NoOpener />}</main>
      <SiteFooter />
    </>
  );
}
