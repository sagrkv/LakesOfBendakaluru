import type { LakeRecord } from "@/lib/lake";
import { formatMonth, WATER_CLASS } from "@/lib/format";
import ClassChart from "./ClassChart";
import Fact, { Note } from "./Fact";
import Readings from "./Readings";
import Section from "./Section";
import { resolve, sourcesOf } from "./sources";
import { directions, joinList, sentence } from "./words";

export default function QualitySection({ lake }: { lake: LakeRecord }) {
  const quality = lake.waterQuality;
  const water = lake.water;
  const stations = quality?.stations ?? [];
  const names = new Map(stations.map((s) => [s.id, s.name]));
  const multi = stations.length > 1;
  const series = quality?.series ?? [];
  const hasTests = Boolean(series.length || quality?.latest?.length || quality?.olderTests?.length || quality?.surveyTests?.length);
  const survey2018 = Boolean(water?.conditionIn2018?.length || water?.pollutant || water?.sewageInflowFrom?.length);
  const latestSource = [...series].sort((a, b) => b.month.localeCompare(a.month))[0]?.source;

  return (
    <Section
      id="water-quality"
      title="How clean the water is"
      missing="Not tested for water quality yet."
      empty={!hasTests && !survey2018}
    >
      {quality?.latest?.map((reading) => (
        <Fact
          key={reading.station}
          label={multi ? `Latest test, ${names.get(reading.station) ?? "station"}` : "Latest test"}
          value={reading.class ? WATER_CLASS[reading.class].short : <span className="missing">Tested, not classed</span>}
          sources={resolve([reading.source])}
        >
          {reading.class ? (
            <p>
              {WATER_CLASS[reading.class].long}. Class {reading.class} on the state board&rsquo;s scale from A, the cleanest,
              to E.
            </p>
          ) : null}
          <Note>Tested {formatMonth(reading.month)}</Note>
        </Fact>
      ))}

      {!quality?.latest?.length ? (
        <Fact label="State pollution board" value={<span className="missing">Not tested by the state board</span>} />
      ) : null}

      {stations.map((station) => {
        const readings = series.filter((r) => r.station === station.id);
        if (readings.length < 2) return null;
        return (
          <Fact
            key={station.id}
            wide
            label={`Class each month${multi ? ` at ${station.name}` : ""}, tested ${readings.length} times since ${formatMonth(station.firstMonth)}`}
            sources={resolve([latestSource])}
          >
            <ClassChart readings={readings} start={station.firstMonth} end={station.lastMonth} />
          </Fact>
        );
      })}

      {water?.conditionIn2018?.length ? (
        <Fact label="How it looked in 2018" value={sentence(joinList(water.conditionIn2018))} sources={sourcesOf(water, "conditionIn2018")} />
      ) : null}
      {water?.pollutant ? (
        <Fact label="What pollutes it, 2018" sources={sourcesOf(water, "pollutant")}>
          <p>{water.pollutant}</p>
        </Fact>
      ) : null}
      {water?.sewageInflowFrom?.length ? (
        <Fact label="Sewage flows in, 2018" sources={sourcesOf(water, "sewageInflowFrom")}>
          <p>From the {directions(water.sewageInflowFrom)}</p>
        </Fact>
      ) : null}
      {quality?.olderTests?.length ? (
        <Fact label="Older tests" value={`${quality.olderTests.length} readings`} sources={resolve(quality.olderTests.map((t) => t.source))}>
          <Note>From {joinList([...new Set(quality.olderTests.map((t) => t.date.slice(0, 4)))].sort())}</Note>
        </Fact>
      ) : null}
      {quality?.surveyTests?.length ? (
        <Fact label="Inlet and outlet tests, 2017-18" value={`${quality.surveyTests.length} readings`} sources={sourcesOf(quality, "surveyTests")} />
      ) : null}

      {quality && hasTests ? (
        <Fact wide label="Every reading">
          <Readings quality={quality} />
        </Fact>
      ) : null}
    </Section>
  );
}
