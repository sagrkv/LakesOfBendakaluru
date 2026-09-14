import type { Metadata } from "next";
import SiteFooter from "@/components/SiteFooter";
import ForgottenHero from "@/components/forgotten/ForgottenHero";
import LargestLost from "@/components/forgotten/LargestLost";
import LostList from "@/components/forgotten/LostList";
import OccupiedFilter from "@/components/forgotten/OccupiedFilter";
import PageTop from "@/components/PageTop";
import { getLost } from "@/components/forgotten/lost";
import { formatCount } from "@/lib/format";

export function generateMetadata(): Metadata {
  const { lost } = getLost();
  return {
    title: "Forgotten lakes of Bendakaluru",
    description: `${formatCount(lost.length)} lakes in and around Bengaluru are on record as gone. Where they were, how big they were and what stands on each site now.`,
  };
}

export default function ForgottenPage() {
  const { lost, acres, withoutExtent, counts } = getLost();

  return (
    <>
      <PageTop />
      <main className="overflow-x-clip">
        <ForgottenHero lost={lost} acres={acres} withoutExtent={withoutExtent} />
        <LargestLost lakes={lost.filter((lake) => lake.acres).slice(0, 8)} />

        <section className="page-x py-16 md:py-26">
          <div className="grid grid-cols-12 gap-x-6">
            <div className="col-span-12 lg:col-span-4">
              <h2 className="font-serif text-[48px] md:text-[64px] leading-[0.95] text-balance">
                What stands on them now
              </h2>
              <p className="mt-6 max-w-[34rem]">
                What surveyors found on each site in 2018. Choose a group to list only those lakes.
              </p>
            </div>
            <OccupiedFilter counts={counts} total={lost.length}>
              <LostList lakes={lost} />
            </OccupiedFilter>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
