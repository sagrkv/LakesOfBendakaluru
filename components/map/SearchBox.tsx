"use client";

import { useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { formatCount } from "@/lib/format";
import type { LakeSummary } from "@/lib/lake";
import { MIN_QUERY, searchLakes, type SearchIndex } from "./search";
import { acresText } from "./words";

type Props = {
  index: SearchIndex | null;
  failed: boolean;
  /** In the phone bar: no visible label, a short placeholder. */
  compact?: boolean;
  onPick: (lake: LakeSummary) => void;
};

function describe(lake: LakeSummary, byWard: boolean): string {
  const ward = lake.ward ? `${lake.ward} ward` : undefined;
  if (byWard) return `In ${ward}`;
  return ward ?? lake.nameKannada ?? "";
}

export default function SearchBox({ index, failed, compact = false, onPick }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const id = useId();

  const result = useMemo(() => (index ? searchLakes(index, query) : { hits: [], total: 0 }), [index, query]);
  const showResults = open && index !== null && query.trim().length >= MIN_QUERY;
  const placeholder = failed ? "Search is unavailable" : !index ? "Loading lakes" : compact ? "Search" : "Hebbal, ಹೆಬ್ಬಾಳ or Yamalur";
  const more = result.total - result.hits.length;

  function pick(lake: LakeSummary) {
    onPick(lake);
    setQuery("");
    setOpen(false);
    input.current?.blur();
  }

  function focusOption(i: number) {
    const buttons = list.current?.querySelectorAll<HTMLButtonElement>("button");
    if (buttons?.length) buttons[Math.min(Math.max(i, 0), buttons.length - 1)].focus();
  }

  function onInputKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && result.hits.length) {
      event.preventDefault();
      focusOption(0);
    } else if (event.key === "Enter" && result.hits[0]) {
      event.preventDefault();
      pick(result.hits[0].lake);
    } else if (event.key === "Escape") {
      event.stopPropagation();
      if (query) setQuery("");
      else input.current?.blur();
    }
  }

  function onOptionKey(event: KeyboardEvent<HTMLButtonElement>, i: number) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusOption(i + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      if (i === 0) input.current?.focus();
      else focusOption(i - 1);
    } else if (event.key === "Escape") {
      event.stopPropagation();
      input.current?.focus();
    }
  }

  return (
    <div
      data-search
      className="relative min-w-0 flex-1"
      onFocus={() => setOpen(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <label htmlFor={id} className={compact ? "sr-only" : "label mb-2 block"}>
        Find a lake by name, Kannada name or ward
      </label>
      <div className="relative">
        <input
          id={id}
          ref={input}
          type="text"
          inputMode="search"
          enterKeyHint="search"
          autoComplete="off"
          spellCheck={false}
          value={query}
          disabled={!index}
          placeholder={placeholder}
          aria-controls={`${id}-results`}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onKeyDown={onInputKey}
          className="h-11 w-full bg-well pr-11 pl-3 text-[17px] leading-none placeholder:text-missing disabled:cursor-wait"
        />
        {query ? (
          <button
            type="button"
            aria-label="Clear search"
            onClick={() => {
              setQuery("");
              input.current?.focus();
            }}
            className="absolute top-0 right-0 grid size-11 place-items-center text-missing transition-colors duration-150 hover:text-ink active:translate-y-px"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
              <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </button>
        ) : null}
      </div>

      {showResults ? (
        <div id={`${id}-results`} className="slip absolute inset-x-0 top-full z-30 mt-2 max-h-[min(360px,50dvh)] overflow-y-auto overscroll-contain">
          {result.hits.length ? (
            <>
              <ul ref={list}>
                {result.hits.map(({ lake, byWard }, i) => (
                  <li key={lake.id}>
                    <button
                      type="button"
                      onClick={() => pick(lake)}
                      onKeyDown={(event) => onOptionKey(event, i)}
                      className="flex min-h-11 w-full items-baseline justify-between gap-3 px-3 py-2 text-left transition-colors duration-150 hover:bg-well focus-visible:bg-well focus-visible:outline-offset-[-2px] active:bg-rule"
                    >
                      <span className="min-w-0">
                        <span className="block font-serif text-[26px] leading-none break-words">{lake.name}</span>
                        <span className="label mt-1 block text-missing">{describe(lake, byWard)}</span>
                      </span>
                      <span className="label shrink-0 tabular-nums">{acresText(lake)}</span>
                    </button>
                  </li>
                ))}
              </ul>
              {more > 0 ? (
                <p className="label border-t border-rule px-3 py-2 text-missing">
                  {formatCount(more)} more {more === 1 ? "lake matches" : "lakes match"}. Type more of the name to narrow it down.
                </p>
              ) : null}
            </>
          ) : (
            <p role="status" className="px-3 py-3 text-[17px]">
              No lake or ward called “{query.trim()}”. Try part of the name, like Hebbal.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
