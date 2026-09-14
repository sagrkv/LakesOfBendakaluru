import { formatAcres, formatMetres } from "@/lib/format";
import type { LakeSummary } from "@/lib/lake";

export function acresText(lake: LakeSummary): string | undefined {
  return lake.acres === undefined ? undefined : `${formatAcres(lake.acres)} acres`;
}

export function pctText(pct: number): string {
  if (pct === 0) return "0%";
  return pct < 10 ? `${pct.toFixed(1)}%` : `${Math.round(pct)}%`;
}

export function distanceText(km: number): string {
  return formatMetres(km * 1000);
}

export function valleyName(valley: string | undefined): string | undefined {
  if (!valley) return undefined;
  if (valley.toLowerCase().startsWith("unnamed")) return "An unnamed valley";
  return `${valley} valley`;
}

export function placeName(lake: LakeSummary): string | undefined {
  if (!lake.ward) return undefined;
  return lake.corporation ? `${lake.ward} ward, ${lake.corporation}` : `${lake.ward} ward`;
}
