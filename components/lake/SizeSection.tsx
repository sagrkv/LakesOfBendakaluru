import type { LakeRecord } from "@/lib/lake";
import { formatAcres, formatMetres } from "@/lib/format";
import Fact, { Note } from "./Fact";
import Section from "./Section";
import { sourcesOf } from "./sources";
import { pitchLine } from "./Title";
import { kindWords } from "./words";

function Acres({ acres }: { acres: number }) {
  return <Note>{pitchLine(acres)}</Note>;
}

export default function SizeSection({ lake }: { lake: LakeRecord }) {
  const size = lake.size;
  const span = lake.sheet?.span;
  const measures = [size?.outlineAcres, size?.recordedAcres, size?.surveyed2018Acres, size?.onOldMapAcres].filter(
    (a): a is number => a !== undefined,
  );
  const disagree = measures.length > 1 && Math.max(...measures) > Math.min(...measures) * 1.05;
  const empty = measures.length === 0 && !span && size?.maxDepthM === undefined && !lake.kind;

  return (
    <Section id="size" title="How big it is" missing="No area on record." empty={empty}>
      {disagree ? (
        <p className="sm:col-span-2 xl:col-span-3 max-w-[65ch]">
          The records disagree on its size, so each measure is shown.
        </p>
      ) : null}
      {size?.outlineAcres !== undefined ? (
        <Fact label="Drawn outline" value={`${formatAcres(size.outlineAcres)} acres`} sources={sourcesOf(size, "outlineAcres")}>
          <Acres acres={size.outlineAcres} />
        </Fact>
      ) : null}
      {size?.recordedAcres !== undefined ? (
        <Fact label="Land records" value={`${formatAcres(size.recordedAcres)} acres`} sources={sourcesOf(size, "recordedAcres")}>
          <Acres acres={size.recordedAcres} />
        </Fact>
      ) : null}
      {size?.surveyed2018Acres !== undefined ? (
        <Fact
          label="2018 lake survey"
          value={`${formatAcres(size.surveyed2018Acres)} acres`}
          sources={sourcesOf(size, "surveyed2018Acres")}
        >
          <Acres acres={size.surveyed2018Acres} />
        </Fact>
      ) : null}
      {size?.onOldMapAcres !== undefined ? (
        <Fact label="On the old map" value={`${formatAcres(size.onOldMapAcres)} acres`} sources={sourcesOf(size, "onOldMapAcres")}>
          <Acres acres={size.onOldMapAcres} />
        </Fact>
      ) : null}
      {span ? (
        <Fact label="End to end" value={formatMetres(span.m)} sources={sourcesOf(size, "outlineAcres")}>
          <Note>The longest straight line across the outline</Note>
        </Fact>
      ) : null}
      {size?.maxDepthM !== undefined ? (
        <Fact label="Deepest point, 2018" value={`${size.maxDepthM} m`} sources={sourcesOf(size, "maxDepthM")} />
      ) : null}
      {lake.kind ? <Fact label="Kind of lake" value={kindWords(lake.kind)} sources={sourcesOf(lake, "kind")} /> : null}
    </Section>
  );
}
