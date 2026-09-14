import type { ExpressionSpecification, FilterSpecification, StyleSpecification } from "maplibre-gl";
import { valleyColorExpression } from "@/lib/valleys";

/*
 * The city drawn in its water. Lakes are flat valley paper with a thin ink edge,
 * disappeared lakes are hollow ink rings, and underneath sits a street layer
 * turned grey and faded into the cream table, so "near me" and a forgotten ring
 * still have streets to be read against.
 * Colours are the direction's table, ink and shadow (docs/brand/direction.md).
 */

export const INK = "#1B1A17";
export const CREAM = "#F6EEDB";
const SHADOW = "#5A3B12";

export const CITY: [number, number] = [77.594, 12.972];

/** Layers a tap or hover can land on, top first. */
export const TAP_LAYERS = ["ring", "spot", "lake-fill", "ring-rest", "spot-rest", "lake-rest"];

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
      streets: {
        type: "raster",
        tiles: ["a", "b", "c", "d"].map((s) => `https://${s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}@2x.png`),
        tileSize: 256,
        maxzoom: 20,
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, © <a href="https://carto.com/attributions">CARTO</a>',
      },
      lakes: {
        type: "geojson",
        data: "/data/lakes.geojson",
        attribution: '<a href="/sources">Lake outlines ATREE-CSEI, CC BY</a>',
      },
      spots: { type: "geojson", data: EMPTY },
      rings: { type: "geojson", data: EMPTY },
      me: { type: "geojson", data: EMPTY },
    },
    layers: [
      { id: "table", type: "background", paint: { "background-color": CREAM } },
      {
        id: "streets",
        type: "raster",
        source: "streets",
        paint: { "raster-saturation": -1, "raster-contrast": -0.1, "raster-opacity": 0.42, "raster-fade-duration": 0 },
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
      {
        id: "ring-rest",
        type: "circle",
        source: "rings",
        filter: nothing,
        paint: {
          "circle-opacity": 0,
          "circle-radius": byZoom(9, 2.5, 12, 4, 15, 7),
          "circle-stroke-color": INK,
          "circle-stroke-width": 1,
          "circle-stroke-opacity": 0.2,
        },
      },
      {
        id: "ring",
        type: "circle",
        source: "rings",
        paint: {
          "circle-opacity": 0,
          "circle-radius": byZoom(9, 2.5, 12, 4, 15, 7),
          "circle-stroke-color": INK,
          "circle-stroke-width": byZoom(9, 1, 14, 1.5),
          "circle-stroke-opacity": byZoom(9, 0.55, 13, 0.9),
        },
      },

      { id: "lake-hover", type: "line", source: "lakes", filter: nothing, paint: { "line-color": INK, "line-width": 2 } },
      { id: "lake-selected", type: "line", source: "lakes", filter: nothing, paint: { "line-color": INK, "line-width": 3 } },
      ...(["spots", "rings"] as const).map((source) => ({
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
