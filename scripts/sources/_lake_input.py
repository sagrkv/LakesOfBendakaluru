"""
Shared input handling for the per-lake raster scripts (jrc_water, worldcover, dem, cascade).

Not a source itself. Every per-lake script takes the lake geometry file and its key property
on the command line, so the build can rerun it on the full lake list later. That list includes
disappeared lakes given as points; a point is buffered to a circle with the lake's recorded area
(or a default radius when there is no area).
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping, shape
from shapely.ops import transform

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import ROOT, SOURCES  # noqa: E402

# UTM 43N covers 72-78 E, which holds all of Bengaluru. Used for every metre-based operation.
TO_UTM = Transformer.from_crs(4326, 32643, always_xy=True).transform
TO_WGS = Transformer.from_crs(32643, 4326, always_xy=True).transform


def parse_args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input", default=str(SOURCES / "atree.geojson"), help="GeoJSON of lakes (polygons or points)")
    parser.add_argument("--key", default="atreeFid", help="property that identifies a lake")
    parser.add_argument(
        "--area-prop", default="areaM2", help="property with the recorded area, used to size point lakes"
    )
    parser.add_argument("--default-radius", type=float, default=50.0, help="radius in m for point lakes with no area")
    return parser.parse_args()


def buffer_m(geom, metres):
    """Buffer a WGS84 geometry by a distance in metres."""
    return transform(TO_WGS, transform(TO_UTM, geom).buffer(metres))


def load_lakes(args):
    """
    Returns a list of dicts: key, geom (WGS84 shapely polygon), isPoint.
    Points become circles with the recorded area, so later steps treat every lake the same.
    """
    path = Path(args.input)
    if not path.is_absolute():
        path = ROOT / path
    lakes = []
    for feature in json.loads(path.read_text(encoding="utf-8"))["features"]:
        props = feature["properties"]
        if not feature.get("geometry"):
            continue
        geom = shape(feature["geometry"])
        is_point = geom.geom_type in ("Point", "MultiPoint")
        if is_point:
            area = props.get(args.area_prop)
            radius = math.sqrt(float(area) / math.pi) if area else args.default_radius
            geom = buffer_m(geom.centroid, radius)
        if geom.is_empty:
            continue
        lakes.append({"key": props[args.key], "geom": geom, "isPoint": is_point})
    return lakes


def lakes_bounds(lakes, margin_deg=0.0):
    xs0, ys0, xs1, ys1 = zip(*(lake["geom"].bounds for lake in lakes))
    return min(xs0) - margin_deg, min(ys0) - margin_deg, max(xs1) + margin_deg, max(ys1) + margin_deg


def cache_window(url, dest, bounds):
    """
    Read the part of a (remote) raster that covers bounds and keep it as a local GeoTIFF.
    Reuses the cached file when it already covers the bounds.
    """
    dest = Path(dest)
    if dest.exists():
        with rasterio.open(dest) as ds:
            b = ds.bounds
            if b.left <= bounds[0] and b.bottom <= bounds[1] and b.right >= bounds[2] and b.top >= bounds[3]:
                return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_path = url if not url.startswith("http") else f"/vsicurl/{url}"
    with rasterio.open(src_path) as src:
        win = from_bounds(*bounds, src.transform).round_offsets(op="floor").round_lengths(op="ceil")
        win = win.intersection(Window(0, 0, src.width, src.height))
        data = src.read(1, window=win)
        profile = src.profile.copy()
        profile.update(
            width=data.shape[1],
            height=data.shape[0],
            transform=src.window_transform(win),
            compress="deflate",
            tiled=True,
            blockxsize=512,
            blockysize=512,
        )
        profile.pop("interleave", None)
    tmp = dest.with_suffix(".part.tif")
    with rasterio.open(tmp, "w", **profile) as out:
        out.write(data, 1)
    tmp.replace(dest)
    return dest


class Grid:
    """An in-memory raster with helpers to pull the pixels under a geometry."""

    def __init__(self, data, transform_, res):
        self.data, self.transform, self.res = data, transform_, res

    @classmethod
    def open(cls, path):
        with rasterio.open(path) as ds:
            return cls(ds.read(1), ds.transform, ds.res)

    def window(self, geom, pad=1):
        """Row/col slices covering a geometry's bounds, padded by a few pixels."""
        x0, y0, x1, y1 = geom.bounds
        inv = ~self.transform
        c0, r0 = inv * (x0, y1)
        c1, r1 = inv * (x1, y0)
        r0, c0 = max(int(math.floor(r0)) - pad, 0), max(int(math.floor(c0)) - pad, 0)
        r1 = min(int(math.ceil(r1)) + pad, self.data.shape[0])
        c1 = min(int(math.ceil(c1)) + pad, self.data.shape[1])
        return slice(r0, r1), slice(c0, c1)

    def mask(self, geom, fallback_touched=True):
        """
        Pixels whose centre is inside geom, as (rows, cols, boolean mask, centre_based).
        If no pixel centre is inside (a very small lake), falls back to every pixel the geometry
        touches and returns centre_based=False.
        """
        rows, cols = self.window(geom)
        shape_ = (max(rows.stop - rows.start, 0), max(cols.stop - cols.start, 0))
        if 0 in shape_:
            return rows, cols, np.zeros(shape_, dtype=bool), True
        t = self.transform * Affine.translation(cols.start, rows.start)
        inside = ~geometry_mask([mapping(geom)], shape_, t, all_touched=False)
        if inside.any() or not fallback_touched:
            return rows, cols, inside, True
        return rows, cols, ~geometry_mask([mapping(geom)], shape_, t, all_touched=True), False

    def values(self, geom, fallback_touched=True):
        """Pixel values under geom (see mask). Returns (values, centre_based)."""
        rows, cols, inside, centre_based = self.mask(geom, fallback_touched)
        return self.data[rows, cols][inside], centre_based


def pixel_area_m2(lat, res_x, res_y):
    """Area of a res_x by res_y degree pixel at a latitude, on the WGS84 ellipsoid."""
    a, e2 = 6378137.0, 0.00669437999014
    phi = math.radians(lat)
    s = 1 - e2 * math.sin(phi) ** 2
    meridional = a * (1 - e2) / s**1.5
    prime = a / math.sqrt(s)
    return (prime * math.cos(phi) * math.radians(res_x)) * (meridional * math.radians(abs(res_y)))
