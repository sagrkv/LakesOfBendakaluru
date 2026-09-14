import type { Metadata } from "next";
import type { CSSProperties } from "react";
import PageTop from "@/components/PageTop";
import SiteFooter from "@/components/SiteFooter";
import KindKey from "@/components/timeline/KindKey";
import { resolveSources } from "@/components/timeline/resolve";
import { SOURCES } from "@/components/timeline/sources";
import { tally } from "@/components/timeline/tally";
import Timeline from "@/components/timeline/Timeline";
import { formatCount } from "@/lib/format";

const TITLE = "Lakes on record, 1800 to today";

export function generateMetadata(): Metadata {
  const { total, oldest, newest } = tally(SOURCES);
  return {
    title: `${TITLE} - Lakes of Bendakaluru`,
    description: `Every map, census, satellite photo and report of Bengaluru's lakes we know of: ${formatCount(total)} records from ${oldest} to ${newest}, what each one tells us, our copy and the original.`,
  };
}

export default function TimelinePage() {
  const sources = resolveSources(SOURCES);
  const { total, oldest, newest, counts } = tally(SOURCES);

  return (
    <>
      <PageTop />
      <main className="overflow-x-clip" style={{ "--paper": "#11A3B5" } as CSSProperties}>
        <section className="page-x pt-10 pb-16 md:pt-16 md:pb-26">
          <h1 className="max-w-[14ch] font-serif text-[64px] leading-[0.86] text-balance md:text-[96px]">
            <span className="highlight">{TITLE}</span>
          </h1>
          <p className="mt-6 max-w-[40rem]">
            We know of {formatCount(total)} records of Bengaluru&rsquo;s lakes, from {oldest} to {newest}. They run down
            the page oldest first. Each one says what it tells us about a lake, with our copy and a link to the original.
          </p>
          <div className="mt-8">
            <KindKey counts={counts} />
          </div>
        </section>

        <section aria-label="Timeline" className="page-x pb-16 md:pb-26">
          <Timeline sources={sources} />
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
