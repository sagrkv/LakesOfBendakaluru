#!/usr/bin/env python3
"""
Decide the list of lakes and give each one a permanent ID.

A lake enters the list from one of these anchors:
  atree:<fid>     an outline in the ATREE lake map (lakes that exist today)
  empri:<code>    a water body in the 2018 state inventory that is not one of those outlines,
                  including the 838 that have disappeared
  hist:<id>       a tank on a 1927-1955 survey map that no current source knows (historic_lakes.py)

2018 inventory rows are paired with ATREE outlines one-to-one by location, with the name
breaking ties. A row left unpaired becomes its own lake; if it sits inside an unclaimed
KGIS or OpenStreetMap water polygon, that polygon becomes its outline.

IDs are stored in data/registry.csv and never change once assigned. The build reads
the registry back, keeps every existing ID, and only mints new ones for new anchors.
A row marked reviewed=yes keeps its pairing even if the geometry would now say otherwise.

Outputs:
  data/registry.csv     id, anchor, paired source IDs, how they were paired
  data/lakes.geojson    every lake as an outline or a point, the input for per-lake stats
"""

import json
import re
import sys
from pathlib import Path

from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, SOURCES, clean, read_csv, slugify, write_csv  # noqa: E402
from historic_lakes import historic_lakes  # noqa: E402
from match import LakeIndex, feature_utm, utm_point  # noqa: E402

REGISTRY = ROOT / "data" / "registry.csv"
LAKES = ROOT / "data" / "lakes.geojson"
COLUMNS = ["id", "anchor", "atreeFid", "empriCode", "histId", "outlineSource", "outlineId", "pairMethod", "pairDistanceM", "pairNameScore", "reviewed"]

# Study area: Bengaluru Urban and Rural districts, a little padded.
LON_RANGE, LAT_RANGE = (77.0, 78.1), (12.5, 13.7)
PAIR_WITHIN_M = 150
NAME_PAIR_WITHIN_M = 1000


def in_area(lon, lat):
    return LON_RANGE[0] <= lon <= LON_RANGE[1] and LAT_RANGE[0] <= lat <= LAT_RANGE[1]


def point_of(row):
    try:
        lon, lat = float(row["lon"]), float(row["lat"])
    except (TypeError, ValueError):
        return None
    return (lon, lat) if in_area(lon, lat) else None


def nice_name(name):
    """ATREE writes "Jogi kere"; make generic words title case without touching real casing."""
    if not name:
        return name
    return " ".join(w[:1].upper() + w[1:] if w.islower() else w for w in name.split())


def load_features(file, key):
    path = SOURCES / file
    if not path.exists():
        return []
    return [(f["properties"][key], f) for f in json.loads(path.read_text())["features"]]


def pair_empri(atree_index, empri_rows, reviewed):
    """
    One-to-one pairing between 2018 inventory rows and ATREE outlines.
    Candidates are ranked by distance (inside = 0) minus a name bonus; the best
    pairs are taken greedily so no outline or row is used twice.
    """
    candidates = []
    for row in empri_rows:
        pt = point_of(row)
        if pt is None or row["empriCode"] in reviewed:
            continue
        p = utm_point(*pt)
        gone = row.get("status") == "disappeared"
        for i, d in atree_index.near(p, NAME_PAIR_WITHIN_M):
            score = max(atree_index.name_score(i, row["name"]), atree_index.name_score(i, row.get("nameOther")) if row.get("nameOther") else 0.0)
            if d > PAIR_WITHIN_M:
                # Coordinates in the inventory are sometimes a few hundred metres off.
                # Farther out, only a near-identical name counts, and never for a lake
                # that is gone: its name usually belongs to the surviving lake next door.
                if score < 0.85 or gone:
                    continue
                method = "name-near"
            elif d > 30 and score < 0.5:
                continue  # close but differently named: likely a neighbouring pond
            else:
                method = "inside" if d == 0 else "near"
            if gone and score < 0.6:
                continue
            candidates.append((d - 100 * score, row["empriCode"], atree_index.keys[i], method, round(d), round(score, 2)))
    candidates.sort()

    pairs = dict(reviewed)  # empriCode -> (atreeFid, method, distance, score)
    used_fids = {v[0] for v in reviewed.values() if v[0] is not None}
    for _, code, fid, method, d, score in candidates:
        if code in pairs or fid in used_fids:
            continue
        pairs[code] = (fid, method, d, score)
        used_fids.add(fid)
    return pairs


def wikipedia_names(atree_index):
    """
    A lake with an English Wikipedia article goes by the article's name: people search
    "Bellandur Lake", not the survey name "Bellandur Amanikere".
    """
    path = SOURCES / "wikidata.csv"
    names = {}
    for row in read_csv(path) if path.exists() else []:
        if not row.get("enwiki") or not point_of(row):
            continue
        m = atree_index.match_point(row["lon"], row["lat"], row["labelEn"], within_m=300, name_floor=0.5)
        if m and (m[1] == 0 or m[2] >= 0.5):
            title = re.sub(r"\s*\(.*?\)|,\s*Bengaluru$|,\s*Bangalore$", "", row["enwiki"]).strip()
            names.setdefault(m[0], nice_name(title))
    return names


def build():
    previous = {r["anchor"]: r for r in read_csv(REGISTRY)} if REGISTRY.exists() else {}
    reviewed = {
        r["empriCode"]: (int(r["atreeFid"]) if r["atreeFid"] else None, r["pairMethod"], r["pairDistanceM"], r["pairNameScore"])
        for r in previous.values()
        if r.get("reviewed") == "yes" and r.get("empriCode")
    }

    atree = load_features("atree.geojson", "atreeFid")
    atree_index = LakeIndex([(fid, [f["properties"]["name"], f["properties"]["nameAlt"]], feature_utm(f)) for fid, f in atree])
    empri = [r for r in read_csv(SOURCES / "empri2018.csv") if r.get("empriCode")] if (SOURCES / "empri2018.csv").exists() else []
    pairs = pair_empri(atree_index, empri, reviewed)
    empri_by_fid = {v[0]: (code, v) for code, v in pairs.items() if v[0] is not None}
    empri_names = {r["empriCode"]: clean(r["name"]) for r in empri}
    empri_other = {r["empriCode"]: clean(r.get("nameOther")) for r in empri}

    popular = wikipedia_names(atree_index)
    lakes = []

    for fid, f in atree:
        code, pair = empri_by_fid.get(fid, (None, None))
        lakes.append(
            {
                "anchor": f"atree:{fid}",
                "name": popular.get(fid) or nice_name(f["properties"]["name"] or empri_names.get(code)) or "Unnamed lake",
                "atreeFid": fid,
                "empriCode": code,
                "outlineSource": "atree",
                "outlineId": fid,
                "pairMethod": pair[1] if pair else None,
                "pairDistanceM": pair[2] if pair else None,
                "pairNameScore": pair[3] if pair else None,
                "geometry": f["geometry"],
                "names": [f["properties"]["name"], f["properties"]["nameAlt"], empri_names.get(code), empri_other.get(code)],
            }
        )

    # Unpaired inventory rows: take an outline from KGIS or OSM if the point falls inside
    # a water polygon that no ATREE lake already overlaps.
    outline_pool = []
    for file, key, label in [("kgis_tanks.geojson", "kgisTankId", "kgis-tank"), ("kgis_ponds.geojson", "kgisPondId", "kgis-pond"), ("osm_water.geojson", "osmId", "osm")]:
        for fid, f in load_features(file, key):
            outline_pool.append((f"{label}:{fid}", f))
    pool_index = LakeIndex([(k, "", feature_utm(f)) for k, f in outline_pool])
    pool_by_key = dict(outline_pool)
    claimed = set()

    for row in empri:
        code = row["empriCode"]
        if code in pairs and pairs[code][0] is not None:
            continue
        pt = point_of(row)
        acres = float(row["extentAcres"]) if row.get("extentAcres") else None
        entry = {
            "anchor": f"empri:{code}",
            "name": nice_name(clean(row["name"])) or f"Unnamed {row.get('kind') or 'water body'}, {row.get('village')}",
            "atreeFid": None,
            "empriCode": code,
            "outlineSource": None,
            "outlineId": None,
            "pairMethod": "unpaired",
            "pairDistanceM": None,
            "pairNameScore": None,
            "geometry": None,
            "point": pt,
            "recordedAcres": acres,
            "names": [clean(row["name"]), clean(row.get("nameOther"))],
        }
        if pt and row.get("status") != "disappeared":
            p = utm_point(*pt)
            for i in pool_index.tree.query(p, predicate="intersects"):
                key = pool_index.keys[i]
                geom = pool_index.geoms[i]
                if key in claimed or geom.area > 4046.86 * 2000:
                    continue
                if atree_index.match_polygon(geom, min_share=0.2):
                    continue
                claimed.add(key)
                entry["outlineSource"], entry["outlineId"] = key.split(":", 1)
                entry["geometry"] = pool_by_key[key]["geometry"]
                break
        lakes.append(entry)

    lakes += historic_lakes(lakes)
    assign_ids(lakes, previous)
    write_outputs(lakes, previous)


def assign_ids(lakes, previous):
    """Keep every ID already in the registry; mint slugs for new anchors, suffixing repeats."""
    taken = set()
    for lake in lakes:
        old = previous.get(lake["anchor"])
        if old:
            lake["id"] = old["id"]
            taken.add(old["id"])
    for lake in sorted((l for l in lakes if "id" not in l), key=lambda l: (l["anchor"].split(":")[0] != "atree", l["anchor"].startswith("hist"), l["name"])):
        base = slugify(lake["name"])
        slug, n = base, 2
        while slug in taken:
            slug, n = f"{base}-{n}", n + 1
        lake["id"] = slug
        taken.add(slug)


def write_outputs(lakes, previous):
    rows = [{c: lake.get(c) for c in COLUMNS if c != "reviewed"} | {"reviewed": None} for lake in lakes]
    for row in rows:
        if previous.get(row["anchor"], {}).get("reviewed") == "yes":
            row["reviewed"] = "yes"
    rows.sort(key=lambda r: r["id"])
    write_csv(REGISTRY, rows, COLUMNS)

    features = []
    for lake in lakes:
        if lake["geometry"]:
            geom = lake["geometry"]
            point = shape(geom).representative_point()
            props = {"hasOutline": True}
        elif lake.get("point"):
            lon, lat = lake["point"]
            geom = {"type": "Point", "coordinates": [lon, lat]}
            point = shape(geom)
            props = {"hasOutline": False}
        else:
            continue  # no location at all; still in the registry, not on the map
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": lake["id"],
                    "name": lake["name"],
                    "names": list(dict.fromkeys(n for n in [lake["name"], *lake.get("names", [])] if n)),
                    "atreeFid": lake["atreeFid"],
                    "empriCode": lake["empriCode"],
                    "histId": lake.get("histId"),
                    "recordedAcres": lake.get("recordedAcres"),
                    # Per-lake stat scripts size a point lake's circle from this.
                    "areaM2": round((lake.get("recordedAcres") or lake.get("historicAcres") or 0) * 4046.86) or None,
                    "labelPoint": [round(point.x, 6), round(point.y, 6)],
                    **props,
                },
                "geometry": geom,
            }
        )
    features.sort(key=lambda f: f["properties"]["id"])
    LAKES.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    with_outline = sum(1 for f in features if f["properties"]["hasOutline"])
    print(f"registry: {len(rows)} lakes, {with_outline} with outline, {len(features) - with_outline} as points, {len(rows) - len(features)} without location")


if __name__ == "__main__":
    build()
