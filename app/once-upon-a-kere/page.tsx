import type { Metadata } from "next";
import PageTop from "@/components/PageTop";
import SiteFooter from "@/components/SiteFooter";
import { printedYearsFor } from "@/components/lake/years/maps";
import Explorer from "@/components/past/Explorer";
import { tag, tally } from "@/components/past/filter";
import PastHero from "@/components/past/PastHero";
import { getPast } from "@/components/past/read";
import { formatCount } from "@/lib/format";
import { getHero } from "@/lib/lakes";

/** Rows rendered with the page; the rest of the list loads on demand. */
const TOP = 40;

export function generateMetadata(): Metadata {
  return {
    title: "Once upon a kere - Lakes of Bendakaluru",
    description: `${formatCount(getPast().length)} lakes in and around Bengaluru are on record as gone. When each one went, and what took its place.`,
  };
}

export default function OnceUponAKerePage() {
  const past = getPast();
  const acres = past.reduce((sum, lake) => sum + (lake.acres ?? 0), 0);
  const { width, height } = getHero();

  return (
    <>
      <PageTop />
      <main className="overflow-x-clip">
        <PastHero
          total={past.length}
          acres={acres}
          withoutExtent={past.filter((lake) => !lake.acres).length}
          holes={past.filter((lake) => lake.xy).length}
          width={width}
          height={height}
        />
        <Explorer
          top={past.slice(0, TOP)}
          counts={tally(past.map(tag))}
          total={past.length}
          printed={printedYearsFor(past)}
        />
      </main>
      <SiteFooter />
    </>
  );
}
