#!/usr/bin/env python3
"""
iNaturalist observations per lake: what people have photographed in or right around each lake.

We pull every verifiable observation in a fixed study box around Bengaluru Urban and Rural once,
then count the ones that fall inside each lake outline grown by 50 m.
One pull serves any lake list, including disappeared lakes, with no further requests.
The box is split into tiles of at most 25,000 observations; each tile is paged by id
(id_above, 200 per page) at no more than one request a second across all tiles.
Pages come from the v2 API so we can ask for only the fields we need.

Only counts and species names are kept. Photos and user names are never stored;
user ids are cached locally only to count distinct observers.
Observations with obscured coordinates (private or threatened species) are skipped,
because their public location is randomised over a ~20 km cell.

Usage:
  .venv/bin/python scripts/sources/inaturalist.py [lakes.geojson] [keyProperty]

Output:
  data/sources/inaturalist.csv
  data/sources/inaturalist.sources.json
Cache: data/cache/inaturalist/ (tile list, observation pages, taxon names).
"""

import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
from shapely import STRtree, box, points

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, SOURCES, write_csv, write_sources  # noqa: E402
from _nature import Http, lake_args, lake_shapes, read_json, write_json  # noqa: E402

V1 = "https://api.inaturalist.org/v1"
V2 = "https://api.inaturalist.org/v2"
CACHE_DIR = CACHE / "inaturalist"
# Bengaluru Urban and Rural with a margin: (south, west, north, east).
STUDY_BOX = (12.50, 77.10, 13.60, 78.05)
TILE_MAX = 25000
PER_PAGE = 200
BUFFER_M = 50
TOP_TAXA = 10
TODAY = date.today().isoformat()
SOURCE_KEY = f"inaturalist-{TODAY[:7]}"
FIELDS = (
    "id,location,obscured,quality_grade,observed_on,license_code,user.id,"
    "taxon.id,taxon.rank_level,taxon.ancestor_ids,taxon.name,taxon.preferred_common_name"
)

HTTP = Http(min_interval=1.0)

COLUMNS = ["key", "observations", "researchGrade", "species", "observers", "lastObserved", "topTaxa", "source"]


def count(bounds):
    south, west, north, east = bounds
    params = {"verifiable": "true", "swlat": south, "swlng": west, "nelat": north, "nelng": east, "per_page": 0}
    return HTTP.get(f"{V1}/observations", params)["total_results"]


def split(bounds):
    """Quarter a box until each piece holds at most TILE_MAX observations."""
    total = count(bounds)
    if total <= TILE_MAX:
        return [{"bounds": list(bounds), "count": total}]
    south, west, north, east = bounds
    mid_lat, mid_lng = round((south + north) / 2, 5), round((west + east) / 2, 5)
    quarters = [
        (south, west, mid_lat, mid_lng), (south, mid_lng, mid_lat, east),
        (mid_lat, west, north, mid_lng), (mid_lat, mid_lng, north, east),
    ]
    return [tile for quarter in quarters for tile in split(quarter)]


def tiles():
    path = CACHE_DIR / "tiles.json"
    cached = read_json(path)
    if cached and cached["box"] == list(STUDY_BOX):
        return cached["tiles"]
    result = split(STUDY_BOX)
    write_json(path, {"fetched": TODAY, "box": list(STUDY_BOX), "tiles": result})
    return result


def compact(obs):
    """Keep only what we count. Species id is the taxon itself, or its parent for subspecies."""
    taxon = obs.get("taxon") or {}
    rank = taxon.get("rank_level")
    ancestors = taxon.get("ancestor_ids") or []
    species = taxon.get("id") if rank == 10 else (ancestors[-2] if rank and rank < 10 and len(ancestors) > 1 else None)
    lat, lng = (float(v) for v in obs["location"].split(",")) if obs.get("location") else (None, None)
    return {
        "id": obs["id"],
        "lat": lat,
        "lng": lng,
        "obscured": bool(obs.get("obscured")),
        "research": obs.get("quality_grade") == "research",
        "date": obs.get("observed_on"),
        "user": (obs.get("user") or {}).get("id"),
        "license": obs.get("license_code"),
        "species": species,
        "speciesName": taxon.get("name") if rank == 10 else None,
        "speciesCommon": taxon.get("preferred_common_name") if rank == 10 else None,
    }


def fetch_tile(tile):
    """Page through one tile by id, caching every page. A short page marks the tile complete."""
    south, west, north, east = tile["bounds"]
    folder = CACHE_DIR / "pages" / f"{south}_{west}_{north}_{east}"
    observations, id_above, page = [], 0, 0
    while True:
        path = folder / f"{page:05d}.json"
        cached = read_json(path)
        if cached is None:
            params = {
                "verifiable": "true", "swlat": south, "swlng": west, "nelat": north, "nelng": east,
                "order_by": "id", "order": "asc", "id_above": id_above, "per_page": PER_PAGE, "fields": FIELDS,
            }
            data = HTTP.get(f"{V2}/observations", params)
            cached = {"fetched": TODAY, "idAbove": id_above, "results": [compact(o) for o in data["results"]]}
            write_json(path, cached)
        observations.extend(cached["results"])
        if len(cached["results"]) < PER_PAGE:
            return observations, cached["fetched"]
        id_above = cached["results"][-1]["id"]
        page += 1
        if page % 25 == 0:
            print(f"  tile {south},{west}: {len(observations):,} of {tile['count']:,}", flush=True)


def species_names(ids):
    """Scientific and common names for species ids we only saw through subspecies."""
    path = CACHE_DIR / "taxa.json"
    names = read_json(path) or {}
    missing = sorted({str(i) for i in ids} - names.keys(), key=int)
    for start in range(0, len(missing), 30):
        batch = missing[start:start + 30]
        data = HTTP.get(f"{V1}/taxa/{','.join(batch)}") or {"results": []}
        for taxon in data["results"]:
            names[str(taxon["id"])] = [taxon.get("name"), taxon.get("preferred_common_name")]
        for key in batch:
            names.setdefault(key, [None, None])
        write_json(path, names)
    return names


def label(species_id, name, common):
    name = name or f"iNaturalist taxon {species_id}"
    return f"{name} ({common})" if common else name


def main():
    args = lake_args(__doc__.strip().splitlines()[0])
    lakes = list(lake_shapes(args.geometry, args.key, BUFFER_M))
    study = box(STUDY_BOX[1], STUDY_BOX[0], STUDY_BOX[3], STUDY_BOX[2])
    outside = [key for key, shape in lakes if not study.contains(shape)]
    if outside:
        raise SystemExit(f"{len(outside)} lakes fall outside the study box, widen STUDY_BOX: {outside[:10]}")
    print(f"{len(lakes)} lakes from {args.geometry}")

    tile_list = tiles()
    print(f"{len(tile_list)} tiles, {sum(t['count'] for t in tile_list):,} observations")
    with ThreadPoolExecutor(max_workers=3) as pool:
        pulled = list(pool.map(fetch_tile, tile_list))
    by_id = {o["id"]: o for observations, _ in pulled for o in observations}
    retrieved = min(fetched for _, fetched in pulled)
    usable = [o for o in by_id.values() if o["lat"] is not None and not o["obscured"]]
    print(f"{len(by_id):,} observations pulled, {len(by_id) - len(usable):,} skipped (obscured or no location)")

    tree = STRtree([shape for _, shape in lakes])
    obs_index, lake_index = tree.query(
        points(np.array([o["lng"] for o in usable]), np.array([o["lat"] for o in usable])), predicate="within"
    )
    per_lake = defaultdict(list)
    for obs_i, lake_i in zip(obs_index, lake_index):
        per_lake[int(lake_i)].append(usable[int(obs_i)])

    names = {}
    for o in usable:
        if o["speciesName"]:
            names[str(o["species"])] = [o["speciesName"], o["speciesCommon"]]
    in_lakes = {o["species"] for group in per_lake.values() for o in group if o["species"]}
    names.update({k: v for k, v in species_names(i for i in in_lakes if str(i) not in names).items() if k not in names})

    rows = []
    for i, (key, _) in enumerate(lakes):
        group = per_lake.get(i, [])
        species = Counter(o["species"] for o in group if o["species"])
        dates = [o["date"] for o in group if o["date"]]
        top = sorted(species.items(), key=lambda item: (-item[1], names[str(item[0])][0] or ""))[:TOP_TAXA]
        rows.append({
            args.key: key,
            "observations": len(group),
            "researchGrade": sum(o["research"] for o in group),
            "species": len(species),
            "observers": len({o["user"] for o in group if o["user"]}),
            "lastObserved": max(dates) if dates else None,
            "topTaxa": [label(s, *names[str(s)]) for s, _ in top],
            "source": SOURCE_KEY,
        })
    write_csv(SOURCES / "inaturalist.csv", rows, [args.key if c == "key" else c for c in COLUMNS])

    licenses = Counter((o["license"] or "all-rights-reserved").upper() for o in usable)
    total = sum(licenses.values()) or 1
    license_note = ", ".join(f"{name} {n / total:.1%}" for name, n in licenses.most_common(5))
    write_sources("inaturalist", [{
        "key": SOURCE_KEY,
        "title": "iNaturalist verifiable observations within 50 m of each lake outline",
        "publisher": "iNaturalist (California Academy of Sciences and National Geographic Society) and its observers",
        "url": "https://www.inaturalist.org/observations?place_id=any&verifiable=true",
        "license": f"Each observation carries its observer's license ({license_note}); we publish counts and species names only",
        "credit": "Observations: iNaturalist community, via iNaturalist.org",
        "asOf": retrieved,
        "retrieved": retrieved,
    }])
    print(f"wrote {len(rows)} rows, {sum(1 for r in rows if r['observations'])} lakes with observations")


if __name__ == "__main__":
    main()
