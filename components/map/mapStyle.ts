import type { ExpressionSpecification, FilterSpecification, LngLatBoundsLike, StyleSpecification } from "maplibre-gl";
import { valleyColorExpression } from "@/lib/valleys";

/*
 * Lakes are flat valley paper with an ink edge, laid on the same satellite view as the lake pages:
 * turned grey and pushed well toward the cream table, so the paper is the only strong colour.
 * Everything outside Bengaluru Urban and Bengaluru North districts is covered in night blue,
 * and their edge is a strip of sun-yellow tape on ink. The Greater Bengaluru city limit is a dashed ink line.
 * Only lakes that exist and have a shape are drawn: disappeared lakes, and lakes no map draws, have their own pages.
 * Colours are the direction's table, ink and shadow (docs/brand/direction.md), plus sun and night from globals.css.
 */

export const INK = "#1B1A17";
export const CREAM = "#F6EEDB";
const SHADOW = "#5A3B12";
const SUN = "#FFC933";
const NIGHT = "#26315F";

/** The two districts, west-south to east-north: what the map opens on. */
export const BENGALURU: LngLatBoundsLike = [
  [77.18, 12.66],
  [77.97, 13.5],
];

/** How far the map may be dragged away from the districts. */
export const AROUND_BENGALURU: LngLatBoundsLike = [
  [76.4, 12.0],
  [78.75, 14.15],
];

/** Layers a tap or hover can land on, top first. */
export const TAP_LAYERS = ["lake-fill", "lake-rest"];

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
      outside: { type: "geojson", data: "/data/outside.geojson" },
      districts: {
        type: "geojson",
        data: "/data/districts.geojson",
        attribution: '<a href="/sources">District boundary © OpenStreetMap contributors</a>',
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
      me: { type: "geojson", data: EMPTY },
    },
    layers: [
      { id: "table", type: "background", paint: { "background-color": CREAM } },
      // Grey, with 60% of the cream table showing through: roads and fields read, lakes stay the brightest thing.
      {
        id: "satellite",
        type: "raster",
        source: "satellite",
        paint: { "raster-saturation": -1, "raster-opacity": 0.4, "raster-fade-duration": 0 },
      },
      // Night over everything that is not Bengaluru, with a little satellite still showing through.
      { id: "outside", type: "fill", source: "outside", paint: { "fill-color": NIGHT, "fill-opacity": 0.88 } },
      // Bengaluru Urban and Bengaluru North together: the edge of every lake on the list, as yellow tape on ink.
      {
        id: "district-casing",
        type: "line",
        source: "districts",
        paint: { "line-color": INK, "line-width": byZoom(8, 4, 14, 8) },
      },
      {
        id: "district-limit",
        type: "line",
        source: "districts",
        paint: { "line-color": SUN, "line-width": byZoom(8, 2, 14, 4) },
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
          "fill-opacity": 0.35,
          "fill-translate": ["interpolate", ["linear"], ["zoom"], 10, ["literal", [0.5, 1]], 15, ["literal", [3, 5]]],
        },
      },
      { id: "lake-fill", type: "fill", source: "lakes", filter: standing, paint: { "fill-color": paper } },
      {
        id: "lake-edge",
        type: "line",
        source: "lakes",
        filter: standing,
        paint: { "line-color": INK, "line-width": byZoom(9, 0.4, 14, 1.5) },
      },

      { id: "lake-hover", type: "line", source: "lakes", filter: nothing, paint: { "line-color": INK, "line-width": 2.5 } },
      { id: "lake-selected", type: "line", source: "lakes", filter: nothing, paint: { "line-color": INK, "line-width": 3.5 } },

      {
        id: "me",
        type: "circle",
        source: "me",
        paint: { "circle-color": INK, "circle-radius": 6, "circle-stroke-color": CREAM, "circle-stroke-width": 3 },
      },
    ],
  };
}
