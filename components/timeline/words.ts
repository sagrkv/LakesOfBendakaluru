import type { Kind, Status } from "./types";

/** Lanes top to bottom on a laptop, left to right on a phone. */
export const KINDS: { kind: Kind; name: string; one: string }[] = [
  { kind: "map", name: "Maps", one: "Map" },
  { kind: "census", name: "Censuses", one: "Census" },
  { kind: "satellite", name: "Satellite and aerial photos", one: "Satellite or aerial photo" },
  { kind: "report", name: "Reports and lists", one: "Report or list" },
];

export const STATUSES: { status: Status; name: string }[] = [
  { status: "on-site", name: "On the site" },
  { status: "found", name: "Found, not added yet" },
  { status: "not-public", name: "Not public" },
];

export function kindName(kind: Kind): string {
  return KINDS.find((k) => k.kind === kind)?.one ?? kind;
}

export function statusName(status: Status): string {
  return STATUSES.find((s) => s.status === status)?.name ?? status;
}
