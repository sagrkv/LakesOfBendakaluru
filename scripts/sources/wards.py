#!/usr/bin/env python3
"""
Ward boundaries for Bengaluru, one GeoJSON per ward map.

  bbmp-2010-198  the 198-ward BBMP map from the 2010 delimitation, used for the 2010 and 2015
                 council elections. ATREE's ward numbers use this map.
  bbmp-2023-225  the 225-ward BBMP map from the final 2023 delimitation (never used for an election).
  gba-2025-369   the 369-ward map of the five Greater Bengaluru Authority city corporations.
                 Boundaries notified as final on 19 Nov 2025, ward renamings of 1 Dec 2025,
                 and the final ward reservations of March 2026. This is the newest official map.

Ward numbers in the GBA map restart at 1 in each corporation, so a ward is identified by
corporation + number ("wardKey", e.g. "West-25").

All files come from OpenCity, which republishes the government KMLs. KML is WGS84 already.

Output: data/sources/wards_2010_198.geojson, wards_2023_225.geojson, wards_2025_gba_369.geojson
"""

import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.validation import make_valid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, SOURCES, clean, write_sources  # noqa: E402

# The three KMLs total about 8 MB, so they live in the ignored cache.
DIR = CACHE / "wards"
NS = {"k": "http://www.opengis.net/kml/2.2"}
RETRIEVED = "2026-09-11"

MAPS = {
    "bbmp-2010-198": {
        "file": "bbmp_wards_2010_198.kml",
        "url": "https://data.opencity.in/dataset/87b978d1-352e-4b90-aa2c-9991e55d3425/resource/"
        "a0329df6-2924-43f4-8fe4-7a6ffcc1d53d/download/806d6b9c-e8d9-4eb0-a3a3-b2ba68ec3cda.kml",
        "out": "wards_2010_198.geojson",
        "count": 198,
    },
    "bbmp-2023-225": {
        "file": "bbmp_wards_2023_225.kml",
        "url": "https://data.opencity.in/dataset/7b492849-a5cb-439b-89e9-e03522055e6a/resource/"
        "7857d752-dda4-4e5e-b9e6-53146372f86b/download/b272c5b2-3e66-4b0f-a59f-35ec7b4caa1e.kml",
        "out": "wards_2023_225.geojson",
        "count": 225,
    },
    "gba-2025-369": {
        "file": "gba_wards_369_reservation_2026-03.kml",
        "url": "https://data.opencity.in/dataset/e6356d29-ce41-4bc7-8292-bbd790070e14/resource/"
        "aa77fba2-689b-43f2-a3d6-a737a42d63bd/download/gba-369-wards-december-2025-appended.kml",
        "out": "wards_2025_gba_369.geojson",
        "count": 369,
    },
}

GBA_CORPORATIONS = {"Central": 63, "East": 50, "North": 72, "South": 72, "West": 112}


def download(url, path):
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LakesOfBendakaluru data build"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            tmp = path.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.rename(path)
            return
        except OSError as e:
            if attempt == 3:
                raise
            print(f"  retry {url}: {e}")
            time.sleep(2 * (attempt + 1))


def ring(text):
    points = []
    for chunk in (text or "").split():
        parts = chunk.split(",")
        if len(parts) >= 2:
            points.append((round(float(parts[0]), 6), round(float(parts[1]), 6)))
    return points


def geometry(placemark):
    polygons = []
    for poly in placemark.findall(".//k:Polygon", NS):
        outer = ring(poly.findtext(".//k:outerBoundaryIs//k:coordinates", namespaces=NS))
        if len(outer) < 4:
            continue
        holes = [ring(h.text) for h in poly.findall(".//k:innerBoundaryIs//k:coordinates", NS)]
        polygons.append(Polygon(outer, [h for h in holes if len(h) >= 4]))
    shape = MultiPolygon(polygons) if len(polygons) > 1 else polygons[0]
    if not shape.is_valid:
        shape = make_valid(shape)
        if shape.geom_type == "GeometryCollection":
            parts = [g for g in shape.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
            shape = MultiPolygon([p for g in parts for p in getattr(g, "geoms", [g])])
    return shape


def attributes(placemark):
    """Both KML attribute styles: <Data name><value> and <SimpleData name>."""
    attrs = {}
    for d in placemark.findall(".//k:Data", NS):
        attrs[d.get("name").strip()] = clean(d.findtext("k:value", namespaces=NS))
    for d in placemark.findall(".//k:SimpleData", NS):
        attrs[d.get("name").strip()] = clean(d.text)
    return attrs


def number(value):
    return None if value is None else int(float(value))


def props_2010(a, placemark):
    name = clean(placemark.findtext("k:name", namespaces=NS))  # "Ward 1"
    return {
        "wardNumber": int(name.split()[-1]),
        "wardName": a.get("Ward Name"),
        "zone": a.get("Zone"),
        "division": a.get("Division"),
        "subdivision": a.get("Subdivision"),
        "assemblyConstituency": a.get("Assembly (MLA) Constituency"),
        "parliamentaryConstituency": a.get("Parliament (MP) Constituency"),
    }


def props_2023(a, placemark):
    ac = a.get("assembly_constituency_name_en") or ""  # "150-YELAHANKA"
    return {
        "wardNumber": number(a.get("id")),
        "wardName": a.get("name_en"),
        "wardNameKannada": a.get("name_ka"),
        "assemblyConstituencyNumber": number(a.get("assembly_constituency_id")),
        "assemblyConstituency": ac.split("-", 1)[-1].strip() or None,
        "parliamentaryConstituency": a.get("parliamentary_constituency_name_en"),
        "population2011": number(a.get("population")),
        "areaKm2": round(float(a["ward_area"]), 3) if a.get("ward_area") else None,
    }


def props_gba(a, placemark):
    corp = a.get("Corporation")  # "West"
    return {
        "wardKey": f"{corp}-{number(a.get('ward_id'))}",
        "corporation": f"Bengaluru {corp}",
        "corporationId": number(a.get("corporation_id")),
        "corporationKannada": a.get("corporation_kn"),
        "wardNumber": number(a.get("ward_id")),
        "wardName": a.get("ward_name"),
        "wardNameKannada": a.get("ward_name_kn"),
        "zone": a.get("zone_name"),
        "revenueDivision": (a.get("RO_Division") or "").removeprefix("RO-").strip() or None,
        "revenueSubdivision": (a.get("ARO_ Sub Division") or "").removeprefix("ARO-").strip() or None,
        "assemblyConstituencyNumber": number(a.get("ac_no")),
        "assemblyConstituency": a.get("ac"),
        "reservation": a.get("Reservation"),
        "population2011": number(a.get("TOT_P")),
    }


PROPS = {"bbmp-2010-198": props_2010, "bbmp-2023-225": props_2023, "gba-2025-369": props_gba}


def build_map(version, spec):
    path = DIR / spec["file"]
    download(spec["url"], path)
    root = ET.parse(path).getroot()
    features = []
    for placemark in root.findall(".//k:Placemark", NS):
        props = PROPS[version](attributes(placemark), placemark)
        features.append(
            {
                "type": "Feature",
                "properties": {"mapVersion": version, **props, "source": f"wards-{version}"},
                "geometry": mapping(geometry(placemark)),
            }
        )

    key = "wardKey" if version.startswith("gba") else "wardNumber"
    features.sort(key=lambda f: (f["properties"].get("corporationId") or 0, f["properties"]["wardNumber"]))
    keys = [f["properties"][key] for f in features]
    assert len(features) == spec["count"], f"{version}: {len(features)} wards, expected {spec['count']}"
    assert len(set(keys)) == len(keys), f"{version}: duplicate ward ids"
    assert all(f["properties"]["wardName"] for f in features), f"{version}: ward without a name"
    if version.startswith("gba"):
        per = {}
        for f in features:
            per[f["properties"]["corporation"]] = per.get(f["properties"]["corporation"], 0) + 1
        assert per == {f"Bengaluru {c}": n for c, n in GBA_CORPORATIONS.items()}, per

    out = SOURCES / spec["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"wards: {version} {len(features)} wards -> {out.relative_to(out.parents[2])}")


def build():
    for version, spec in MAPS.items():
        build_map(version, spec)
    write_sources(
        "wards",
        [
            {
                "key": "wards-bbmp-2010-198",
                "title": "BBMP Ward Map - 2015 (198 wards, 2010 delimitation)",
                "publisher": "BBMP, via OpenCity",
                "url": "https://data.opencity.in/dataset/bbmp-ward-information",
                "license": "not stated",
                "credit": "Ward boundaries: BBMP, via OpenCity",
                "asOf": "2010",
                "retrieved": RETRIEVED,
            },
            {
                "key": "wards-bbmp-2023-225",
                "title": "BBMP Final Wards Map - 2023 (225 wards)",
                "publisher": "Government of Karnataka, Urban Development Department, via OpenCity",
                "url": "https://data.opencity.in/dataset/bbmp-wards-delimitation-2023",
                "license": "Public Domain",
                "credit": "Ward boundaries: Government of Karnataka, via OpenCity",
                "asOf": "2023",
                "retrieved": RETRIEVED,
            },
            {
                "key": "wards-gba-2025-369",
                "title": "GBA Wards Map with Reservation - March 2026 (369 wards, five city corporations)",
                "publisher": "Greater Bengaluru Authority / Government of Karnataka, via OpenCity",
                "url": "https://data.opencity.in/dataset/gba-ward-wise-reservations-2026",
                # Boundaries final 2025-11-19, names 2025-12-01, reservations March 2026.
                "license": "Public Domain",
                "credit": "Ward boundaries: Greater Bengaluru Authority, via OpenCity",
                "asOf": "2026-03",
                "retrieved": RETRIEVED,
            },
        ],
    )


if __name__ == "__main__":
    build()
