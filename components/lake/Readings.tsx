import type { LakeRecord } from "@/lib/lake";
import { formatMonth } from "@/lib/format";
import SourceLink from "@/components/paper/SourceLink";
import { formatReading, measureName, measureUnit, statisticName, tidyPlace } from "./measures";
import { resolve, sourcesOf } from "./sources";

type Quality = NonNullable<LakeRecord["waterQuality"]>;
type Row = { key: string; cells: (string | undefined)[]; values: Record<string, number>; source?: string };

const SERIES_MEASURES = ["dissolvedOxygen", "bod", "fecalColiform", "totalColiform"];

const th = "label px-3 py-2 text-left align-bottom whitespace-nowrap";
const td = "px-3 py-2 align-top whitespace-nowrap";

function Table({
  caption,
  heads,
  measures,
  rows,
  units,
}: {
  caption: string;
  heads: string[];
  measures: string[];
  rows: Row[];
  units?: Record<string, string>;
}) {
  const withSource = rows.some((row) => row.source);
  return (
    <div className="mt-6">
      <p className="label">{caption}</p>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full border-collapse text-[12.5px] leading-[1.35] tabular-nums">
          <thead>
            <tr className="border-b border-ink/40">
              {heads.map((head) => (
                <th key={head} scope="col" className={th}>
                  {head}
                </th>
              ))}
              {measures.map((m) => (
                <th key={m} scope="col" className={`${th} text-right`}>
                  {measureName(m)}
                  {measureUnit(m, units) ? <span className="block font-normal">{measureUnit(m, units)}</span> : null}
                </th>
              ))}
              {withSource ? <th scope="col" className={th}><span className="sr-only">Source</span></th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-b border-rule">
                {row.cells.map((cell, i) => (
                  <td key={i} className={td}>
                    {cell ?? ""}
                  </td>
                ))}
                {measures.map((m) => (
                  <td key={m} className={`${td} text-right`}>
                    {row.values[m] !== undefined ? formatReading(row.values[m]) : ""}
                  </td>
                ))}
                {withSource ? (
                  <td className={td}>
                    <SourceLink source={resolve([row.source])[0]} />
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const measuresIn = (list: { values: Record<string, number> }[]) => [
  ...new Set(list.flatMap((item) => Object.keys(item.values))),
];

/** Every water test on record, behind one disclosure. Technical names and units live only here. */
export default function Readings({ quality }: { quality: Quality }) {
  const stations = new Map(quality.stations?.map((s) => [s.id, s.name]));
  const multi = (quality.stations?.length ?? 0) > 1;
  const series = [...(quality.series ?? [])].sort((a, b) => b.month.localeCompare(a.month));
  const surveySources = sourcesOf(quality, "surveyTests");

  return (
    <details className="group">
      <summary className="label ink-link inline-flex min-h-11 cursor-pointer items-center list-none [&::-webkit-details-marker]:hidden">
        <span className="group-open:hidden">Show every reading</span>
        <span className="hidden group-open:inline">Hide the readings</span>
      </summary>

      {quality.latest?.map((reading) => (
        <Table
          key={`latest-${reading.station}`}
          caption={`Latest test, ${formatMonth(reading.month)}${multi ? `, ${stations.get(reading.station) ?? reading.station}` : ""}${
            reading.belowDetection?.length
              ? `. Too low to measure: ${reading.belowDetection.map((m) => measureName(m).toLowerCase()).join(", ")}`
              : ""
          }`}
          heads={["Measure", "Unit"]}
          measures={["value"]}
          units={{ value: "" }}
          rows={Object.entries(reading.values).map(([m, v]) => ({
            key: m,
            cells: [measureName(m), measureUnit(m, quality.units)],
            values: { value: v },
          }))}
        />
      ))}

      {series.length ? (
        <Table
          caption="Every month the state board tested it"
          heads={multi ? ["Month", "Station", "Class"] : ["Month", "Class"]}
          measures={SERIES_MEASURES.filter((m) => series.some((r) => r.values[m] !== undefined))}
          units={quality.units}
          rows={series.map((r) => ({
            key: `${r.month}-${r.station}`,
            cells: multi
              ? [formatMonth(r.month), stations.get(r.station) ?? r.station, r.class]
              : [formatMonth(r.month), r.class],
            values: r.values,
            source: r.source,
          }))}
        />
      ) : null}

      {quality.olderTests?.length ? (
        <Table
          caption="Older tests"
          heads={["Date", "Where", "Reading"]}
          measures={measuresIn(quality.olderTests)}
          rows={quality.olderTests.map((t, i) => ({
            key: `${t.source}-${i}`,
            cells: [
              t.date,
              [t.station, t.point].filter(Boolean).map((p) => tidyPlace(p as string)).join(", "),
              t.statistic ? statisticName(t.statistic) : undefined,
            ],
            values: t.values,
            source: t.source,
          }))}
        />
      ) : null}

      {quality.surveyTests?.length ? (
        <>
          <Table
            caption="Inlet and outlet tests, 2017-18 lake survey"
            heads={["Date", "Where"]}
            measures={measuresIn(quality.surveyTests)}
            rows={quality.surveyTests.map((t, i) => ({
              key: `survey-${i}`,
              cells: [t.date, t.point],
              values: t.values,
            }))}
          />
          <div className="mt-2">
            {surveySources.map((source) => (
              <SourceLink key={source.key} source={source} />
            ))}
          </div>
        </>
      ) : null}
    </details>
  );
}
