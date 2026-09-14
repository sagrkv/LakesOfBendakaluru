#!/usr/bin/env python3
"""
Link every source record to a lake in the registry.

Output: data/crosswalk.csv, one row per link:
  id, source, sourceId, method, distanceM, nameScore

Corrections: data/crosswalk_overrides.csv (id, source, sourceId, action) where action is
"add" to force a link or "remove" to drop one. Overrides are applied last, so a person's
correction always wins over the geometry.

Methods, strongest first:
  outline      the source's polygon overlaps the lake's outline
  inside       the source's point is inside the lake
  near         the point is within a short distance, and the name agrees where required
  survey       same village and land survey number as the lake's 2018 inventory record
  ward-name    same old ward, similar name (for lists that only give ward and name)
  area-name    no location, but a known area (the 1986 metropolitan area); accepted only when exactly one
               lake in that area has that name and no other record of the source claims the lake
  unique-name  no location at all; accepted only when exactly one lake has that name
"""

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, SOURCES, name_key, read_csv, write_csv  # noqa: E402
from match import LakeIndex, feature_utm, to_utm, utm_point  # noqa: E402

CROSSWALK = ROOT / "data" / "crosswalk.csv"
OVERRIDES = ROOT / "data" / "crosswalk_overrides.csv"
COLUMNS = ["id", "source", "sourceId", "method", "distanceM", "nameScore"]

# The 1986 Bangalore Metropolitan Area (the conurbation and its green belt, about 1,279 km2 in the 1984
# plan) has no digital boundary. Its green belt list reaches Hoskote, Devanahalli, Magadi and Nelamangala
# taluks, so lakes within 25 km of Vidhana Soudha stand in for it.
RAU_CENTRE = (77.5906, 12.9796)
RAU_RADIUS_M = 25_000
# A printed name that only describes a place ("Tank east of Haralur") is not a name.
RAU_DESCRIPTIVE = re.compile(r"\b(east|west|north|south|near|between|adjoining)\b", re.I)


def lake_index():
    """Index of all registry lakes; a point lake is a circle of its recorded size."""
    features = json.loads((ROOT / "data" / "lakes.geojson").read_text())["features"]
    entries = []
    for f in features:
        p = f["properties"]
        geom = feature_utm(f)
        if not p["hasOutline"]:
            acres = p.get("recordedAcres") or 0.5
            geom = geom.buffer(max(15.0, math.sqrt(acres * 4046.86 / math.pi)))
        entries.append((p["id"], p.get("names") or [p["name"]], geom))
    return LakeIndex(entries), {f["properties"]["id"]: f for f in features}


def rows(file):
    path = SOURCES / file
    return read_csv(path) if path.exists() else []


def features(file):
    path = SOURCES / file
    return json.loads(path.read_text())["features"] if path.exists() else []


def has_point(row):
    try:
        float(row["lat"]), float(row["lon"])
        return True
    except (TypeError, ValueError, KeyError):
        return False


class Linker:
    def __init__(self):
        self.links = []

    def add(self, lake_id, source, source_id, method, distance=None, score=None):
        self.links.append(
            {"id": lake_id, "source": source, "sourceId": str(source_id), "method": method, "distanceM": distance, "nameScore": score}
        )


def link_polygons(linker, index, feats, source, id_prop, min_share=0.3):
    """Each source polygon goes to the lake it overlaps most; each lake keeps its best polygon."""
    best_for_lake = {}
    for f in feats:
        if not f.get("geometry"):
            continue
        geom = feature_utm(f)
        if geom.is_empty:
            continue
        m = index.match_polygon(geom, min_share=min_share)
        if not m:
            continue
        lake_id, share = m
        sid = f["properties"][id_prop]
        if lake_id not in best_for_lake or share > best_for_lake[lake_id][1]:
            best_for_lake[lake_id] = (sid, share)
    for lake_id, (sid, share) in best_for_lake.items():
        linker.add(lake_id, source, sid, "outline", None, share)


def link_points(linker, index, records, source, id_col, name_col=None, within_m=150, name_floor=0.4, one_per_lake=False, name_weight=100):
    """
    Points match the lake they fall in, or a nearby lake whose name agrees.
    With one_per_lake, a lake keeps only its closest record (for sources that describe the
    same lake once, like the Water Bodies Census); otherwise a lake can have several (stations).
    """
    chosen = {}
    for r in records:
        if not has_point(r):
            continue
        name = r.get(name_col) if name_col else None
        m = index.match_point(r["lon"], r["lat"], name, within_m=within_m, name_floor=name_floor if name else 0.0, name_weight=name_weight)
        if not m:
            continue
        lake_id, d, score = m
        if d > 30 and name and score < name_floor:
            continue
        if one_per_lake:
            if lake_id in chosen and chosen[lake_id][1] <= d:
                continue
            chosen[lake_id] = (r[id_col], d, score)
        else:
            linker.add(lake_id, source, r[id_col], "inside" if d == 0 else "near", d, score if name else None)
    for lake_id, (sid, d, score) in chosen.items():
        linker.add(lake_id, source, sid, "inside" if d == 0 else "near", d, score if name_col else None)


def survey_keys(village, surveys):
    """(village key, survey number) pairs. Survey text like '59 (Mattikere)' names its own village."""
    keys = set()
    for s in (surveys or "").split(";"):
        s = s.strip()
        if not s:
            continue
        own_village = village
        if "(" in s:
            s, own_village = s.split("(", 1)
            own_village = own_village.rstrip(")")
        number = s.strip().split("/")[0].strip().lower()
        if number and own_village:
            keys.add((name_key(own_village), number))
    return keys


def link_by_survey(linker, survey_index, records, source, id_col, village_col, survey_col):
    for r in records:
        hits = set()
        for key in survey_keys(r.get(village_col), r.get(survey_col)):
            hits |= survey_index.get(key, set())
        if len(hits) == 1:
            linker.add(next(iter(hits)), source, r[id_col], "survey")


def link_historic_tests(linker, index, station_lake):
    """Older test sets: by KSPCB station code, else by location, else by a unique name."""
    stations = {}
    for r in rows("wq_historic.csv"):
        stations.setdefault(f"{r['dataset']}:{r['stationId']}", r)
    for sid, r in stations.items():
        if r.get("stationCode") in station_lake:
            linker.add(station_lake[r["stationCode"]], "wq_historic", sid, "station-code")
            continue
        if has_point(r):
            m = index.match_point(r["lon"], r["lat"], r["stationName"], within_m=300, name_floor=0.4)
            if m:
                linker.add(m[0], "wq_historic", sid, "inside" if m[1] == 0 else "near", m[1], m[2])
                continue
        lake_id = index.match_unique_name(r["stationName"])
        if lake_id:
            linker.add(lake_id, "wq_historic", sid, "unique-name")


def word_key(name):
    """name_key word by word, sorted, so "Amanikere, Belandur" and "Bellandur Amanikere" agree."""
    return "".join(sorted(k for k in (name_key(w) for w in re.split(r"[\s,.&-]+", name or "")) if k))


def rau_name_keys(printed):
    """Keys for a tank name as printed in 1986: "A or B/C" gives three, a place note in brackets is dropped."""
    if not printed or RAU_DESCRIPTIVE.search(printed):
        return set()
    bare = re.sub(r"\(.*?\)|\(.*$", " ", printed)
    return {k for k in (word_key(part) for part in re.split(r"\bor\b|/", bare)) if k}


def link_rau1986(linker, index):
    """
    The 1986 Lakshman Rau lists give a tank's name and no location. Candidates are the lakes in the
    metropolitan area the report covers; a row links only when exactly one candidate has its name key,
    and only when no other row of the report points at the same lake.
    """
    area = utm_point(*RAU_CENTRE).buffer(RAU_RADIUS_M)
    lakes_by_key = defaultdict(set)
    for i in index.tree.query(area, predicate="intersects"):
        for name in index.aliases[i]:
            if word_key(name):
                lakes_by_key[word_key(name)].add(index.keys[i])
    claims = defaultdict(list)
    for r in rows("rau1986.csv"):
        found = {next(iter(lakes_by_key[k])) for k in rau_name_keys(r["name"]) if len(lakes_by_key.get(k, ())) == 1}
        if len(found) == 1:
            claims[found.pop()].append(r["rauId"])
    for lake_id, rau_ids in claims.items():
        if len(rau_ids) == 1:
            linker.add(lake_id, "rau1986", rau_ids[0], "area-name")


def build():
    index, lakes = lake_index()
    registry = {r["id"]: r for r in read_csv(ROOT / "data" / "registry.csv")}
    linker = Linker()

    # 2018 inventory and ATREE come from the registry pairing itself.
    for lake_id, r in registry.items():
        if r["atreeFid"]:
            linker.add(lake_id, "atree", r["atreeFid"], "outline")
        if r["empriCode"]:
            linker.add(lake_id, "empri2018", r["empriCode"], r["pairMethod"] or "anchor", r["pairDistanceM"], r["pairNameScore"])

    # Village + survey number, from each lake's 2018 inventory record.
    empri = {r["empriCode"]: r for r in rows("empri2018.csv")}
    survey_index = defaultdict(set)
    for lake_id, r in registry.items():
        e = empri.get(r["empriCode"])
        if e:
            for key in survey_keys(e["village"], e["surveyNumbers"]):
                survey_index[key].add(lake_id)

    link_polygons(linker, index, features("osm_water.geojson"), "osm", "osmId")
    # OSM names become aliases, so the name checks below see every name a lake goes by.
    osm_names = {f["properties"]["osmId"]: f["properties"] for f in features("osm_water.geojson")}
    for l in linker.links:
        if l["source"] == "osm":
            o = osm_names[l["sourceId"]]
            index.add_aliases(l["id"], [o.get("name"), *(o.get("altNames") or "").split(";")])
    link_polygons(linker, index, features("kgis_tanks.geojson"), "kgis_tanks", "kgisTankId")
    link_polygons(linker, index, features("kgis_ponds.geojson"), "kgis_ponds", "kgisPondId", min_share=0.5)
    link_polygons(linker, index, features("kgis_wetlands.geojson"), "kgis_wetlands", "kgisWetlandId", min_share=0.5)

    link_points(linker, index, rows("wikidata.csv"), "wikidata", "qid", "labelEn", within_m=300, name_floor=0.5, one_per_lake=True)
    link_points(linker, index, rows("bbmp_lms.csv"), "bbmp_lms", "bbmpLmsId", "name", within_m=200, name_floor=0.4, one_per_lake=True)
    link_points(linker, index, rows("wbc2018.csv"), "wbc2018", "wbcId", None, within_m=100, one_per_lake=True)
    # Station coordinates are rough, so a matching name within 1 km beats a point that lands in the lake next door.
    link_points(linker, index, rows("kspcb_stations.csv"), "kspcb", "stationId", "lakeName", within_m=1000, name_floor=0.5, name_weight=1000)

    # Stations that matched no lake by location (no coordinates, or coordinates KSPCB
    # printed far from the lake) fall back to a unique name.
    linked_stations = {l["sourceId"] for l in linker.links if l["source"] == "kspcb"}
    for r in rows("kspcb_stations.csv"):
        if r["stationId"] not in linked_stations:
            lake_id = index.match_unique_name(r["lakeName"])
            if lake_id:
                linker.add(lake_id, "kspcb", r["stationId"], "unique-name")
    station_lake = {l["sourceId"]: l["id"] for l in linker.links if l["source"] == "kspcb"}
    link_historic_tests(linker, index, station_lake)

    custody = rows("bbmp_custody.csv")
    for r in custody:
        r["_id"] = f"{r['slNo']}-{r['parcelIndex']}"
    link_by_survey(linker, survey_index, custody, "bbmp_custody", "_id", "village", "surveyNumbers")
    link_by_survey(linker, survey_index, rows("landrecords_lakes_digital.csv"), "landrecords_digital", "mapId", "village", "surveyNumbers")
    link_by_survey(linker, survey_index, rows("landrecords_lakes_survey.csv"), "landrecords_survey", "mapId", "village", "surveyNumbers")

    # Lists that give only a lake name and an old ward: search lakes in or near that ward.
    wards_2010 = {f["properties"]["wardNumber"]: to_utm(shape(f["geometry"])).buffer(500) for f in features("wards_2010_198.geojson")}
    for r in rows("ktcda_custodians.csv"):
        best = None
        for w in (r.get("wardNumbers") or "").split(";"):
            area = wards_2010.get(int(w)) if w.strip().isdigit() else None
            if area is None:
                continue
            for i in index.tree.query(area, predicate="intersects"):
                score = index.name_score(i, r["lakeName"])
                if score >= 0.6 and (best is None or score > best[1]):
                    best = (index.keys[i], score)
        if best:
            linker.add(best[0], "ktcda", r["slNo"] + "-" + r["custodian"], "ward-name", None, round(best[1], 2))
        else:
            lake_id = index.match_unique_name(r["lakeName"])
            if lake_id:
                linker.add(lake_id, "ktcda", r["slNo"] + "-" + r["custodian"], "unique-name")

    # Minor Irrigation tanks and citizen groups carry names only.
    for r in rows("mi_tanks.csv"):
        lake_id = index.match_unique_name(r["name"])
        if lake_id:
            linker.add(lake_id, "mi_tanks", r["miTankId"], "unique-name")
    for n, r in enumerate(rows("lake_groups.csv")):
        for lake_name in (r.get("lakes") or "").split(";"):
            lake_id = index.match_unique_name(lake_name)
            if lake_id:
                linker.add(lake_id, "lake_groups", n, "unique-name")

    link_rau1986(linker, index)

    links = apply_overrides(linker.links)
    links.sort(key=lambda l: (l["id"], l["source"], l["sourceId"]))
    write_csv(CROSSWALK, links, COLUMNS)

    counts = defaultdict(int)
    for l in links:
        counts[l["source"]] += 1
    print("joins: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))


def apply_overrides(links):
    if not OVERRIDES.exists():
        return links
    overrides = read_csv(OVERRIDES)
    removed = {(o["source"], o["sourceId"]) for o in overrides if o["action"] == "remove"}
    removed |= {(o["source"], o["sourceId"]) for o in overrides if o["action"] == "add"}  # re-homed below
    kept = [l for l in links if (l["source"], l["sourceId"]) not in removed]
    for o in overrides:
        if o["action"] == "add":
            kept.append({"id": o["id"], "source": o["source"], "sourceId": o["sourceId"], "method": "manual", "distanceM": None, "nameScore": None})
    return kept


if __name__ == "__main__":
    build()
