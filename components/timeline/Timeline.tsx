"use client";

import { useMemo, useRef, useState, type CSSProperties, type KeyboardEvent } from "react";
import DetailSlip from "./DetailSlip";
import { GAPS } from "./gaps";
import { at, END, layoutLanes, START, TICKS, type Placed } from "./layout";
import Mark from "./Mark";
import styles from "./timeline.module.css";
import type { Resolved } from "./types";

/** The empty stretch of the lower lanes where the slip sits on wide screens. */
const SLIP_FROM = 1848;
const SLIP_TO = 1953;

const NEXT: Record<string, (i: number, last: number) => number> = {
  ArrowRight: (i, last) => Math.min(i + 1, last),
  ArrowDown: (i, last) => Math.min(i + 1, last),
  ArrowLeft: (i) => Math.max(i - 1, 0),
  ArrowUp: (i) => Math.max(i - 1, 0),
  Home: () => 0,
  End: (_, last) => last,
};

/** Every record as a mark on one axis, grouped by kind, with the gaps named and a slip for the chosen one. */
export default function Timeline({ sources }: { sources: Resolved[] }) {
  const { lanes, steps } = useMemo(() => layoutLanes(sources), [sources]);
  const [selected, setSelected] = useState<number | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const marks = useRef<(HTMLButtonElement | null)[]>([]);
  const closing = useRef(false);

  const select = (index: number) => {
    if (closing.current) {
      closing.current = false;
      return;
    }
    setSelected(index);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "Escape") return setSelected(null);
    const next = NEXT[event.key];
    if (!next) return;
    event.preventDefault();
    const index = next(selected ?? 0, sources.length - 1);
    const mark = marks.current[index];
    mark?.focus({ preventScroll: true });
    mark?.scrollIntoView({ block: "nearest", inline: "nearest" });
    setSelected(index);
  };

  const close = () => {
    const index = selected;
    setSelected(null);
    if (index === null) return;
    closing.current = true;
    marks.current[index]?.focus();
    closing.current = false;
  };

  const renderMark = (placed: Placed, rows: number) => (
    <Mark
      key={placed.source.id}
      ref={(node) => {
        marks.current[placed.index] = node;
      }}
      placed={placed}
      rows={rows}
      selected={selected === placed.index}
      tabbable={(selected ?? 0) === placed.index}
      hovered={hovered === placed.index}
      onSelect={select}
      onHover={setHovered}
      onKeyDown={onKeyDown}
    />
  );

  const chartStyle = {
    "--lane-cols": lanes.map((lane) => `minmax(64px, ${lane.rows}fr)`).join(" "),
    "--steps": steps,
    "--slip-a": at(SLIP_FROM),
    "--slip-len": (SLIP_TO - SLIP_FROM) / (END - START),
  } as CSSProperties;

  return (
    <>
      <p className="xl:hidden mb-6 label font-normal text-missing">
        Tap a mark to read what it tells us and open it.
      </p>
      <div role="group" aria-label="Every record, oldest first" className={styles.chart} style={chartStyle}>
        <div aria-hidden className={styles.backdrop}>
          {TICKS.map((year) => (
            <span key={year} className={styles.gridline} style={{ "--a": at(year) } as CSSProperties} />
          ))}
          {GAPS.map((gap) => (
            <span
              key={gap.from}
              className={styles.band}
              style={{ "--a": at(gap.from), "--len": (gap.to - gap.from) / (END - START) } as CSSProperties}
            />
          ))}
        </div>

        <div className={styles.notes}>
          {GAPS.map((gap) => (
            <p key={gap.from} className={`${styles.note} label`} style={{ "--a": at(gap.from) } as CSSProperties}>
              {gap.years}. <span className="missing font-normal">{gap.text}</span>
            </p>
          ))}
        </div>

        <div aria-hidden className={styles.ticks}>
          {TICKS.map((year) => (
            <span
              key={year}
              className={`${styles.tick} label font-normal text-missing tabular-nums`}
              style={{ "--a": at(year) } as CSSProperties}
            >
              {year}
            </span>
          ))}
        </div>

        {lanes.map((lane, k) => {
          const place = { "--h-row": k + 3, "--v-col": k + 2, "--rows": lane.rows } as CSSProperties;
          return (
            <div key={lane.kind} role="group" aria-label={lane.name} className="contents">
              <h3 className={`${styles.laneName} label`} style={place}>
                {lane.name}
              </h3>
              <div className={styles.track} style={place}>
                {lane.dated.map((placed) => renderMark(placed, lane.rows))}
              </div>
              <div className={styles.undated} style={place}>
                {lane.undated.map((placed) => renderMark(placed, lane.rows))}
              </div>
            </div>
          );
        })}

        <p className={`${styles.undatedName} label`}>No year on record</p>

        <div className={styles.slipArea}>
          <DetailSlip source={selected === null ? null : sources[selected]} onClose={close} />
        </div>
      </div>
    </>
  );
}
