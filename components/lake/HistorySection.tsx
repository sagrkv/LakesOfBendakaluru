import type { LakeRecord } from "@/lib/lake";
import Fact from "./Fact";
import Section from "./Section";
import { sourcesOf } from "./sources";
import { sentence, who } from "./words";

/** What the 2018 survey saw on and around the site. Dated facts live on the timeline. */
export default function HistorySection({ lake }: { lake: LakeRecord }) {
  const h = lake.history;
  const gone = lake.status !== "exists";
  const empty = !(h?.nowOccupiedBy || h?.convertedBy?.length || h?.surroundings2018 || h?.remarks2018);

  return (
    <Section
      id="the-site"
      title={gone ? "What took its place" : "Around it"}
      missing={gone ? "Nothing on record about what took its place." : "Nothing on record about what is around it."}
      empty={empty}
    >
      {h?.nowOccupiedBy ? (
        <Fact label="On the site now" value={h.nowOccupiedBy} sources={sourcesOf(h, "nowOccupiedBy")} />
      ) : null}
      {h?.convertedBy?.length ? (
        <Fact label="Filled in by" sources={sourcesOf(h, "convertedBy")}>
          <p>{sentence(who(h.convertedBy))}</p>
        </Fact>
      ) : null}
      {h?.surroundings2018 ? (
        <Fact label="Around it in 2018" sources={sourcesOf(h, "surroundings2018")}>
          <p>{h.surroundings2018}</p>
        </Fact>
      ) : null}
      {h?.remarks2018 ? (
        <Fact label="Surveyor's note, 2018" sources={sourcesOf(h, "remarks2018")}>
          <p>{h.remarks2018}</p>
        </Fact>
      ) : null}
    </Section>
  );
}
