import type { Metadata } from "next";
import type { CSSProperties } from "react";
import PageTop from "@/components/PageTop";
import SiteFooter from "@/components/SiteFooter";
import { printedYearsFor } from "@/components/lake/years/maps";
import Explorer from "@/components/past/Explorer";
import { tag, tally } from "@/components/past/filter";
import PastHero from "@/components/past/PastHero";
import { getPast } from "@/components/past/read";
import { formatCount } from "@/lib/format";
import { getHero } from "@/lib/lakes";
import { share } from "@/lib/share";

/** Rows rendered with the page; the rest of the list loads on demand. */
const TOP = 40;

export function generateMetadata(): Metadata {
  return share(
    "Once upon a kere - Lakes of Bendakaluru",
    `${formatCount(getPast().length)} lakes in and around Bengaluru are on record as gone. See when each one went, how big it was, and what was built where it used to be.`,
    "/once-upon-a-kere",
  );
}

export default function OnceUponAKerePage() {
  const past = getPast();
  const acres = past.reduce((sum, lake) => sum + (lake.acres ?? 0), 0);
  const { width, height } = getHero();

  return (
    <>
      <PageTop />
      <main className="overflow-x-clip" style={{ "--paper": "#F2502B" } as CSSProperties}>
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
