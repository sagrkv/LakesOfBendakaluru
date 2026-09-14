"use client";

import { useEffect, useRef, useState } from "react";
import { AttributionControl, Map as MapLibreMap, NavigationControl, type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { BBox, LakeSummary, LngLat } from "@/lib/lake";
import { pointsOf } from "./geo";
import { CITY, collectionFilters, mapStyle, onlyId, TAP_LAYERS } from "./mapStyle";

export type Flight = { key: number; box: BBox; maxZoom: number };
export type MapStatus = "loading" | "ready" | "error" | "unsupported";

type Props = {
  lakes: LakeSummary[] | null;
  members: string[] | null;
  selectedId: string | null;
  here: LngLat | null;
  flight: Flight | null;
  /** Where to look once the map and the lake list are both ready; used once. */
  initialFlight: Flight | null;
  /** Room kept clear on the right, for the lake card on a laptop. */
  padRight: number;
  reloadKey: number;
  onSelect: (id: string | null) => void;
  onStatus: (status: MapStatus) => void;
};

function flyTo(map: MapLibreMap, flight: Flight, padRight: number, animate: boolean) {
  map.resize();
  const edge = map.getContainer().clientWidth < 640 ? 32 : 64;
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [west, south, east, north] = flight.box;
  map.fitBounds(
    [
      [west, south],
      [east, north],
    ],
    {
      padding: { top: edge, bottom: edge, left: edge, right: edge + padRight },
      maxZoom: flight.maxZoom,
      duration: animate && !still ? 700 : 0,
    },
  );
}

function source(map: MapLibreMap, id: string) {
  return map.getSource(id) as GeoJSONSource | undefined;
}

export default function LakeCanvas(props: Props) {
  const { lakes, members, selectedId, here, flight, initialFlight, padRight, reloadKey } = props;
  const container = useRef<HTMLDivElement>(null);
  const tag = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const callbacks = useRef({ onSelect: props.onSelect, onStatus: props.onStatus });
  const didInitial = useRef(false);
  const lastFlight = useRef(0);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    callbacks.current = { onSelect: props.onSelect, onStatus: props.onStatus };
  });

  useEffect(() => {
    const el = container.current;
    if (!el) return;

    let map: MapLibreMap;
    try {
      map = new MapLibreMap({
        container: el,
        style: mapStyle(),
        center: CITY,
        zoom: el.clientWidth < 640 ? 9.6 : 10.4,
        minZoom: 7,
        maxZoom: 17,
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
      });
    } catch {
      callbacks.current.onStatus("unsupported");
      return;
    }
    mapRef.current = map;
    map.touchZoomRotate.disableRotation();
    map.keyboard.disableRotation();
    // Bottom controls stack upwards, so the attribution added first stays underneath.
    map.addControl(new AttributionControl({ compact: false }), "bottom-right");
    map.addControl(new NavigationControl({ showCompass: false }), "bottom-right");

    map.on("load", () => {
      setLoaded(true);
      callbacks.current.onStatus("ready");
    });

    map.on("error", (event) => {
      const { sourceId } = event as { sourceId?: string };
      const name = (event.error as Error | undefined)?.name ?? "";
      if (sourceId === "lakes") callbacks.current.onStatus("error");
      else if (name.includes("GPU") || /webgl/i.test(event.error?.message ?? "")) callbacks.current.onStatus("unsupported");
    });

    const hit = (point: { x: number; y: number }, reach: number) => {
      const layers = TAP_LAYERS.filter((layer) => map.getLayer(layer));
      const exact = map.queryRenderedFeatures([point.x, point.y], { layers });
      if (exact.length || !reach) return exact[0];
      return map.queryRenderedFeatures(
        [
          [point.x - reach, point.y - reach],
          [point.x + reach, point.y + reach],
        ],
        { layers },
      )[0];
    };

    // A finger is wider than a small lake, so a tap that misses looks 14 px around it.
    map.on("click", (event) => {
      const feature = hit(event.point, 14);
      const id = feature?.properties?.id;
      callbacks.current.onSelect(typeof id === "string" ? id : null);
    });

    let hovered = "";
    const hideTag = () => {
      if (tag.current) tag.current.hidden = true;
      map.getCanvas().style.cursor = "";
      if (hovered) map.setFilter("lake-hover", onlyId(null));
      hovered = "";
    };

    map.on("mousemove", (event) => {
      const feature = hit(event.point, 0);
      const id = feature?.properties?.id;
      const name = feature?.properties?.name;
      if (typeof id !== "string" || typeof name !== "string") return hideTag();

      map.getCanvas().style.cursor = "pointer";
      if (id !== hovered) {
        hovered = id;
        map.setFilter("lake-hover", onlyId(feature?.source === "lakes" ? id : null));
      }
      const el = tag.current;
      if (!el) return;
      el.textContent = name;
      el.hidden = false;
      const flip = event.point.x > map.getContainer().clientWidth - 240;
      el.style.transform = `translate(${event.point.x + (flip ? -12 : 12)}px, ${event.point.y + 12}px)${flip ? " translateX(-100%)" : ""}`;
    });
    map.on("mouseout", hideTag);
    map.on("movestart", hideTag);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map || !lakes) return;
    source(map, "spots")?.setData(pointsOf(lakes, (lake) => lake.status === "exists" && !lake.hasOutline));
    source(map, "rings")?.setData(pointsOf(lakes, (lake) => lake.status !== "exists"));
  }, [loaded, lakes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    const filters = collectionFilters(members);
    for (const layer of ["lake-shadow", "lake-fill", "lake-edge"]) map.setFilter(layer, filters.lakeLive);
    map.setFilter("lake-rest", filters.lakeRest);
    for (const layer of ["spot", "ring"]) map.setFilter(layer, filters.pointLive);
    for (const layer of ["spot-rest", "ring-rest"]) map.setFilter(layer, filters.pointRest);
  }, [loaded, members]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    for (const layer of ["lake-selected", "spots-selected", "rings-selected"]) map.setFilter(layer, onlyId(selectedId));
  }, [loaded, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    source(map, "me")?.setData(pointsOf(here ? [{ id: "me", name: "You are here", status: "exists", hasOutline: false, point: here }] : [], () => true));
  }, [loaded, here]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map || !lakes || didInitial.current) return;
    didInitial.current = true;
    if (initialFlight) flyTo(map, initialFlight, padRight, false);
  }, [loaded, lakes, initialFlight, padRight]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map || !flight || flight.key === lastFlight.current) return;
    lastFlight.current = flight.key;
    flyTo(map, flight, padRight, true);
  }, [loaded, flight, padRight]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map || reloadKey === 0) return;
    source(map, "lakes")?.setData("/data/lakes.geojson");
  }, [loaded, reloadKey]);

  return (
    <div className="absolute inset-0 max-lg:[&_.maplibregl-ctrl-group]:hidden">
      <div ref={container} className="absolute inset-0" role="region" aria-label="Map of the lakes" />
      <div
        ref={tag}
        hidden
        aria-hidden
        className="slip label pointer-events-none absolute top-0 left-0 z-10 px-2 py-1 whitespace-nowrap"
      />
    </div>
  );
}
