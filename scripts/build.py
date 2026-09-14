#!/usr/bin/env python3
"""
Build the site's lake data from the cleaned sources.

Steps:
  1. registry.py  decides the list of lakes and their permanent IDs
  2. joins.py     links every source record to a lake
  3. this file    assembles one record per lake and writes public/data/

Outputs (public/data/):
  lakes.json         one summary row per lake, for lists, search and stats
  lakes.geojson      outlines of every lake that has one, with a few map properties
  outside.geojson    the world with the two districts cut out, tinted on the map
  past.json          every lake that disappeared or was converted, lean rows for the Past Lakes page
  past-sheet.svg     the city as ink paper with a hole where each past lake was
  missing.json       every lake recorded as existing that no map draws, lean rows for the Missing Lakes page
  missing-sheet.svg  the city as dots: faint for lakes a map draws, a ring for each missing lake
  lake/<id>.json     the full record for one lake page
  sources.json       every source key: title, publisher, link, license, credit, dates
  hero.json          simplified outlines of existing lakes for the home page drawing
  openers.json       ids of lakes the opening screen may show
"""

import json
import shutil
import sys
from pathlib import Path

from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import joins  # noqa: E402
import registry  # noqa: E402
from assemble.context import Context  # noqa: E402
from assemble.hero import Frame, build_hero, frame_points  # noqa: E402
from assemble.missing import missing_rows, missing_sheet  # noqa: E402
from assemble.past import past_rows, past_sheet  # noqa: E402
from assemble.place import identity, location, responsibility, size  # noqa: E402
from assemble.sheet import build_sheet  # noqa: E402
from assemble.story import encroachment, history, links, nature, photos  # noqa: E402
from assemble.water import quality, water  # noqa: E402
from common import OUT, SOURCES  # noqa: E402

OPENER_MIN_ROOM_M = 40  # narrower than this and the name would be set on a sliver of water
OPENER_MIN_ROOM_SHARE = 0.15  # room width as a share of the lake's long side; below it the name sits on a sliver

SECTIONS = {
    "location": location,
    "size": size,
    "responsibility": responsibility,
    "water": water,
    "waterQuality": quality,
    "encroachment": encroachment,
    "nature": nature,
    "history": history,
    "links": links,
}


def record(ctx, lake_id):
    reg = ctx.registry[lake_id]
    empri = ctx.empri.get(reg["empriCode"]) if reg["empriCode"] else None
    atree = ctx.atree.get(reg["atreeFid"]) if reg["atreeFid"] else None
    rec = identity(ctx, lake_id, reg, empri, atree).done()
    for name, build_section in SECTIONS.items():
        section = build_section(ctx, lake_id, reg, empri, atree).done()
        if section:
            rec[name] = section
    pics = photos(ctx, lake_id)
    if pics:
        rec["photos"] = pics
    rec["events"] = []  # no source publishes these yet; filled from news and orders later
    feature = ctx.lakes.get(lake_id)
    if feature and feature["properties"]["hasOutline"]:
        sheet = build_sheet(feature["geometry"])
        if sheet:
            rec["sheet"] = sheet
    return rec


def summary(rec, frame):
    """The fields a list or map needs, without opening the lake file. `sizeRank` is added by the caller."""
    loc, size, water, resp, wq = (rec.get(k, {}) for k in ("location", "size", "water", "responsibility", "waterQuality"))
    latest = (wq.get("latest") or [{}])[0]
    point = loc.get("point")
    return {
        k: v
        for k, v in {
            "id": rec["id"],
            "name": rec["name"],
            "nameKannada": rec.get("nameKannada"),
            "status": rec.get("status"),
            "kind": rec.get("kind"),
            "point": loc.get("point"),
            "bbox": loc.get("bbox"),
            "hasOutline": loc.get("hasOutline", False),
            "acres": size.get("outlineAcres") or size.get("recordedAcres") or size.get("surveyed2018Acres"),
            "valley": water.get("valley"),
            "custodian": (resp.get("custodian") or {}).get("code"),
            "corporation": (loc.get("ward") or {}).get("corporation"),
            "ward": (loc.get("ward") or {}).get("name"),
            "waterClass": latest.get("class"),
            "waterClassMonth": latest.get("month"),
            "nowOccupiedBy": rec.get("history", {}).get("nowOccupiedBy"),
            "builtPct": rec.get("nature", {}).get("builtInsideOutlinePct"),
            "encroachedPct": rec.get("encroachment", {}).get("pct2018"),
            "campaign": bool(resp.get("campaignUrls") or resp.get("communityGroups")) or None,
            "photo": (rec.get("photos") or [{}])[0].get("thumb"),
            "yearBuilt": rec.get("history", {}).get("yearBuilt"),
            "xy": list(frame.project(point)) if point else None,
        }.items()
        if v is not None
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def build():
    registry.build()
    joins.build()
    ctx = Context()

    records = [record(ctx, lake_id) for lake_id in sorted(ctx.registry)]
    # One frame for the home drawing and every summary's xy, wide enough for the disappeared lakes too.
    frame = Frame(
        [p for f in ctx.lakes.values() for p in frame_points(f["geometry"])]
        + [r["location"]["point"] for r in records if r.get("location", {}).get("point")]
    )
    summaries = sorted((summary(r, frame) for r in records), key=lambda s: -(s.get("acres") or 0))
    rank = 0
    for s in summaries:
        if s.get("status") == "exists" and s.get("acres") is not None:
            rank += 1
            s["sizeRank"] = rank

    lake_dir = OUT / "lake"
    if lake_dir.exists():
        shutil.rmtree(lake_dir)
    for rec in records:
        write_json(lake_dir / f"{rec['id']}.json", rec)
    write_json(OUT / "lakes.json", summaries)

    by_id = {s["id"]: s for s in summaries}
    outlines = []
    for lake_id, f in ctx.lakes.items():
        s = by_id[lake_id]
        props = {k: s.get(k) for k in ("id", "name", "status", "acres", "valley", "custodian")}
        if f["properties"]["hasOutline"]:
            outlines.append({"type": "Feature", "id": lake_id, "properties": props, "geometry": f["geometry"]})
    write_json(OUT / "lakes.geojson", {"type": "FeatureCollection", "features": outlines})
    write_json(OUT / "city.geojson", city_boundary(ctx.wards))
    districts, district_sources = district_boundary()
    write_json(OUT / "districts.geojson", districts)
    write_json(OUT / "outside.geojson", outside_mask(districts))

    past = past_rows(records, summaries)
    write_json(OUT / "past.json", past)
    (OUT / "past-sheet.svg").write_text(past_sheet(past, summaries, frame), encoding="utf-8")

    missing = missing_rows(records, summaries)
    write_json(OUT / "missing.json", missing)
    (OUT / "missing-sheet.svg").write_text(missing_sheet(missing, summaries, frame), encoding="utf-8")
    print(f"missing: {len(missing)} lakes recorded as existing that no map draws")

    used = set()
    for rec in records:
        collect_sources(rec, used)
    # The satellite view and the district boundary on the map are credited without being facts in any record.
    used |= {"esri-world-imagery", *district_sources}
    write_json(OUT / "sources.json", {k: v for k, v in sorted(ctx.sources.items()) if k in used})

    existing = [(s["id"], s["name"], s.get("acres"), ctx.lakes[s["id"]]["geometry"]) for s in summaries if s.get("hasOutline") and s.get("status") == "exists"]
    write_json(OUT / "hero.json", build_hero(existing, frame))

    openers = [r["id"] for r in records if is_opener(r)]
    write_json(OUT / "openers.json", openers)
    print(f"openers: {len(openers)} lakes can open the site")

    report(records, used, ctx)


def is_opener(rec):
    sheet, room = rec.get("sheet"), rec.get("sheet", {}).get("room")
    if rec.get("status") != "exists" or not room or rec["name"].startswith("Unnamed"):
        return False
    return room["w"] >= OPENER_MIN_ROOM_M and room["w"] >= OPENER_MIN_ROOM_SHARE * max(sheet["w"], sheet["h"])


def city_boundary(wards):
    """The Greater Bengaluru limit: all 369 wards of the 2025 map merged, simplified to about 20 m."""
    city = unary_union([shape(w["geometry"]).buffer(0) for w in wards]).simplify(0.0002)
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "Greater Bengaluru", "source": "wards-gba-2025-369"}, "geometry": mapping(city)}],
    }


def district_boundary():
    """The outer edge of Bengaluru Urban and Bengaluru North (formerly Rural), simplified to about 30 m."""
    districts = json.loads((SOURCES / "districts.geojson").read_text(encoding="utf-8"))["features"]
    edge = unary_union([shape(d["geometry"]).buffer(0) for d in districts]).simplify(0.0003)
    keys = {d["properties"]["source"] for d in districts}
    collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Bengaluru Urban and Bengaluru North districts", "source": sorted(keys)[0]},
                "geometry": mapping(edge),
            }
        ],
    }
    return collection, keys


def outside_mask(districts):
    """Everything on the map except the two districts, so the map can tint it and keep Bengaluru in focus."""
    edge = unary_union([shape(f["geometry"]) for f in districts["features"]])
    world = box(-180, -85, 180, 85)
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": mapping(world.difference(edge))}]}


def collect_sources(node, used):
    """Every source key a record points at, so sources.json carries exactly those."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "src":
                for keys in v.values():
                    used.update(keys if isinstance(keys, list) else [keys])
            elif k == "source" and isinstance(v, str):
                used.add(v)
            else:
                collect_sources(v, used)
    elif isinstance(node, list):
        for v in node:
            collect_sources(v, used)


def report(records, used, ctx):
    def has(path):
        n = 0
        for r in records:
            node = r
            for part in path.split("."):
                node = node.get(part) if isinstance(node, dict) else None
            n += node is not False and node not in (None, [], {})
        return n

    statuses = {}
    for r in records:
        statuses[r.get("status")] = statuses.get(r.get("status"), 0) + 1
    print(f"build: {len(records)} lakes " + ", ".join(f"{v} {k}" for k, v in sorted(statuses.items(), key=str)))
    for path in (
        "nameKannada", "location.hasOutline", "location.ward", "location.surveyNumbers", "size.recordedAcres", "size.surveyed2018Acres",
        "responsibility.custodian", "responsibility.developmentStatus", "water.valley", "water.downstream", "water.presence", "water.current",
        "water.nearestTreatmentPlant", "waterQuality.latest", "encroachment.koliwadAcres", "encroachment.officialMaps", "nature.birds",
        "nature.observations", "nature.landAround", "history.yearBuilt", "history.nowOccupiedBy", "links.wikipedia", "photos", "sheet",
    ):
        print(f"  {path:34} {has(path)}")
    missing = used - set(ctx.sources) - {"per-entry"}
    if missing:
        print(f"  source keys with no citation: {sorted(missing)}")


if __name__ == "__main__":
    build()
