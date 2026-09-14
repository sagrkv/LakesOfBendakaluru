#!/usr/bin/env python3
"""
KGIS (Karnataka GIS, KSRSAC) water-body polygons for Bengaluru Urban district, as published on OpenCity.

Three layers, one output file each:
  tanks     1,356 polygons from the KGIS land-use map: 1,325 tanks and 31 islands inside tanks
  ponds     6,570 pond polygons from the same land-use map
  wetlands  265 polygons from the KGIS wetlands layer, clipped to Bengaluru Urban

The KGIS land-use id column (KGISLULCID) is empty in both land-use layers, so OBJECTID is
the only key. We keep it verbatim ("kgisTankId", "kgisPondId").
`areaM2` is measured on the ellipsoid from the polygon; `shapeAreaM2` is the publisher's own
SHAPE.STArea() figure (projected square metres), kept for comparison. The wetlands layer was
clipped to the district after that figure was computed, so for 18 wetlands that cross the
district edge `shapeAreaM2` is the whole wetland and `areaM2` only the part inside.
In the wetlands layer KGISWetlandID always equals OBJECTID; we keep KGISWetlandID.

Outputs: data/sources/kgis_tanks.geojson, kgis_ponds.geojson, kgis_wetlands.geojson
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import requests
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.validation import make_valid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, SOURCES, clean, write_sources  # noqa: E402

DIR = CACHE / "kgis_tanks"
NS = {"k": "http://www.opengis.net/kml/2.2"}
GEOD = Geod(ellps="WGS84")

LAKES_PONDS = "https://data.opencity.in/dataset/lakes-and-ponds-in-bengaluru-district"
WETLANDS = "https://data.opencity.in/dataset/wetlands-of-karnataka-and-bengaluru-urban"
DOWNLOADS = {
    "tanks": "https://data.opencity.in/dataset/d4e99898-7e4d-486c-abd0-5aec637a36a8/resource/"
    "11617e96-5aa2-4f2d-8df3-89727b6a75f3/download/2556496f-b582-4345-afee-760aeae69823.kml",
    "ponds": "https://data.opencity.in/dataset/d4e99898-7e4d-486c-abd0-5aec637a36a8/resource/"
    "4cde3f7e-428c-4e00-8165-3098e2440f3f/download/a43a2897-4968-42ad-8985-357a4e61b78e.kml",
    "wetlands": "https://data.opencity.in/dataset/69d28d30-b11d-49a7-9ff0-0d4f7d881522/resource/"
    "8f61888f-94c0-488f-bbdc-c7b160161458/download/5b8dca1e-1ded-4ad2-8cd9-3cea2cd0cfbd.kml",
}
EXPECTED = {"tanks": 1356, "ponds": 6570, "wetlands": 265}

# National Wetland Inventory and Assessment (ISRO SAC) classes used by the KGIS wetland codes.
WETLAND_CLASSES = {
    "1101": "Lake/Pond",
    "1102": "Ox-bow lake",
    "1103": "High altitude wetland",
    "1104": "Riverine wetland",
    "1105": "Waterlogged (natural)",
    "1106": "River/Stream",
    "1201": "Reservoir/Barrage",
    "1202": "Tank/Pond",
    "1203": "Waterlogged (man-made)",
    "1204": "Salt pan",
}


def download(layer):
    path = DIR / f"{layer}.kml"
    if not path.exists():
        response = requests.get(DOWNLOADS[layer], timeout=300)
        response.raise_for_status()
        DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
    return path


def ring(text):
    points = []
    for chunk in (text or "").split():
        parts = chunk.split(",")
        if len(parts) >= 2:
            points.append((float(parts[0]), float(parts[1])))
    return points


def geometry(placemark):
    polygons = []
    for poly in placemark.findall(".//k:Polygon", NS):
        outer = ring(poly.findtext(".//k:outerBoundaryIs//k:coordinates", namespaces=NS))
        if len(outer) < 4:
            continue
        holes = [ring(h.text) for h in poly.findall(".//k:innerBoundaryIs//k:coordinates", NS)]
        polygons.append(Polygon(outer, [h for h in holes if len(h) >= 4]))
    if not polygons:
        return None
    shape = make_valid(MultiPolygon(polygons) if len(polygons) > 1 else polygons[0])
    if shape.geom_type == "GeometryCollection":
        parts = [g for g in shape.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        shape = MultiPolygon([p for g in parts for p in getattr(g, "geoms", [g])])
    return shape


def placemarks(path):
    root = ET.parse(path).getroot()
    for placemark in root.findall(".//k:Placemark", NS):
        attrs = {d.get("name"): clean(d.text) for d in placemark.findall(".//k:SimpleData", NS)}
        yield attrs, geometry(placemark)


def number(text, digits=1):
    return None if text is None else round(float(text), digits)


def common_props(shape, attrs):
    point = shape.representative_point()
    return {
        "areaM2": round(abs(GEOD.geometry_area_perimeter(shape)[0])),
        "shapeAreaM2": number(attrs.get("SHAPE.STArea()")),
        "shapeLengthM": number(attrs.get("SHAPE.STLength()")),
        "labelPoint": [round(point.x, 6), round(point.y, 6)],
    }


def land_use(attrs, shape, id_key, source):
    return {
        id_key: int(attrs["OBJECTID"]),
        "lulcCode": attrs.get("LULC_Code"),
        # Descriptions from the most general level to the most specific.
        "lulcDesc": [d for d in (attrs.get(f"LULC_Desc_{i}") for i in range(1, 6)) if d],
        "remarks": attrs.get("Remarks"),
        **common_props(shape, attrs),
        "source": source,
    }


def wetland(attrs, shape, source):
    code = attrs.get("KGISWetlandCode")
    return {
        "kgisWetlandId": int(float(attrs["KGISWetlandID"])),
        "wetlandCode": code,
        "wetlandClass": WETLAND_CLASSES.get(code),
        "forestBeatId": int(float(attrs["KGISForestBeatID"])) if attrs.get("KGISForestBeatID") else None,
        **common_props(shape, attrs),
        "source": source,
    }


def build_layer(layer, make):
    features = []
    for attrs, shape in placemarks(download(layer)):
        if shape is None or shape.is_empty:
            print(f"kgis_tanks: {layer} {attrs.get('OBJECTID')} has no polygon, skipped")
            continue
        features.append({"type": "Feature", "properties": make(attrs, shape), "geometry": mapping(shape)})
    if len(features) != EXPECTED[layer]:
        print(f"kgis_tanks: WARNING {layer} has {len(features)} features, expected {EXPECTED[layer]}")
    first_key = next(iter(features[0]["properties"]))
    features.sort(key=lambda f: f["properties"][first_key])
    out = SOURCES / f"kgis_{layer}.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"kgis_tanks: {len(features)} {layer} -> {out.relative_to(out.parents[2])}")


def build():
    build_layer("tanks", lambda a, s: land_use(a, s, "kgisTankId", "kgis-tanks"))
    build_layer("ponds", lambda a, s: land_use(a, s, "kgisPondId", "kgis-ponds"))
    build_layer("wetlands", lambda a, s: wetland(a, s, "kgis-wetlands"))

    retrieved = date.fromtimestamp((DIR / "tanks.kml").stat().st_mtime).isoformat()
    base = {
        "publisher": "Karnataka State Remote Sensing Applications Centre (KSRSAC), Karnataka GIS, via OpenCity",
        "license": "Public domain (as marked on OpenCity)",
        "credit": "Water-body polygons: KSRSAC / KGIS, via OpenCity",
        "asOf": "not stated",
        "retrieved": retrieved,
    }
    write_sources(
        "kgis_tanks",
        [
            {"key": "kgis-tanks", "title": "Bengaluru Urban Lakes (Tanks) Map", "url": LAKES_PONDS, **base},
            {"key": "kgis-ponds", "title": "Bengaluru Urban Ponds Map", "url": LAKES_PONDS, **base},
            {"key": "kgis-wetlands", "title": "Bengaluru Urban Wetlands Map", "url": WETLANDS, **base},
        ],
    )


if __name__ == "__main__":
    build()
