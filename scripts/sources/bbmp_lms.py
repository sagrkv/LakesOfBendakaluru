#!/usr/bin/env python3
"""
BBMP Lake Monitoring System (lms.bbmpgov.in): the lakes BBMP tracks, with a point each.

The public map reads nine JSON feeds: /locations/0 is every lake, /locations/1..8 are
the same lakes split by BBMP zone. We keep the LMS id verbatim ("bbmpLmsId") and take
the zone from whichever zone feed lists the lake.

The per-lake pages (/viewlakenew/<id>) have returned HTTP 500 (a database login error)
every time we tried, so only the feed fields are captured. The script still probes one
page and reports if that changes.

The site's certificate chain is incomplete, so we verify against the system trust store
(truststore) instead of certifi.

Output: data/sources/bbmp_lms.csv
"""

import json
import sys
from datetime import date
from pathlib import Path

import requests
import truststore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, clean, write_csv, write_sources  # noqa: E402

truststore.inject_into_ssl()

BASE = "https://lms.bbmpgov.in"
DIR = RAW / "bbmp_lms"
# Order of the zone feeds, as wired up in the site's map script.
ZONES = {
    1: "Bommanahalli",
    2: "Dasarahalli",
    3: "East",
    4: "Mahadevapura",
    5: "RR Nagar",
    6: "South",
    7: "West",
    8: "Yelahanka",
}
COLUMNS = ["bbmpLmsId", "name", "zone", "lat", "lon", "latRaw", "lonRaw", "coordNote", "url", "source"]

# A few points were typed as degrees-minutes-seconds with the separators dropped
# ("12.5855" = 12 deg 58' 55"). Decoded only where the result lands on the ATREE outline
# of the same lake (Ulsoor, Konanakunte).
PACKED_DMS = {116, 221}
# Rough box around Bengaluru Urban; points outside it are typos and are left blank.
BOX = (12.7, 13.3, 77.3, 77.85)
# Known-bad points inside the box, left blank with this note.
NOTES = {
    25: "longitude 77.37332 looks like packed DMS (77 deg 37' 33\"), which would move it about 27 km east; not corrected",
    232: "latitude split across both fields (13 deg 2' 42.88\" N); no longitude given",
    233: "latitude split across both fields (13 deg 2' 48.40\" N); no longitude given",
}


def feed(index):
    path = DIR / f"locations_{index}.json"
    if not path.exists():
        response = requests.get(f"{BASE}/locations/{index}", timeout=60)
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise RuntimeError(f"locations/{index} returned success=false")
        DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))["locations"]


def packed_dms(text):
    """'77.3408.3' -> 77 deg 34' 08.3"; '12.5855' -> 12 deg 58' 55"."""
    degrees, rest = text.split(".", 1)
    digits = rest.replace(".", "")
    minutes, seconds = int(digits[:2]), float(digits[2:4] + "." + digits[4:] if len(digits) > 4 else digits[2:4])
    return int(degrees) + minutes / 60 + seconds / 3600


def to_float(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def point(lake_id, lat_raw, lon_raw):
    """Return (lat, lon, note). Unusable points come back blank with a note saying why."""
    if lake_id in PACKED_DMS:
        return round(packed_dms(lat_raw), 6), round(packed_dms(lon_raw), 6), "decoded from packed DMS"
    if lake_id in NOTES:
        return None, None, NOTES[lake_id]
    lat, lon = to_float(lat_raw), to_float(lon_raw)
    if lat is None or lon is None:
        return None, None, "unparseable coordinates"
    if not (BOX[0] < lat < BOX[1] and BOX[2] < lon < BOX[3]):
        return None, None, "outside Bengaluru, likely a typo"
    return lat, lon, None


def probe_detail(lake_id):
    try:
        response = requests.get(f"{BASE}/viewlakenew/{lake_id}", timeout=60)
    except requests.RequestException as error:
        return f"error {error.__class__.__name__}"
    return f"HTTP {response.status_code}"


def build():
    zone_of = {}
    for index, zone in ZONES.items():
        for location in feed(index):
            if location["id"] in zone_of and zone_of[location["id"]] != zone:
                raise RuntimeError(f"lake {location['id']} is in two zones")
            zone_of[location["id"]] = zone

    rows = []
    for location in feed(0):
        lake_id = location["id"]
        lat, lon, note = point(lake_id, location["latitude"], location["longitude"])
        rows.append(
            {
                "bbmpLmsId": lake_id,
                "name": clean(location["name"]),
                "zone": zone_of.get(lake_id),
                "lat": lat,
                "lon": lon,
                "latRaw": location["latitude"],
                "lonRaw": location["longitude"],
                "coordNote": note,
                "url": f"{BASE}/viewlakenew/{lake_id}",
                "source": "bbmp-lms",
            }
        )
    rows.sort(key=lambda r: r["bbmpLmsId"])

    missing_zone = [r["bbmpLmsId"] for r in rows if not r["zone"]]
    if missing_zone:
        print(f"bbmp_lms: no zone for {missing_zone}")
    status = probe_detail(rows[0]["bbmpLmsId"])
    for row in rows:
        if row["coordNote"]:
            print(f"bbmp_lms: {row['bbmpLmsId']} {row['name']}: {row['coordNote']}")
    print(f"bbmp_lms: detail page probe -> {status}")

    out = SOURCES / "bbmp_lms.csv"
    write_csv(out, rows, COLUMNS)
    write_sources(
        "bbmp_lms",
        [
            {
                "key": "bbmp-lms",
                "title": "Lakes Monitoring System",
                "publisher": "Bruhat Bengaluru Mahanagara Palike (BBMP), Lakes Division",
                "url": BASE,
                "license": "not stated",
                "credit": "Lake locations: BBMP Lakes Monitoring System",
                "asOf": "not stated",
                "retrieved": date.fromtimestamp((DIR / "locations_0.json").stat().st_mtime).isoformat(),
            }
        ],
    )
    print(f"bbmp_lms: {len(rows)} lakes -> {out.relative_to(out.parents[2])}")


if __name__ == "__main__":
    build()
