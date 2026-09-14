import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { CSSProperties } from "react";
import type { LakeRecord } from "@/lib/lake";
import { paperFor } from "@/lib/valleys";
import { formatAcres, formatMonth, WATER_CLASS } from "@/lib/format";
import { getLake, getLakes, getSummary } from "@/lib/lakes";
import SiteFooter from "@/components/SiteFooter";
import BuiltSection from "@/components/lake/BuiltSection";
import CareSection from "@/components/lake/CareSection";
import FlowSection from "@/components/lake/FlowSection";
import Hero from "@/components/lake/Hero";
import HistorySection from "@/components/lake/HistorySection";
import LinksSection from "@/components/lake/LinksSection";
import NatureSection from "@/components/lake/NatureSection";
import PhotosSection from "@/components/lake/PhotosSection";
import PlaceSection from "@/components/lake/PlaceSection";
import QualitySection from "@/components/lake/QualitySection";
import SizeSection from "@/components/lake/SizeSection";
import Title, { bestAcres } from "@/components/lake/Title";
import { displayName, percent } from "@/components/lake/words";
import YearsSection from "@/components/lake/years/YearsSection";

type Props = { params: Promise<{ id: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return getLakes().map((lake) => ({ id: lake.id }));
}

/** Two or three plain sentences a link preview can carry. */
function describe(lake: LakeRecord, name: string): string {
  const size = bestAcres(lake);
  const valley = lake.water?.valley;
  const place = lake.location?.ward?.name ?? lake.location?.village;
  const parts: string[] = [];

  if (lake.status === "exists") {
    parts.push(
      `${name} is a${size ? ` ${formatAcres(size.acres)}-acre` : ""} lake${place ? ` in ${place}` : ""}${
        valley ? `, in the ${valley} valley` : ""
      }.`,
    );
  } else {
    const now = lake.history?.nowOccupiedBy;
    parts.push(
      `${name} was a lake${place ? ` in ${place}` : ""}${lake.history?.goneBy ? `, gone by ${lake.history.goneBy}` : ""}.`,
    );
    if (now) parts.push(`On the site now: ${now.toLowerCase()}.`);
  }

  const custodian = lake.responsibility?.custodian;
  if (custodian) parts.push(`Looked after by ${custodian.code}.`);
  const latest = lake.waterQuality?.latest?.find((r) => r.class);
  if (latest?.class) parts.push(`Water tested ${formatMonth(latest.month)}: ${WATER_CLASS[latest.class].short.toLowerCase()}.`);
  const built = lake.location?.hasOutline ? lake.nature?.builtInsideOutlinePct : undefined;
  if (built !== undefined && built >= 1) parts.push(`${percent(built)} of it is built over.`);
  return parts.join(" ");
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const lake = getLake((await params).id);
  if (!lake) return { title: "Lake not found · Lakes of Bendakaluru" };
  const name = displayName(lake.name);
  const description = describe(lake, name);
  const photo = lake.photos?.[0];
  return {
    title: `${name} · Lakes of Bendakaluru`,
    description,
    openGraph: {
      title: name,
      description,
      siteName: "Lakes of Bendakaluru",
      images: photo ? [{ url: photo.thumb, alt: `${name}. Photo: ${photo.credit}` }] : undefined,
    },
  };
}

export default async function LakePage({ params }: Props) {
  const { id } = await params;
  const lake = getLake(id);
  if (!lake) notFound();

  const name = displayName(lake.name);
  const rankedCount = getLakes().filter((l) => l.sizeRank !== undefined).length;
  const gone = lake.status !== "exists";

  return (
    <>
      <main>
        <Hero lake={lake} name={name} />
        {/* Slips and headlines below take the lake's own paper. */}
        <div
          className="page-x mx-auto max-w-[1600px] pb-16 md:pb-[104px]"
          style={{ "--paper": paperFor(lake.water?.valley).sheet } as CSSProperties}
        >
          <Title lake={lake} summary={getSummary(lake.id)} rankedCount={rankedCount} />
          <YearsSection lake={lake} />
          <SizeSection lake={lake} />
          {gone ? <HistorySection lake={lake} /> : null}
          <QualitySection lake={lake} />
          <BuiltSection lake={lake} />
          <CareSection lake={lake} />
          <FlowSection lake={lake} />
          <NatureSection lake={lake} />
          {gone ? null : <HistorySection lake={lake} />}
          <PhotosSection lake={lake} name={name} />
          <PlaceSection lake={lake} />
          <LinksSection lake={lake} />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
