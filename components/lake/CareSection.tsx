import type { LakeRecord } from "@/lib/lake";
import ExternalLink from "./ExternalLink";
import Fact, { Note } from "./Fact";
import Section from "./Section";
import { sourcesOf } from "./sources";
import { hostname, sentence } from "./words";

export default function CareSection({ lake }: { lake: LakeRecord }) {
  const r = lake.responsibility;
  const empty = !r || !Object.keys(r).some((key) => key !== "src");

  return (
    <Section id="who-looks-after-it" title="Who looks after it" missing="Nobody on record looks after it." empty={empty}>
      {r?.custodian ? (
        <Fact label="Looked after by" value={r.custodian.name} sources={sourcesOf(r, "custodian")}>
          {r.custodian.code !== r.custodian.name ? <Note>{r.custodian.code}</Note> : null}
        </Fact>
      ) : (
        <Fact label="Looked after by" value={<span className="missing">Nobody on record</span>} />
      )}
      {r?.developmentStatus ? (
        <Fact label="City work on the lake" value={sentence(r.developmentStatus)} sources={sourcesOf(r, "developmentStatus")} />
      ) : null}
      {r?.zone ? <Fact label="City zone" value={r.zone} sources={sourcesOf(r, "zone")} /> : null}
      {r?.monitoringPage ? (
        <Fact label="City lake page" sources={sourcesOf(r, "monitoringPage")}>
          <p>
            <ExternalLink href={r.monitoringPage}>Open its page on the city&rsquo;s lake monitoring site</ExternalLink>
          </p>
        </Fact>
      ) : null}
      {r?.communityGroups?.length ? (
        <Fact label="Residents' groups" sources={sourcesOf(r, "communityGroups")}>
          <ul>
            {r.communityGroups.map((group) => (
              <li key={group.url ?? group.name}>
                {group.url ? <ExternalLink href={group.url}>{group.name}</ExternalLink> : group.name}
              </li>
            ))}
          </ul>
        </Fact>
      ) : null}
      {r?.campaignUrls?.length ? (
        <Fact label="Campaign pages" sources={sourcesOf(r, "campaignUrls")}>
          <ul>
            {r.campaignUrls.map((url) => (
              <li key={url}>
                <ExternalLink href={url}>{hostname(url)}</ExternalLink>
              </li>
            ))}
          </ul>
        </Fact>
      ) : null}
    </Section>
  );
}
