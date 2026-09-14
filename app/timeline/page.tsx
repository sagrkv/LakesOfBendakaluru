import type { Metadata } from "next";
import type { CSSProperties } from "react";
import PageTop from "@/components/PageTop";
import SiteFooter from "@/components/SiteFooter";
import Legend from "@/components/timeline/Legend";
import NotPublic from "@/components/timeline/NotPublic";
import { resolveSources } from "@/components/timeline/resolve";
import SourceList from "@/components/timeline/SourceList";
import { SOURCES } from "@/components/timeline/sources";
import { tally } from "@/components/timeline/tally";
import Timeline from "@/components/timeline/Timeline";
import { formatCount } from "@/lib/format";

const TITLE = "Lakes on record, 1800 to today";

export function generateMetadata(): Metadata {
  const { total, oldest, newest } = tally(SOURCES);
  return {
    title: `${TITLE} - Lakes of Bendakaluru`,
    description: `Every map, census, satellite photo and report of Bengaluru's lakes we know of: ${formatCount(total)} records from ${oldest} to ${newest}, what each one tells us, and where to open it.`,
  };
}

export default function TimelinePage() {
  const sources = resolveSources(SOURCES);
  const { total, oldest, newest, oldestOnSite, counts, undated } = tally(SOURCES);

  return (
    <>
      <PageTop />
      <main className="overflow-x-clip" style={{ "--paper": "#11A3B5" } as CSSProperties}>
        <section className="page-x pt-10 md:pt-16 pb-16 md:pb-26">
          <div className="grid grid-cols-12 gap-x-6 gap-y-6 items-end">
            <h1 className="col-span-12 lg:col-span-7 font-serif text-[64px] md:text-[96px] leading-[0.86] text-balance">
              <span className="highlight">{TITLE}</span>
            </h1>
            <p className="col-span-12 md:col-span-8 lg:col-span-5 max-w-[34rem]">
              We know of {formatCount(total)} records of Bengaluru&rsquo;s lakes, from {oldest} to {newest}.{" "}
              {formatCount(counts["on-site"])} of them are on this site, and the oldest of those is from {oldestOnSite}.{" "}
              {formatCount(counts.found)} are public but not added yet. {formatCount(counts["not-public"])} are known to
              exist but are not public. {formatCount(undated)} have no year on record.
            </p>
          </div>
        </section>

        <section aria-labelledby="timeline-title" className="page-x pb-16 md:pb-26">
          <div className="flex flex-wrap items-baseline justify-between gap-x-10 gap-y-4 mb-10">
            <h2 id="timeline-title" className="font-serif text-[26px] md:text-[36px] leading-none">
              <span className="highlight">Year by year</span>
            </h2>
            <Legend counts={counts} />
          </div>
          <Timeline sources={sources} />
        </section>

        <section aria-labelledby="closed-title" className="page-x pb-16 md:pb-26">
          <h2 id="closed-title" className="font-serif text-[26px] md:text-[36px] leading-none">
            <span className="highlight">Not public</span>
          </h2>
          <p className="mt-2 label font-normal text-missing">
            These {formatCount(counts["not-public"])} records are known to exist, but no copy is public for anyone to use.
          </p>
          <NotPublic sources={sources} />
        </section>

        <section aria-labelledby="list-title" className="page-x pb-16 md:pb-26">
          <h2 id="list-title" className="font-serif text-[26px] md:text-[36px] leading-none">
            <span className="highlight">Every record, oldest first</span>
          </h2>
          <p className="mt-2 label font-normal text-missing">
            The same {formatCount(total)} records as the timeline, with the same links.
          </p>
          <SourceList sources={sources} />
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
