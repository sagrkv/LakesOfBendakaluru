import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Sheet } from "./lake";

/*
 * Shared pieces of the link preview images: the table, ink and sun colours, the serif,
 * the wordmark label and a lake cut out of its paper. Previews are drawn by next/og,
 * which only does flexbox, so every box with more than one child is a flex box.
 */

export const OG_SIZE = { width: 1200, height: 630 };
export const TABLE = "#F6EEDB";
export const INK = "#1B1A17";
export const SUN = "#FFC933";
const SHADOW = "#5A3B12";

export const OG_FONTS = [
  { name: "Instrument Serif", data: readFileSync(join(process.cwd(), "assets/fonts/InstrumentSerif-Regular.ttf")), style: "normal", weight: 400 },
  { name: "Instrument Serif", data: readFileSync(join(process.cwd(), "assets/fonts/InstrumentSerif-Italic.ttf")), style: "italic", weight: 400 },
] as const;

export function OgWordmark({ size = 40 }: { size?: number }) {
  return (
    <div
      style={{
        display: "flex",
        alignSelf: "flex-start",
        background: SUN,
        color: INK,
        fontStyle: "italic",
        fontSize: size,
        lineHeight: 1,
        padding: `${size * 0.18}px ${size * 0.4}px ${size * 0.3}px`,
        transform: "rotate(-1.2deg)",
        boxShadow: `3px 6px 0 ${INK}`,
      }}
    >
      Lakes of Bendakaluru
    </div>
  );
}

/** One lake as SVG markup, fitted inside a w by h box at (x, y), in its paper with an ink edge and a brown shadow. */
export function lakeMarkup(sheet: Sheet, color: string, box: { x: number; y: number; w: number; h: number }, tilt = 0): string {
  const k = Math.min(box.w / sheet.w, box.h / sheet.h);
  const cx = box.x + box.w / 2;
  const cy = box.y + box.h / 2;
  const place = `translate(${cx} ${cy}) rotate(${tilt}) scale(${k}) translate(${-sheet.w / 2} ${-sheet.h / 2})`;
  return `<g transform="${place}">
    <path d="${sheet.d}" fill-rule="evenodd" fill="${SHADOW}" fill-opacity="0.3" transform="translate(${6 / k} ${10 / k})"/>
    <path d="${sheet.d}" fill-rule="evenodd" fill="${color}" stroke="${INK}" stroke-width="${2.5 / k}" stroke-linejoin="round"/>
  </g>`;
}

export function svgImage(markup: string, width: number, height: number): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">${markup}</svg>`;
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}
