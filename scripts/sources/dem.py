#!/usr/bin/env python3
"""
Copernicus DEM GLO-30: ground height of each lake, from the 30 m global elevation model.

The model is a surface model: it measures the top of whatever is there, so trees and buildings
beside a lake raise the shore values. Water surfaces are flattened in the model.

elevationMinM / elevationMedianM: over pixels whose centre is inside the outline.
shoreElevationM: median of the model sampled every 15 m along the outline.

Usage: .venv/bin/python scripts/sources/dem.py [--input lakes.geojson --key atreeFid]
Output: data/sources/dem.csv
"""

import math
import sys
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.merge import merge
from shapely.geometry import MultiPoint
from shapely.ops import transform

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, SOURCES, write_csv, write_sources  # noqa: E402

from _lake_input import TO_UTM, TO_WGS, Grid, lakes_bounds, load_lakes, parse_args  # noqa: E402

NAME = "dem"
SOURCE_KEY = "copernicus-dem-glo30"
TILE_URL = "https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
SHORE_STEP_M = 15
CREDIT = (
    "Copernicus DEM (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 "
    "provided under COPERNICUS by the European Union and ESA"
)
COLUMNS = ["key", "pixelCount", "elevationMinM", "elevationMedianM", "shoreElevationM", "source"]


def tile_names(bounds):
    """One-degree tiles covering bounds, e.g. Copernicus_DSM_COG_10_N12_00_E077_00_DEM."""
    names = []
    for lat in range(math.floor(bounds[1]), math.floor(bounds[3]) + 1):
        for lon in range(math.floor(bounds[0]), math.floor(bounds[2]) + 1):
            ns, ew = ("N" if lat >= 0 else "S"), ("E" if lon >= 0 else "W")
            names.append(f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM")
    return names


def fetch_tiles(bounds):
    """Download the whole tiles once into data/cache/dem/. Tiles over open sea do not exist and are skipped."""
    paths = []
    for name in tile_names(bounds):
        path = CACHE / NAME / f"{name}.tif"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            response = requests.get(TILE_URL.format(name=name), timeout=300)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            path.with_suffix(".part").write_bytes(response.content)
            path.with_suffix(".part").replace(path)
        paths.append(path)
    return paths


def mosaic(bounds):
    """The DEM for bounds as (float32 array, transform, resolution). Used by cascade.py too."""
    paths = fetch_tiles(bounds)
    sources = [rasterio.open(p) for p in paths]
    try:
        # Snap the bounds outward to the tiles' own pixel grid, so merge copies pixels without resampling.
        res = sources[0].res
        x0, y1 = sources[0].bounds.left, sources[0].bounds.top
        bounds = (
            x0 + math.floor((bounds[0] - x0) / res[0]) * res[0],
            y1 - math.ceil((y1 - bounds[1]) / res[1]) * res[1],
            x0 + math.ceil((bounds[2] - x0) / res[0]) * res[0],
            y1 - math.floor((y1 - bounds[3]) / res[1]) * res[1],
        )
        data, affine = merge(sources, bounds=bounds, nodata=-32767)
    finally:
        for s in sources:
            s.close()
    return data[0].astype(np.float32), affine, res


def shore_points(geom):
    """Points every SHORE_STEP_M metres along a polygon's outline (all rings)."""
    boundary = transform(TO_UTM, geom).boundary
    lines = getattr(boundary, "geoms", [boundary])
    points = []
    for line in lines:
        n = max(int(line.length // SHORE_STEP_M), 4)
        points += [line.interpolate(i / n, normalized=True) for i in range(n)]
    return list(transform(TO_WGS, MultiPoint(points)).geoms)


def build():
    args = parse_args(__doc__.split("\n")[1])
    lakes = load_lakes(args)
    bounds = lakes_bounds(lakes, margin_deg=0.01)
    grid = Grid(*mosaic(bounds))
    inv = ~grid.transform

    rows = []
    for lake in lakes:
        values, _ = grid.values(lake["geom"])
        values = values[values > -1000]
        shore = []
        for p in shore_points(lake["geom"]):
            col, row = inv * (p.x, p.y)
            shore.append(grid.data[int(row), int(col)])
        shore = np.array(shore)
        shore = shore[shore > -1000]
        rows.append(
            {
                "key": lake["key"],
                "pixelCount": int(values.size),
                "elevationMinM": round(float(values.min()), 1) if values.size else None,
                "elevationMedianM": round(float(np.median(values)), 1) if values.size else None,
                "shoreElevationM": round(float(np.median(shore)), 1) if shore.size else None,
                "source": SOURCE_KEY,
            }
        )

    write_csv(SOURCES / f"{NAME}.csv", rows, COLUMNS)
    write_sources(
        NAME,
        [
            {
                "key": SOURCE_KEY,
                "title": "Copernicus DEM GLO-30 (30 m digital surface model)",
                "publisher": "European Space Agency, Copernicus programme",
                "url": "https://registry.opendata.aws/copernicus-dem/",
                "license": "Copernicus DEM licence (free use with attribution)",
                "credit": CREDIT,
                "asOf": "2011-2015",
                "retrieved": "2026-09-11",
            }
        ],
    )
    print(f"{NAME}: {len(rows)} lakes -> data/sources/{NAME}.csv")


if __name__ == "__main__":
    build()
