/** Plain-language formatting shared by every page. Safe in the browser. */

import type { WaterClass } from "./lake";

/** A FIFA pitch is 105 m by 68 m. */
const PITCH_ACRES = (105 * 68) / 4046.86;

export function formatAcres(acres: number): string {
  if (acres >= 100) return Math.round(acres).toLocaleString("en-IN");
  if (acres >= 10) return acres.toFixed(1);
  return acres.toFixed(2);
}

export function pitches(acres: number): string {
  const n = acres / PITCH_ACRES;
  if (n < 1) return "smaller than a football pitch";
  const rounded = n < 10 ? Math.round(n * 10) / 10 : Math.round(n);
  return `${rounded.toLocaleString("en-IN")} football pitch${rounded === 1 ? "" : "es"}`;
}

export function formatCount(n: number): string {
  return n.toLocaleString("en-IN");
}

export function formatMetres(m: number): string {
  return m >= 1000 ? `${(m / 1000).toFixed(m >= 10000 ? 0 : 1)} km` : `${Math.round(m)} m`;
}

export function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] ?? s[v] ?? s[0]}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-07" -> "July 2026" style, short: "Jul 2026". */
export function formatMonth(month: string): string {
  const [y, m] = month.split("-");
  return m ? `${MONTHS[Number(m) - 1]} ${y}` : y;
}

export function formatCoords([lng, lat]: [number, number]): string {
  return `${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`;
}

/**
 * KSPCB classes lakes A to E by the use the water is fit for.
 * A is drinking water after disinfection; E is irrigation and industrial cooling only.
 */
export const WATER_CLASS: Record<WaterClass, { short: string; long: string }> = {
  A: { short: "Drinkable after disinfection", long: "Fit to drink after disinfection" },
  B: { short: "Fit for bathing", long: "Fit for outdoor bathing" },
  C: { short: "Drinkable after treatment", long: "Fit to drink after full treatment" },
  D: { short: "Fit only for wildlife and fish", long: "Fit only for wildlife and fisheries" },
  E: { short: "Fit only for irrigation", long: "Fit only for irrigation, cooling and waste disposal" },
};
