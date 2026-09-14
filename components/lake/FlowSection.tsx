import Link from "next/link";
import type { LakeRecord, LakeRef } from "@/lib/lake";
import { formatMetres } from "@/lib/format";
import { paperFor } from "@/lib/valleys";
import Fact, { Note } from "./Fact";
import Section from "./Section";
import { sourcesOf } from "./sources";
import { joinList, sentence } from "./words";

const PARTS = [
  ["inletDrains", "inlet drain", "inlet drains"],
  ["wasteWeirs", "overflow weir", "overflow weirs"],
  ["sluiceGates", "sluice gate", "sluice gates"],
  ["culverts", "culvert", "culverts"],
  ["checkDams", "check dam", "check dams"],
  ["islands", "island", "islands"],
] as const;

/** Most neighbours are lakes with pages; some are rivers or unmatched names and carry no id. */
function Neighbour({ lakeRef }: { lakeRef: LakeRef }) {
  if (!lakeRef.id) return <>{lakeRef.name}</>;
  return (
    <Link href={`/lake/${lakeRef.id}`} className="ink-link">
      {lakeRef.name}
    </Link>
  );
}

export default function FlowSection({ lake }: { lake: LakeRecord }) {
  const water = lake.water;
  const plant = water?.nearestTreatmentPlant;
  const parts = PARTS.filter(([key]) => water?.[key] !== undefined);
  const empty =
    !water?.valley &&
    !water?.upstream?.length &&
    !water?.downstream &&
    water?.catchmentKm2 === undefined &&
    !water?.sourceOfWater &&
    parts.length === 0 &&
    !water?.uses?.length &&
    !plant;

  return (
    <Section
      id="water-flow"
      title="Where its water comes from and goes"
      missing="Where its water comes from and goes is not on record."
      empty={empty}
    >
      {water?.valley ? (
        <Fact
          label="Valley"
          value={
            <span className="flex items-start gap-3">
              <span aria-hidden className="sheet-shadow mt-1 size-5 shrink-0 md:size-7" style={{ background: paperFor(water.valley).sheet }} />
              <span className="min-w-0">{water.valley}</span>
            </span>
          }
          sources={sourcesOf(water, "valley")}
        >
          <Note>The river basin its water drains to</Note>
        </Fact>
      ) : null}
      {water?.upstream?.length ? (
        <Fact label="Water comes from" sources={sourcesOf(water, "upstream")}>
          <ul>
            {water.upstream.map((ref) => (
              <li key={ref.id ?? ref.name}>
                <Neighbour lakeRef={ref} />
              </li>
            ))}
          </ul>
        </Fact>
      ) : null}
      {water?.downstream ? (
        <Fact label="Overflows into" sources={sourcesOf(water, "downstream")}>
          <p>
            <Neighbour lakeRef={water.downstream} />
          </p>
        </Fact>
      ) : null}
      {water?.catchmentKm2 !== undefined ? (
        <Fact
          label="Catchment"
          value={`${water.catchmentKm2.toLocaleString("en-IN", { maximumFractionDigits: 1 })} km²`}
          sources={sourcesOf(water, "catchmentKm2")}
        >
          <Note>The land that drains into it</Note>
        </Fact>
      ) : null}
      {water?.sourceOfWater ? (
        <Fact label="Fed by, 2018 survey" sources={sourcesOf(water, "sourceOfWater")}>
          <p>{water.sourceOfWater}</p>
        </Fact>
      ) : null}
      {parts.length ? (
        <Fact label="Built parts, 2018 survey" sources={sourcesOf(water, ...parts.map(([key]) => key))}>
          <p>
            {sentence(
              joinList(
                parts.map(([key, one, many]) => {
                  const n = water?.[key] ?? 0;
                  return `${n === 0 ? "no" : n} ${n === 1 ? one : many}`;
                }),
              ),
            )}
          </p>
        </Fact>
      ) : null}
      {water?.uses?.length ? (
        <Fact label="Used for, 2018 survey" sources={sourcesOf(water, "uses")}>
          <p>{sentence(joinList(water.uses))}</p>
        </Fact>
      ) : null}
      {plant ? (
        <Fact label="Nearest sewage treatment plant" sources={sourcesOf(water, "nearestTreatmentPlant")}>
          <p>{plant.name}</p>
          <Note>
            {formatMetres(plant.distanceM)} away
            {typeof plant.capacityMld === "number" ? `, treats ${plant.capacityMld} million litres a day` : ""}
          </Note>
        </Fact>
      ) : null}
    </Section>
  );
}
