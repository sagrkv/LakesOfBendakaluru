#!/usr/bin/env python3
"""
Which lakes were on the old maps, and which old tanks match no lake today.

Reads data/sources/historic_water.geojson and historic_sheets.geojson (made by
historic_maps.py) and a lake file (default: today's ATREE outlines).

historic_presence.csv, one row per lake, per map year:
  onMap<Year>          true if historic water lies within the map's alignment tolerance of
                       the lake outline; false if not; empty if the lake is outside that
                       year's map coverage, when the lake today is smaller than the smallest
                       water body that map shows, or when the map leaves some water undrawn
                       (the 1945 reprint lacks its blue plate): a missing tank proves nothing
  overlapPct<Year>     share of the lake's outline covered by that year's historic water
  historicArea<Year>M2 total area of the historic water bodies counted for onMap

historic_lost.csv, one row per historic water body with no lake within tolerance: the
candidates for the Forgotten Lakes list. alsoOnMaps lists the water bodies on the other
map years at the same place, so one vanished tank seen on two maps shows as such.

The tolerance is each map year's median alignment error (between 25 and 150 m).

Run: .venv/bin/python scripts/sources/historic_presence.py [--input lakes.geojson --key id]
"""

import json
import sys
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _lake_input import TO_UTM, TO_WGS, load_lakes, parse_args  # noqa: E402
from common import SOURCES, write_csv  # noqa: E402


def read_features(path):
    return json.loads(path.read_text(encoding="utf-8"))["features"]


def tolerance_by_year(sheets):
    tol = {}
    for s in sheets:
        p = s["properties"]
        tol[p["year"]] = max(tol.get(p["year"], 0), p["residualMedianM"] or 0)
    return {y: min(max(t, 25), 150) for y, t in tol.items()}


def main():
    args = parse_args(__doc__.split("\n")[1])
    key = args.key
    lakes = load_lakes(args)
    for lake in lakes:
        lake["utm"] = transform(TO_UTM, lake["geom"]).buffer(0)
    sheets = read_features(SOURCES / "historic_sheets.geojson")
    water = read_features(SOURCES / "historic_water.geojson")
    years = sorted({s["properties"]["year"] for s in sheets})
    tol = tolerance_by_year(sheets)

    by_year = {}
    for y in years:
        polys = [
            (f["properties"], transform(TO_UTM, shape(f["geometry"])).buffer(0))
            for f in water
            if f["properties"]["year"] == y
        ]
        cover = [
            (
                s["properties"]["source"],
                transform(TO_UTM, shape(s["geometry"])),
                s["properties"]["showsAllWater"] and s["properties"]["minAreaM2"],
            )
            for s in sheets
            if s["properties"]["year"] == y
        ]
        by_year[y] = {
            "props": [p for p, _ in polys],
            "geoms": [g for _, g in polys],
            "tree": STRtree([g for _, g in polys]),
            "cover": cover,
        }

    rows = []
    for lake in lakes:
        g = lake["utm"]
        point = g.representative_point()
        row, used = {key: lake["key"]}, []
        for y in years:
            d = by_year[y]
            # Per covering sheet: the smallest lake whose absence it can show, or False.
            covering = [(src, smallest) for src, c, smallest in d["cover"] if c.contains(point)]
            sources = [src for src, _ in covering]
            if not sources:
                row.update({f"onMap{y}": None, f"overlapPct{y}": None, f"historicArea{y}M2": None})
                continue
            used += sources
            near = [d["geoms"][i] for i in d["tree"].query(g, predicate="dwithin", distance=tol[y])]
            overlap = unary_union([h.intersection(g) for h in near]).area if near else 0.0
            row.update(
                {
                    f"onMap{y}": True if near else (False if all(m and g.area >= m for _, m in covering) else None),
                    f"overlapPct{y}": round(100 * overlap / g.area, 1) if g.area else 0.0,
                    f"historicArea{y}M2": round(sum(h.area for h in near)),
                }
            )
        row["source"] = sorted(set(used))
        rows.append(row)
    columns = [key] + [c for y in years for c in (f"onMap{y}", f"overlapPct{y}", f"historicArea{y}M2")] + ["source"]
    write_csv(SOURCES / "historic_presence.csv", rows, columns)

    lake_tree = STRtree([lake["utm"] for lake in lakes])
    nearest_col = "nearest" + key[0].upper() + key[1:]
    lost = []
    for y in years:
        d = by_year[y]
        for props, h in zip(d["props"], d["geoms"]):
            if len(lake_tree.query(h, predicate="dwithin", distance=tol[y])):
                continue
            i = int(lake_tree.nearest(h))
            also = [
                by_year[o]["props"][j]["histId"]
                for o in years
                if o != y
                for j in by_year[o]["tree"].query(h, predicate="dwithin", distance=max(tol[y], tol[o]))
            ]
            pt = transform(TO_WGS, h.representative_point())
            lost.append(
                {
                    "histId": props["histId"],
                    "year": y,
                    "lat": round(pt.y, 6),
                    "lon": round(pt.x, 6),
                    "areaM2": props["areaM2"],
                    nearest_col: lakes[i]["key"],
                    "nearestDistanceM": round(h.distance(lakes[i]["utm"])),
                    "alsoOnMaps": also,
                    "sheet": props["sheet"],
                    "confidence": props["confidence"],
                    "source": props["source"],
                }
            )
    write_csv(
        SOURCES / "historic_lost.csv",
        lost,
        [
            "histId",
            "year",
            "lat",
            "lon",
            "areaM2",
            nearest_col,
            "nearestDistanceM",
            "alsoOnMaps",
            "sheet",
            "confidence",
            "source",
        ],
    )

    for y in years:
        vals = [r[f"onMap{y}"] for r in rows]
        print(
            f"{y}: {vals.count(True)} lakes on the map, {vals.count(False)} not, {vals.count(None)} no answer; "
            f"{sum(1 for r in lost if r['year'] == y)} historic water bodies match no lake (tolerance {tol[y]} m)"
        )


if __name__ == "__main__":
    main()
