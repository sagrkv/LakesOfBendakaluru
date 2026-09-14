import type { LakeRecord, Rau1986 } from "@/lib/lake";
import { sourcesOf } from "../sources";
import type { Entry } from "./types";

/**
 * The scan's short columns are sometimes garbled (Hebbal's agency reads "Forest DeptxKSTIK", then a dash run).
 * Plain words, numbers and common punctuation pass; a dash run, a stray symbol, a letter glued to a digit
 * or capitals glued to a lower-case word do not.
 */
export function readable(text: string | undefined): string | undefined {
  const t = text?.trim();
  if (!t) return undefined;
  const plain = /^[A-Za-z0-9 .,&()'/-]+$/.test(t);
  const glued = /[a-z][A-Z]{2}|[A-Za-z]\d|\d[A-Za-z]/.test(t);
  return plain && !glued ? t : undefined;
}

function lowerFirst(text: string): string {
  return /^[A-Z][a-z]/.test(text) ? text[0].toLowerCase() + text.slice(1) : text;
}

function headline(r: Rau1986): string {
  if (r.status === "live" || r.status === "disused") return `Listed as a ${r.status} tank by the Lakshman Rau committee`;
  if (r.list === "green belt") return "Listed among green belt tanks by the Lakshman Rau committee";
  return "Listed by the Lakshman Rau committee";
}

/** The 1986 expert committee's row for the tank. Area is shown as printed, never converted. */
export function rauEntry(h: LakeRecord["history"]): Entry[] {
  const r = h?.rau1986;
  if (!r) return [];
  const zone = readable(r.zone);
  const agency = readable(r.agency);
  const name = r.nameAsPrinted?.trim();

  const notes = [
    name ? `Printed as ${name}${r.tankNo ? `, tank ${r.tankNo}` : ""}` : "",
    r.areaHa ? `${r.areaHa} ha, as printed in the 1986 report` : "",
    zone ? `Among the tanks ${lowerFirst(zone)}${r.taluk ? `, ${r.taluk} taluk` : ""}` : "",
    agency ? `Work to be done by: ${agency}` : "",
  ].filter(Boolean);

  return [
    {
      id: "rau-1986",
      from: 1986,
      when: "1986",
      label: headline(r),
      notes,
      sources: sourcesOf(h, "rau1986"),
      lane: "records",
      tone: "lake",
      rau: r,
    },
  ];
}
