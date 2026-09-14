import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import MapExplorer from "@/components/map/MapExplorer";
import MapFallback from "@/components/map/MapFallback";
import { share } from "@/lib/share";

export const metadata: Metadata = share(
  "Every lake on one map · Lakes of Bendakaluru",
  "Find any lake in Bengaluru on one map. Search by name, Kannada name or ward, or see the biggest lakes, the most polluted, the most built over and the ones near you.",
  "/map",
);

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
