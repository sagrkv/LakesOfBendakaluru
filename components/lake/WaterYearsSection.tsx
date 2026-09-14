import type { LakeRecord } from "@/lib/lake";
import { formatAcres } from "@/lib/format";
import Fact, { Note } from "./Fact";
import Section from "./Section";
import ShareBars from "./ShareBars";
import YearlyChart from "./YearlyChart";
import { resolve, sourcesOf } from "./sources";
import { percent } from "./words";

export default function WaterYearsSection({ lake }: { lake: LakeRecord }) {
  const water = lake.water;
  const presence = water?.presence;
  const years = water?.yearly ?? [];
  const current = water?.current ?? [];
  const everWet = years.some((d) => d.waterAcres > 0);
  const lastYear = years[years.length - 1];
  const rough = presence?.lowConfidence || current.some((c) => c.lowConfidence);
  const empty = !presence && years.length === 0 && current.length === 0;

  return (
    <Section id="water-over-the-years" title="Water over the years" missing="No satellite record of its water." empty={empty}>
      {presence ? (
        <Fact
          label="Water seen by satellite since 1984"
          value={`${percent(presence.occurrencePct)} of the time`}
          sources={sourcesOf(water, "presence")}
        >
          {presence.firstYear && presence.lastYear ? (
            <p>
              First seen with water in {presence.firstYear}, last in {presence.lastYear}.
            </p>
          ) : (
            <p>Never seen holding water.</p>
          )}
          {presence.lostPct > 0 || presence.gainedPct > 0 ? (
            <Note>
              {percent(presence.lostPct)} of its water area has since gone dry; {percent(presence.gainedPct)} is new water
            </Note>
          ) : null}
        </Fact>
      ) : null}

      {lastYear && everWet ? (
        <Fact label={`Water in ${lastYear.year}`} value={`${formatAcres(lastYear.waterAcres)} acres`} sources={sourcesOf(water, "yearly")} />
      ) : null}

      {years.length > 1 ? (
        everWet ? (
          <Fact
            wide
            label={`Acres of water each year, ${years[0].year} to ${lastYear.year}`}
            sources={sourcesOf(water, "yearly")}
          >
            <YearlyChart years={years} outlineAcres={lake.size?.outlineAcres} />
          </Fact>
        ) : (
          <Fact label={`Water each year, ${years[0].year} to ${lastYear.year}`} sources={sourcesOf(water, "yearly")}>
            <p>No open water seen in any year.</p>
          </Fact>
        )
      ) : null}

      {current.length ? (
        <Fact wide label="What covers it now" sources={resolve(current.map((c) => c.source))}>
          <div className="pt-2">
            <ShareBars seasons={current} />
          </div>
          <p className="mt-4 max-w-[65ch]">
            Floating weed looks like land to the older satellite record, so a lake covered in weed can look dry in the
            years above.
          </p>
          {rough ? <Note>The lake is small for these images, so treat the shares as rough.</Note> : null}
        </Fact>
      ) : null}
    </Section>
  );
}
