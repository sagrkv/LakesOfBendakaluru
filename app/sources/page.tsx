import type { Metadata } from "next";
import type { CSSProperties } from "react";
import SiteFooter from "@/components/SiteFooter";
import PageTop from "@/components/PageTop";
import { formatCount } from "@/lib/format";
import { getSources } from "@/lib/lakes";
import { share } from "@/lib/share";
import { groupByPublisher, withKeys } from "./catalog";
import CreditLines from "./CreditLines";
import { requiredCredits } from "./required";
import Section from "./Section";
import SourceGroups from "./SourceGroups";

export const metadata: Metadata = share(
  "Sources and credits - Lakes of Bendakaluru",
  "Every source behind Lakes of Bendakaluru, grouped by publisher, with its date, its licence and the credit line it asks for.",
  "/sources",
);

export default function SourcesPage() {
  const sources = withKeys(getSources());
  const credits = requiredCredits(sources);
  const groups = groupByPublisher(sources);

  return (
    <>
      <PageTop />
      <main style={{ "--paper": "#2FA35B" } as CSSProperties}>
        <section className="page-x pt-10 md:pt-16">
          <div className="grid grid-cols-12 gap-x-6">
            <h1 className="col-span-12 font-serif text-[64px] md:text-[96px] leading-[0.86] text-balance">
              <span className="highlight">Sources and credits</span>
            </h1>
            <p className="col-span-12 md:col-span-8 lg:col-span-6 mt-6">
              Every fact on this site comes from a published source. Each one is listed here once, with its date, its
              licence and the credit line it asks for.
            </p>
          </div>
        </section>

        <Section title="Credit lines" intro="These sources ask to be credited wherever their data is shown.">
          <CreditLines credits={credits} />
        </Section>

        <Section title="How the sources fit together">
          <div className="max-w-[40rem] space-y-6">
            <p>
              Every lake has one permanent id that we own. It stays the same when a lake is renamed or a source is
              rebuilt, so a lake&apos;s address on this site does not change.
            </p>
            <p>
              When two sources disagree, we keep both and label each one. Area is the usual case: the drawn outline,
              the land record and the 2018 survey often give three different numbers.
            </p>
            <p>
              Sources are matched to lakes by location first. A name only decides between lakes that are already
              close, because dozens of lake names repeat across Bengaluru.
            </p>
          </div>
        </Section>

        <Section title="Every source" intro={`${formatCount(sources.length)} sources, grouped by publisher.`}>
          <SourceGroups groups={groups} />
        </Section>
      </main>
      <SiteFooter />
    </>
  );
}
