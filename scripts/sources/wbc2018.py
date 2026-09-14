#!/usr/bin/env python3
"""
First Water Bodies Census (Ministry of Jal Shakti, reference year 2017-18), one point per water body.

OpenCity publishes a Bengaluru Urban KML (718 points) and a Karnataka KML (27,013 points).
Bengaluru Urban comes from its own file; Bengaluru Rural (15 points) is filtered out of the
Karnataka file by the census's own district field. Every field is kept.

Keys kept verbatim: `wbcId` is the census unique_id ("1/12/002/000001/000099/001"), `miId` and
`objectId` are the portal's record ids.

Most attribute fields are unreliable for Bengaluru: every row says "not in use", "natural" and
"not encroached", storage capacity is 4 for 713 of 718 rows and spread area is 0 or 1. They look
like form defaults, not measurements. The enumeration dates (mostly 2021-22) are also later than
the 2017-18 reference year. Treat the location, village, type and ownership as the useful part.
The photo links point at mi6census.mowr.gov.in, which no longer resolves (September 2026).

Outputs: data/sources/wbc2018.csv
"""

import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (  # noqa: E402
    CACHE,
    RAW,
    ROOT,
    SOURCES,
    clean,
    write_csv,
    write_sources,
)

DATASET = "https://data.opencity.in/dataset/bengaluru-urban-and-karnataka-water-bodies-census-data"
RESOURCE = "https://data.opencity.in/dataset/97448b4d-9154-4342-9db0-4198f52baca3/resource/"
URBAN_URL = RESOURCE + "bab6a73b-c237-4808-b982-6624bda036b0/download/f76d1d1c-0360-4a44-a9f9-7f8b5e3fe4f9.kml"
STATE_URL = RESOURCE + "88187824-6dba-4ec2-9973-6f0e3ec85ecc/download/b6a59e3c-9b29-4844-babe-3d22498bd967.kml"
URBAN = RAW / "wbc2018" / "bengaluru_urban.kml"
STATE = CACHE / "wbc2018" / "karnataka.kml"
NS = {"k": "http://www.opengis.net/kml/2.2"}
EXPECTED = {"BANGALORE URBAN": 718, "BANGALORE RURAL": 15}

# Water body types as numbered in the census schedule.
TYPES = {
    "01": "Pond",
    "02": "Tank",
    "03": "Lake",
    "04": "Reservoir",
    "05": "Water conservation scheme / check dam / percolation tank",
    "06": "Other",
}

# Our column -> the census field it comes from (None = derived here).
FIELDS = {
    "wbcId": "unique_id",
    "miId": "mi_id",
    "objectId": "objectid",
    "state": "state",
    "district": "district",
    "taluk": "block_tehsil",
    "village": "village",
    "waterBodyTypeCode": "water_body_type",
    "waterBodyType": None,
    "lat": None,
    "lon": None,
    "ruralOrUrban": "rural_or_urban",
    "enumerationDate": None,
    "khasraNumber": "khasra_number",
    "ownership": "water_body_ownership",
    "use": "waterbody_use",
    "inUse": "waterbody_use_notuse",
    "nature": "water_body_nature",
    "maxDepthWhenFull": "max_depth_water_body_fully_fill",
    "storageCapacity": "storage_capacity_water_body_ori",
    "waterSpreadArea": "water_spread_area_of_water_body",
    "encroached": "waterbody_encroached",
    "photoUrl": "image_path",
    "remarks": "remarks",
    "uuid": "uuid",
    "districtNwic": "district_nwic",
    "districtIw": "district_iw",
    "districtCode": "district_code",
    "subdistrictNwic": "subdistrict_nwic",
    "subdistrictCode": "subdistrict_code",
    "villageNwic": "village_nwic",
    "villageCode": "village_code",
    "source": None,
}


def download(url, path):
    if not path.exists():
        response = requests.get(url, timeout=600)
        response.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
    return path


def placemarks(path):
    for placemark in ET.parse(path).getroot().iter(f"{{{NS['k']}}}Placemark"):
        yield {d.get("name"): clean(d.text) for d in placemark.iter(f"{{{NS['k']}}}SimpleData")}


def integer_text(text):
    """Fields typed float in the KML ('5958644.0') are integer ids; keep them as written otherwise."""
    if text and text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def row(attrs):
    out = {column: integer_text(attrs.get(field)) for column, field in FIELDS.items() if field}
    out["waterBodyType"] = TYPES.get(attrs.get("water_body_type"))
    out["lat"] = round(float(attrs["latitude"]), 7)
    out["lon"] = round(float(attrs["longitude"]), 7)
    stamp = attrs.get("enumeration_date")
    out["enumerationDate"] = (
        datetime.fromtimestamp(float(stamp) / 1000, tz=timezone.utc).date().isoformat() if stamp else None
    )
    out["source"] = "wbc-2017-18"
    return out


def build():
    urban = [a for a in placemarks(download(URBAN_URL, URBAN)) if a.get("district") == "BANGALORE URBAN"]
    rural = [a for a in placemarks(download(STATE_URL, STATE)) if a.get("district") == "BANGALORE RURAL"]
    rows = [row(a) for a in urban + rural]

    counts = {"BANGALORE URBAN": len(urban), "BANGALORE RURAL": len(rural)}
    for district, expected in EXPECTED.items():
        if counts[district] != expected:
            print(f"wbc2018: WARNING {district} has {counts[district]} rows, expected {expected}")
    ids = [r["wbcId"] for r in rows]
    if len(set(ids)) != len(ids):
        raise RuntimeError("wbc2018: duplicate unique_id")

    rows.sort(key=lambda r: (r["district"], r["wbcId"]))
    out = SOURCES / "wbc2018.csv"
    write_csv(out, rows, list(FIELDS))
    latest = max(r["enumerationDate"] for r in rows if r["enumerationDate"])
    retrieved = date.fromtimestamp(URBAN.stat().st_mtime).isoformat()
    write_sources(
        "wbc2018",
        [
            {
                "key": "wbc-2017-18",
                "title": "Water Bodies Census, 1st census (reference year 2017-18), Bengaluru Urban and Rural",
                "publisher": "Ministry of Jal Shakti, Department of Water Resources, River Development and Ganga "
                "Rejuvenation, via OpenCity",
                "url": DATASET,
                "license": "Public domain (as marked on OpenCity)",
                "credit": "Water Bodies Census, Ministry of Jal Shakti",
                # Latest field enumeration date in the rows we keep.
                "asOf": latest,
                "retrieved": retrieved,
            }
        ],
    )
    print(f"wbc2018: {counts['BANGALORE URBAN']} urban + {counts['BANGALORE RURAL']} rural -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
