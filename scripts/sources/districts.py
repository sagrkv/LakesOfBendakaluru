#!/usr/bin/env python3
"""
District boundaries of Bangalore from OpenStreetMap: Bengaluru Urban, and Bengaluru North
(called Bengaluru Rural until 2025). The lake list covers these two districts.

Downloads: data/cache/osm/districts.json (Overpass response, reused on rerun; delete it to pull fresh data).
Output: data/sources/districts.geojson, one feature per district.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import SOURCES, clean, write_sources  # noqa: E402
from osm import feature, overpass, relation_shape, snapshot, write_geojson  # noqa: E402

# OSM relation ids, so a renamed district cannot silently drop out of the query.
DISTRICTS = {2020589: "Bengaluru Urban", 2020588: "Bengaluru North (formerly Bengaluru Rural)"}
QUERY = "[out:json][timeout:300];relation(id:" + ",".join(map(str, DISTRICTS)) + ");out body geom;"


def build():
    data = overpass("districts", QUERY)
    source = f"osm-districts-{snapshot(data)[:7]}"
    features = []
    for element in data["elements"]:
        shape = relation_shape(element)
        if shape is None:
            raise RuntimeError(f"districts: relation {element['id']} did not close into an area")
        tags = element.get("tags", {})
        features.append(
            feature(
                shape,
                {
                    "osmId": f"relation/{element['id']}",
                    "name": clean(tags.get("name")),
                    "oldName": clean(tags.get("old_name")),
                    "wikidata": clean(tags.get("wikidata")),
                    "source": source,
                },
            )
        )
    found = {int(f["properties"]["osmId"].split("/")[1]) for f in features}
    if found != set(DISTRICTS):
        raise RuntimeError(f"districts: expected relations {sorted(DISTRICTS)}, got {sorted(found)}")

    write_geojson(SOURCES / "districts.geojson", features)
    write_sources(
        "districts",
        [
            {
                "key": source,
                "title": "OpenStreetMap boundaries of Bengaluru Urban and Bengaluru North (formerly Bengaluru Rural) districts",
                "publisher": "OpenStreetMap contributors",
                "url": "https://www.openstreetmap.org/relation/2020589",
                "license": "ODbL 1.0",
                "credit": "© OpenStreetMap contributors",
                "asOf": snapshot(data),
                "retrieved": date.today().isoformat(),
            }
        ],
    )
    print(f"districts: {len(features)} districts -> data/sources/districts.geojson")


if __name__ == "__main__":
    build()
