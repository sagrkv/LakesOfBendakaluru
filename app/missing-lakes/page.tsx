import type { Metadata } from "next";
import PageTop from "@/components/PageTop";
import SiteFooter from "@/components/SiteFooter";
import { printedYearsFor } from "@/components/lake/years/maps";
import Explorer from "@/components/missing/Explorer";
import { hasNewer, tag, tally } from "@/components/missing/filter";
import MissingHero from "@/components/missing/MissingHero";
import { getMissing } from "@/components/missing/read";
import RecordNote from "@/components/missing/RecordNote";
import { formatCount } from "@/lib/format";
import { getHero } from "@/lib/lakes";

/** Rows rendered with the page; the rest of the list loads on demand. */
const TOP = 40;

export function generateMetadata(): Metadata {
  return {
    title: "Missing lakes of Bangalore - Lakes of Bendakaluru",
    description: `In 2018 the state recorded ${formatCount(getMissing().length)} lakes in and around Bengaluru as still there, but no map we have draws them. What the record says about each one.`,
  };
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export default function MissingLakesPage() {
  const missing = getMissing();
  const sizes = missing.flatMap((lake) => (lake.acres ? [lake.acres] : []));
  const { width, height } = getHero();

  return (
    <>
      <PageTop />
      <main className="overflow-x-clip">
        <MissingHero
          total={missing.length}
          median={sizes.length ? median(sizes) : 0}
          newer={missing.filter(hasNewer).length}
          withoutExtent={missing.length - sizes.length}
          width={width}
          height={height}
        />
        <Explorer
          top={missing.slice(0, TOP)}
          counts={tally(missing.map(tag))}
          total={missing.length}
          note={<RecordNote lakes={missing} />}
          printed={printedYearsFor(missing)}
        />
      </main>
      <SiteFooter />
    </>
  );
}
