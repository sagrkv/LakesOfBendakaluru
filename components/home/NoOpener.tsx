import Link from "next/link";
import Wordmark from "@/components/Wordmark";

/** When no lake can open the site, say so and send people to the map, which lists every lake. */
export default function NoOpener() {
  return (
    <section className="page-x min-h-[80svh] pt-4 pb-16 md:pt-10 md:pb-26">
      <Wordmark />
      <h1 className="mt-16 max-w-[12ch] font-serif text-[64px] leading-[0.95] font-normal md:mt-26">
        <span className="highlight">No lake to show right now</span>
      </h1>
      <p className="mt-6 max-w-[45ch]">The cut-out lakes for this page are not ready. Every lake is still on the map.</p>
      <Link href="/map" className="button-ink mt-10 text-[28px] md:text-[38px]">
        See all lakes
      </Link>
    </section>
  );
}
