import type { LakeRecord } from "@/lib/lake";
import { NOW } from "@/components/timeline/gaps";
import Section from "../Section";
import { gapSentence, segmentsOf } from "./axis";
import { entriesOf } from "./entries";
import EntryRow from "./EntryRow";
import Figure from "./Figure";

/**
 * Every dated record of the lake on one line from the oldest to today, then the same records as a list with sources.
 * Sits right under the title slips: it is the lake's whole story, and the sections below take one side of it each.
 */
export default function YearsSection({ lake }: { lake: LakeRecord }) {
  const entries = entriesOf(lake);
  const segments = segmentsOf(entries, NOW);
  const gaps = gapSentence(segments, NOW);

  return (
    <Section id="through-the-years" title="Through the years" missing="No dated record of this lake." empty={entries.length === 0}>
      <div className="min-w-0 sm:col-span-2 xl:col-span-3">
        {gaps ? <p className="missing mb-6 max-w-[65ch] md:mb-10">{gaps}</p> : null}
        <Figure lake={lake} entries={entries} segments={segments} />
        <ol className="mt-10 border-t border-rule md:mt-16">
          {entries.map((entry) => (
            <EntryRow key={entry.id} entry={entry} />
          ))}
        </ol>
      </div>
    </Section>
  );
}
