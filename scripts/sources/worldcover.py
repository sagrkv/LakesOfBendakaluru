#!/usr/bin/env python3
"""
ESA WorldCover 2021: land cover around and inside each lake, from 10 m satellite classification.

Ring: the band 0-500 m outside the lake outline. Its water share includes neighbouring lakes.
Inside: the lake outline itself. Built-up land inside an outline is a sign of encroachment or loss.
A pixel counts when its centre is inside the ring or outline.

Usage: .venv/bin/python scripts/sources/worldcover.py [--input lakes.geojson --key atreeFid]
Output: data/sources/worldcover.csv
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, SOURCES, write_csv, write_sources  # noqa: E402

from _lake_input import Grid, buffer_m, cache_window, lakes_bounds, load_lakes, parse_args  # noqa: E402

NAME = "worldcover"
SOURCE_KEY = "esa-worldcover-2021"
URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
RING_M = 500

CLASSES = {10: "Tree", 20: "Shrub", 30: "Grass", 40: "Crop", 50: "Built", 60: "Bare", 80: "Water", 90: "Wetland"}
INSIDE = {80: "Water", 90: "Wetland", 50: "Built"}

COLUMNS = (
    ["key", "ringPixelCount"]
    + [f"ring{name}Pct" for name in CLASSES.values()]
    + ["insidePixelCount"]
    + [f"inside{name}Pct" for name in INSIDE.values()]
    + ["source"]
)


def tile_name(bounds):
    """WorldCover tiles are 3 x 3 degrees, named by their south-west corner."""
    lat = int(math.floor(bounds[1] / 3) * 3)
    lon = int(math.floor(bounds[0] / 3) * 3)
    if math.floor(bounds[3] / 3) * 3 != lat or math.floor(bounds[2] / 3) * 3 != lon:
        raise SystemExit(f"{NAME}: lakes span more than one WorldCover tile {bounds}; add a mosaic step")
    return f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}{'E' if lon >= 0 else 'W'}{abs(lon):03d}"


def shares(values, classes):
    valid = values[values > 0]
    if not valid.size:
        return {name: None for name in classes.values()}
    return {name: round(100 * float((valid == code).mean()), 1) for code, name in classes.items()}


def build():
    args = parse_args(__doc__.split("\n")[1])
    lakes = load_lakes(args)
    bounds = lakes_bounds(lakes, margin_deg=0.01)  # about 1.1 km, more than the ring
    tile = tile_name(bounds)
    grid = Grid.open(cache_window(URL.format(tile=tile), CACHE / NAME / f"{tile}.tif", bounds))

    rows = []
    for lake in lakes:
        ring = buffer_m(lake["geom"], RING_M).difference(lake["geom"])
        ring_values, _ = grid.values(ring, fallback_touched=False)
        inside_values, _ = grid.values(lake["geom"])
        row = {"key": lake["key"], "source": SOURCE_KEY}
        row["ringPixelCount"] = int((ring_values > 0).sum())
        row |= {f"ring{k}Pct": v for k, v in shares(ring_values, CLASSES).items()}
        row["insidePixelCount"] = int((inside_values > 0).sum())
        row |= {f"inside{k}Pct": v for k, v in shares(inside_values, INSIDE).items()}
        rows.append(row)

    write_csv(SOURCES / f"{NAME}.csv", rows, COLUMNS)
    write_sources(
        NAME,
        [
            {
                "key": SOURCE_KEY,
                "title": f"ESA WorldCover 10 m 2021 v200, tile {tile}",
                "publisher": "European Space Agency",
                "url": "https://esa-worldcover.org/en",
                "license": "CC BY 4.0",
                "credit": "(c) ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium",
                "asOf": "2021",
                "retrieved": "2026-09-11",
            }
        ],
    )
    print(f"{NAME}: {len(rows)} lakes -> data/sources/{NAME}.csv")


if __name__ == "__main__":
    build()
