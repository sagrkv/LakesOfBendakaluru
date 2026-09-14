#!/usr/bin/env python3
"""
GBIF occurrence counts per lake: how many species records sit in or right around each lake.

For every lake we ask the GBIF occurrence search for records inside the outline grown by 50 m,
with limit=0 and facets, so each lake costs one request and no records are downloaded.
Most records near Bengaluru lakes are eBird checklists shared through GBIF.

Usage:
  .venv/bin/python scripts/sources/gbif.py [lakes.geojson] [keyProperty]

Output:
  data/sources/gbif.csv          one row per lake
  data/sources/gbif_species.csv  one row per lake and species with at least one record
  data/sources/gbif.sources.json
Cache: data/cache/gbif/ (occurrence facets per search shape, species and dataset lookups).
"""

import hashlib
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from shapely import wkt
from shapely.geometry import MultiPolygon
from shapely.geometry.polygon import orient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, SOURCES, write_csv, write_sources  # noqa: E402
from _nature import Http, lake_args, lake_shapes, read_json, write_json  # noqa: E402

API = "https://api.gbif.org/v1"
CACHE_DIR = CACHE / "gbif"
BUFFER_M = 50
MAX_WKT = 3000  # characters, keeps the GET URL well under GBIF's limit once encoded
BIRDS = 212  # GBIF backbone classKey for Aves
EBIRD = "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
RECENT_YEARS = 5
TOP_BIRDS = 10
TODAY = date.today().isoformat()
SOURCE_KEY = f"gbif-{TODAY[:7]}"

HTTP = Http(min_interval=0.15)

LAKE_COLUMNS = [
    "key", "records", "species", "birdRecords", "birdSpecies", "firstYear", "lastYear",
    "recordsLast5Years", "topBirds", "datasets", "ebirdShare", "source",
]
SPECIES_COLUMNS = ["key", "speciesKey", "scientificName", "vernacularName", "class", "records", "iucnCategory", "source"]


def search_wkt(shape):
    """Simplified WKT with counter-clockwise outer rings, short enough for a GET request."""
    for tolerance in (0.00001, 0.00002, 0.00005, 0.0001, 0.0002, 0.0005, 0.001, 0.002):
        simple = shape.simplify(tolerance, preserve_topology=True)
        if not simple.is_valid:
            simple = simple.buffer(0)
        parts = [orient(p, 1.0) for p in getattr(simple, "geoms", [simple]) if p.geom_type == "Polygon"]
        geom = parts[0] if len(parts) == 1 else MultiPolygon(parts)
        text = wkt.dumps(geom, rounding_precision=5, trim=True)
        if len(text) <= MAX_WKT:
            return text
    return wkt.dumps(orient(shape.convex_hull, 1.0), rounding_precision=5, trim=True)


def occurrence_facets(geometry):
    """One limit=0 search with every facet we need. Cached by the search shape."""
    path = CACHE_DIR / "occurrences" / f"{hashlib.sha1(geometry.encode()).hexdigest()}.json"
    cached = read_json(path)
    if cached:
        return cached
    params = [
        ("geometry", geometry),
        ("limit", 0),
        ("occurrenceStatus", "PRESENT"),
        ("hasGeospatialIssue", "false"),
        ("facetMincount", 1),
        ("facet", "speciesKey"), ("speciesKey.facetLimit", 10000),
        ("facet", "classKey"), ("classKey.facetLimit", 200),
        ("facet", "year"), ("year.facetLimit", 500),
        ("facet", "datasetKey"), ("datasetKey.facetLimit", 500),
        ("facet", "license"), ("license.facetLimit", 20),
    ]
    data = HTTP.get(f"{API}/occurrence/search", params)
    result = {
        "fetched": TODAY,
        "count": data["count"],
        "facets": {f["field"]: {c["name"]: c["count"] for c in f["counts"]} for f in data.get("facets", [])},
    }
    write_json(path, result)
    return result


def usable(name):
    """Backbone names are sometimes eBird slash groups ("Gray/Purple Heron") or lists."""
    return bool(name) and not any(c in name for c in "/,;") and not name.isupper()


def english_name(key, backbone):
    if usable(backbone):
        return backbone[0].upper() + backbone[1:]
    data = HTTP.get(f"{API}/species/{key}/vernacularNames", {"limit": 1000}) or {}
    names = [r for r in data.get("results", []) if r.get("language") == "eng" and usable(r.get("vernacularName"))]
    rank = {"The Clements Checklist": 0, "IOC World Bird List, v": 1, "Catalogue of Life": 2}
    names.sort(key=lambda r: rank.get(r.get("source"), 9))
    if not names:
        return None
    name = names[0]["vernacularName"]
    return name[0].upper() + name[1:]


def species_info(key):
    path = CACHE_DIR / "species" / f"{key}.json"
    cached = read_json(path)
    if cached:
        return cached
    record = HTTP.get(f"{API}/species/{key}") or {}
    iucn = HTTP.get(f"{API}/species/{key}/iucnRedListCategory") or {}
    info = {
        "fetched": TODAY,
        "speciesKey": int(key),
        "scientificName": record.get("canonicalName") or record.get("scientificName"),
        "vernacularName": english_name(key, record.get("vernacularName")),
        "class": record.get("class"),
        "classKey": record.get("classKey"),
        "iucnCategory": iucn.get("code"),
    }
    write_json(path, info)
    return info


def dataset_title(key):
    path = CACHE_DIR / "datasets" / f"{key}.json"
    cached = read_json(path)
    if cached:
        return cached["title"]
    data = HTTP.get(f"{API}/dataset/{key}") or {}
    info = {"fetched": TODAY, "title": data.get("title") or key, "license": data.get("license")}
    write_json(path, info)
    return info["title"]


def lake_row(key, result, species, titles):
    facets = result["facets"]
    records = result["count"]
    counts = facets.get("SPECIES_KEY", {})
    years = sorted(int(y) for y in facets.get("YEAR", {}))
    recent_from = date.today().year - RECENT_YEARS + 1
    birds = sorted(
        ((n, species[k]) for k, n in counts.items() if species[k]["classKey"] == BIRDS),
        key=lambda item: (-item[0], item[1]["scientificName"] or ""),
    )
    datasets = sorted(facets.get("DATASET_KEY", {}).items(), key=lambda item: -item[1])[:3]
    return {
        "key": key,
        "records": records,
        "species": len(counts),
        "birdRecords": facets.get("CLASS_KEY", {}).get(str(BIRDS), 0),
        "birdSpecies": len(birds),
        "firstYear": years[0] if years else None,
        "lastYear": years[-1] if years else None,
        "recordsLast5Years": sum(n for y, n in facets.get("YEAR", {}).items() if int(y) >= recent_from),
        "topBirds": [
            f"{s['scientificName']} ({s['vernacularName']})" if s["vernacularName"] else s["scientificName"]
            for _, s in birds[:TOP_BIRDS]
        ],
        "datasets": [titles[k] for k, _ in datasets],
        "ebirdShare": round(facets.get("DATASET_KEY", {}).get(EBIRD, 0) / records, 3) if records else None,
        "source": SOURCE_KEY,
    }


def main():
    args = lake_args(__doc__.strip().splitlines()[0])
    lakes = [(key, search_wkt(shape)) for key, shape in lake_shapes(args.geometry, args.key, BUFFER_M)]
    print(f"{len(lakes)} lakes from {args.geometry}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda lake: occurrence_facets(lake[1]), lakes))
    print(f"occurrence searches done, {sum(r['count'] for r in results):,} records in total")

    species_keys = sorted({k for r in results for k in r["facets"].get("SPECIES_KEY", {})}, key=int)
    dataset_keys = sorted({k for r in results for k in r["facets"].get("DATASET_KEY", {})})
    with ThreadPoolExecutor(max_workers=4) as pool:
        species = dict(zip(species_keys, pool.map(species_info, species_keys)))
        titles = dict(zip(dataset_keys, pool.map(dataset_title, dataset_keys)))
    print(f"{len(species):,} species, {len(titles)} datasets looked up")

    rows = [lake_row(key, result, species, titles) for (key, _), result in zip(lakes, results)]
    species_rows = [
        {
            "key": key,
            "speciesKey": k,
            "scientificName": species[k]["scientificName"],
            "vernacularName": species[k]["vernacularName"],
            "class": species[k]["class"],
            "records": n,
            "iucnCategory": species[k]["iucnCategory"],
            "source": SOURCE_KEY,
        }
        for (key, _), result in zip(lakes, results)
        for k, n in sorted(result["facets"].get("SPECIES_KEY", {}).items(), key=lambda item: -item[1])
    ]
    lake_columns = [args.key if c == "key" else c for c in LAKE_COLUMNS]
    species_columns = [args.key if c == "key" else c for c in SPECIES_COLUMNS]
    write_csv(SOURCES / "gbif.csv", [{args.key if k == "key" else k: v for k, v in r.items()} for r in rows], lake_columns)
    write_csv(
        SOURCES / "gbif_species.csv",
        [{args.key if k == "key" else k: v for k, v in r.items()} for r in species_rows],
        species_columns,
    )

    licenses = Counter()
    for result in results:
        licenses.update(result["facets"].get("LICENSE", {}))
    total = sum(licenses.values()) or 1
    license_note = ", ".join(f"{name.replace('_', ' ').replace(' 1 0', ' 1.0').replace(' 4 0', ' 4.0')} {n / total:.1%}" for name, n in licenses.most_common())
    retrieved = min(r["fetched"] for r in results) if results else TODAY
    write_sources("gbif", [{
        "key": SOURCE_KEY,
        "title": "GBIF occurrence search: records within 50 m of each lake outline",
        "publisher": "GBIF.org, with data from eBird (Cornell Lab of Ornithology), iNaturalist and other publishers",
        "url": "https://www.gbif.org/occurrence/search",
        "license": f"Per dataset, by record share: {license_note}",
        "credit": "Species records: GBIF.org occurrence data, mostly eBird",
        "citation": f"GBIF.org ({retrieved}) GBIF Occurrence Search, counts by lake via https://api.gbif.org/v1/occurrence/search",
        "asOf": retrieved,
        "retrieved": retrieved,
    }])
    print(f"wrote {len(rows)} lake rows, {len(species_rows):,} lake-species rows")


if __name__ == "__main__":
    main()
