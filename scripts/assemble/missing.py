"""
The Missing Lakes page: lakes recorded as existing that no map we have draws.

Every one is a 2018 inventory lake with a location but no outline from ATREE, KGIS or OpenStreetMap.
missing.json holds one lean row per lake, only what the page shows or filters by.
missing-sheet.svg is the city drawn as dots: a faint dot for each lake a map draws, a ring for each missing one.
"""

from .past import MAP_YEARS

KTCDA_2024 = "ktcda-lakes-2024"
INK = "#1B1A17"
RING_R = 6  # frame units; the frame is 1000 wide, so a ring is about 5 px across on a laptop


def is_missing(rec):
    loc = rec.get("location", {})
    return rec.get("status") == "exists" and not loc.get("hasOutline") and bool(loc.get("point"))


def missing_rows(records, summaries):
    """Largest first by the 2018 extent. Unknown facts are left out."""
    by_id = {r["id"]: r for r in records}
    rows = []
    for s in summaries:
        rec = by_id[s["id"]]
        if not is_missing(rec):
            continue
        loc, water, resp, h = (rec.get(k, {}) for k in ("location", "water", "responsibility", "history"))
        ward = loc.get("ward") or {}
        seen = [y for y in ((water.get("presence") or {}).get("lastYear"), h.get("lastSeenWithWater")) if y]
        row = {
            "id": rec["id"],
            "name": rec["name"],
            "nameKannada": rec.get("nameKannada"),
            "kind": rec.get("kind"),
            "acres": rec.get("size", {}).get("surveyed2018Acres"),
            "village": loc.get("village"),
            "taluk": loc.get("taluk"),
            "ward": ward.get("name"),
            "custodian": (resp.get("custodian") or {}).get("name"),
            "condition2018": water.get("conditionIn2018") or None,
            "uses2018": water.get("uses") or None,
            "onList2024": (resp.get("src") or {}).get("custodian") == KTCDA_2024 or None,
            "monitoringPage": resp.get("monitoringPage"),
            "waterSeen": int(max(seen)) if seen else None,
            "onMap": [year for year in MAP_YEARS if h.get(f"onMap{year}")] or None,
            "xy": s.get("xy"),
        }
        rows.append({k: v for k, v in row.items() if v is not None})
    return sorted(rows, key=lambda row: -(row.get("acres") or 0))


def missing_sheet(rows, summaries, frame):
    """An SVG on a clear ground: faint dots for drawn lakes, an ink ring for each missing one."""
    w, h = frame.width, frame.height
    drawn = "".join(
        f"M{s['xy'][0]:g} {s['xy'][1]:g}h0" for s in summaries if s.get("status") == "exists" and s.get("hasOutline") and s.get("xy")
    )
    rings = "".join(f'<circle cx="{row["xy"][0]:g}" cy="{row["xy"][1]:g}" r="{RING_R}"/>' for row in rows if row.get("xy"))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:g}" width="{w:g}" height="{h:g}">'
        f'<path d="{drawn}" fill="none" stroke="{INK}" stroke-opacity="0.22" stroke-width="4" stroke-linecap="round"/>'
        f'<g fill="none" stroke="{INK}" stroke-width="2.2">{rings}</g>'
        "</svg>"
    )
