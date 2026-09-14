import { ImageResponse } from "next/og";
import { bestAcres } from "@/components/lake/Title";
import { displayName, percent } from "@/components/lake/words";
import { formatAcres, WATER_CLASS } from "@/lib/format";
import type { LakeRecord } from "@/lib/lake";
import { getLake } from "@/lib/lakes";
import { INK, lakeMarkup, OG_FONTS, OG_SIZE, OgWordmark, svgImage, TABLE } from "@/lib/og";
import { SITE_HOST } from "@/lib/share";
import { paperFor } from "@/lib/valleys";

export const alt = "The lake cut out at its real shape, with its size, water quality and how much is built over.";
export const size = OG_SIZE;
export const contentType = "image/png";

const SHAPE = { width: 620, height: 630 };

/** Three short facts for the slips: what a reader of a shared link most wants to know. */
function facts(lake: LakeRecord): [string, string][] {
  if (lake.status !== "exists") {
    return [
      ["What happened", lake.status === "converted" ? "Converted" : "Disappeared"],
      ["Gone by", lake.history?.goneBy ? String(lake.history.goneBy) : "Not recorded"],
      ["Size", bestAcres(lake) ? `${formatAcres(bestAcres(lake)?.acres ?? 0)} acres` : "Not recorded"],
    ];
  }
  const size = bestAcres(lake);
  const tested = lake.waterQuality?.latest?.find((reading) => reading.class)?.class;
  const built = lake.location?.hasOutline ? lake.nature?.builtInsideOutlinePct : undefined;
  return [
    // The two short facts first, so they share a row and the longer water line takes the next.
    ["Size", size ? `${formatAcres(size.acres)} acres` : "Not recorded"],
    ["Built over", built === undefined ? "Not measured" : percent(built)],
    ["Water", tested ? WATER_CLASS[tested].short : "Not tested"],
  ];
}

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const lake = getLake((await params).id);
  const name = lake ? displayName(lake.name) : "Lake not found";
  const paper = paperFor(lake?.water?.valley);
  const nameSize = Math.round(Math.min(104, Math.max(60, 1300 / Math.max(name.length, 8))));
  const shape = lake?.sheet
    ? svgImage(lakeMarkup(lake.sheet, paper.sheet, { x: 40, y: 50, w: 540, h: 530 }, -3), SHAPE.width, SHAPE.height)
    : svgImage(
        `<circle cx="310" cy="315" r="120" fill="${paper.sheet}" stroke="${INK}" stroke-width="3"/>`,
        SHAPE.width,
        SHAPE.height,
      );

  return new ImageResponse(
    (
      <div style={{ display: "flex", width: "100%", height: "100%", background: TABLE, color: INK, fontFamily: "Instrument Serif" }}>
        <img src={shape} width={SHAPE.width} height={SHAPE.height} alt="" style={{ position: "absolute", left: 580, top: 0 }} />
        <div style={{ display: "flex", flexDirection: "column", width: 600, padding: "56px 0 48px 64px", height: "100%" }}>
          <OgWordmark size={34} />
          <div style={{ display: "flex", marginTop: 40, fontSize: nameSize, lineHeight: 0.9 }}>{name}</div>
          <div style={{ display: "flex", alignItems: "center", marginTop: 20, fontSize: 28 }}>
            <div style={{ display: "flex", width: 22, height: 22, marginRight: 12, background: paper.sheet, border: `2px solid ${INK}` }} />
            {lake?.water?.valley ? `${lake.water.valley} valley` : "No valley on record"}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", marginTop: 32 }}>
            {(lake ? facts(lake) : []).map(([label, value], i) => (
              <div
                key={label}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  marginRight: 16,
                  marginBottom: 16,
                  padding: "10px 16px 14px",
                  background: TABLE,
                  boxShadow: `2px 4px 0 rgba(90, 59, 18, 0.35)`,
                  border: `1px solid rgba(27, 26, 23, 0.12)`,
                  transform: `rotate(${[-1.2, 0.8, -0.6][i]}deg)`,
                }}
              >
                <div style={{ display: "flex", fontSize: 20 }}>{label}</div>
                <div style={{ display: "flex", fontSize: 36, lineHeight: 1 }}>{value}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", marginTop: "auto", fontSize: 26, fontStyle: "italic" }}>{SITE_HOST}</div>
        </div>
      </div>
    ),
    { ...OG_SIZE, fonts: [...OG_FONTS] },
  );
}
