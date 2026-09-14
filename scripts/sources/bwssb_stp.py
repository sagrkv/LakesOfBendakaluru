#!/usr/bin/env python3
"""
BWSSB sewage treatment plants.

Two lists, kept as separate rows told apart by `source`:

  bwssb-stp-locations   OpenCity "BWSSB Sewage Treatment Plant Locations": 39 rows with lat/lon,
                        type, capacity in KLD and a functioning flag. 6 of the rows are
                        intermediate sewage pumping stations, not treatment plants. Undated.
  bwssb-stp-es-2024-25  Economic Survey of Karnataka: 34 BWSSB plants, 1,348.5 MLD in total, with
  bwssb-stp-es-2025-26  location, treatment process, drainage valley and that year's inflow. No
                        coordinates. The two years list the same plants; only the inflow differs.

The location list has known errors, kept as published: the three V. Valley rows have capacities
that do not match their names (the "150 MLD" row says 60,000 KLD and sits at the K&C Valley plant),
and Kadugodi "6 MLD" says 5,000 KLD. "Hebbal 60MLD" and "V.Valley 150 MLD" both sit at the K&C Valley
plant (12.94, 77.65), not in their own valleys, so their points are wrong. `capacityMldFromName` holds the figure in the plant's name.

Output: data/sources/bwssb_stp.csv
"""

import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, clean, write_csv, write_sources  # noqa: E402

NAME = "bwssb_stp"
OC = "https://data.opencity.in/dataset/"
FILES = {
    "bwssb-stp-locations": (
        OC + "de97d604-7791-43d1-8572-e460cd520ba0/resource/5b40965d-152d-4d09-a3f2-d5858f1a2e01/"
        "download/242994a9-af09-4a01-bbb7-aa6dfedd5541.csv",
        "stp_locations.csv",
    ),
    "bwssb-stp-es-2024-25": (
        OC + "987307b6-be14-4d83-80eb-f85fdd35851c/resource/f237230d-5e6e-483a-ac92-a5f2d5892ada/"
        "download/a8979805-e97b-47a3-9593-8396cd715974.csv",
        "stp_status_es_2024_25.csv",
    ),
    "bwssb-stp-es-2025-26": (
        OC + "699b7b8d-3813-4e44-8d70-cfdf1414ee85/resource/5a506604-c40a-4946-bbd1-006d8a51f531/"
        "download/ka-bwssb-stps-2025-26.csv",
        "stp_inflows_es_2025_26.csv",
    ),
}

COLUMNS = [
    "source", "stpId", "name", "lat", "lon", "type", "capacityKld", "capacityMld", "capacityMldFromName",
    "functioning", "locationNear", "process", "drainageZone", "inflowMld", "year",
]


def fetch(key):
    url, filename = FILES[key]
    path = RAW / NAME / filename
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (lakes-of-bendakaluru data build)"})
        path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return list(csv.DictReader(io.StringIO(path.read_bytes().decode("utf-8-sig"))))


def number(text):
    text = clean(text)
    return None if text is None else float(text)


def locations():
    rows = fetch("bwssb-stp-locations")
    assert len(rows) == 39, len(rows)
    out = []
    for r in rows:
        name = clean(r["STPName"])
        in_name = re.search(r"(\d+(?:\.\d+)?)\s*\.?\s*MLD", name, re.I)
        kld = number(r["TreatmentCapacity (KLD)"])
        out.append(
            {
                "source": "bwssb-stp-locations",
                "stpId": clean(r["STPId"]),
                "name": name,
                "lat": number(r["Latitude"]),
                "lon": number(r["Longitude"]),
                "type": clean(r["PlantType"]),
                "capacityKld": None if kld is None else int(kld),
                "capacityMld": None if kld is None else kld / 1000,
                "capacityMldFromName": float(in_name.group(1)) if in_name else None,
                "functioning": {"TRUE": True, "FALSE": False}.get(clean(r["Status"])),
            }
        )
    return out


def survey(key, year):
    rows = [r for r in fetch(key) if clean(r["Name"]) != "Total"]
    assert len(rows) == 34, (key, len(rows))
    out = []
    zone = None
    for i, r in enumerate(rows, 1):
        # The drainage zone is written once, on the first plant of each valley.
        zone = clean(r["Drainage Zone"]) or zone
        mld = number(r["Capacity in MLD"])
        out.append(
            {
                "source": key,
                "stpId": clean(r.get("_id")) or str(i),  # row order; the 2024-25 file has no id column
                "name": clean(r["Name"]),
                "capacityMld": mld,
                "capacityKld": int(mld * 1000),
                "locationNear": clean(r["Location near to"]),
                "process": clean(r["Type of process of treating sewage"]),
                "drainageZone": zone,
                "inflowMld": number(r["Inflow"]),
                "year": year,
            }
        )
    total = sum(r["capacityMld"] for r in out)
    assert abs(total - 1348.5) < 0.01, total
    return out


def build():
    out = locations() + survey("bwssb-stp-es-2024-25", "2024-25") + survey("bwssb-stp-es-2025-26", "2025-26")
    write_csv(SOURCES / f"{NAME}.csv", out, COLUMNS)
    write_sources(
        NAME,
        [
            {
                "key": "bwssb-stp-locations",
                "title": "BWSSB Sewage Treatment Plants (STP) Locations and Details",
                "publisher": "Bangalore Water Supply and Sewerage Board (BWSSB), via OpenCity",
                "url": "https://data.opencity.in/dataset/bwssb-sewage-treatment-plant-locations",
                "license": "Other (Public Domain)",
                "credit": "BWSSB, via OpenCity",
                "asOf": "not stated",
                "retrieved": "2026-09-11",
            },
            {
                "key": "bwssb-stp-es-2024-25",
                "title": "Economic Survey of Karnataka 2024-25: BWSSB STP Status",
                "publisher": "Planning, Programme Monitoring and Statistics Department, Government of Karnataka, via OpenCity",
                "url": "https://data.opencity.in/dataset/economic-survey-of-karnataka-2024-25",
                "license": "Other (Public Domain)",
                "credit": "Economic Survey of Karnataka 2024-25, via OpenCity",
                "asOf": "2024-25",
                "retrieved": "2026-09-11",
            },
            {
                "key": "bwssb-stp-es-2025-26",
                "title": "Economic Survey of Karnataka 2025-26: BWSSB STPs and Inflows",
                "publisher": "Planning, Programme Monitoring and Statistics Department, Government of Karnataka, via OpenCity",
                "url": "https://data.opencity.in/dataset/economic-survey-of-karnataka-2025-26",
                "license": "Other (Public Domain)",
                "credit": "Economic Survey of Karnataka 2025-26, via OpenCity",
                "asOf": "2025-26",
                "retrieved": "2026-09-11",
            },
        ],
    )
    counts = {k: sum(r["source"] == k for r in out) for k in FILES}
    print(f"{NAME}: {len(out)} rows {counts} -> data/sources/{NAME}.csv")


if __name__ == "__main__":
    build()
