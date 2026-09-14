import type { LakeRecord, Rau1986, Source } from "@/lib/lake";

/** Filled: the record finds a lake. Outlined: the record finds none. */
export type Tone = "lake" | "no-lake";

export type Season = NonNullable<NonNullable<LakeRecord["water"]>["current"]>[number];

/** One dated fact on a lake's timeline. */
export type Entry = {
  id: string;
  from: number;
  /** Last year, when the fact covers a span. */
  to?: number;
  /** Separate years for one fact, such as two map sheets printed in different years. */
  points?: number[];
  /** The year column as a reader sees it. */
  when: string;
  label: string;
  notes: string[];
  sources: Source[];
  /** Records are pieces on the top lane; water and land cover draw their own strips. */
  lane: "records" | "water" | "cover";
  tone: Tone;
  link?: { href: string; label: string };
  seasons?: Season[];
  rau?: Rau1986;
};

export function yearSpan(from: number, to: number): string {
  return from === to ? String(from) : `${from}-${to}`;
}
