#!/usr/bin/env python3
"""
Rerun the per-lake stat scripts on the full lake list (data/lakes.geojson, keyed by id),
so disappeared lakes and lakes outlined from KGIS/OSM get the same numbers as the rest.

Drainage (cascade) runs only on lakes that exist and have an outline: water cannot
drain into a lake that is gone, and a point is too small to find its channel.

Usage: .venv/bin/python scripts/run_stats.py [script ...]   (default: all)
The registry must be current first: run scripts/build.py, then this, then build.py again.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, ROOT, SOURCES, read_csv  # noqa: E402

LAKES = ROOT / "data" / "lakes.geojson"
EXISTING = CACHE / "lakes_existing_outlines.geojson"
PY = str(ROOT / ".venv" / "bin" / "python")


def existing_outlines():
    """Lakes with an outline that the 2018 inventory does not list as disappeared."""
    gone = {r["empriCode"] for r in read_csv(SOURCES / "empri2018.csv") if r.get("status") == "disappeared"}
    features = json.loads(LAKES.read_text())["features"]
    keep = [f for f in features if f["properties"]["hasOutline"] and f["properties"].get("empriCode") not in gone]
    EXISTING.parent.mkdir(parents=True, exist_ok=True)
    EXISTING.write_text(json.dumps({"type": "FeatureCollection", "features": keep}))
    return EXISTING


def commands():
    lakes = str(LAKES)
    common = ["--input", lakes, "--key", "id", "--area-prop", "areaM2"]
    return {
        "jrc_water": ["jrc_water.py", *common],
        "worldcover": ["worldcover.py", *common],
        "dem": ["dem.py", *common],
        "historic_presence": ["historic_presence.py", *common],
        "cascade": lambda: ["cascade.py", "--input", str(existing_outlines()), "--key", "id", "--area-prop", "areaM2"],
        "gbif": ["gbif.py", lakes, "id"],
        "inaturalist": ["inaturalist.py", lakes, "id"],
        "sentinel2": ["sentinel2.py", lakes, "id"],
        "commons_photos": ["commons_photos.py", lakes, "--key", "id"],
    }


def main(names):
    table = commands()
    for name in names or table:
        spec = table[name]
        args = spec() if callable(spec) else spec
        print(f"== {name}", flush=True)
        subprocess.run([PY, str(ROOT / "scripts" / "sources" / args[0]), *args[1:]], check=True, cwd=ROOT)


if __name__ == "__main__":
    main(sys.argv[1:])
