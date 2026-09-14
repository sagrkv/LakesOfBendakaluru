import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import MapExplorer from "@/components/map/MapExplorer";
import MapFallback from "@/components/map/MapFallback";

export const metadata: Metadata = {
  title: "Every lake on one map · Lakes of Bendakaluru",
  description:
    "Every lake in Bengaluru on one map: the biggest, the most polluted, the most built over, the ones near you and the ones that disappeared.",
};

/** The map runs edge to edge on phones, so it reaches under the notch and the home bar. */
export const viewport: Viewport = {
  themeColor: "#F6EEDB",
  viewportFit: "cover",
};

export default function MapPage() {
  // The explorer reads ?c= in the browser, so it renders below a Suspense boundary.
  return (
    <Suspense fallback={<MapFallback />}>
      <MapExplorer />
    </Suspense>
  );
}
