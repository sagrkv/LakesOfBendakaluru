import type { LakeRecord } from "@/lib/lake";
import { formatCount, formatMonth } from "@/lib/format";
import Fact, { Note } from "./Fact";
import Section from "./Section";
import { sourcesOf } from "./sources";
import { commonName, iucnWords, joinList, sentence } from "./words";

export default function NatureSection({ lake }: { lake: LakeRecord }) {
  const n = lake.nature;
  const empty =
    !n?.birds && !n?.allSpecies && !n?.threatened?.length && !n?.observations && !n?.fauna2018?.length && !n?.plants2018?.length && !n?.weeds2018;

  return (
    <Section id="nature" title="What lives here" missing="No wildlife records from this lake yet." empty={empty}>
      {n?.birds ? (
        <Fact label="Birds recorded" value={`${formatCount(n.birds.species)} species`} sources={sourcesOf(n, "birds")}>
          {n.birds.top.length ? <p>Most seen: {joinList(n.birds.top.slice(0, 5).map(commonName))}.</p> : null}
          <Note>{formatCount(n.birds.records)} sightings, mostly from birdwatchers</Note>
        </Fact>
      ) : null}
      {n?.allSpecies ? (
        <Fact
          label="All wildlife recorded"
          value={n.allSpecies.species === undefined ? undefined : `${formatCount(n.allSpecies.species)} species`}
          sources={sourcesOf(n, "allSpecies")}
        >
          <Note>
            {formatCount(n.allSpecies.records)} records
            {n.allSpecies.firstYear && n.allSpecies.lastYear
              ? n.allSpecies.firstYear === n.allSpecies.lastYear
                ? `, all in ${n.allSpecies.firstYear}`
                : `, ${n.allSpecies.firstYear} to ${n.allSpecies.lastYear}`
              : ""}
          </Note>
        </Fact>
      ) : null}
      {n?.threatened?.length ? (
        <Fact label="Threatened species seen here" value={formatCount(n.threatened.length)} sources={sourcesOf(n, "threatened")}>
          <ul>
            {n.threatened.map((s) => (
              <li key={s.scientificName}>
                {s.name} <span className="label font-normal">{iucnWords(s.iucn).toLowerCase()}</span>
              </li>
            ))}
          </ul>
        </Fact>
      ) : null}
      {n?.observations ? (
        <Fact label="Photographed on iNaturalist" value={`${formatCount(n.observations.count)} times`} sources={sourcesOf(n, "observations")}>
          {n.observations.species !== undefined ? (
            <p>
              {formatCount(n.observations.species)} species
              {n.observations.researchGrade !== undefined
                ? `, ${formatCount(n.observations.researchGrade)} confirmed by other naturalists`
                : ""}
              .
            </p>
          ) : null}
          {n.observations.top?.length ? <p>Most seen: {joinList(n.observations.top.slice(0, 5).map(commonName))}.</p> : null}
          {n.observations.lastObserved ? <Note>Last seen {formatMonth(n.observations.lastObserved.slice(0, 7))}</Note> : null}
        </Fact>
      ) : null}
      {n?.fauna2018?.length ? (
        <Fact label="Animals seen, 2018 survey" sources={sourcesOf(n, "fauna2018")}>
          <p>{sentence(joinList(n.fauna2018))}</p>
        </Fact>
      ) : null}
      {n?.plants2018?.length ? (
        <Fact label="Water plants, 2018 survey" sources={sourcesOf(n, "plants2018")}>
          <p>{sentence(joinList(n.plants2018))}</p>
        </Fact>
      ) : null}
      {n?.weeds2018 ? (
        <Fact label="Weed cover, 2018 survey" sources={sourcesOf(n, "weeds2018")}>
          <p>{sentence(n.weeds2018)}</p>
        </Fact>
      ) : null}
    </Section>
  );
}
