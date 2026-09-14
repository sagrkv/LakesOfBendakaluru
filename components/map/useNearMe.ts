"use client";

import { useCallback, useState } from "react";
import type { LngLat } from "@/lib/lake";

export type NearMe =
  | { status: "idle" }
  | { status: "locating" }
  | { status: "found"; here: LngLat }
  | { status: "denied" }
  | { status: "unavailable" };

/** Asks the browser for a location only when someone taps Near me. */
export function useNearMe(): [NearMe, (onFound?: (here: LngLat) => void) => void] {
  const [state, setState] = useState<NearMe>({ status: "idle" });

  const locate = useCallback((onFound?: (here: LngLat) => void) => {
    if (!("geolocation" in navigator)) {
      setState({ status: "unavailable" });
      return;
    }
    setState({ status: "locating" });
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const here: LngLat = [position.coords.longitude, position.coords.latitude];
        setState({ status: "found", here });
        onFound?.(here);
      },
      (error) => setState({ status: error.code === error.PERMISSION_DENIED ? "denied" : "unavailable" }),
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 5 * 60 * 1000 },
    );
  }, []);

  return [state, locate];
}
