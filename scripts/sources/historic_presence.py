#!/usr/bin/env python3
"""
Which lakes were on the old maps, and which old tanks match no lake today.

Reads data/sources/historic_water.geojson and historic_sheets.geojson (made by
historic_maps.py) and a lake file (default: today's ATREE outlines).

Sheets are grouped by edition: the map year a record uses. Sheets of one survey printed
over several years share one (the 1914-1917 sheets are 1914, the 1973-1980 sheets 1975);
single sheets use their own year.

historic_presence.csv, one row per lake, per edition:
  onMap<Edition>          true if historic water lies within the edition's alignment tolerance of
                          the lake outline; false if not; empty if the lake is outside that
                          edition's coverage, when the lake today is smaller than the smallest
                          water body that map shows, or when the map leaves some water undrawn
                          (the 1945 reprint lacks its blue plate): a missing tank proves nothing
  overlapPct<Edition>     share of the lake's outline covered by that edition's historic water
  historicArea<Edition>M2 total area of the historic water bodies counted for onMap
  source<Edition>         the sheet or sheets that answered, whose citations carry the year printed

historic_lost.csv, one row per historic water body with no lake within tolerance: the
candidates for the Forgotten Lakes list. alsoOnMaps lists the water bodies on the other
editions at the same place, so one vanished tank seen on two maps shows as such.

The tolerance is each edition's largest per-sheet median alignment error (between 25 and 150 m).

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


def tolerance_by_edition(sheets):
    tol = {}
    for s in sheets:
        p = s["properties"]
        tol[p["edition"]] = max(tol.get(p["edition"], 0), p["residualMedianM"] or 0)
    return {e: min(max(t, 25), 150) for e, t in tol.items()}


def main():
    args = parse_args(__doc__.split("\n")[1])
    key = args.key
    lakes = load_lakes(args)
    for lake in lakes:
        lake["utm"] = transform(TO_UTM, lake["geom"]).buffer(0)
    sheets = read_features(SOURCES / "historic_sheets.geojson")
    water = read_features(SOURCES / "historic_water.geojson")
    editions = sorted({s["properties"]["edition"] for s in sheets})
    tol = tolerance_by_edition(sheets)

    by_edition = {}
    for e in editions:
        polys = [
            (f["properties"], transform(TO_UTM, shape(f["geometry"])).buffer(0))
            for f in water
            if f["properties"]["edition"] == e
        ]
        cover = [
            (
                s["properties"]["source"],
                transform(TO_UTM, shape(s["geometry"])),
                s["properties"]["showsAllWater"] and s["properties"]["minAreaM2"],
            )
            for s in sheets
            if s["properties"]["edition"] == e
        ]
        by_edition[e] = {
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
        for e in editions:
            d = by_edition[e]
            # Per covering sheet: the smallest lake whose absence it can show, or False.
            covering = [(src, smallest) for src, c, smallest in d["cover"] if c.contains(point)]
            if not covering:
                row.update({f"onMap{e}": None, f"overlapPct{e}": None, f"historicArea{e}M2": None, f"source{e}": None})
                continue
            near = [i for i in d["tree"].query(g, predicate="dwithin", distance=tol[e])]
            geoms = [d["geoms"][i] for i in near]
            overlap = unary_union([h.intersection(g) for h in geoms]).area if geoms else 0.0
            # Cite the sheets whose tanks were counted; for an absence, the sheets that cover the lake.
            sources = sorted({d["props"][i]["source"] for i in near} or {src for src, _ in covering})
            used += sources
            row.update(
                {
                    f"onMap{e}": True if geoms else (False if all(m and g.area >= m for _, m in covering) else None),
                    f"overlapPct{e}": round(100 * overlap / g.area, 1) if g.area else 0.0,
                    f"historicArea{e}M2": round(sum(h.area for h in geoms)),
                    f"source{e}": sources,
                }
            )
        row["source"] = sorted(set(used))
        rows.append(row)
    columns = (
        [key]
        + [c for e in editions for c in (f"onMap{e}", f"overlapPct{e}", f"historicArea{e}M2", f"source{e}")]
        + ["source"]
    )
    write_csv(SOURCES / "historic_presence.csv", rows, columns)

    lake_tree = STRtree([lake["utm"] for lake in lakes])
    nearest_col = "nearest" + key[0].upper() + key[1:]
    lost = []
    for e in editions:
        d = by_edition[e]
        for props, h in zip(d["props"], d["geoms"]):
            if len(lake_tree.query(h, predicate="dwithin", distance=tol[e])):
                continue
            i = int(lake_tree.nearest(h))
            also = [
                by_edition[o]["props"][j]["histId"]
                for o in editions
                if o != e
                for j in by_edition[o]["tree"].query(h, predicate="dwithin", distance=max(tol[e], tol[o]))
            ]
            pt = transform(TO_WGS, h.representative_point())
            lost.append(
                {
                    "histId": props["histId"],
                    "edition": e,
                    "year": props["year"],
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
            "edition",
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

    for e in editions:
        vals = [r[f"onMap{e}"] for r in rows]
        print(
            f"{e}: {vals.count(True)} lakes on the map, {vals.count(False)} not, {vals.count(None)} no answer; "
            f"{sum(1 for r in lost if r['edition'] == e)} historic water bodies match no lake (tolerance {tol[e]} m)"
        )


if __name__ == "__main__":
    main()
