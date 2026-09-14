"use client";

import { useCallback, useRef, useState } from "react";
import { tag, type Tagged } from "./filter";
import type { MissingLake } from "./types";

export type AllMissing = { status: "idle" | "loading" | "error"; lakes: null } | { status: "ready"; lakes: Tagged[] };

/** The full list is fetched only when someone asks for it: showing everything, or choosing a bar. */
export function useAllMissing() {
  const [state, setState] = useState<AllMissing>({ status: "idle", lakes: null });
  const started = useRef(false);

  const load = useCallback(async () => {
    if (started.current) return;
    started.current = true;
    setState({ status: "loading", lakes: null });
    try {
      const response = await fetch("/data/missing.json");
      if (!response.ok) throw new Error(`missing.json answered ${response.status}`);
      const rows: unknown = await response.json();
      if (!Array.isArray(rows)) throw new Error("missing.json is not a list");
      setState({ status: "ready", lakes: (rows as MissingLake[]).map(tag) });
    } catch {
      started.current = false;
      setState({ status: "error", lakes: null });
    }
  }, []);

  return { ...state, load };
}
