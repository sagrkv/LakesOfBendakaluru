import type { ExpressionSpecification, FilterSpecification, StyleSpecification } from "maplibre-gl";
import { valleyColorExpression } from "@/lib/valleys";

/*
 * Lakes are flat valley paper with a thin ink edge, laid on the same satellite view as the
 * lake pages: turned grey and pushed toward the cream table. The Greater Bengaluru limit is
 * a dashed ink line. Disappeared lakes are not drawn; they have their own page.
 * Colours are the direction's table, ink and shadow (docs/brand/direction.md).
 */

export const INK = "#1B1A17";
export const CREAM = "#F6EEDB";
const SHADOW = "#5A3B12";

export const CITY: [number, number] = [77.594, 12.972];

/** Layers a tap or hover can land on, top first. */
export const TAP_LAYERS = ["spot", "lake-fill", "spot-rest", "lake-rest"];

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

const id: ExpressionSpecification = ["get", "id"];
const nothing: FilterSpecification = ["==", id, ""];
const standing: ExpressionSpecification = ["==", ["get", "status"], "exists"];

/** Members of the open collection at full strength, everything else faded; no collection shows all. */
export function collectionFilters(members: string[] | null) {
  const isMember: ExpressionSpecification = ["in", id, ["literal", members ?? []]];
  return {
    lakeLive: (members ? ["all", standing, isMember] : standing) as FilterSpecification,
    lakeRest: (members ? ["all", standing, ["!", isMember]] : nothing) as FilterSpecification,
    pointLive: (members ? isMember : ["!=", id, ""]) as FilterSpecification,
    pointRest: (members ? ["!", isMember] : nothing) as FilterSpecification,
  };
}

export function onlyId(value: string | null): FilterSpecification {
  return ["==", id, value ?? ""];
}

const byZoom = (...stops: number[]): ExpressionSpecification =>
  ["interpolate", ["linear"], ["zoom"], ...stops] as ExpressionSpecification;

export function mapStyle(): StyleSpecification {
  const paper = valleyColorExpression() as ExpressionSpecification;

  return {
    version: 8,
    sources: {
      satellite: {
        type: "raster",
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
        tileSize: 256,
        maxzoom: 19,
        attribution: "Satellite view: Esri, Maxar, Earthstar Geographics",
      },
      city: {
        type: "geojson",
        data: "/data/city.geojson",
        attribution: '<a href="/sources">City limit: 2025 Greater Bengaluru ward map</a>',
      },
      lakes: {
        type: "geojson",
        data: "/data/lakes.geojson",
        attribution: '<a href="/sources">Lake outlines ATREE-CSEI, CC BY</a>',
      },
      spots: { type: "geojson", data: EMPTY },
      me: { type: "geojson", data: EMPTY },
    },
    layers: [
      { id: "table", type: "background", paint: { "background-color": CREAM } },
      // Grey, and 35% of the cream table showing through, as on the lake pages.
      {
        id: "satellite",
        type: "raster",
        source: "satellite",
        paint: { "raster-saturation": -1, "raster-opacity": 0.65, "raster-fade-duration": 0 },
      },
      {
        id: "city-limit",
        type: "line",
        source: "city",
        paint: { "line-color": INK, "line-opacity": 0.8, "line-width": byZoom(9, 1.25, 14, 2.5), "line-dasharray": [4, 2] },
      },

      { id: "lake-rest", type: "fill", source: "lakes", filter: nothing, paint: { "fill-color": paper, "fill-opacity": 0.22 } },
      {
        id: "lake-shadow",
        type: "fill",
        source: "lakes",
        filter: standing,
        paint: {
          "fill-color": SHADOW,
          "fill-opacity": 0.3,
          "fill-translate": ["interpolate", ["linear"], ["zoom"], 10, ["literal", [0.5, 1]], 15, ["literal", [3, 5]]],
        },
      },
      { id: "lake-fill", type: "fill", source: "lakes", filter: standing, paint: { "fill-color": paper } },
      {
        id: "lake-edge",
        type: "line",
        source: "lakes",
        filter: standing,
        paint: { "line-color": INK, "line-opacity": 0.75, "line-width": byZoom(9, 0.3, 14, 1) },
      },

      {
        id: "spot-rest",
        type: "circle",
        source: "spots",
        filter: nothing,
        paint: { "circle-color": paper, "circle-opacity": 0.22, "circle-radius": byZoom(9, 2, 15, 5) },
      },
      {
        id: "spot",
        type: "circle",
        source: "spots",
        paint: {
          "circle-color": paper,
          "circle-radius": byZoom(9, 2, 15, 5),
          "circle-stroke-color": INK,
          "circle-stroke-width": 0.75,
        },
      },

      { id: "lake-hover", type: "line", source: "lakes", filter: nothing, paint: { "line-color": INK, "line-width": 2 } },
      { id: "lake-selected", type: "line", source: "lakes", filter: nothing, paint: { "line-color": INK, "line-width": 3 } },
      ...(["spots"] as const).map((source) => ({
        id: `${source}-selected`,
        type: "circle" as const,
        source,
        filter: nothing,
        paint: {
          "circle-opacity": 0,
          "circle-radius": byZoom(9, 6, 15, 11),
          "circle-stroke-color": INK,
          "circle-stroke-width": 3,
        },
      })),

      {
        id: "me",
        type: "circle",
        source: "me",
        paint: { "circle-color": INK, "circle-radius": 6, "circle-stroke-color": CREAM, "circle-stroke-width": 3 },
      },
    ],
  };
}
