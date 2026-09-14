import type { CSSProperties } from "react";
import Link from "next/link";
import type { LakeRecord, LakeSummary } from "@/lib/lake";
import { formatAcres, formatMonth, ordinal, pitches, WATER_CLASS } from "@/lib/format";
import { paperFor } from "@/lib/valleys";
import Slip from "@/components/paper/Slip";
import { displayName, kindWords, percent, sentence } from "./words";

/** The lake's area as the record best knows it, and which measure that is. */
export function bestAcres(lake: LakeRecord): { acres: number; label: string } | undefined {
  const size = lake.size;
  if (size?.outlineAcres !== undefined) return { acres: size.outlineAcres, label: "Size" };
  if (size?.surveyed2018Acres !== undefined) return { acres: size.surveyed2018Acres, label: "Size in the 2018 survey" };
  if (size?.recordedAcres !== undefined) return { acres: size.recordedAcres, label: "Size on land records" };
  if (size?.onOldMapAcres !== undefined) return { acres: size.onOldMapAcres, label: "Size on the old map" };
  return undefined;
}

export function pitchLine(acres: number): string {
  const p = pitches(acres);
  return p.startsWith("smaller") ? sentence(p) : `About ${p}`;
}

function Gap({ children }: { children: string }) {
  return <span className="missing">{children}</span>;
}

function Sub({ children }: { children: string }) {
  return <span className="label mt-2 block font-sans font-normal">{children}</span>;
}

/** Where the lake is, in one line: kind, ward or village, corporation or taluk. */
function placeLine(lake: LakeRecord): string | undefined {
  const loc = lake.location;
  const place = loc?.ward?.name
    ? `${loc.ward.name} ward${loc.ward.corporation ? `, ${loc.ward.corporation}` : ""}`
    : loc?.village
      ? `${loc.village} village${loc.taluk ? `, ${loc.taluk} taluk` : ""}`
      : undefined;
  const kind = lake.kind ? kindWords(lake.kind) : undefined;
  if (!place) return kind;
  return kind ? `${kind}, in ${place}` : `In ${place}`;
}

export default function Title({
  lake,
  summary,
  rankedCount,
}: {
  lake: LakeRecord;
  summary?: LakeSummary;
  rankedCount: number;
}) {
  const name = displayName(lake.name);
  const words = name.split(/\s+/);
  const longest = Math.max(...words.map((w) => w.length));
  // Instrument Serif runs about half an em per letter; fit the longest word, and keep to about three lines.
  const fit = Math.max(longest, name.length / 3, 6) * 0.52;

  const size = bestAcres(lake);
  const valley = lake.water?.valley;
  const paper = paperFor(valley);
  const custodian = lake.responsibility?.custodian;
  const latest = lake.waterQuality?.latest?.find((reading) => reading.class);
  const builtPct = lake.location?.hasOutline ? lake.nature?.builtInsideOutlinePct : undefined;
  const encroached = lake.encroachment?.pct2018;
  const organising = Boolean(
    lake.responsibility?.campaignUrls?.length || lake.responsibility?.communityGroups?.length,
  );
  const line = placeLine(lake);

  return (
    <header
      className="pt-6 [--name:min(96px,calc((100vw_-_32px)/var(--fit)))] md:pt-10 md:[--name:min(160px,calc((min(100vw,1600px)_-_80px)/var(--fit)))]"
      style={{ "--fit": fit.toFixed(2) } as CSSProperties}
    >
      {lake.location?.point ? (
        <p className="label mb-6 font-normal text-missing md:mb-10">Satellite view: Esri, Maxar, Earthstar Geographics</p>
      ) : null}

      <h1 className="font-serif text-[length:var(--name)] leading-[0.86] break-words">
        <span className="highlight">{name}</span>
      </h1>
      {lake.nameKannada ? (
        <p lang="kn" className="mt-4 font-kannada text-[length:max(20px,calc(var(--name)/4))] leading-[1.2] font-semibold">
          {lake.nameKannada}
        </p>
      ) : null}
      {lake.namesOther?.length ? (
        <p className="mt-4 max-w-[65ch]">
          <span className="label">Also called </span>
          {lake.namesOther.join(", ")}
        </p>
      ) : null}
      {line ? <p className="mt-2 max-w-[65ch]">{line}</p> : null}

      {/* The map draws only lakes that exist and have a shape; the others live on their own pages. */}
      {lake.status !== "exists" ? (
        <Link href="/once-upon-a-kere" className="button-ink mt-8 text-[28px] md:mt-10 md:text-[38px]">
          See the lakes that disappeared
        </Link>
      ) : lake.location?.hasOutline ? (
        <Link href={`/map#${lake.id}`} className="button-ink mt-8 text-[28px] md:mt-10 md:text-[38px]">
          See it on the map
        </Link>
      ) : lake.location?.point ? (
        <Link href="/missing-lakes" className="button-ink mt-8 text-[28px] md:mt-10 md:text-[38px]">
          See the lakes no map draws
        </Link>
      ) : (
        <p className="missing mt-8">Not on the map: no location on record.</p>
      )}

      <div className="mt-10 grid items-start gap-6 sm:grid-cols-2 md:mt-16 lg:grid-cols-3">
        <Slip label={size?.label ?? "Size"} seed={`${lake.id}-size`} order={0}>
          {size ? (
            <>
              {formatAcres(size.acres)} acres
              <Sub>{pitchLine(size.acres)}</Sub>
            </>
          ) : (
            <Gap>No area on record</Gap>
          )}
        </Slip>

        <Slip label="Rank by size" seed={`${lake.id}-rank`} order={1}>
          {lake.status === "exists" && summary?.sizeRank ? (
            <>
              {ordinal(summary.sizeRank)} largest
              <Sub>{`Of ${rankedCount.toLocaleString("en-IN")} lakes that still exist`}</Sub>
            </>
          ) : lake.status === "exists" ? (
            <Gap>Not ranked: no area measured</Gap>
          ) : (
            <>
              {lake.status === "converted" ? "Converted" : "Disappeared"}
              <Sub>{lake.history?.goneBy ? `Gone by ${lake.history.goneBy}` : "The year it went is not recorded"}</Sub>
            </>
          )}
        </Slip>

        <Slip label="Valley" seed={`${lake.id}-valley`} order={2}>
          {valley ? (
            <span className="flex items-start gap-3">
              <span aria-hidden className="sheet-shadow mt-1 size-5 shrink-0 md:size-7" style={{ background: paper.sheet }} />
              <span className="min-w-0 break-words">{valley}</span>
            </span>
          ) : (
            <Gap>No valley on record</Gap>
          )}
        </Slip>

        <Slip label="Who looks after it" seed={`${lake.id}-care`} order={3}>
          {custodian ? (
            <>
              {custodian.code}
              {custodian.name !== custodian.code ? <Sub>{custodian.name}</Sub> : null}
            </>
          ) : (
            <Gap>Nobody on record looks after it</Gap>
          )}
        </Slip>

        <Slip label="Water quality" seed={`${lake.id}-quality`} order={4}>
          {latest?.class ? (
            <>
              {WATER_CLASS[latest.class].short}
              <Sub>{`Tested ${formatMonth(latest.month)}`}</Sub>
            </>
          ) : (
            <Gap>Not tested for water quality yet</Gap>
          )}
        </Slip>

        <Slip label="Built over" seed={`${lake.id}-built`} order={5}>
          {builtPct !== undefined ? (
            <>
              {percent(builtPct)} of the lake
              <Sub>
                {encroached !== undefined
                  ? `Satellite, 2021. The 2018 survey found ${percent(encroached)} encroached.`
                  : "Satellite land cover, 2021"}
              </Sub>
            </>
          ) : encroached !== undefined ? (
            <>
              {percent(encroached)} encroached
              <Sub>2018 survey</Sub>
            </>
          ) : (
            <Gap>No survey of building on record</Gap>
          )}
        </Slip>

        {organising ? (
          <Link href="#who-looks-after-it" className="block sm:col-span-2 lg:col-span-1">
            <Slip label="Campaign" seed={`${lake.id}-campaign`} order={6} className="hover:underline">
              <span className="italic">Residents are organising here</span>
            </Slip>
          </Link>
        ) : null}
      </div>
    </header>
  );
}
