"use client";

import SourceRow from "./SourceRow";
import type { Resolved } from "./types";

/**
 * The same records as the timeline, as a plain list for reading and for search engines.
 * A client component only so the page sends the records once: the timeline already receives this array,
 * and a server-rendered list would repeat all of it in the page's data as well as its HTML.
 */
export default function SourceList({ sources }: { sources: Resolved[] }) {
  return (
    <ol className="mt-6 border-t border-rule">
      {sources.map((source) => (
        <SourceRow key={source.id} source={source} />
      ))}
    </ol>
  );
}
