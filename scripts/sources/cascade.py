#!/usr/bin/env python3
"""
Lake cascade: which lake each lake drains into, worked out two ways.

streams: along the ATREE-CSEI stream network (inside BBMP only). Each segment is oriented by the
DEM, because the digitised direction is random. From the edge where the stream leaves the lake,
the flow is followed to the first other lake it touches.

dem: flow routing on the Copernicus 30 m DEM with the ATREE streams burned in. Depressions are
filled; each lake is one flat sink that overflows at the lowest point of its rim. From that outlet
the flow is followed to the first other lake. The same routing gives the upstream area (catchmentKm2)
and the valley basin: the first named river the flow reaches (rivers from OpenStreetMap). The two
city valleys are not named rivers, so each is the drain out of its main lake down to the first
named river (Koramangala-Challaghatta from Bellandur, Hebbal from Hebbal lake).

downstreamKey prefers streams where the stream trace reaches a lake, else dem.

Usage: .venv/bin/python scripts/sources/cascade.py [--input lakes.geojson --key atreeFid]
Output: data/sources/cascade.csv
"""

import json
import sys
from pathlib import Path

import numpy as np
import requests
from rasterio.features import rasterize
from shapely.geometry import LineString, mapping
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, write_csv, write_sources  # noqa: E402

import _streams  # noqa: E402
from _flow import Routing  # noqa: E402
from _lake_input import buffer_m, lakes_bounds, load_lakes, parse_args, pixel_area_m2  # noqa: E402
from dem import CREDIT as DEM_CREDIT  # noqa: E402
from dem import mosaic  # noqa: E402

NAME = "cascade"
MARGIN_DEG = 0.2  # routing extends ~22 km past the outermost lake so catchments are not cut off
BURN_M = 20  # streams are lowered this much so the routing follows them
LAKE_BUFFER_M = 30  # a stream within one pixel of an outline counts as touching it
RIVER_BUFFER_M = 150  # DEM channel cells this close to a mapped river take its name
RIVER_MIN_KM2 = 10  # ...if they drain at least this much, so side streams are not renamed

OVERPASS = "https://overpass-api.de/api/interpreter"
# Every named river in the extent, plus the major rivers where OpenStreetMap tags them as streams or drains.
MAJOR = "Arkav|Vrisha|Vrusha|Suvarna|Kumud|Pinakini"
# Spellings of one river, first match wins. Ponnaiyar and Then Pennai are the Tamil names of the Dakshina Pinakini.
# Kumadvati (flows north to the Uttara Pinakini) is a different river from Kumudavathi (flows south to the Arkavathi).
SPELLINGS = [
    ("kumadvati", "Kumadvati"),
    ("kumud", "Kumudvathi"),
    ("arkav", "Arkavathi"),
    ("vrisha", "Vrishabhavathi"),
    ("vrusha", "Vrishabhavathi"),
    ("suvarna", "Suvarnamukhi"),
    ("uttara pinakini", "Uttara Pinakini"),
    ("pinakini", "Dakshina Pinakini"),
    ("ponnai", "Dakshina Pinakini"),
    ("pennai", "Dakshina Pinakini"),
]
# The two city valleys that join the Dakshina Pinakini are not named rivers on the map. Each is
# the drain that runs out of its main lake: the lake and its outflow down to the first named river.
# Given as a point inside the lake so the rule works for any lake list.
VALLEY_LAKES = {
    "Koramangala-Challaghatta": (77.6670, 12.9360),  # Bellandur
    "Hebbal": (77.5867, 13.0472),  # Hebbal
}

COLUMNS = [
    "key",
    "downstreamKey",
    "downstreamMethod",
    "downstreamKeyStreams",
    "downstreamKeyDem",
    "agree",
    "upstreamKeys",
    "cascadeDepth",
    "catchmentKm2",
    "valleyBasin",
    "outletLon",
    "outletLat",
    "source",
]


def river_name(name):
    lower = name.lower()
    return next((canonical for key, canonical in SPELLINGS if key in lower), name)


def fetch_rivers(bounds):
    path = RAW / NAME / "osm_rivers.json"
    if not path.exists():
        box = f"({bounds[1]},{bounds[0]},{bounds[3]},{bounds[2]})"
        query = (
            f'[out:json][timeout:180];(way["waterway"="river"]["name"]{box};'
            f'way["waterway"]["name"~"{MAJOR}",i]{box};);out geom;'
        )
        headers = {"User-Agent": "LakesOfBendakaluru data build"}
        response = requests.post(OVERPASS, data={"data": query}, headers=headers, timeout=240)
        response.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(response.text, encoding="utf-8")
    rivers = []
    for way in json.loads(path.read_text(encoding="utf-8"))["elements"]:
        name = way.get("tags", {}).get("name")
        if name and len(way.get("geometry", [])) >= 2:
            rivers.append((river_name(name), LineString([(p["lon"], p["lat"]) for p in way["geometry"]])))
    return rivers


class Raster:
    """The routing grid: DEM, lake ids, stream cells, cell areas."""

    def __init__(self, bounds, lakes, streams):
        self.z, self.transform, res = mosaic(bounds)
        self.shape = self.z.shape
        lat = self.transform.f + self.transform.e * (np.arange(self.shape[0]) + 0.5)
        self.cell_area = np.array([pixel_area_m2(y, *res) for y in lat])
        self.seed = self.z < -1000
        self.seed[0, :] = self.seed[-1, :] = self.seed[:, 0] = self.seed[:, -1] = True

        by_size = sorted(range(len(lakes)), key=lambda i: -lakes[i]["geom"].area)
        self.lake = rasterize(
            [(mapping(lakes[i]["geom"]), i + 1) for i in by_size], self.shape, transform=self.transform, dtype="int32"
        )
        present = np.zeros(len(lakes) + 1, dtype=bool)
        present[np.unique(self.lake)] = True
        for i, lake in enumerate(lakes):  # lakes smaller than a pixel keep the pixel at their centre
            if not present[i + 1]:
                self.lake[self.cell(*lake["geom"].representative_point().coords[0])] = i + 1
        self.streams = rasterize(
            [mapping(LineString(p)) for _, p in streams], self.shape, transform=self.transform, all_touched=True
        ).astype(bool)

    def cell(self, lon, lat):
        col, row = ~self.transform * (lon, lat)
        return int(row), int(col)

    def flat(self, lon, lat):
        r, c = self.cell(lon, lat)
        return r * self.shape[1] + c

    def centre(self, flat_index):
        r, c = divmod(int(flat_index), self.shape[1])
        return self.transform * (c + 0.5, r + 0.5)

    def routings(self):
        burned = np.where(self.streams, self.z - BURN_M, self.z)
        plain = Routing(burned, self.seed, self.cell_area)
        # Each lake becomes flat at its lowest DEM value.
        low = np.full(self.lake.max() + 1, np.inf, dtype=np.float32)
        np.minimum.at(low, self.lake.ravel(), self.z.ravel())
        flooded = np.where(self.lake > 0, low[self.lake], burned).astype(np.float32)
        return plain, Routing(flooded, self.seed, self.cell_area, lake=self.lake)


def valley_labels(grid, routing, rivers):
    """
    Grid of valley codes: named river channels first, then each city valley's lake and the path
    from its outlet down to the first named river.
    """
    names = sorted({n for n, _ in rivers} | set(VALLEY_LAKES))
    code = {n: i + 1 for i, n in enumerate(names)}
    shapes = [(mapping(buffer_m(line, RIVER_BUFFER_M)), code[n]) for n, line in rivers]
    label = np.zeros(grid.shape, dtype=np.int16)
    if shapes:
        label = rasterize(shapes, grid.shape, transform=grid.transform, dtype="int16")
    label[routing.acc.reshape(grid.shape) < RIVER_MIN_KM2 * 1e6] = 0
    label = label.ravel()
    lake_flat = grid.lake.ravel()
    for name, (lon, lat) in VALLEY_LAKES.items():
        lake_id = lake_flat[grid.flat(lon, lat)]
        if not lake_id:
            continue
        label[lake_flat == lake_id] = code[name]
        for c in routing.path(routing.lake_outlet[lake_id]):
            if label[c]:
                break
            label[c] = code[name]
    return label, {v: k for k, v in code.items()}


def exit_side(grid, routing, start):
    """Where the flow leaves the grid, for lakes that meet no named river."""
    r, c = divmod(routing.path(start)[-1], grid.shape[1])
    ns = "N" if r < grid.shape[0] / 3 else "S" if r > 2 * grid.shape[0] / 3 else ""
    ew = "W" if c < grid.shape[1] / 3 else "E" if c > 2 * grid.shape[1] / 3 else ""
    return f"unnamed, leaves to {ns + ew or 'centre'}"


def depth(key, upstream, memo, stack=()):
    """Lakes in the longest chain upstream of key. Cycles are cut where they close."""
    if key in memo:
        return memo[key]
    best = 0
    for up in upstream.get(key, []):
        if up not in stack:
            best = max(best, 1 + depth(up, upstream, memo, stack + (key,)))
    memo[key] = best
    return best


def streams_method(grid, plain, segments, lakes):
    """Downstream lake and outlet point per lake key along the ATREE streams, oriented by the plain routing."""
    keys = [lake["key"] for lake in lakes]
    geoms = [lake["geom"] for lake in lakes]
    acc = plain.acc.reshape(grid.shape)

    def upstream_area(lon, lat):
        # Stream vertices sit on DEM pixel edges, so take the largest value in the 3 x 3 cells around.
        r, c = grid.cell(lon, lat)
        return acc[max(r - 1, 0) : r + 2, max(c - 1, 0) : c + 2].max()

    graph = _streams.StreamGraph(segments, upstream_area)
    edge_list = graph.edges()
    edge_tree = STRtree([LineString([graph.xy[a], graph.xy[b]]) for a, b in edge_list])
    lake_tree = STRtree(geoms)
    down, outlet = {}, {}
    for lake in lakes:
        edge = graph.outlet(buffer_m(lake["geom"], LAKE_BUFFER_M), edge_tree, edge_list)
        if edge:
            outlet[lake["key"]] = graph.xy[edge[1]]
            down[lake["key"]] = graph.trace(edge, lake["key"], lake_tree, keys, geoms)
    return down, outlet, graph


def build():
    args = parse_args(__doc__.split("\n")[1])
    lakes = load_lakes(args)
    keys = [lake["key"] for lake in lakes]
    bounds = lakes_bounds(lakes, MARGIN_DEG)
    segments = _streams.parse(_streams.fetch(RAW / NAME / "streams.kml"))
    rivers = fetch_rivers(bounds)

    grid = Raster(bounds, lakes, segments)
    plain, routing = grid.routings()
    print(f"{NAME}: routed {grid.shape[0]} x {grid.shape[1]} cells")

    streams_down, streams_outlet, graph = streams_method(grid, plain, segments, lakes)
    del plain

    # DEM method.
    lake_flat = grid.lake.ravel()
    down_lake = routing.first_downstream(grid.lake)
    catchment = np.bincount(lake_flat, weights=routing.acc, minlength=len(lakes) + 1)
    label, names = valley_labels(grid, routing, rivers)
    down_label = routing.first_downstream(label.reshape(grid.shape))
    valley_lake_ids = {grid.lake[grid.cell(*p)] for p in VALLEY_LAKES.values()} - {0}

    rows = {}
    for i, lake in enumerate(lakes):
        lake_id, key = i + 1, lake["key"]
        outlet = routing.lake_outlet[lake_id]
        dem_down, valley = None, None
        if outlet >= 0:
            target = lake_flat[outlet] or down_lake[outlet]
            dem_down = keys[target - 1] if target and target != lake_id else None
            code = label[outlet] or down_label[outlet]
            valley = names[code] if code else exit_side(grid, routing, outlet)
        if lake_id in valley_lake_ids:
            valley = names[label[routing.lake_first[lake_id]]]
        s_down = streams_down.get(key)
        use_streams = s_down is not None
        outlet_xy = streams_outlet[key] if use_streams else (grid.centre(outlet) if outlet >= 0 else None)
        rows[key] = {
            "key": key,
            "downstreamKey": s_down if use_streams else dem_down,
            "downstreamMethod": "streams" if use_streams else ("dem" if dem_down is not None else None),
            "downstreamKeyStreams": s_down,
            "downstreamKeyDem": dem_down,
            "agree": (s_down == dem_down) if s_down is not None and dem_down is not None else None,
            "catchmentKm2": round(catchment[lake_id] / 1e6, 2),
            "valleyBasin": valley,
            "outletLon": round(float(outlet_xy[0]), 6) if outlet_xy is not None else None,
            "outletLat": round(float(outlet_xy[1]), 6) if outlet_xy is not None else None,
            "source": "cascade-streams-dem",
        }

    upstream = {}
    for row in rows.values():
        if row["downstreamKey"] is not None:
            upstream.setdefault(row["downstreamKey"], []).append(row["key"])
    memo = {}
    for key, row in rows.items():
        row["upstreamKeys"] = sorted(upstream.get(key, []))
        row["cascadeDepth"] = depth(key, upstream, memo)

    write_csv(SOURCES / f"{NAME}.csv", list(rows.values()), COLUMNS)
    write_sources(
        NAME,
        [
            {
                "key": "cascade-streams-dem",
                "title": "Lake cascade derived from the ATREE-CSEI stream network and Copernicus DEM flow routing",
                "publisher": "Computed for this project from ATREE-CSEI streams, Copernicus DEM and OpenStreetMap rivers",
                "url": "https://data.opencity.in/dataset/map-lakes-streams-bengaluru-urban-within-bbmp-area",
                "license": "CC BY (ATREE-CSEI streams); Copernicus DEM licence; ODbL (OpenStreetMap river names)",
                "credit": f"Streams: ATREE-CSEI. {DEM_CREDIT}. River names (c) OpenStreetMap contributors",
                "asOf": "2026-09",
                "retrieved": "2026-09-11",
            }
        ],
    )
    kml_share = 100 * graph.kml_downhill / graph.segment_count
    print(f"{NAME}: {graph.segment_count} stream segments, {kml_share:.0f}% digitised in the flow direction")
    print(f"{NAME}: {graph.snapped} one-pixel gaps in the stream lines joined")
    print(f"{NAME}: {len(rows)} lakes -> data/sources/{NAME}.csv")


if __name__ == "__main__":
    build()
