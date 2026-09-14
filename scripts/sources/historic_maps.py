#!/usr/bin/env python3
"""
Water bodies drawn on old maps of Bengaluru (Survey of India 1927 and 1945, US Army 1955).

For each map sheet (Survey of India and US Army Map Service, all public domain, from
Wikimedia Commons):
  1. download the full-resolution scan to data/cache/historic_maps/
  2. georeference it from its printed graticule (historic_maps_georef.py)
  3. segment the water drawn on it (historic_maps_water.py)
  4. measure and correct the remaining offset against today's lakes (historic_maps_align.py)
Sheets that cannot be aligned to within MAX_RESIDUAL_M are reported and left out.

Outputs:
  data/sources/historic_water.geojson   one polygon per water body per map
  data/sources/historic_sheets.geojson  each sheet's coverage (where water was read), year, accuracy
  data/sources/historic_maps.sources.json
Then runs historic_presence.py for the per-lake tables.

Run: .venv/bin/python scripts/sources/historic_maps.py [sheet-key ...]
"""

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import shapely
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, SOURCES, write_sources  # noqa: E402
from historic_maps_align import align, to_utm, to_wgs  # noqa: E402
from historic_maps_georef import georeference  # noqa: E402
from historic_maps_sheets import SHEETS  # noqa: E402
from historic_maps_water import blank_mask, water_mask  # noqa: E402

NAME = "historic_maps"
DIR = CACHE / NAME
USER_AGENT = "LakesOfBendakaluru/0.1 (https://filtercoffee.dev; research on Bengaluru lakes)"
RETRIEVED = "2026-09-11"
MAX_RESIDUAL_M = 150
# Leave-one-out error of a translation needs at least 3 other lakes.
MIN_CONTROL_LAKES = 4
# Lakes used to check alignment in the report.
NAMED = {
    38: "Hebbal",
    157: "Ulsoor",
    497: "Sankey",
    103: "Bellandur",
    142: "Madiwala",
    439: "Hesaraghatta",
    44: "Yelahanka",
    159: "Varthur",
}
# Output is limited to today's lake area plus 5 km, so distant towns on the sheets are left out.
STUDY_MARGIN_M = 5000
# Flat-filled town areas smaller than this are symbols, not towns.
MIN_BLANK_M2 = 1_000_000


def fetch(sheet):
    path = DIR / sheet["file"]
    if path.exists() and path.stat().st_size > 0:
        return path
    DIR.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(sheet["download"], headers={"User-Agent": USER_AGENT})
    tmp = path.with_suffix(".part")
    with urllib.request.urlopen(request, timeout=600) as response, tmp.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    tmp.replace(path)
    return path


def load_lakes():
    features = json.loads((SOURCES / "atree.geojson").read_text(encoding="utf-8"))["features"]
    lakes = []
    for f in features:
        g = make_valid(to_utm(shape(f["geometry"]))).buffer(0)
        if not g.is_empty:
            lakes.append((f["properties"]["atreeFid"], f["properties"]["name"], g))
    return lakes


def polygons_from_mask(mask, fit, simplify_px):
    """Contours in scan pixels -> polygons on the sheet's lon/lat, then UTM metres."""
    contours, hierarchy = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hierarchy is None:
        return []
    hierarchy = hierarchy[0]

    def ring(contour):
        pts = cv2.approxPolyDP(contour, simplify_px, True)[:, 0, :].astype(float)
        if len(pts) < 3:
            return None
        lon, lat = fit.pixel_to_lonlat(pts[:, 0], pts[:, 1])
        return list(zip(lon, lat))

    polys = []
    for i, contour in enumerate(contours):
        if hierarchy[i][3] != -1:
            continue  # holes are attached to their outer ring below
        shell = ring(contour)
        if shell is None:
            continue
        holes, child = [], hierarchy[i][2]
        while child != -1:
            h = ring(contours[child])
            if h is not None:
                holes.append(h)
            child = hierarchy[child][0]
        poly = make_valid(to_utm(Polygon(shell, holes)))
        polys.extend(p for p in getattr(poly, "geoms", [poly]) if isinstance(p, Polygon) and not p.is_empty)
    return polys


def confidence(sheet, area, blue_share):
    """
    high/medium/low from how the tank was drawn and its size against the sheet's
    smallest reliable size. Dot stipple on the 1945 reprint is never "high"; neither is
    anything near the size limit, where stream beads and symbols get through.
    """
    ratio = area / sheet["minAreaM2"]
    best = "medium" if sheet["style"] == "soi-stipple" else "high"
    if sheet["style"] == "soi-colour" and not sheet["water"].get("dotScreen") and blue_share < 0.5:
        best = "medium"
    levels = ["low", "medium", "high"]
    if ratio >= 3:
        return best
    if ratio >= 1.5:
        return levels[max(levels.index(best) - 1, 0)]
    return "low"


def process(sheet, lakes, study):
    img = cv2.imread(str(fetch(sheet)), cv2.IMREAD_COLOR)
    fit, geo_report = georeference(sheet, img)
    mask, blue = water_mask(img, sheet)
    blank = blank_mask(img, sheet)
    del img
    west, south, east, north = sheet["bounds"]
    edge = np.linspace(0, 1, 41)
    ring = (
        [(west + (east - west) * t, north) for t in edge]
        + [(east, north + (south - north) * t) for t in edge]
        + [(east + (west - east) * t, south) for t in edge]
        + [(west, south + (north - south) * t) for t in edge]
    )
    footprint = to_utm(Polygon(ring))
    polys = [p.intersection(footprint) for p in polygons_from_mask(mask, fit, sheet["simplifyPx"])]
    polys = [
        q for p in polys for q in getattr(p, "geoms", [p]) if isinstance(q, Polygon) and q.area >= sheet["minAreaM2"]
    ]
    blue_polys = unary_union(polygons_from_mask(blue, fit, sheet["simplifyPx"])) if blue.any() else Polygon()

    correct, align_report = align(polys, footprint, lakes, sheet["align"], NAMED)
    residual = align_report["residualP90M"]
    usable = (
        residual is not None
        and align_report["residualMedianM"] <= MAX_RESIDUAL_M
        and align_report["controlLakesKept"] >= MIN_CONTROL_LAKES
        and not sheet.get("reject")
    )
    # Coverage: where water was read from this sheet. Towns drawn as flat fill and
    # everything outside the study area are left out, so a lake there gets no answer.
    coverage = footprint
    if blank is not None and blank.any():
        towns = [p for p in polygons_from_mask(blank, fit, sheet["simplifyPx"]) if p.area >= MIN_BLANK_M2]
        coverage = coverage.difference(unary_union(towns))
    coverage = make_valid(correct(coverage)).intersection(study)
    # Every sheet's corrected polygons go to the cache for review, usable or not.
    review = [
        {"type": "Feature", "properties": {"sheet": sheet["key"]}, "geometry": mapping(to_wgs(correct(p)))}
        for p in polys
    ]
    write_geojson(DIR / f"review-{sheet['key']}.geojson", review)
    rows = []
    if usable:
        for p in polys:
            share = p.intersection(blue_polys).area / p.area if not blue_polys.is_empty else 0.0
            pc = make_valid(correct(p))
            if not study.contains(pc.representative_point()):
                continue
            rows.append({"geom": pc, "sheet": sheet, "blueShare": share})
    report = {
        "georeference": geo_report,
        "alignment": align_report,
        "usable": usable,
        "rejected": sheet.get("reject"),
        "waterBodies": len(rows),
    }
    return rows, coverage, report


def merge_across_edges(rows):
    """Join the pieces of one tank split by the edge between two sheets of the same year."""
    merged, used = [], set()
    for i, a in enumerate(rows):
        if i in used:
            continue
        group = [i]
        for j in range(i + 1, len(rows)):
            b = rows[j]
            if j in used or b["sheet"]["year"] != a["sheet"]["year"] or b["sheet"]["key"] == a["sheet"]["key"]:
                continue
            if a["geom"].distance(b["geom"]) < 60:
                group.append(j)
        if len(group) == 1:
            merged.append(a)
            continue
        used.update(group)
        parts = [rows[k] for k in group]
        geom = unary_union([p["geom"].buffer(40) for p in parts]).buffer(-40)
        main = max(parts, key=lambda p: p["geom"].area)
        merged.append({**main, "geom": geom})
    return merged


def main(only):
    lakes = load_lakes()
    study = unary_union([g for _, _, g in lakes]).convex_hull.buffer(STUDY_MARGIN_M)
    rows, sheet_features, reports = [], [], {}
    for sheet in SHEETS:
        if only and sheet["key"] not in only:
            continue
        print(f"{sheet['key']}: {sheet['title']}", flush=True)
        sheet_rows, coverage, report = process(sheet, lakes, study)
        reports[sheet["key"]] = report
        print(json.dumps(report, indent=1), flush=True)
        if not report["usable"]:
            print(f"  skipped: {sheet.get('reject') or f'alignment error above {MAX_RESIDUAL_M} m'}", flush=True)
            continue
        rows.extend(sheet_rows)
        a, g = report["alignment"], report["georeference"]
        sheet_features.append(
            {
                "type": "Feature",
                "properties": {
                    "sheet": sheet["key"],
                    "title": sheet["title"],
                    "year": sheet["year"],
                    "scale": sheet["scale"],
                    "url": sheet["url"],
                    "showsAllWater": sheet.get("showsAllWater", True),
                    "minAreaM2": sheet["minAreaM2"],
                    "graticuleRmsM": g["rmsResidualM"],
                    "shiftToWgs84M": a["sheetShiftM"],
                    "correction": a["correction"],
                    "controlLakes": a["controlLakesKept"],
                    "offsetBeforeMedianM": a["offsetBeforeMedianM"],
                    "residualMedianM": a["residualMedianM"],
                    "residualP90M": a["residualP90M"],
                    "source": sheet["sourceKey"],
                },
                "geometry": mapping(shapely.set_precision(to_wgs(coverage), 1e-6)),
            }
        )

    rows = merge_across_edges(rows)
    rows.sort(key=lambda r: (r["sheet"]["year"], r["sheet"]["key"], -r["geom"].centroid.y, r["geom"].centroid.x))
    counters, features = {}, []
    for r in rows:
        s = r["sheet"]
        counters[s["key"]] = counters.get(s["key"], 0) + 1
        geom = r["geom"]
        if isinstance(geom, MultiPolygon):
            geom = max(geom.geoms, key=lambda p: p.area)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "histId": f"{s['key']}-{counters[s['key']]:04d}",
                    "sheet": s["key"],
                    "year": s["year"],
                    "scale": s["scale"],
                    "areaM2": round(geom.area),
                    "name": None,
                    "confidence": confidence(s, geom.area, r["blueShare"]),
                    "source": s["sourceKey"],
                },
                # Snapped to the 6-decimal grid it is written at, so it stays valid when read back.
                "geometry": mapping(shapely.set_precision(make_valid(to_wgs(geom.simplify(1.0))), 1e-6)),
            }
        )

    if only:
        print("partial run: outputs not written", flush=True)
        return
    write_geojson(SOURCES / "historic_water.geojson", features)
    write_geojson(SOURCES / "historic_sheets.geojson", sheet_features)
    (DIR / "report.json").write_text(json.dumps(reports, indent=1) + "\n", encoding="utf-8")
    write_sources(
        NAME,
        [
            {
                "key": s["sourceKey"],
                "title": s["title"],
                "publisher": s["publisher"],
                "url": s["url"],
                "license": s["license"],
                "credit": s["credit"],
                "asOf": str(s["year"]),
                "retrieved": RETRIEVED,
            }
            for s in SHEETS
            if s["key"] in {f["properties"]["sheet"] for f in sheet_features}
        ],
    )
    print(f"{len(features)} historic water bodies from {len(sheet_features)} sheets", flush=True)
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "historic_presence.py")], check=True)


def write_geojson(path, features):
    def rounded(obj):
        if isinstance(obj, float):
            return round(obj, 6)
        if isinstance(obj, (list, tuple)):
            return [rounded(v) for v in obj]
        if isinstance(obj, dict):
            return {k: rounded(v) for k, v in obj.items()}
        return obj

    fc = {"type": "FeatureCollection", "features": [rounded(f) for f in features]}
    path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
