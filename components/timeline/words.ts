import type { Kind } from "./types";

/** Each kind of record, with the paper its slip and its mark on the line are cut from. */
export const KINDS: { kind: Kind; name: string; one: string; paper: string }[] = [
  { kind: "map", name: "Maps", one: "Map", paper: "#FF8A1F" },
  { kind: "census", name: "Censuses", one: "Census", paper: "#F59AC0" },
  { kind: "satellite", name: "Satellite and aerial photos", one: "Satellite or aerial photo", paper: "#1F48D6" },
  { kind: "report", name: "Reports and lists", one: "Report or list", paper: "#2FA35B" },
];

export function kindOf(kind: Kind) {
  return KINDS.find((k) => k.kind === kind) ?? KINDS[0];
}
