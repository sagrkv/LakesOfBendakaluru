import type { LakeRecord } from "@/lib/lake";
import Fact, { Note } from "./Fact";
import Section from "./Section";
import { sourcesOf } from "./sources";
import { joinList, sentence, who } from "./words";

export default function HistorySection({ lake }: { lake: LakeRecord }) {
  const h = lake.history;
  const maps = ([1927, 1945, 1955] as const).filter((year) => h?.[`onMap${year}`]);
  const empty = !h || !Object.keys(h).some((key) => key !== "src");

  return (
    <Section id="history" title="Its history" missing="No history on record." empty={empty}>
      {h?.yearBuilt !== undefined ? (
        <Fact label="Built" value={String(h.yearBuilt)} sources={sourcesOf(h, "yearBuilt")}>
          <Note>As recorded in the 2018 lake survey</Note>
        </Fact>
      ) : null}
      {h?.rejuvenated !== undefined ? (
        <Fact
          label="Restored"
          value={h.rejuvenated ? (h.yearRejuvenated ? String(h.yearRejuvenated) : "Yes") : "Not restored"}
          sources={sourcesOf(h, "rejuvenated", "yearRejuvenated")}
        />
      ) : null}
      {maps.length ? (
        <Fact
          label="On old survey maps"
          value={joinList(maps.map(String))}
          sources={sourcesOf(h, ...maps.map((year) => `onMap${year}`), "knownOnlyFromOldMap")}
        >
          {h?.knownOnlyFromOldMap ? (
            <p>
              Known only from the old map; no lake has been seen here since.
              {h.oldMapConfidence ? ` The match to the map is ${h.oldMapConfidence === "high" ? "sure" : "likely"}.` : ""}
            </p>
          ) : (
            <Note>Drawn on the {maps.length === 1 ? "map" : "maps"} of those years</Note>
          )}
        </Fact>
      ) : null}
      {h?.lastSeenWithWater !== undefined ? (
        <Fact label="Last seen with water" value={String(h.lastSeenWithWater)} sources={sourcesOf(h, "lastSeenWithWater")}>
          <Note>By satellite, which has records from 1984</Note>
        </Fact>
      ) : null}
      {h?.goneBy !== undefined ? <Fact label="Gone by" value={String(h.goneBy)} sources={sourcesOf(h, "goneBy")} /> : null}
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
