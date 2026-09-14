/** The record of Bengaluru's lakes, source by source. See docs/research/timeline-sources.md. */

export type Kind = "map" | "census" | "satellite" | "report";

/** On the site: in the pipeline now. Found: public, not added yet. Not public: known to exist, no copy to use. */
export type Status = "on-site" | "found" | "not-public";

/** A link as the research gives it, or the key of a source the site already cites in sources.json. */
export type SourceLink = { label: string; href: string } | { label: string; key: string };

export type TimelineSource = {
  id: string;
  /** First year the source records. Left out when no year is on record. */
  from?: number;
  /** Last year, when the source covers a span. */
  to?: number;
  /** The date as a reader sees it. */
  when: string;
  title: string;
  /** Publisher or holder. Left out when the research does not name one. */
  holder?: string;
  kind: Kind;
  /** What it tells us about a lake, in one plain sentence. */
  tells: string;
  coverage: string;
  licence: string;
  status: Status;
  /** How it can be had, when that is the obstacle. */
  access?: string;
  links: SourceLink[];
};

/** A source with its links resolved to addresses, ready to render. */
export type ResolvedLink = { label: string; href: string };
export type Resolved = Omit<TimelineSource, "links"> & { links: ResolvedLink[]; sourcesAnchor?: string };

/** A stretch of years the record barely covers, named on the timeline. */
export type Gap = { from: number; to: number; years: string; text: string };
