import type { BBox, LakeSummary, LngLat } from "@/lib/lake";

const EARTH_KM = 6371;

/** Straight-line distance between two points, in kilometres. */
export function distanceKm([lng1, lat1]: LngLat, [lng2, lat2]: LngLat): number {
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLng = (lng2 - lng1) * rad;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_KM * Math.asin(Math.sqrt(a));
}

/** About 450 m either side of a lake that is known only as a point. */
const POINT_PAD = 0.004;

export function boxOf(lake: LakeSummary): BBox | null {
  if (lake.bbox) return lake.bbox;
  if (!lake.point) return null;
  return boxAround(lake.point);
}

export function boxAround([lng, lat]: LngLat): BBox {
  return [lng - POINT_PAD, lat - POINT_PAD, lng + POINT_PAD, lat + POINT_PAD];
}

export function unionBox(boxes: (BBox | null)[]): BBox | null {
  let out: BBox | null = null;
  for (const box of boxes) {
    if (!box) continue;
    out = out
      ? [Math.min(out[0], box[0]), Math.min(out[1], box[1]), Math.max(out[2], box[2]), Math.max(out[3], box[3])]
      : box;
  }
  return out;
}

type PointCollection = GeoJSON.FeatureCollection<GeoJSON.Point, { id: string; name: string; valley: string }>;

/** Lakes drawn as points on the map: the ones with no outline. */
export function pointsOf(lakes: LakeSummary[], keep: (lake: LakeSummary) => boolean): PointCollection {
  const features: PointCollection["features"] = [];
  for (const lake of lakes) {
    if (!lake.point || !keep(lake)) continue;
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: lake.point },
      properties: { id: lake.id, name: lake.name, valley: lake.valley ?? "" },
    });
  }
  return { type: "FeatureCollection", features };
}
