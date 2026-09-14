#!/usr/bin/env python3
"""
Impact Observatory yearly land cover: what each lake's area was classed as, every year from 2017.

Impact Observatory, Microsoft and Esri classify every 10 m Sentinel-2 pixel once a year into
water, trees, flooded vegetation, crops, built area, bare ground, snow, clouds or rangeland.
The stated accuracy is about 75%, so a single year can flip; read the series as a trend.

Access: Esri's Living Atlas image service, no key. One raster per year; the script asks the
service which years exist, so a new year is picked up on the next run. Rasters are exported
in UTM 43N on the product's own 10 m grid, 4000 x 4000 pixels at a time, for 12.65-13.48 N,
77.18-77.96 E. (Microsoft Planetary Computer carries the same product but stops at 2023.)

Lake area: the outline where there is one. A lake known only as a point is a circle of its
recorded extent (0.5 acre when none, at least 15 m radius), as in joins.lake_index().
A pixel counts when its centre is inside the area; a lake too small to hold a centre uses
every pixel it touches. Clouds and no-data are left out of the shares.

Columns:
  pixels                 clear pixels counted
  waterPct ... rangelandPct   share of those pixels in each class
  lowConfidence          no outline (a circle), under a quarter acre, or no pixel centre inside

Usage: .venv/bin/python scripts/sources/io_lulc.py [--input data/lakes.geojson --key id]
Output: data/sources/io_lulc.csv (one row per lake and year), data/sources/io_lulc.sources.json
Cache: data/cache/io_lulc/<year>/<x>_<y>.tif
"""

import argparse
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
import requests
from affine import Affine
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, ROOT, SOURCES, write_csv, write_sources  # noqa: E402

from _lake_input import Grid  # noqa: E402

NAME = "io_lulc"
SERVICE = "https://ic.imagery1.arcgis.com/arcgis/rest/services/Sentinel2_10m_LandCover/ImageServer"
ITEM_URL = "https://www.arcgis.com/home/item.html?id=cfcb7609de5f478eb7666240902d4d3d"
CACHE_DIR = CACHE / NAME

AREA = (77.18, 12.65, 77.96, 13.48)  # west, south, east, north
EPSG = 32643  # UTM 43N, the product's own grid over Bengaluru
PIXEL = 10
TILE_PX = 4000  # the service's largest export
WORKERS = 6

POINT_ACRES = 0.5
POINT_MIN_RADIUS_M = 15.0
ACRE_M2 = 4046.86
SMALL_M2 = ACRE_M2 / 4

CLASSES = {1: "water", 2: "trees", 4: "floodedVegetation", 5: "crops", 7: "built", 8: "bareGround", 11: "rangeland"}
NOT_CLEAR = {0, 10}  # no data, clouds
COLUMNS = ["key", "year", "pixels"] + [f"{name}Pct" for name in CLASSES.values()] + ["lowConfidence", "source"]

TO_UTM = Transformer.from_crs(4326, EPSG, always_xy=True).transform


def source_key(year):
    return f"io-lulc-{year}"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--input", default=str(ROOT / "data" / "lakes.geojson"), help="lake GeoJSON with hasOutline")
    parser.add_argument("--key", default="id", help="property that identifies a lake")
    return parser.parse_args()


def get(url, params, attempts=5):
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, timeout=180)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            if attempt == attempts - 1:
                raise
            print(f"{NAME}: retrying after {error}", flush=True)
            time.sleep(5 * (attempt + 1))


def years_available():
    """Year -> raster id, as the service lists them."""
    params = {"where": "1=1", "outFields": "OBJECTID,Year", "returnGeometry": "false", "f": "json"}
    features = get(f"{SERVICE}/query", params).json()["features"]
    return {int(f["attributes"]["Year"]): int(f["attributes"]["OBJECTID"]) for f in features}


def grid_extent():
    """The area in UTM metres, snapped out to the 10 m grid and to whole export tiles."""
    xs, ys = zip(*(TO_UTM(x, y) for x in AREA[::2] for y in AREA[1::2]))
    step = PIXEL * TILE_PX
    x0 = math.floor(min(xs) / PIXEL) * PIXEL
    y1 = math.ceil(max(ys) / PIXEL) * PIXEL
    cols = math.ceil((max(xs) - x0) / step)
    rows = math.ceil((y1 - min(ys)) / step)
    return x0, y1, cols, rows


def fetch_tile(year, raster_id, x, y):
    """One 4000 x 4000 pixel export whose top-left corner is (x, y), cached as a GeoTIFF."""
    dest = CACHE_DIR / str(year) / f"{x}_{y}.tif"
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    span = PIXEL * TILE_PX
    params = {
        "bbox": f"{x},{y - span},{x + span},{y}",
        "bboxSR": EPSG,
        "imageSR": EPSG,
        "size": f"{TILE_PX},{TILE_PX}",
        "format": "tiff",
        "pixelType": "U8",
        "interpolation": "RSP_NearestNeighbor",
        "mosaicRule": json.dumps({"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [raster_id]}),
        "f": "image",
    }
    response = get(f"{SERVICE}/exportImage", params)
    if "tiff" not in response.headers.get("content-type", ""):
        raise SystemExit(f"{NAME}: {year} tile {x},{y} came back as {response.headers.get('content-type')}: {response.text[:200]}")
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(response.content)
    with rasterio.open(tmp) as ds:
        expected = (float(x), float(y), float(PIXEL))
        if (ds.transform.c, ds.transform.f, ds.transform.a) != expected or ds.shape != (TILE_PX, TILE_PX):
            raise SystemExit(f"{NAME}: {year} tile {x},{y} is off the 10 m grid: {ds.transform} {ds.shape}")
    tmp.replace(dest)
    return dest


def year_grid(year, raster_id, extent):
    """The whole area for one year as a Grid in UTM 43N."""
    x0, y1, cols, rows = extent
    span = PIXEL * TILE_PX
    corners = [(x0 + c * span, y1 - r * span, r, c) for r in range(rows) for c in range(cols)]
    with ThreadPoolExecutor(WORKERS) as pool:
        paths = list(pool.map(lambda t: fetch_tile(year, raster_id, t[0], t[1]), corners))
    data = np.zeros((rows * TILE_PX, cols * TILE_PX), dtype=np.uint8)
    for (_, _, r, c), path in zip(corners, paths):
        with rasterio.open(path) as ds:
            data[r * TILE_PX : (r + 1) * TILE_PX, c * TILE_PX : (c + 1) * TILE_PX] = ds.read(1)
    return Grid(data, Affine(PIXEL, 0, x0, 0, -PIXEL, y1), (PIXEL, PIXEL))


def load_lakes(args):
    """Each lake's area in UTM: its outline, or a circle of its recorded extent."""
    lakes = []
    for feature in json.loads(Path(args.input).read_text(encoding="utf-8"))["features"]:
        props = feature["properties"]
        if not feature.get("geometry"):
            continue
        geom = transform(TO_UTM, shape(feature["geometry"]))
        outlined = bool(props.get("hasOutline")) and geom.geom_type in ("Polygon", "MultiPolygon")
        if not outlined:
            acres = props.get("recordedAcres") or POINT_ACRES
            geom = geom.centroid.buffer(max(POINT_MIN_RADIUS_M, math.sqrt(acres * ACRE_M2 / math.pi)))
        if geom.is_empty:
            continue
        lakes.append({"key": props[args.key], "geom": geom, "outlined": outlined})
    return lakes


def row_for(lake, values, centre_based, year):
    clear = values[~np.isin(values, list(NOT_CLEAR))]
    row = {"key": lake["key"], "year": year, "pixels": int(clear.size), "source": source_key(year)}
    for code, name in CLASSES.items():
        row[f"{name}Pct"] = round(100 * float((clear == code).mean()), 1) if clear.size else None
    low = not lake["outlined"] or lake["geom"].area < SMALL_M2 or not centre_based or not clear.size
    row["lowConfidence"] = "true" if low else "false"
    return row


def build():
    args = parse_args()
    lakes = load_lakes(args)
    years = years_available()
    extent = grid_extent()
    started = time.time()

    rows, masks = [], None
    for year, raster_id in sorted(years.items()):
        grid = year_grid(year, raster_id, extent)
        if masks is None:  # the grid is the same every year, so each lake's pixels are found once
            masks = [grid.mask(lake["geom"]) for lake in lakes]
        for lake, (r, c, inside, centre_based) in zip(lakes, masks):
            rows.append(row_for(lake, grid.data[r, c][inside], centre_based, year))
        print(f"{NAME}: {year} done after {time.time() - started:.0f} s", flush=True)

    write_csv(SOURCES / f"{NAME}.csv", rows, COLUMNS)
    retrieved = date.today().isoformat()
    write_sources(
        NAME,
        [
            {
                "key": source_key(year),
                "title": f"Sentinel-2 10m Land Use/Land Cover {year} (Impact Observatory annual land cover v2)",
                "publisher": "Impact Observatory, Microsoft and Esri",
                "url": ITEM_URL,
                "license": "CC BY 4.0",
                "credit": f"Esri Land Cover {year}, produced by Impact Observatory, Microsoft and Esri, CC BY 4.0",
                "asOf": str(year),
                "retrieved": retrieved,
            }
            for year in sorted(years)
        ],
    )
    print(f"{NAME}: {len(lakes)} lakes x {len(years)} years ({min(years)}-{max(years)}) -> data/sources/{NAME}.csv")


if __name__ == "__main__":
    build()
