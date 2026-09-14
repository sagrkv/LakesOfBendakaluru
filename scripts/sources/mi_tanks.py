#!/usr/bin/env python3
"""
Karnataka Minor Irrigation Department tanks, from the National Water Data Portal (India-WRIS).

The statewide CSV lists 3,404 tanks with owner, location down to village, command and spread area,
storage, embankment and waste weir. We keep the Bengaluru Urban and Bengaluru Rural rows.
The file has no coordinates, so matching has to go by village and name.

The CSV is Windows-1252 encoded. In the waste weir column some rows hold a ditto mark ('"', '…"…')
meaning "same as the row above"; we resolve it from the previous row in file order and keep the raw text.

Output: data/sources/mi_tanks.csv
"""

import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, clean, write_csv, write_sources  # noqa: E402

NAME = "mi_tanks"
DATASET = "https://nwdp.nwic.gov.in/dataset/karnataka-minor-irrigation-tank"
URL = (
    "https://nwdp.nwic.gov.in/dataset/5ebfc603-d347-43e9-a827-ae07f47188b4/resource/"
    "52dc620d-5020-4885-a870-cd6d26064f3b/download/karnatka_minor_irregation_tank.csv"
)
RAW_FILE = RAW / NAME / "karnatka_minor_irregation_tank.csv"
DISTRICTS = {"Bengaluru Urban", "Bengaluru Rural"}

WEIRS = [
    (r"sloping\s*ap+ron", "sloping apron"),
    (r"clear\s*over\s*fall", "clear overfall"),
    (r"^over\s*fall", "overfall"),
    (r"flush\s*escape", "flush escape"),
    (r"ogee", "ogee weir"),
    (r"natural", "natural"),
]

# source column -> our column
COLUMNS = {
    "Tank ID": "miTankId",
    "Tank Name": "name",
    "Tank Owner": "owner",
    "District": "district",
    "Taluk": "taluk",
    "GPName": "gramPanchayat",
    "VillageName": "village",
    "Command Area (Ha)": "commandAreaHa",
    "Tank Spread Area (Ha)": "spreadAreaHa",
    "Storage Capacity (MCFT)": "storageMcft",
    "Designed Water Utilization (MCFT)": "designedUtilisationMcft",
    "Embankment Type": "embankmentType",
    "Embankment Height (m)": "embankmentHeightM",
    "Embankment Top Width (m)": "embankmentTopWidthM",
    "Embankment Length (m)": "embankmentLengthM",
    "Waste Weir Type": "wasteWeirTypeRaw",
    "Kodi Length Details": "kodiLengthM",
    "Waste Weir Flow (cumecs)": "wasteWeirFlowCumecs",
}


def fetch():
    if not RAW_FILE.exists():
        RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (lakes-of-bendakaluru data build)"})
        RAW_FILE.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    return RAW_FILE.read_bytes().decode("cp1252")


def weir_type(raw, previous):
    if raw is None:
        return None
    if not re.search(r"[a-z]", raw, re.I):  # a ditto mark
        return previous
    for pattern, label in WEIRS:
        if re.search(pattern, raw, re.I):
            return label
    return raw.lower()


def build():
    rows = list(csv.DictReader(io.StringIO(fetch())))
    assert len(rows) == 3404, f"expected 3,404 tanks statewide, got {len(rows)}"
    assert set(COLUMNS) <= set(rows[0]), sorted(set(COLUMNS) - set(rows[0]))

    out = []
    previous_weir = None
    for row in rows:
        record = {ours: clean(row[theirs]) for theirs, ours in COLUMNS.items()}
        weir = weir_type(record["wasteWeirTypeRaw"], previous_weir)
        previous_weir = weir
        if record["district"] not in DISTRICTS:
            continue
        out.append({"source": "nwdp-mi-tanks", **record, "wasteWeirType": weir})

    columns = ["source", *COLUMNS.values(), "wasteWeirType"]
    write_csv(SOURCES / f"{NAME}.csv", out, columns)
    write_sources(
        NAME,
        [
            {
                "key": "nwdp-mi-tanks",
                "title": "Minor Irrigation Tank Karnataka",
                "publisher": "Minor Irrigation Department, Karnataka, via the National Water Data Portal (NWIC, India-WRIS)",
                "url": DATASET,
                "license": "Other (Open)",
                "credit": "Karnataka Minor Irrigation Department, National Water Data Portal",
                "asOf": "2026-07",  # date the portal published this resource; the data itself is undated
                "retrieved": "2026-09-11",
            }
        ],
    )
    by_district = {d: sum(r["district"] == d for r in out) for d in sorted(DISTRICTS)}
    print(f"{NAME}: {len(out)} tanks {by_district} of {len(rows)} statewide -> data/sources/{NAME}.csv")


if __name__ == "__main__":
    build()
