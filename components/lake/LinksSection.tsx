import type { LakeRecord } from "@/lib/lake";
import ExternalLink from "./ExternalLink";
import Fact from "./Fact";
import Section from "./Section";
import { sourcesOf } from "./sources";

const ID_NAMES: Record<string, string> = {
  atreeFid: "ATREE lake map",
  empriCode: "2018 lake survey",
  ldaId: "Lake Development Authority",
  kgisTankId: "KGIS tank map",
  kgisPondId: "KGIS pond map",
  minorIrrigationId: "Minor Irrigation Department",
  waterBodyCensusId: "Water bodies census",
  bbmpLmsId: "City lake monitoring site",
};

export default function LinksSection({ lake }: { lake: LakeRecord }) {
  const links = lake.links;
  const wiki = links?.wikipedia;
  // The city lake page already sits under who looks after it when the record has it there.
  const bbmp = lake.responsibility?.monitoringPage ? undefined : links?.bbmpLakePage;
  const ids = Object.entries(links?.ids ?? {});
  const empty = !wiki?.en && !wiki?.kn && !links?.osm?.length && !bbmp && !links?.wikidata && !links?.commonsCategory && ids.length === 0;

  return (
    <Section id="read-more" title="Read more" missing="No other pages about it yet." empty={empty}>
      {wiki?.en ? (
        <Fact wide label="Wikipedia" sources={sourcesOf(links, "wikipedia")}>
          {wiki.en.summary ? <p className="max-w-[65ch]">{wiki.en.summary}</p> : null}
          <p className="mt-2">
            <ExternalLink href={wiki.en.url}>Read {wiki.en.title} on Wikipedia</ExternalLink>
          </p>
        </Fact>
      ) : null}
      {wiki?.kn ? (
        <Fact wide label="Kannada Wikipedia" sources={sourcesOf(links, "wikipedia")}>
          <div lang="kn" className="font-semibold">
            {wiki.kn.summary ? <p className="max-w-[65ch] font-kannada">{wiki.kn.summary}</p> : null}
            <p className="mt-2 font-kannada">
              <ExternalLink href={wiki.kn.url}>{wiki.kn.title}</ExternalLink>
            </p>
          </div>
        </Fact>
      ) : null}
      {links?.osm?.length ? (
        <Fact label="OpenStreetMap" sources={sourcesOf(links, "osm")}>
          <ul>
            {links.osm.map((url, i) => (
              <li key={url}>
                <ExternalLink href={url}>{links.osm!.length > 1 ? `Open part ${i + 1} on OpenStreetMap` : "Open it on OpenStreetMap"}</ExternalLink>
              </li>
            ))}
          </ul>
        </Fact>
      ) : null}
      {bbmp ? (
        <Fact label="City lake page" sources={sourcesOf(links, "bbmpLakePage")}>
          <p>
            <ExternalLink href={bbmp}>Open its page on the city&rsquo;s lake monitoring site</ExternalLink>
          </p>
        </Fact>
      ) : null}
      {links?.commonsCategory ? (
        <Fact label="Wikimedia Commons" sources={sourcesOf(links, "commonsCategory")}>
          <p>
            <ExternalLink href={`https://commons.wikimedia.org/wiki/Category:${encodeURIComponent(links.commonsCategory.replace(/ /g, "_"))}`}>
              See every photo of it
            </ExternalLink>
          </p>
        </Fact>
      ) : null}
      {links?.wikidata ? (
        <Fact label="Wikidata" sources={sourcesOf(links, "wikidata")}>
          <p>
            <ExternalLink href={`https://www.wikidata.org/wiki/${links.wikidata}`}>{links.wikidata}</ExternalLink>
          </p>
        </Fact>
      ) : null}
      {ids.length ? (
        <Fact label="Its number in each record">
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1">
            {ids.map(([key, value]) => (
              <div key={key} className="contents">
                <dt className="label font-normal">{ID_NAMES[key] ?? key}</dt>
                <dd className="label font-normal break-all tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
        </Fact>
      ) : null}
    </Section>
  );
}
