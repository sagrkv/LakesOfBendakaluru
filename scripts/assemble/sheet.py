"""
The cut-out sheet for one lake: its outline in metres, the biggest open area inside it
where the name is typeset, and its longest end-to-end measure.

Coordinates are UTM 43N metres shifted so the outline's bounding box starts at (0, 0),
with x growing east and y growing down, so the front end can use them as SVG units.
"""

import math

import cv2
import numpy as np
from pyproj import Transformer
from shapely import prepared
from shapely.geometry import MultiPolygon, Polygon, box, shape
from shapely.ops import transform

_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True).transform

ASPECT = 0.3  # the room's height is at least this share of its width
GRID = 600  # raster cells along the outline's long side when searching for the room
SIMPLIFY_STEPS = 900  # simplify tolerance is the long side divided by this, at least 1 m


def build_sheet(geometry):
    """geometry: a GeoJSON Polygon or MultiPolygon in lon/lat. Returns None for anything else."""
    if geometry["type"] not in ("Polygon", "MultiPolygon"):
        return None
    utm = transform(_to_utm, shape(geometry))
    min_x, min_y, max_x, max_y = utm.bounds
    w, h = max_x - min_x, max_y - min_y
    if w <= 0 or h <= 0:
        return None
    lake = transform(lambda x, y: (x - min_x, max_y - y), utm)

    tolerance = max(1.0, max(w, h) / SIMPLIFY_STEPS)
    drawn = [p for p in (_simplify(poly, tolerance) for poly in _polygons(lake)) if p is not None]
    if not drawn:
        return None
    d = "".join(_subpath(ring) for poly in drawn for ring in (poly.exterior, *poly.interiors))

    # The name must sit inside both the real water and the simplified shape the page draws.
    water = lake.intersection(MultiPolygon(drawn))
    room = _room(water, w, h)
    return {
        "w": round(w, 1),
        "h": round(h, 1),
        "origin": [round(min_x, 1), round(max_y, 1)],
        "d": d,
        **({"room": room} if room else {}),
        "span": _span(lake),
    }


def _polygons(geom):
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]


def _simplify(poly, tolerance):
    """Simplify each ring and drop rings that collapse to nothing."""
    exterior = _ring(poly.exterior, tolerance)
    if exterior is None:
        return None
    holes = [r for r in (_ring(i, tolerance) for i in poly.interiors) if r is not None]
    simple = Polygon(exterior, holes)
    return simple if simple.is_valid else Polygon(exterior)


def _ring(ring, tolerance):
    coords = [(round(x, 1), round(y, 1)) for x, y in ring.simplify(tolerance, preserve_topology=True).coords]
    deduped = [c for i, c in enumerate(coords) if i == 0 or c != coords[i - 1]]
    if len(deduped) < 4 or Polygon(deduped).area < tolerance * tolerance:
        return None
    return deduped


def _subpath(ring):
    coords = list(ring.coords)[:-1]
    return "M" + "L".join(f"{_num(x)} {_num(y)}" for x, y in coords) + "Z"


def _num(v):
    text = f"{v:.1f}"
    return text[:-2] if text.endswith(".0") else text


def _room(water, w, h):
    """
    The widest axis-aligned rectangle inside the water whose height is at least ASPECT of
    its width. Found on a raster first, then grown to the real outline in metres.
    """
    if water.is_empty:
        return None
    cell = max(w, h) / GRID
    cols, rows = math.ceil(w / cell) + 1, math.ceil(h / cell) + 1
    mask = np.zeros((rows, cols), np.uint8)
    shift = 4  # sub-cell precision for fillPoly
    scale = (1 << shift) / cell
    for poly in _polygons(water):
        part = np.zeros_like(mask)
        cv2.fillPoly(part, [np.round(np.asarray(poly.exterior.coords) * scale).astype(np.int32)], 1, cv2.LINE_8, shift)
        for hole in poly.interiors:
            cv2.fillPoly(part, [np.round(np.asarray(hole.coords) * scale).astype(np.int32)], 0, cv2.LINE_8, shift)
        mask |= part
    # fillPoly paints every cell the boundary touches; eroding keeps only cells fully in the water.
    mask = cv2.erode(mask, np.ones((3, 3), np.uint8), borderValue=0)
    if not mask.any():
        return _grow(water, None, w, h)

    table = np.zeros((rows + 1, cols + 1), np.int64)
    table[1:, 1:] = mask.cumsum(0).cumsum(1)

    def fits(rw, rh):
        """Top-left cells of every rw x rh window that is all water."""
        if rw > cols or rh > rows:
            return None
        s = table[rh:, rw:] - table[:-rh, rw:] - table[rh:, :-rw] + table[:-rh, :-rw]
        hits = np.argwhere(s == rw * rh)
        return hits if len(hits) else None

    def need(rw):
        return max(1, math.ceil(ASPECT * rw))

    lo, hi = 1, cols  # feasibility of a width is monotone: a narrower room fits inside a wider one
    if fits(1, 1) is None:
        return _grow(water, None, w, h)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(mid, need(mid)) is not None:
            lo = mid
        else:
            hi = mid - 1
    best_w = lo
    lo, hi = need(best_w), rows  # at that width, take the tallest room
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(best_w, mid) is not None:
            lo = mid
        else:
            hi = mid - 1
    hits = fits(best_w, lo)
    r, c = hits[len(hits) // 2]
    return _grow(water, (c * cell, r * cell, (c + best_w) * cell, (r + lo) * cell), w, h)


def _grow(water, start, w, h):
    """Shrink the raster room until it is truly inside, then push each edge out to the shore."""
    inside = prepared.prep(water)
    if start is None:
        p = water.representative_point()
        start = (p.x, p.y, p.x, p.y)
    x0, y0, x1, y1 = start
    while not inside.contains(box(x0, y0, x1, y1)) and x1 - x0 > 0.01:
        cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * 0.45, (y1 - y0) * 0.45
        x0, y0, x1, y1 = cx - hw, cy - hh, cx + hw, cy + hh
    if not inside.contains(box(x0, y0, x1, y1)):
        return None

    def push(edges, index, limit):
        lo, hi = edges[index], limit
        for _ in range(24):
            mid = (lo + hi) / 2
            trial = list(edges)
            trial[index] = mid
            if inside.contains(box(*trial)):
                lo = mid
            else:
                hi = mid
        return lo

    edges = [x0, y0, x1, y1]
    for _ in range(3):
        edges[1] = push(edges, 1, 0.0)
        edges[3] = push(edges, 3, h)
        height = edges[3] - edges[1]
        spare = height / ASPECT - (edges[2] - edges[0])
        if spare > 0:
            edges[0] = push(edges, 0, max(0.0, edges[0] - spare))
            edges[2] = push(edges, 2, min(w, edges[0] + height / ASPECT))
    # Round inward so the published rectangle stays inside the water, then keep the aspect.
    x0, y0 = math.ceil(edges[0] * 10) / 10, math.ceil(edges[1] * 10) / 10
    x1, y1 = math.floor(edges[2] * 10) / 10, math.floor(edges[3] * 10) / 10
    x1 = min(x1, x0 + math.floor((y1 - y0) / ASPECT * 10) / 10)
    if x1 <= x0 or y1 <= y0:
        return None
    return {"x": x0, "y": y0, "w": round(x1 - x0, 1), "h": round(y1 - y0, 1)}


def _span(lake):
    """The two outline vertices farthest apart: the ends of the convex hull's diameter."""
    pts = np.asarray(lake.convex_hull.exterior.coords)[:-1]
    diff = pts[:, None, :] - pts[None, :, :]
    dist = np.hypot(diff[..., 0], diff[..., 1])
    i, j = np.unravel_index(dist.argmax(), dist.shape)
    (x1, y1), (x2, y2) = pts[i], pts[j]
    return {"x1": round(x1, 1), "y1": round(y1, 1), "x2": round(x2, 1), "y2": round(y2, 1), "m": round(dist[i, j])}
