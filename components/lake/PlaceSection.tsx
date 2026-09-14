import type { LakeRecord } from "@/lib/lake";
import { formatCoords } from "@/lib/format";
import Fact, { Note } from "./Fact";
import Section from "./Section";
import { sourcesOf } from "./sources";

export default function PlaceSection({ lake }: { lake: LakeRecord }) {
  const loc = lake.location;
  const ward = loc?.ward;
  const area = [
    loc?.hobli ? `${loc.hobli} hobli` : undefined,
    loc?.taluk ? `${loc.taluk} taluk` : undefined,
    loc?.district ? `${loc.district} district` : undefined,
  ].filter(Boolean);
  const empty = !loc || !Object.keys(loc).some((key) => !["src", "bbox", "hasOutline"].includes(key));

  return (
    <Section id="where-it-is" title="Where it is" missing="No location on record." empty={empty}>
      {ward?.name ? (
        <Fact label={ward.number ? `Ward ${ward.number}` : "Ward"} value={ward.name} sources={sourcesOf(loc, "ward")}>
          {ward.nameKannada ? (
            <p lang="kn" className="font-kannada font-semibold">
              {ward.nameKannada}
            </p>
          ) : null}
          <Note>
            {[ward.corporation ? `${ward.corporation} corporation` : undefined, ward.assemblyConstituency ? `${ward.assemblyConstituency} assembly seat` : undefined]
              .filter(Boolean)
              .join(", ")}
          </Note>
        </Fact>
      ) : null}
      {loc?.insideCity !== undefined && !ward?.name ? (
        <Fact
          label="Greater Bengaluru"
          value={loc.insideCity ? "Inside the city" : "Outside the city limits"}
          sources={sourcesOf(loc, "insideCity")}
        />
      ) : null}
      {loc?.village ? (
        <Fact label="Village" value={loc.village} sources={sourcesOf(loc, "village", "hobli", "taluk", "district")}>
          {area.length ? <Note>{area.join(", ")}</Note> : null}
        </Fact>
      ) : null}
      {loc?.surveyNumbers?.length ? (
        <Fact label="Land survey numbers" sources={sourcesOf(loc, "surveyNumbers")}>
          <p>{loc.surveyNumbers.join(", ")}</p>
        </Fact>
      ) : null}
      {loc?.elevationM !== undefined ? (
        <Fact label="Height above sea level" value={`${Math.round(loc.elevationM)} m`} sources={sourcesOf(loc, "elevationM")} />
      ) : null}
      {loc?.point ? (
        <Fact label="Coordinates" sources={sourcesOf(loc, "point")}>
          <p className="tabular-nums">{formatCoords(loc.point)}</p>
        </Fact>
      ) : null}
    </Section>
  );
}
