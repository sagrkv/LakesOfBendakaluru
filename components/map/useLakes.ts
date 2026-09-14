"use client";

import { useCallback, useEffect, useState } from "react";
import type { LakeSummary } from "@/lib/lake";

export type LakesState =
  | { status: "loading" }
  | { status: "ready"; lakes: LakeSummary[]; gone: number }
  | { status: "error" };

/**
 * Reads public/data/lakes.json in the browser, so the page itself stays static and small.
 * The map shows only lakes that still exist; the rest are counted for the link to the Forgotten Lakes page.
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
        const lakes = all.filter((lake) => lake.status === "exists");
        setState({ status: "ready", lakes, gone: all.length - lakes.length });
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
