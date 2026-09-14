"""
Tanks drawn on old survey maps that no current source knows, not even as disappeared.

A traced water body from data/sources/historic_water.geojson becomes a lake when:
  - the map traced it with high or medium confidence
  - it lies in the study area
  - no lake already in the list (an ATREE outline or a 2018 inventory point) is within 250 m
  - no water polygon on today's maps (OpenStreetMap, KGIS tanks and ponds) is within 100 m,
    because a tank that still holds water is a gap in our list, not a lost lake
The same tank traced on several maps is kept once, from the oldest map.

This reads the traced shapes directly, never historic_lost.csv: that file is computed
against the lake list itself, so reading it here would loop.
"""

import json
import math

from shapely.geometry import Point, shape

from common import SOURCES, read_csv
from match import LakeIndex, feature_utm, to_utm, utm_point

LAKE_CLEAR_M = 250
WATER_CLEAR_M = 100
SAME_TANK_M = 250
AREA = (77.18, 12.65, 77.96, 13.48)


def _features(file):
    path = SOURCES / file
    return json.loads(path.read_text())["features"] if path.exists() else []


def place_names():
    """Ward names inside the city; outside it, OpenStreetMap villages and 2018 inventory villages."""
    wards = [(shape(f["geometry"]), f["properties"]["wardName"]) for f in _features("wards_2025_gba_369.geojson")]
    places = []
    for file, name_col in (("osm_places.csv", "name"), ("empri2018.csv", "village")):
        path = SOURCES / file
        for r in read_csv(path) if path.exists() else []:
            try:
                places.append((utm_point(r["lon"], r["lat"]), r[name_col]))
            except (TypeError, ValueError):
                pass
    return wards, places


def place_near(lon, lat, wards, places):
    pt = Point(lon, lat)
    for geom, name in wards:
        if geom.contains(pt):
            return name
    p = utm_point(lon, lat)
    best = min(((p.distance(v), name) for v, name in places if name), default=None)
    return best[1] if best and best[0] <= 3000 else None


def historic_lakes(lakes):
    """lakes: entries already in the list, each with a lon/lat `geometry` or `point`. Returns new entries."""
    known = []
    for lake in lakes:
        if lake.get("geometry"):
            known.append((lake["anchor"], "", to_utm(shape(lake["geometry"]))))
        elif lake.get("point"):
            known.append((lake["anchor"], "", utm_point(*lake["point"]).buffer(max(15.0, math.sqrt((lake.get("recordedAcres") or 0.5) * 4046.86 / math.pi)))))
    known_index = LakeIndex(known)
    water = [(f["properties"].get("osmId") or f["properties"].get("kgisTankId") or f["properties"].get("kgisPondId"), "", feature_utm(f)) for file in ("osm_water.geojson", "kgis_tanks.geojson", "kgis_ponds.geojson") for f in _features(file)]
    water_index = LakeIndex(water)
    wards, places = place_names()

    traced = [f for f in _features("historic_water.geojson") if f["properties"]["confidence"] in ("high", "medium")]
    traced.sort(key=lambda f: (f["properties"]["year"], f["properties"]["histId"]))
    added = []  # (utm point, entry)
    for f in traced:
        p = f["properties"]
        point = shape(f["geometry"]).representative_point()
        if not (AREA[0] <= point.x <= AREA[2] and AREA[1] <= point.y <= AREA[3]):
            continue
        u = utm_point(point.x, point.y)
        if known_index.near(u, LAKE_CLEAR_M) or water_index.near(u, WATER_CLEAR_M):
            continue
        if any(q.distance(u) <= SAME_TANK_M for q, _ in added):
            continue  # the same tank, already taken from an older map
        place = place_near(point.x, point.y, wards, places)
        added.append(
            (
                u,
                {
                    "anchor": f"hist:{p['histId']}",
                    "name": f"Unnamed tank near {place}" if place else "Unnamed tank",
                    "atreeFid": None,
                    "empriCode": None,
                    "histId": p["histId"],
                    "outlineSource": None,
                    "outlineId": None,
                    "pairMethod": "historic-map",
                    "pairDistanceM": None,
                    "pairNameScore": None,
                    "geometry": None,
                    "point": (round(point.x, 6), round(point.y, 6)),
                    "recordedAcres": None,
                    "historicAcres": round(p["areaM2"] / 4046.86, 2),
                    "names": [],
                },
            )
        )
    return [e for _, e in added]
