"use client";

import { useCallback, useRef, useState } from "react";
import { tag, type Tagged } from "./filter";
import type { PastLake } from "./types";

export type AllPast = { status: "idle" | "loading" | "error"; lakes: null } | { status: "ready"; lakes: Tagged[] };

/** The full list is fetched only when someone asks for it: showing everything, or choosing a bar. */
export function useAllPast() {
  const [state, setState] = useState<AllPast>({ status: "idle", lakes: null });
  const started = useRef(false);

  const load = useCallback(async () => {
    if (started.current) return;
    started.current = true;
    setState({ status: "loading", lakes: null });
    try {
      const response = await fetch("/data/past.json");
      if (!response.ok) throw new Error(`past.json answered ${response.status}`);
      const rows: unknown = await response.json();
      if (!Array.isArray(rows)) throw new Error("past.json is not a list");
      setState({ status: "ready", lakes: (rows as PastLake[]).map(tag) });
    } catch {
      started.current = false;
      setState({ status: "error", lakes: null });
    }
  }, []);

  return { ...state, load };
}
