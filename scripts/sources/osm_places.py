#!/usr/bin/env python3
"""
Village, town and suburb names from OpenStreetMap, used to say where an unnamed tank was.

Output: data/sources/osm_places.csv (osmId, name, nameKn, place, lat, lon, source)
"""

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, SOURCES, write_csv, write_sources  # noqa: E402

BBOX = (12.65, 77.18, 13.48, 77.96)
QUERY = f"""
[out:json][timeout:180];
node["place"~"^(village|hamlet|town|suburb|neighbourhood|quarter)$"]["name"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
out;
"""
CACHED = CACHE / "osm_places" / "places.json"
HEADERS = {"User-Agent": "LakesOfBendakaluru/1.0 (open data project; https://filtercoffee.dev)"}


def fetch():
    if CACHED.exists():
        return json.loads(CACHED.read_text())
    for attempt in range(4):
        try:
            r = requests.post("https://overpass-api.de/api/interpreter", data={"data": QUERY}, headers=HEADERS, timeout=240)
            r.raise_for_status()
            CACHED.parent.mkdir(parents=True, exist_ok=True)
            CACHED.write_text(r.text)
            return r.json()
        except requests.RequestException as err:
            print(f"overpass attempt {attempt + 1} failed: {err}")
            time.sleep(15 * (attempt + 1))
    raise SystemExit("overpass unavailable")


def build():
    data = fetch()
    rows = [
        {
            "osmId": f"node/{el['id']}",
            "name": el["tags"]["name"],
            "nameKn": el["tags"].get("name:kn"),
            "place": el["tags"]["place"],
            "lat": el["lat"],
            "lon": el["lon"],
            "source": "osm-places-2026-09",
        }
        for el in data["elements"]
    ]
    rows.sort(key=lambda r: r["osmId"])
    write_csv(SOURCES / "osm_places.csv", rows, ["osmId", "name", "nameKn", "place", "lat", "lon", "source"])
    write_sources(
        "osm_places",
        [
            {
                "key": "osm-places-2026-09",
                "title": "OpenStreetMap place names (villages, towns, suburbs)",
                "publisher": "OpenStreetMap contributors",
                "url": "https://www.openstreetmap.org/",
                "license": "ODbL 1.0",
                "credit": "© OpenStreetMap contributors",
                "asOf": "2026-09",
                "retrieved": time.strftime("%Y-%m-%d"),
            }
        ],
    )
    print(f"osm_places: {len(rows)} places")


if __name__ == "__main__":
    build()
