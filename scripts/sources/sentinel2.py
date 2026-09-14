#!/usr/bin/env python3
"""
Sentinel-2 water and floating weed cover per lake, from cloud-free median composites.

For each season we take the clearest Sentinel-2 L2A scenes, mask clouds and shadows with the
scene classification band, and build a per-pixel median of green, red, red edge, NIR and SWIR.
Every 10 m pixel whose centre is inside a lake outline (shrunk by one pixel where the lake is big
enough, to keep shore pixels out) is then called open water, floating vegetation, or dry/built.

Columns:
  pixels                 10 m pixels measured; clearObs is the median cloud-free scenes per pixel
  openWaterPct           not vegetated, and MNDWI or NDWI above 0
  floatingVegetationPct  green vegetation that is wet: low SWIR (water under it) or high moisture
                         index. Water hyacinth, but also reeds and marsh; Sentinel-2 cannot tell
                         floating from rooted, and small tree-covered islands count here too
  dryOrBuiltPct          the rest: dry bed, grass, bare soil, paths, buildings
  meanNdvi               mean NDVI over the pixels
  turbidityRel           mean red reflectance over open water. Relative, uncalibrated
  chlorophyllRel         mean NDCI (red edge B05 vs red) over open water. Relative, uncalibrated
  lowConfidence          outline under 1 ha, under 20 pixels, or under 3 clear scenes

Seasons (the latest completed one of each, relative to today), using the 10 most recent scenes
per tile under the season's cloud limit, so the composite dates are in compositeStart/End:
  dry           1 Jan - 31 May, scenes under 20% cloud   the "current" state, lowest water
  postmonsoon   1 Oct - 31 Dec, scenes under 50% cloud   lakes at their fullest

Usage:
  .venv/bin/python scripts/sources/sentinel2.py [lakes.geojson] [keyProperty]

Output:
  data/sources/sentinel2.csv            one row per lake and season
  data/sources/sentinel2.sources.json
Cache: data/cache/sentinel2/<scene>/<band>-<pixelset>.npy holds the raw pixel values of one band
of one scene at the lake pixels, so a re-run with the same outlines downloads nothing.
"""

import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
import requests
from pyproj import Geod, Transformer
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.windows import Window
from shapely.geometry import box, shape
from shapely.ops import transform

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, ROOT, SOURCES, write_csv, write_sources  # noqa: E402

STAC = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
CACHE_DIR = CACHE / "sentinel2"
EPSG = 32643  # UTM 43N, the grid of every Sentinel-2 tile over Bengaluru
PIXEL = 10
MAX_SCENES = 10  # most recent clear scenes per tile per season
BANDS = {"green": "B03", "red": "B04", "rededge1": "B05", "nir": "B08", "swir16": "B11", "scl": "SCL"}
# Scene classification classes kept as clear: dark area, vegetation, bare, water, unclassified.
# Dropped: no data, defective, cloud shadow, cloud medium/high, cirrus, snow.
CLEAR_SCL = [2, 4, 5, 6, 7]

# Thresholds, checked by eye on false-colour composites of Bellandur and Varthur (weed-choked),
# Ulsoor and Sankey (open water) and Hebbal, against tree cover and bare ground just outside them.
VEG_NDVI = 0.3  # (nir - red) / (nir + red) at or above this is vegetation
WATER_MNDWI = 0.0  # below VEG_NDVI, (green - swir) / (green + swir) above this is water ...
WATER_NDWI = 0.0  # ... or (green - nir) / (green + nir) above this
# Vegetation floating on or standing in water is wetter than trees and grass on land:
# its SWIR reflectance is low because water sits under it, or its moisture index is high.
WEED_SWIR = 0.15  # B11 reflectance below this
WEED_NDMI = 0.2  # (nir - swir) / (nir + swir) above this
MIN_AREA_M2 = 10_000
MIN_PIXELS = 20
MIN_CLEAR = 3  # median clear observations per pixel
MIN_WATER_PIXELS = 10  # for the turbidity and chlorophyll indicators

COLUMNS = [
    "season", "compositeStart", "compositeEnd", "scenes", "pixels", "clearObs",
    "openWaterPct", "floatingVegetationPct", "dryOrBuiltPct", "meanNdvi",
    "turbidityRel", "chlorophyllRel", "lowConfidence", "source",
]

GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_MAX_RETRY": "6",
    "GDAL_HTTP_RETRY_DELAY": "2",
    "GDAL_HTTP_MULTIRANGE": "YES",
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "VSI_CACHE": "FALSE",
}


def seasons(today):
    """
    The latest completed dry season and post-monsoon season, with the most scene cloud percent allowed.
    Clouds left in a scene are masked per pixel; post-monsoon skies are rarely clear, so it allows more.
    """
    dry_year = today.year if today >= date(today.year, 6, 1) else today.year - 1
    post_year = today.year - 1
    return [
        ("dry", date(dry_year, 1, 1), date(dry_year, 5, 31), 20),
        ("postmonsoon", date(post_year, 10, 1), date(post_year, 12, 31), 50),
    ]


# ---------- lakes to pixels ----------


def lake_pixels(features, key):
    """Global 10 m pixel indices (column, northing row) inside each outline, eroded one pixel where it can."""
    to_utm = Transformer.from_crs(4326, EPSG, always_xy=True).transform
    geod = Geod(ellps="WGS84")
    lakes = []
    for f in features:
        geom = shape(f["geometry"])
        utm = transform(to_utm, geom)
        minx, miny, maxx, maxy = utm.bounds
        c0, c1 = int(np.floor(minx / PIXEL)), int(np.ceil(maxx / PIXEL))
        k0, k1 = int(np.floor(miny / PIXEL)), int(np.ceil(maxy / PIXEL))
        grid = {"out_shape": (k1 - k0, c1 - c0), "transform": from_origin(c0 * PIXEL, k1 * PIXEL, PIXEL, PIXEL)}
        mask = rasterize([utm], **grid, dtype="uint8").astype(bool)
        inner = erode(mask)
        rows, cols = np.nonzero(inner if inner.sum() >= MIN_PIXELS else mask)
        # Every pixel the outline touches: the set we download, so rule changes need no new download.
        t_rows, t_cols = np.nonzero(rasterize([utm], **grid, dtype="uint8", all_touched=True))
        lakes.append({
            "key": f["properties"][key],
            "name": f["properties"].get("name"),
            "areaM2": abs(geod.geometry_area_perimeter(geom)[0]),
            "utm": utm,
            "cols": (c0 + cols).astype(np.int64),
            "rows": (k1 - 1 - rows).astype(np.int64),  # northing index: pixel spans [row*10, row*10+10)
            "touchedCols": (c0 + t_cols).astype(np.int64),
            "touchedRows": (k1 - 1 - t_rows).astype(np.int64),
        })
    return lakes


ROW_SPAN = 1_000_000


def pixel_id(cols, rows):
    return cols * ROW_SPAN + rows


def erode(mask):
    """Drop every pixel that touches the outside, including diagonally."""
    padded = np.pad(mask, 1)
    out = mask.copy()
    h, w = mask.shape
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            out &= padded[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
    return out


# ---------- scenes ----------


def search(start, end):
    """Every L2A item over the lakes in the window, one per tile and date (latest processing)."""
    body = {
        "collections": [COLLECTION],
        "bbox": [77.18, 12.65, 77.96, 13.48],
        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
        "limit": 200,
    }
    items, url = [], f"{STAC}/search"
    while url:
        response = requests.post(url, json=body, timeout=60)
        response.raise_for_status()
        page = response.json()
        items += page["features"]
        nxt = [link for link in page.get("links", []) if link["rel"] == "next"]
        url, body = (nxt[0]["href"], nxt[0].get("body", body)) if nxt else (None, None)
    latest = {}
    for item in items:
        p = item["properties"]
        slot = (p["grid:code"], p["datetime"][:10])
        if slot not in latest or p.get("s2:sequence", "0") > latest[slot]["properties"].get("s2:sequence", "0"):
            latest[slot] = item
    return list(latest.values())


def tile_box(item):
    t = item["assets"]["red"]["proj:transform"]
    n = item["assets"]["red"]["proj:shape"]
    return box(t[2], t[5] + t[4] * n[0], t[2] + t[0] * n[1], t[5])


def assign_tiles(lakes, items):
    """Each lake is read from one tile: the one whose edge is farthest from the lake."""
    boxes = {}
    for item in items:
        if item["properties"]["proj:epsg"] == EPSG:
            boxes.setdefault(item["properties"]["grid:code"], tile_box(item))
    for lake in lakes:
        margins = {code: b.exterior.distance(lake["utm"]) for code, b in boxes.items() if b.contains(lake["utm"])}
        lake["tile"] = max(margins, key=margins.get) if margins else None
    return boxes


def pick_scenes(items, tile, max_cloud):
    clear = [
        i for i in items
        if i["properties"]["grid:code"] == tile and i["properties"]["eo:cloud_cover"] <= max_cloud
    ]
    clear.sort(key=lambda i: i["properties"]["datetime"], reverse=True)
    return sorted(clear[:MAX_SCENES], key=lambda i: i["properties"]["datetime"])


# ---------- pixel reads ----------


def band_pixels(item, band, cols, rows):
    """Raw values of one band at the given global pixels, read block by block and cached."""
    asset = item["assets"][band]
    t = asset["proj:transform"]
    res = t[0]
    # Pixel centres in tile coordinates at this band's resolution.
    tc = ((cols * PIXEL + PIXEL / 2 - t[2]) // res).astype(np.int64)
    tr = ((t[5] - rows * PIXEL - PIXEL / 2) // res).astype(np.int64)
    digest = hashlib.sha1(tc.tobytes() + tr.tobytes()).hexdigest()[:12]
    path = CACHE_DIR / item["id"] / f"{BANDS[band]}-{digest}.npy"
    if path.exists():
        return np.load(path)
    out = np.zeros(len(tc), dtype=np.uint16)
    blocks = (tr // 1024) * 10_000 + tc // 1024
    with rasterio.Env(**GDAL_ENV), rasterio.open(asset["href"]) as src:
        for b in np.unique(blocks):
            sel = blocks == b
            r0, r1 = tr[sel].min(), tr[sel].max() + 1
            c0, c1 = tc[sel].min(), tc[sel].max() + 1
            data = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0))
            out[sel] = data[tr[sel] - r0, tc[sel] - c0]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.npy")
    np.save(tmp, out)
    os.replace(tmp, path)
    return out


def reflectance(item, band, raw):
    rb = item["assets"][band]["raster:bands"][0]
    # Earth Search has already removed the -0.1 offset from the pixels when this flag is set.
    offset = 0 if item["properties"].get("earthsearch:boa_offset_applied") else rb.get("offset", 0)
    value = raw.astype(np.float32) * rb.get("scale", 1) + offset
    return np.where(raw == 0, np.nan, value)


def composite(items, cols, rows):
    """Median reflectance per band over the clear observations, and the clear count per pixel."""
    tasks = [(item, band) for item in items for band in BANDS]
    with ThreadPoolExecutor(max_workers=12) as pool:
        raws = list(pool.map(lambda t: band_pixels(t[0], t[1], cols, rows), tasks))
    raw = {(item["id"], band): r for (item, band), r in zip(tasks, raws)}
    clear = np.stack([np.isin(raw[(i["id"], "scl")], CLEAR_SCL) for i in items])
    bands = {}
    for band in BANDS:
        if band == "scl":
            continue
        stack = np.stack([reflectance(i, band, raw[(i["id"], band)]) for i in items])
        stack[~clear] = np.nan
        with np.errstate(all="ignore"):
            bands[band] = np.nanmedian(stack, axis=0)
    return bands, clear.sum(axis=0)


# ---------- classification ----------


def ratio(a, b):
    with np.errstate(all="ignore"):
        return (a - b) / (a + b)


def classify(b):
    ndvi = ratio(b["nir"], b["red"])
    ndwi = ratio(b["green"], b["nir"])
    mndwi = ratio(b["green"], b["swir16"])
    ndmi = ratio(b["nir"], b["swir16"])
    veg = ndvi >= VEG_NDVI
    water = ~veg & ((mndwi > WATER_MNDWI) | (ndwi > WATER_NDWI))
    weed = veg & ((b["swir16"] < WEED_SWIR) | (ndmi > WEED_NDMI))
    return {"ndvi": ndvi, "ndci": ratio(b["rededge1"], b["red"]), "water": water, "weed": weed}


def pct(part, whole):
    return round(100 * part / whole, 1) if whole else None


def mean(values):
    values = values[np.isfinite(values)]
    return round(float(values.mean()), 4) if len(values) else None


def lake_row(lake, idx, bands, cls, clear_obs, season, scenes, source):
    valid = idx[~np.isnan(cls["ndvi"][idx])]
    n = len(valid)
    water = valid[cls["water"][valid]]
    weed = int(cls["weed"][valid].sum())
    clear = int(np.median(clear_obs[idx])) if len(idx) else 0
    enough_water = len(water) >= MIN_WATER_PIXELS
    return {
        "season": season,
        "compositeStart": scenes[0]["properties"]["datetime"][:10] if scenes else None,
        "compositeEnd": scenes[-1]["properties"]["datetime"][:10] if scenes else None,
        "scenes": len(scenes),
        "pixels": n,
        "clearObs": clear,
        "openWaterPct": pct(len(water), n),
        "floatingVegetationPct": pct(weed, n),
        "dryOrBuiltPct": pct(n - len(water) - weed, n),
        "meanNdvi": mean(cls["ndvi"][valid]),
        "turbidityRel": mean(bands["red"][water]) if enough_water else None,
        "chlorophyllRel": mean(cls["ndci"][water]) if enough_water else None,
        "lowConfidence": "yes" if lake["areaM2"] < MIN_AREA_M2 or n < MIN_PIXELS or clear < MIN_CLEAR else "no",
        "source": source,
    }


def empty_row(lake, season, source):
    row = {c: None for c in COLUMNS}
    return {**row, "season": season, "pixels": 0, "lowConfidence": "yes", "source": source}


# ---------- main ----------


def run_season(lakes, key, season, start, end, max_cloud):
    items = search(start, end)
    assign_tiles(lakes, items)
    source = f"sentinel2-{start.year}-{season}"
    rows, used = [], []
    for tile in sorted({lake["tile"] for lake in lakes if lake["tile"]}):
        members = [lake for lake in lakes if lake["tile"] == tile]
        scenes = pick_scenes(items, tile, max_cloud)
        dates = [s["properties"]["datetime"][:10] for s in scenes]
        print(f"  {season} {tile}: {len(members)} lakes, {len(scenes)} scenes {dates[0] if dates else ''}..{dates[-1] if dates else ''}", flush=True)
        if not scenes:
            rows += [{key: lake["key"], **empty_row(lake, season, source)} for lake in members]
            continue
        used += scenes
        touched = np.unique(np.concatenate([pixel_id(lake["touchedCols"], lake["touchedRows"]) for lake in members]))
        bands, clear_obs = composite(scenes, touched // ROW_SPAN, touched % ROW_SPAN)
        cls = classify(bands)
        for lake in members:
            idx = np.searchsorted(touched, pixel_id(lake["cols"], lake["rows"]))
            rows.append({key: lake["key"], **lake_row(lake, idx, bands, cls, clear_obs, season, scenes, source)})
    rows += [{key: lake["key"], **empty_row(lake, season, source)} for lake in lakes if not lake["tile"]]
    dates = sorted(s["properties"]["datetime"][:10] for s in used)
    entry = {
        "key": source,
        "title": f"Sentinel-2 L2A median composite, {season} season {dates[0] if dates else start} to {dates[-1] if dates else end}",
        "publisher": "European Space Agency, Copernicus programme; cloud-optimised copies by Element 84 Earth Search",
        "url": "https://registry.opendata.aws/sentinel-2-l2a-cogs/",
        "license": "Copernicus Sentinel data terms and conditions (free, full and open)",
        "credit": f"Contains modified Copernicus Sentinel data {end.year}",
        "asOf": dates[-1] if dates else str(end),
        "retrieved": date.today().isoformat(),
    }
    return rows, entry


def main():
    geo_path = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCES / "atree.geojson"
    key = sys.argv[2] if len(sys.argv) > 2 else "atreeFid"
    features = [f for f in json.loads(geo_path.read_text())["features"] if f.get("geometry")]
    lakes = lake_pixels(features, key)
    print(f"sentinel2: {len(lakes)} lakes, {sum(len(lake['cols']) for lake in lakes):,} pixels")
    rows, entries = [], []
    for season, start, end, max_cloud in seasons(date.today()):
        season_rows, entry = run_season(lakes, key, season, start, end, max_cloud)
        rows += season_rows
        entries.append(entry)
    out = SOURCES / "sentinel2.csv"
    write_csv(out, rows, [key, *COLUMNS])
    write_sources("sentinel2", entries)
    print(f"sentinel2: {len(rows)} rows -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
