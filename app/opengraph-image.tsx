import { ImageResponse } from "next/og";
import { formatCount } from "@/lib/format";
import { INK, lakeMarkup, OG_FONTS, OG_SIZE, OgWordmark, svgImage, TABLE } from "@/lib/og";
import { getLake, getLakes } from "@/lib/lakes";
import { SITE_HOST, SITE_IMAGE_ALT } from "@/lib/share";
import { paperFor } from "@/lib/valleys";

export const alt = SITE_IMAGE_ALT;
export const size = OG_SIZE;
export const contentType = "image/png";

const COLLAGE = { width: 700, height: 630 };

/** Where each lake sits in the collage, largest first: box centre, box size and tilt. The right column runs off the edge. */
const SLOTS = [
  { x: 200, y: 170, s: 300, tilt: -5 },
  { x: 480, y: 130, s: 260, tilt: 4 },
  { x: 640, y: 330, s: 240, tilt: -2 },
  { x: 350, y: 360, s: 250, tilt: 3 },
  { x: 130, y: 440, s: 200, tilt: -3 },
  { x: 520, y: 530, s: 230, tilt: -4 },
  { x: 290, y: 570, s: 190, tilt: 5 },
  { x: 680, y: 580, s: 190, tilt: 2 },
];

/** The largest standing lake of each valley's paper, so every colour of the site is in the picture. */
function collage(): string {
  const seen = new Set<string>();
  const picks = getLakes().flatMap((summary) => {
    if (summary.status !== "exists" || !summary.hasOutline) return [];
    const paper = paperFor(summary.valley).sheet;
    const sheet = seen.has(paper) ? undefined : getLake(summary.id)?.sheet;
    if (!sheet) return [];
    seen.add(paper);
    return [{ sheet, paper }];
  });
  const markup = picks
    .slice(0, SLOTS.length)
    .map(({ sheet, paper }, i) => {
      const { x, y, s, tilt } = SLOTS[i];
      return lakeMarkup(sheet, paper, { x: x - s / 2, y: y - s / 2, w: s, h: s }, tilt);
    })
    .join("");
  return svgImage(markup, COLLAGE.width, COLLAGE.height);
}

export default function Image() {
  const lakes = getLakes();
  const standing = lakes.filter((lake) => lake.status === "exists").length;

  return new ImageResponse(
    (
      <div style={{ display: "flex", width: "100%", height: "100%", background: TABLE, color: INK, fontFamily: "Instrument Serif" }}>
        <img src={collage()} width={COLLAGE.width} height={COLLAGE.height} alt="" style={{ position: "absolute", left: 540, top: 0 }} />
        <div style={{ display: "flex", flexDirection: "column", width: 560, padding: "56px 0 48px 64px", height: "100%" }}>
          <OgWordmark size={40} />
          <div style={{ display: "flex", marginTop: 44, fontSize: 104, lineHeight: 0.9 }}>Every lake in Bengaluru</div>
          <div style={{ display: "flex", marginTop: 24, fontSize: 32, lineHeight: 1.2 }}>
            {`${formatCount(standing)} still here, ${formatCount(lakes.length - standing)} gone. Size, who looks after it, how clean the water is.`}
          </div>
          <div style={{ display: "flex", marginTop: "auto", fontSize: 26, fontStyle: "italic" }}>{SITE_HOST}</div>
        </div>
      </div>
    ),
    { ...OG_SIZE, fonts: [...OG_FONTS] },
  );
}
