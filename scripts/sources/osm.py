#!/usr/bin/env python3
"""
OpenStreetMap water areas and lake-related features for the ATREE extent, from Overpass.

Every water area is kept with its full geometry and tags. Nothing is matched to lakes here;
the build matches by overlap with our outlines, never by name.

Downloads: data/cache/osm/{water,features}.json (Overpass responses, reused on rerun;
delete them to pull fresh data).
Output:
  data/sources/osm_water.geojson     natural=water, landuse=reservoir|basin, natural=wetland
  data/sources/osm_features.geojson  wastewater treatment plants, lakeside parks
"""

import json
import re
import sys
import time
from pathlib import Path

import requests
from pyproj import Geod
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, mapping
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, SOURCES, clean, write_sources  # noqa: E402

BBOX = (12.65, 77.18, 13.48, 77.96)  # south, west, north, east
OVERPASS = "https://overpass-api.de/api/interpreter"
USER_AGENT = "LakesOfBendakaluru/1.0 (https://filtercoffee.dev; open data project)"
GEOD = Geod(ellps="WGS84")
DIR = CACHE / "osm"

# The bbox is a per-statement filter, not a global setting, so geometry of features that
# cross the edge is not clipped.
WATER_QUERY = """
[out:json][timeout:600];
(
  way["natural"="water"]({b});
  relation["natural"="water"]["type"="multipolygon"]({b});
  way["water"]({b});
  relation["water"]["type"="multipolygon"]({b});
  way["landuse"~"^(reservoir|basin)$"]({b});
  relation["landuse"~"^(reservoir|basin)$"]["type"="multipolygon"]({b});
  way["natural"="wetland"]({b});
  relation["natural"="wetland"]["type"="multipolygon"]({b});
);
out body geom;
"""

FEATURES_QUERY = """
[out:json][timeout:300];
(
  nwr["man_made"="wastewater_plant"]({b});
  nwr["leisure"="park"]["name"~"lake|kere|kunte|katte",i]({b});
);
out body geom;
"""


def overpass(name, query):
    path = DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    DIR.mkdir(parents=True, exist_ok=True)
    body = query.format(b=",".join(map(str, BBOX)))
    for attempt in range(5):
        response = requests.post(OVERPASS, data={"data": body}, headers={"User-Agent": USER_AGENT}, timeout=900)
        if response.status_code in (429, 504):
            time.sleep(60 * (attempt + 1))
            continue
        response.raise_for_status()
        data = response.json()
        if data.get("remark") and "error" in data["remark"].lower():
            raise RuntimeError(f"overpass {name}: {data['remark']}")
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
    raise RuntimeError(f"overpass {name}: gave up after repeated rate limiting")


def areas_only(shape):
    """make_valid can return collections with stray lines; keep the polygon parts."""
    if shape.is_empty:
        return None
    if shape.geom_type in ("Polygon", "MultiPolygon"):
        return shape
    polygons = [p for g in getattr(shape, "geoms", []) for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon"]
    return MultiPolygon(polygons) if polygons else None


def coords(points):
    return [(p["lon"], p["lat"]) for p in points]


def way_shape(element):
    """A closed way is an area; an open way on its own is not."""
    points = coords(element.get("geometry") or [])
    if len(points) < 4 or points[0] != points[-1]:
        return None
    return areas_only(make_valid(Polygon(points)))


def relation_shape(element):
    """
    Join member ways into rings and fill them by the even-odd rule.

    polygonize splits the plane into faces bounded by the member ways. A face is water when it lies
    inside an odd number of rings: lake (1) in, island (2) out, pond on the island (3) in.
    This does not trust the outer/inner roles, which are often wrong in practice.
    """
    lines = []
    for member in element.get("members", []):
        if member.get("type") != "way" or not member.get("geometry"):
            continue
        points = coords(member["geometry"])
        if len(points) >= 2:
            lines.append(LineString(points))
    if not lines:
        return None
    noded = unary_union(lines)
    faces = list(polygonize(getattr(noded, "geoms", [noded])))
    if not faces:
        return None
    exteriors = [Polygon(face.exterior) for face in faces]
    water = []
    for face in faces:
        inside = face.representative_point()
        depth = sum(1 for ring in exteriors if ring.contains(inside))
        if depth % 2 == 1:
            water.append(face)
    return areas_only(make_valid(unary_union(water))) if water else None


def point_shape(element):
    if element["type"] == "node":
        return Point(element["lon"], element["lat"])
    return None


def shape_of(element):
    if element["type"] == "way":
        return way_shape(element)
    if element["type"] == "relation":
        return relation_shape(element)
    return point_shape(element)


def names(tags, keys):
    values = []
    for key in keys:
        for part in (tags.get(key) or "").split(";"):
            text = clean(part)
            if text and text not in values and text != clean(tags.get("name")):
                values.append(text)
    return values


def area_m2(shape):
    return round(abs(GEOD.geometry_area_perimeter(shape)[0]))


def feature(shape, properties):
    return {"type": "Feature", "properties": properties, "geometry": mapping(shape)}


def write_geojson(path, features):
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )


def snapshot(data):
    """The OSM database timestamp of the response, used as the as-of date."""
    return data["osm3s"]["timestamp_osm_base"][:10]


def build_water(data, source):
    features, skipped = [], 0
    for element in data["elements"]:
        tags = element.get("tags", {})
        shape = shape_of(element)
        if shape is None or shape.geom_type == "Point":
            skipped += 1
            continue
        features.append(
            feature(
                shape,
                {
                    "osmId": f"{element['type']}/{element['id']}",
                    "name": clean(tags.get("name")),
                    "nameKn": clean(tags.get("name:kn")),
                    "altNames": ";".join(names(tags, ["alt_name", "old_name", "official_name", "name:en"])) or None,
                    "water": clean(tags.get("water")),
                    "natural": clean(tags.get("natural")),
                    "landuse": clean(tags.get("landuse")),
                    "intermittent": clean(tags.get("intermittent")),
                    "wikidata": clean(tags.get("wikidata")),
                    "wikipedia": clean(tags.get("wikipedia")),
                    "wikimediaCommons": clean(tags.get("wikimedia_commons")),
                    "areaM2": area_m2(shape),
                    "source": source,
                },
            )
        )
    features.sort(key=lambda f: (f["properties"]["osmId"].split("/")[0], int(f["properties"]["osmId"].split("/")[1])))
    return features, skipped


def capacity_tags(tags):
    return ";".join(f"{k}={v}" for k, v in sorted(tags.items()) if "capacity" in k) or None


def capacity_mld(tags):
    """No plant carries a capacity tag, but many names do: "Hebbal 60MLD Sewage Treatment Plant"."""
    for key in ("name", "note"):
        match = re.search(r"(\d+(?:\.\d+)?)\s*(MLD|KLD)\b", tags.get(key) or "", re.I)
        if match:
            value = float(match.group(1)) / (1000 if match.group(2).upper() == "KLD" else 1)
            return round(value, 3)
    return None


def build_features(data, source):
    features = []
    for element in data["elements"]:
        tags = element.get("tags", {})
        shape = shape_of(element)
        if shape is None:
            continue
        kind = "wastewater_plant" if tags.get("man_made") == "wastewater_plant" else "lakeside_park"
        features.append(
            feature(
                shape,
                {
                    "osmId": f"{element['type']}/{element['id']}",
                    "kind": kind,
                    "name": clean(tags.get("name")),
                    "nameKn": clean(tags.get("name:kn")),
                    "operator": clean(tags.get("operator")),
                    "capacity": capacity_tags(tags),
                    "capacityMld": capacity_mld(tags) if kind == "wastewater_plant" else None,
                    "areaM2": None if shape.geom_type == "Point" else area_m2(shape),
                    "source": source,
                },
            )
        )
    features.sort(key=lambda f: (f["properties"]["kind"], f["properties"]["osmId"]))
    return features


def main():
    water_data = overpass("water", WATER_QUERY)
    features_data = overpass("features", FEATURES_QUERY)
    as_of = snapshot(water_data)
    source = f"osm-{as_of[:7]}"
    retrieved = time.strftime("%Y-%m-%d", time.localtime((DIR / "water.json").stat().st_mtime))

    water, skipped = build_water(water_data, source)
    write_geojson(SOURCES / "osm_water.geojson", water)
    extras = build_features(features_data, source)
    write_geojson(SOURCES / "osm_features.geojson", extras)

    write_sources(
        "osm",
        [
            {
                "key": source,
                "title": "OpenStreetMap water areas, treatment plants and lakeside parks around Bengaluru",
                "publisher": "OpenStreetMap contributors",
                "url": "https://www.openstreetmap.org/",
                "license": "ODbL 1.0",
                "credit": "© OpenStreetMap contributors",
                "asOf": as_of,
                "retrieved": retrieved,
            }
        ],
    )
    named = sum(1 for f in water if f["properties"]["name"])
    kinds = {}
    for f in extras:
        kinds[f["properties"]["kind"]] = kinds.get(f["properties"]["kind"], 0) + 1
    print(f"osm_water: {len(water)} areas ({named} named, {skipped} open ways or nodes skipped)")
    print(f"osm_features: {kinds}")


if __name__ == "__main__":
    main()
