import type { LakeRecord } from "@/lib/lake";
import { formatAcres } from "@/lib/format";
import ExternalLink from "./ExternalLink";
import Fact, { Note } from "./Fact";
import Section from "./Section";
import { resolve, sourcesOf } from "./sources";
import { directions, percent, sentence, who } from "./words";
import { tidyPlace } from "./measures";

const COVER: Record<string, string> = {
  built: "built",
  tree: "trees",
  grass: "grass",
  crop: "crops",
  bare: "bare ground",
  shrub: "shrubs",
  water: "water",
};

export default function BuiltSection({ lake }: { lake: LakeRecord }) {
  const e = lake.encroachment;
  const nature = lake.nature;
  const builtInside = lake.location?.hasOutline ? nature?.builtInsideOutlinePct : undefined;
  const around = Object.entries(nature?.landAround ?? {})
    .filter(([, v]) => (v ?? 0) >= 0.5)
    .sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0));
  // The 2018 survey's share and the census mark are dated, so they sit on the timeline.
  const hasEncroachment = e && Object.keys(e).some((key) => !["src", "pct2018", "census2018Encroached"].includes(key));
  const empty = builtInside === undefined && !hasEncroachment && around.length === 0;

  return (
    <Section id="built-over" title="How much is built over" missing="No survey of building or encroachment on record." empty={empty}>
      {builtInside !== undefined ? (
        <Fact label="Built inside the outline" value={percent(builtInside)} sources={sourcesOf(nature, "builtInsideOutlinePct")}>
          <Note>From satellite land cover, 2021</Note>
        </Fact>
      ) : null}
      {e?.koliwadAcres !== undefined ? (
        <Fact label="Encroached area, 2017" value={`${formatAcres(e.koliwadAcres)} acres`} sources={sourcesOf(e, "koliwadAcres")}>
          <Note>Reported by the state legislature&rsquo;s committee on lake encroachment</Note>
        </Fact>
      ) : null}
      {e?.by?.length ? (
        <Fact label="Encroached by" sources={sourcesOf(e, "by")}>
          <p>{sentence(who(e.by))}</p>
        </Fact>
      ) : null}
      {e?.for ? (
        <Fact label="Taken for" sources={sourcesOf(e, "for")}>
          <p>{e.for}</p>
        </Fact>
      ) : null}
      {e?.side ? (
        <Fact label="Where it is encroached" sources={sourcesOf(e, "side")}>
          <p>On the {directions(e.side)} side</p>
        </Fact>
      ) : null}
      {e?.dumping ? (
        <Fact label="Dumped in it" sources={sourcesOf(e, "dumping")}>
          <p>{e.dumping}</p>
        </Fact>
      ) : null}
      {e?.otherIssues ? (
        <Fact label="Other problems noted" sources={sourcesOf(e, "otherIssues")}>
          <p>{e.otherIssues}</p>
        </Fact>
      ) : null}
      {e?.officialMaps?.length ? (
        <Fact label="Land record maps" sources={resolve(e.officialMaps.map((m) => m.source))}>
          <ul>
            {e.officialMaps.map((m) => (
              <li key={m.url}>
                <ExternalLink href={m.url}>
                  Survey number {m.surveyNumber}, {tidyPlace(m.village)}
                </ExternalLink>
              </li>
            ))}
          </ul>
        </Fact>
      ) : null}
      {around.length ? (
        <Fact label="Land within 500 m" sources={sourcesOf(nature, "landAround")}>
          <p>{sentence(around.map(([k, v]) => `${percent(v ?? 0)} ${COVER[k] ?? k}`).join(", "))}</p>
          <Note>From satellite land cover, 2021</Note>
        </Fact>
      ) : null}
    </Section>
  );
}
