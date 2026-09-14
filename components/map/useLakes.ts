"use client";

import { useCallback, useEffect, useState } from "react";
import type { LakeSummary } from "@/lib/lake";

export type LakesState =
  | { status: "loading" }
  | { status: "ready"; lakes: LakeSummary[]; gone: number; missing: number }
  | { status: "error" };

/**
 * Reads public/data/lakes.json in the browser, so the page itself stays static and small.
 * The map shows only lakes that still exist and have a shape. Lakes that disappeared, and lakes the
 * 2018 survey recorded but no map draws, are counted for the links to their own pages.
 */
export function useLakes(): [LakesState, () => void] {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<LakesState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetch("/data/lakes.json", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`lakes.json answered ${response.status}`);
        return response.json() as Promise<unknown>;
      })
      .then((data) => {
        if (!Array.isArray(data)) throw new Error("lakes.json is not a list");
        const all = data as LakeSummary[];
        const existing = all.filter((lake) => lake.status === "exists");
        const lakes = existing.filter((lake) => lake.hasOutline);
        setState({ status: "ready", lakes, gone: all.length - existing.length, missing: existing.length - lakes.length });
      })
      .catch(() => {
        if (!controller.signal.aborted) setState({ status: "error" });
      });
    return () => controller.abort();
  }, [attempt]);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  return [state, retry];
}
