#!/usr/bin/env python3
"""
Checks on the built data in public/data. Exits non-zero on any failure.
Run after scripts/build.py.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, ROOT, read_csv  # noqa: E402

STATUSES = {"exists", "disappeared", "converted"}
KINDS = {"kere", "katte", "kunte"}
CLASSES = {"A", "B", "C", "D", "E"}
LON, LAT = (77.0, 78.1), (12.5, 13.7)

failures = []


def fail(message):
    failures.append(message)


def source_keys(node, found):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "src":
                for keys in v.values():
                    found.update(keys if isinstance(keys, list) else [keys])
            elif k == "source" and isinstance(v, str):
                found.add(v)
            else:
                source_keys(v, found)
    elif isinstance(node, list):
        for v in node:
            source_keys(v, found)


def check_record(rec, ids, sources):
    rid = rec["id"]
    if rec.get("status") not in STATUSES:
        fail(f"{rid}: status {rec.get('status')!r}")
    if rec.get("kind") and rec["kind"] not in KINDS:
        fail(f"{rid}: kind {rec['kind']!r}")
    point = rec.get("location", {}).get("point")
    if point and not (LON[0] <= point[0] <= LON[1] and LAT[0] <= point[1] <= LAT[1]):
        fail(f"{rid}: point {point} outside Bengaluru")
    for field, value in rec.get("size", {}).items():
        if field != "src" and isinstance(value, (int, float)) and value < 0:
            fail(f"{rid}: size.{field} is negative")
    water = rec.get("water", {})
    for ref in [water.get("downstream")] + water.get("upstream", []):
        if ref and ref.get("id") and ref["id"] not in ids:
            fail(f"{rid}: drainage points at unknown lake {ref['id']}")
        if ref and ref.get("id") == rid:
            fail(f"{rid}: drains into itself")
    for entry in rec.get("waterQuality", {}).get("series", []):
        if entry.get("class") and entry["class"] not in CLASSES:
            fail(f"{rid}: water class {entry['class']!r} in {entry['month']}")
    for key in (k for k in list_keys(rec) if k != "per-entry"):
        if key not in sources:
            fail(f"{rid}: source key {key!r} has no citation")


def list_keys(rec):
    found = set()
    source_keys(rec, found)
    return found


def main():
    summaries = json.loads((OUT / "lakes.json").read_text())
    sources = json.loads((OUT / "sources.json").read_text())
    ids = [s["id"] for s in summaries]
    if len(ids) != len(set(ids)):
        fail("lakes.json has repeated ids")
    ids = set(ids)

    registry = read_csv(ROOT / "data" / "registry.csv")
    if {r["id"] for r in registry} != ids:
        fail("registry and lakes.json list different lakes")
    anchors = [r["anchor"] for r in registry]
    if len(anchors) != len(set(anchors)):
        fail("registry has repeated anchors")

    files = {p.stem for p in (OUT / "lake").glob("*.json")}
    if files != ids:
        fail(f"lake files and lakes.json differ by {len(files ^ ids)}")

    for path in sorted((OUT / "lake").glob("*.json")):
        check_record(json.loads(path.read_text()), ids, sources)

    for key, entry in sources.items():
        for field in ("title", "publisher", "url", "license"):
            if not entry.get(field):
                fail(f"sources.json {key}: missing {field}")

    past = json.loads((OUT / "past.json").read_text())
    past_ids = {row["id"] for row in past}
    gone = {row["id"] for row in summaries if row.get("status") != "exists"}
    if past_ids != gone:
        fail(f"past.json and the past lakes in lakes.json differ by {len(past_ids ^ gone)}")

    if failures:
        print(f"check_data: {len(failures)} problems")
        for message in failures[:50]:
            print("  " + message)
        sys.exit(1)
    print(f"check_data: ok ({len(ids)} lakes, {len(sources)} sources, {len(past)} past)")


if __name__ == "__main__":
    main()
