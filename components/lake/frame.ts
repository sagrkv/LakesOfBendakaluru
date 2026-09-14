import type { LakeRecord, LngLat } from "@/lib/lake";

/**
 * The satellite view behind a lake, requested in EPSG:32643 (UTM 43N) so the cut-out,
 * whose outline is in metres, sits exactly on the ground it was traced from.
 */

const A = 6378137;
const F = 1 / 298.257223563;
const E2 = F * (2 - F);
const EP2 = E2 / (1 - E2);
const K0 = 0.9996;
const LON0 = (75 * Math.PI) / 180;

/** WGS84 longitude and latitude to UTM zone 43 north, in metres. */
export function toUtm43([lng, lat]: LngLat): [number, number] {
  const phi = (lat * Math.PI) / 180;
  const sin = Math.sin(phi);
  const cos = Math.cos(phi);
  const tan = Math.tan(phi);
  const n = A / Math.sqrt(1 - E2 * sin * sin);
  const t = tan * tan;
  const c = EP2 * cos * cos;
  const a = cos * ((lng * Math.PI) / 180 - LON0);
  const e4 = E2 * E2;
  const e6 = e4 * E2;
  const m =
    A *
    ((1 - E2 / 4 - (3 * e4) / 64 - (5 * e6) / 256) * phi -
      ((3 * E2) / 8 + (3 * e4) / 32 + (45 * e6) / 1024) * Math.sin(2 * phi) +
      ((15 * e4) / 256 + (45 * e6) / 1024) * Math.sin(4 * phi) -
      ((35 * e6) / 3072) * Math.sin(6 * phi));
  const x =
    K0 * n * (a + ((1 - t + c) * a ** 3) / 6 + ((5 - 18 * t + t * t + 72 * c - 58 * EP2) * a ** 5) / 120) + 500000;
  const y =
    K0 *
    (m +
      n *
        tan *
        ((a * a) / 2 +
          ((5 - t + 9 * c + 4 * c * c) * a ** 4) / 24 +
          ((61 - 58 * t + t * t + 600 * c - 330 * EP2) * a ** 6) / 720));
  return [x, y];
}

/**
 * The hero is 4:5 on a phone and 5:2 from tablet up, both cropped from one square image.
 * A phone sees the middle 80% of its width, a laptop the middle 40% of its height,
 * so the square is sized for the lake to fit both crops with room around it.
 */
const PHONE_VISIBLE_W = 0.8;
const WIDE_VISIBLE_H = 0.4;
const ROOM = 1.25;
const MIN_SIDE_M = 400;
const POINT_SIDE_M = 700;

export type Frame = {
  /** Side of the square image on the ground, in metres. */
  side: number;
  url: (px: number) => string;
  /** Where the cut-out or point sits inside the square, as percentages. */
  box: { left: number; top: number; width: number; height: number };
};

function exportUrl(cx: number, cy: number, side: number, px: number): string {
  const h = side / 2;
  const bbox = [cx - h, cy - h, cx + h, cy + h].map((v) => v.toFixed(1)).join(",");
  const params = new URLSearchParams({
    bbox,
    bboxSR: "32643",
    imageSR: "32643",
    size: `${px},${px}`,
    format: "jpg",
    f: "image",
  });
  return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?${params}`;
}

export function sheetFrame(lake: LakeRecord): Frame | undefined {
  const sheet = lake.sheet;
  if (!sheet) return undefined;
  const centre = [sheet.origin[0] + sheet.w / 2, sheet.origin[1] - sheet.h / 2];
  const side = Math.max((sheet.w * ROOM) / PHONE_VISIBLE_W, (sheet.h * ROOM) / WIDE_VISIBLE_H, MIN_SIDE_M);
  return {
    side,
    url: (px) => exportUrl(centre[0], centre[1], side, px),
    box: {
      left: ((side - sheet.w) / 2 / side) * 100,
      top: ((side - sheet.h) / 2 / side) * 100,
      width: (sheet.w / side) * 100,
      height: (sheet.h / side) * 100,
    },
  };
}

export function pointFrame(point: LngLat): Frame {
  const [cx, cy] = toUtm43(point);
  return {
    side: POINT_SIDE_M,
    url: (px) => exportUrl(cx, cy, POINT_SIDE_M, px),
    box: { left: 50, top: 50, width: 0, height: 0 },
  };
}
