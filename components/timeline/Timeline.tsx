import RecordSlip from "./RecordSlip";
import { rowsOf, type Row } from "./rows";
import type { Resolved } from "./types";

/*
 * One ink line down the page, oldest at the top. On a phone the line runs down the left edge;
 * from 1024 px the years sit in their own column left of it and stay in view while their records scroll past.
 * Record marks are placed against these column widths (RecordSlip), so change them together.
 */
const ROW = "grid grid-cols-[24px_minmax(0,1fr)] gap-x-4 lg:grid-cols-[160px_24px_minmax(0,760px)] lg:gap-x-6";
const SPACE = "pb-10 md:pb-16";

/** The line itself: solid, or dashed where the record is thin. A dot marks where a year starts. */
function Line({ dashed = false, dot = false }: { dashed?: boolean; dot?: boolean }) {
  return (
    <div aria-hidden className="relative">
      <span
        className={`absolute inset-y-0 left-1/2 w-[3px] -translate-x-1/2 ${
          dashed ? "bg-[repeating-linear-gradient(var(--color-ink)_0_8px,transparent_8px_16px)]" : "bg-ink"
        }`}
      />
      {dot ? <span className="absolute top-3 left-1/2 size-4 -translate-x-1/2 rounded-full bg-ink ring-4 ring-table lg:top-5" /> : null}
    </div>
  );
}

function Year({ label, records }: { label: string; records: Resolved[] }) {
  return (
    <li className={ROW}>
      <div className="hidden lg:block">
        <p className="sticky top-6 text-right font-serif text-[64px] leading-none tabular-nums">{label}</p>
      </div>
      <Line dot />
      <div className={`${SPACE} min-w-0`}>
        <p className="font-serif text-[40px] leading-none tabular-nums lg:hidden">{label}</p>
        <ul aria-label={label} className="mt-4 space-y-6 lg:mt-0 lg:space-y-8">
          {records.map((source) => (
            <li key={source.id}>
              <RecordSlip source={source} />
            </li>
          ))}
        </ul>
      </div>
    </li>
  );
}

function RowItem({ row }: { row: Row }) {
  switch (row.type) {
    case "century":
      return (
        <li className={ROW}>
          <div className="hidden lg:block" />
          <Line />
          <h2 className={`${SPACE} font-serif text-[64px] leading-[0.86] md:text-[96px]`}>
            <span className="highlight">{row.label}</span>
          </h2>
        </li>
      );
    case "gap":
      return (
        <li className={ROW}>
          <div className="hidden lg:block" />
          <Line dashed />
          <p className={`${SPACE} max-w-[40rem]`}>
            <span className="label block">{row.gap.years}</span>
            <span className="missing mt-1 block">{row.gap.text}</span>
          </p>
        </li>
      );
    case "year":
      return <Year label={String(row.year)} records={row.records} />;
    case "undated":
      return <Year label="No year" records={row.records} />;
  }
}

/** Every record on one line, oldest first, then the records with no year on record. */
export default function Timeline({ sources }: { sources: Resolved[] }) {
  return (
    <ol aria-label="Every record, oldest first">
      {rowsOf(sources).map((row, i) => (
        <RowItem key={i} row={row} />
      ))}
    </ol>
  );
}
