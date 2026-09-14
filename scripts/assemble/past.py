"""
The Past Lakes page: every lake that disappeared or was converted.

past.json holds one lean row per past lake, only what the page shows or filters by.
past-sheet.svg is the city as one sheet of ink paper with a hole where each past lake was,
drawn here so the page links to it instead of inlining thousands of shapes.
"""

import math

MAP_YEARS = (1927, 1945, 1955)
SQ_M_PER_ACRE = 4046.86
M_PER_DEGREE = 111320
HOLE_WIDENING = 6  # holes are drawn this many times wider than the lake was, so half-acre ponds show
MIN_HOLE = 1.5  # radius in frame units for a lake with no recorded extent
INK, TABLE = "#1B1A17", "#F6EEDB"


def past_rows(records, summaries):
    """Largest first, as lakes.json is. Unknown facts are left out."""
    by_id = {r["id"]: r for r in records}
    rows = []
    for s in summaries:
        if s.get("status") == "exists":
            continue
        h = by_id[s["id"]].get("history", {})
        maps = [year for year in MAP_YEARS if h.get(f"onMap{year}")]
        row = {
            "id": s["id"],
            "name": s["name"],
            "acres": s.get("acres"),
            "valley": s.get("valley"),
            "xy": s.get("xy"),
            "goneBy": h.get("goneBy"),
            "lastSeenWithWater": h.get("lastSeenWithWater"),
            "onMap": maps or None,
            "knownOnlyFromOldMap": h.get("knownOnlyFromOldMap") or None,
            "convertedBy": h.get("convertedBy") or None,
            "nowOccupiedBy": h.get("nowOccupiedBy"),
        }
        rows.append({k: v for k, v in row.items() if v is not None})
    return rows


def past_sheet(rows, summaries, frame):
    """An SVG of ink paper with a hole per past lake and a faint dot per lake still there."""
    per_unit = M_PER_DEGREE / frame.scale
    w, h = frame.width, frame.height

    holes = []
    for row in rows:
        if "xy" not in row:
            continue
        radius_m = math.sqrt(row["acres"] * SQ_M_PER_ACRE / math.pi) if row.get("acres") else 0
        r = max(MIN_HOLE, radius_m * HOLE_WIDENING / per_unit)
        x, y = row["xy"]
        holes.append(f'<circle cx="{x:g}" cy="{y:g}" r="{r:.1f}"/>')

    dots = "".join(f"M{s['xy'][0]:g} {s['xy'][1]:g}h0" for s in summaries if s.get("status") == "exists" and s.get("xy"))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:g}" width="{w:g}" height="{h:g}">'
        f'<mask id="holes" maskUnits="userSpaceOnUse" x="0" y="0" width="{w:g}" height="{h:g}">'
        f'<rect width="{w:g}" height="{h:g}" fill="#fff"/><g fill="#000">{"".join(holes)}</g></mask>'
        f'<rect width="{w:g}" height="{h:g}" fill="{INK}" mask="url(#holes)"/>'
        f'<path d="{dots}" fill="none" stroke="{TABLE}" stroke-opacity="0.3" stroke-width="2.8" stroke-linecap="round"/>'
        "</svg>"
    )
