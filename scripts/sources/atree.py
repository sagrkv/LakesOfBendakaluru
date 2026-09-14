#!/usr/bin/env python3
"""
ATREE-CSEI lake outlines: the base list of 1,350 lakes that exist today.

The file is ATREE's copy of the BBMP lake master list, as published on OpenCity.
Each placemark keeps its FID, which is our stable key for this source ("atreeFid").

Output: data/sources/atree.geojson
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.validation import make_valid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, clean, write_sources  # noqa: E402

KML = RAW / "bbmp_lakes_masterlist.kml"
NS = {"k": "http://www.opengis.net/kml/2.2"}
GEOD = Geod(ellps="WGS84")

# The master list carries a one-letter valley code (K, H, V, B, S, A, O) with no published
# legend. Checked against computed drainage, "V" lakes do not drain to the Vrishabhavathi,
# so the code is kept as printed and never translated into a valley name here.

# Agency codes as they appear in the Custodian / New_Custod columns.
CUSTODIANS = {"BBMP", "BDA", "MID", "KFD", "KLCDA", "KSTDA", "EN", "HD", "ZP"}


def parse_description(html):
    """Attributes live in a two-column HTML table inside <description>."""
    cells = re.findall(r"<td[^>]*>(.*?)</td>", html or "", re.S | re.I)
    cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
    # cells[0] is the placemark title, then label/value pairs.
    return {cells[i]: cells[i + 1] for i in range(1, len(cells) - 1, 2)}


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
    # make_valid can return a GeometryCollection with stray lines; keep the areas only.
    if shape.geom_type == "GeometryCollection":
        parts = [g for g in shape.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        shape = MultiPolygon([p for g in parts for p in getattr(g, "geoms", [g])])
    return shape


def links(text):
    """The Facebook column sometimes holds two links separated by blank lines."""
    return [u.rstrip(",;.") for u in re.findall(r"https?://\S+", text or "")]


def build():
    root = ET.parse(KML).getroot()
    features = []
    for placemark in root.findall(".//k:Placemark", NS):
        shape = geometry(placemark)
        if shape is None or shape.is_empty:
            continue
        attrs = {k: clean(v) for k, v in parse_description(placemark.findtext("k:description", namespaces=NS)).items()}
        name = attrs.get("Name_of_th") or clean(placemark.findtext("k:name", namespaces=NS))

        custodian = attrs.get("New_Custod") or attrs.get("Custodian")
        if custodian not in CUSTODIANS:
            custodian = attrs.get("Custodian") if attrs.get("Custodian") in CUSTODIANS else None

        ward_name = attrs.get("Ward_Name")
        outside = bool(ward_name and "outside bbmp" in ward_name.lower())
        valley = attrs.get("Valley")
        area_m2 = abs(GEOD.geometry_area_perimeter(shape)[0])
        point = shape.representative_point()

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "atreeFid": int(attrs["FID"]),
                    "name": name,
                    "nameAlt": attrs.get("Alternativ"),
                    "ldaId": attrs.get("LDA"),
                    "valleyCode": valley,
                    "custodianCode": custodian,
                    "outsideBbmp": outside,
                    "wardNumber": attrs.get("Ward_Numbe"),
                    "wardName": None if outside else ward_name,
                    # The ward council whose members these are ended its term in 2020.
                    "councillor2015": attrs.get("Ward_Couns"),
                    "wardOffice2015": attrs.get("Ward_offic"),
                    "wardContact2015": attrs.get("Ward_Conta"),
                    "campaignUrls": links(attrs.get("Facebook")),
                    "areaM2": round(area_m2),
                    "labelPoint": [round(point.x, 6), round(point.y, 6)],
                    "source": "atree-lakes",
                },
                "geometry": mapping(shape),
            }
        )

    features.sort(key=lambda f: f["properties"]["atreeFid"])
    out = SOURCES / "atree.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    write_sources(
        "atree",
        [
            {
                "key": "atree-lakes",
                "title": "Map of Lakes in Bengaluru Urban and Rural Districts",
                "publisher": "ATREE-CSEI, from the BBMP lake master list",
                "url": "https://data.opencity.in/dataset/map-lakes-streams-bengaluru-urban-within-bbmp-area",
                "license": "CC BY",
                "credit": "Lake outlines: ATREE-CSEI",
                # The publisher gives no survey date; OpenCity first listed it in November 2022.
                "asOf": "not stated",
                "retrieved": "2026-09-10",
            }
        ],
    )
    print(f"atree: {len(features)} lakes -> {out.relative_to(out.parents[2])}")


if __name__ == "__main__":
    build()
