"use client";

import { useCallback, useSyncExternalStore } from "react";
import { useSearchParams } from "next/navigation";
import { isCollectionKey, type CollectionKey } from "./collections";

/** The open collection lives in ?c= so a list can be shared. Choosing one adds a history step. */
export function useCollectionParam(): [CollectionKey | null, (key: CollectionKey | null) => void] {
  const params = useSearchParams();
  const value = params.get("c");

  const set = useCallback((key: CollectionKey | null) => {
    const next = new URLSearchParams(window.location.search);
    if (key) next.set("c", key);
    else next.delete("c");
    const query = next.toString();
    window.history.pushState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`);
  }, []);

  return [isCollectionKey(value) ? value : null, set];
}

const SELECT_EVENT = "lakes:select";

function subscribe(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  window.addEventListener(SELECT_EVENT, onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
    window.removeEventListener(SELECT_EVENT, onChange);
  };
}

function readHash(): string {
  try {
    return decodeURIComponent(window.location.hash.slice(1));
  } catch {
    return "";
  }
}

/** The open lake lives in the hash, so /map#<id> links from lake pages open straight onto it. */
export function useHashLake(): [string | null, (id: string | null) => void] {
  const id = useSyncExternalStore(subscribe, readHash, () => "");

  const set = useCallback((next: string | null) => {
    const hash = next ? `#${encodeURIComponent(next)}` : "";
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${hash}`);
    window.dispatchEvent(new Event(SELECT_EVENT));
  }, []);

  return [id || null, set];
}

const WIDE = "(min-width: 1024px)";

function subscribeWide(onChange: () => void) {
  const query = window.matchMedia(WIDE);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

/** Laptops get a side panel; phones and tablets get a dock under the map. */
export function useWide(): boolean {
  return useSyncExternalStore(
    subscribeWide,
    () => window.matchMedia(WIDE).matches,
    () => false,
  );
}
