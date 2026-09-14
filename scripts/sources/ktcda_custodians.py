#!/usr/bin/env python3
"""
KTCDA "List of Lakes in Bengaluru": which agency looks after each lake.

KTCDA publishes four PDFs, one per custodian: BBMP (201 lakes, with ward and assembly
constituency), BDA (5), Karnataka Forest Department (4) and BMRCL (1), each with taluk.
OpenCity mirrors the same four files byte for byte as "Bengaluru Lakes and Their Maintainers"
(2024). OpenCity's CSV transcription of the BBMP list truncates some names, so we read the PDFs.

The BBMP list's ward numbers are from the 198-ward map (2010 delimitation):
ward 150 Bellandur, 149 Varthur, 54 Hoodi.

Output: data/sources/ktcda_custodians.csv
"""

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, clean, write_csv, write_sources  # noqa: E402

NAME = "ktcda_custodians"
PAGE = "https://ktcda.karnataka.gov.in/28/list-of-lakes-in-bengaluru/en"
BASE = "https://ktcda.karnataka.gov.in/storage/pdf-files/"
# custodian code (as used in the ATREE data where it exists) -> KTCDA file name, expected row count
FILES = {
    "BBMP": ("BBMP Lakes.pdf", 201),
    "BDA": ("BDA Lakes.pdf", 5),
    "KFD": ("LAKES_Forest.pdf", 4),
    "BMRCL": ("BMRCL Lakes.pdf", 1),
}
AGENCY = {
    "BBMP": "Bruhat Bengaluru Mahanagara Palike",
    "BDA": "Bangalore Development Authority",
    "KFD": "Karnataka Forest Department",
    "BMRCL": "Bangalore Metro Rail Corporation Limited",
}

# Assembly constituency spellings in the BBMP list -> official name.
CONSTITUENCIES = {
    "yeshwanthpura": "Yeshwanthpur",
    "yashwanthpura": "Yeshwanthpur",
    "yeshwanthapur": "Yeshwanthpur",
    "rajarajeshwarinagara": "Rajarajeshwarinagar",
    "rajarajeshwari nagar": "Rajarajeshwarinagar",
    "sarvagna nagara": "Sarvagnanagar",
    "c.v.raman nagara": "C.V. Raman Nagar",
    "c.v.raman nagar": "C.V. Raman Nagar",
    "shivajinagar": "Shivajinagar",
    "yalahanka": "Yelahanka",
    "kr puram": "K.R. Pura",
    "mahadevapura": "Mahadevapura",
    "bommanahalli": "Bommanahalli",
    "bengaluru south": "Bangalore South",
    "byatarayanapura": "Byatarayanapura",
    "dasarahalli": "Dasarahalli",
    "padmanabanagar": "Padmanabhanagar",
    "govindarajanagara": "Govindrajnagar",
    "anekal": "Anekal",
    "anekal & bengaluru south": "Anekal; Bangalore South",
    "basavanagudi": "Basavanagudi",
    "vijayanagara": "Vijayanagar",
    "chikkapete": "Chickpet",
    "btm layout": "B.T.M. Layout",
    "malleshwaram": "Malleshwaram",
}


def fetch():
    folder = RAW / NAME
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for code, (filename, _) in FILES.items():
        path = folder / filename.replace(" ", "_")
        if not path.exists():
            url = BASE + urllib.parse.quote(filename)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (lakes-of-bendakaluru data build)"})
            path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        paths[code] = path
    return paths


def table_rows(path):
    """Data rows of every table: first cell is a serial number, skipping the '1 2 3 4' column-number row."""
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    cells = [(c or "") for c in row]
                    if cells[0].strip().isdigit() and cells[1].strip() != "2":
                        rows.append(cells)
    return rows


def parse_wards(text):
    """'Ward No: 184\\nUttarahalli,\\nWard No: 197\\nVassanthpura' -> [(184, 'Uttarahalli'), (197, 'Vassanthpura')]."""
    if not text:
        return []
    wards = []
    for part in re.split(r"\s*&\s*|,\s*(?=Ward No)", text):
        number = re.search(r"\d+", part)
        name = re.sub(r"ward\s*no\.?\s*[:.\-]?|\bward\b|\d+|[(),.:\-]", " ", part, flags=re.I)
        name = clean(name)
        wards.append((int(number.group()) if number else None, name))
    return wards


def constituency(text):
    if not text:
        return None, None
    low = re.sub(r"^\d+\s*-?\s*", "", text.lower()).strip()
    if "bangalore north" in low:
        return None, "Bangalore North (Additional)"  # a taluk written in the constituency column
    if "ward no" in low:
        low = low.split(",")[0]
    return CONSTITUENCIES.get(low, clean(text)), None


def build():
    paths = fetch()
    out = []
    for code, (filename, expected) in FILES.items():
        rows = table_rows(paths[code])
        assert len(rows) == expected, f"{filename}: {len(rows)} rows, expected {expected}"
        for cells in rows:
            cells = [clean(c) for c in cells]
            if code == "BBMP":
                sl, ward_raw, ac_raw, name_raw = cells[:4]
                taluk_raw = None
            else:
                sl, taluk_raw, name_raw = cells[:3]
                ward_raw = ac_raw = None
            disused = bool(name_raw and re.search(r"\(disused lake\)", name_raw, re.I))
            name = clean(re.sub(r"\(disused lake\)", "", name_raw or "", flags=re.I))
            outside = bool(ward_raw and "out of bbmp" in ward_raw.lower())
            wards = [] if outside else parse_wards(ward_raw)
            ac, taluk_from_ac = constituency(ac_raw)
            taluk = taluk_raw
            if taluk and taluk.lower().startswith("anekal"):
                taluk = "Anekal"  # "Anekal talk"
            out.append(
                {
                    "source": "ktcda-lakes-2024",
                    "custodian": code,
                    "custodianName": AGENCY[code],
                    "slNo": int(sl),
                    "lakeName": name,
                    "disused": disused,
                    "wardNumbers": [w[0] for w in wards if w[0] is not None],
                    "wardNames": [w[1] for w in wards if w[1]],
                    "wardMap": "bbmp-2010-198" if wards else None,
                    "wardRaw": ward_raw,
                    "assemblyConstituency": ac,
                    "assemblyConstituencyRaw": ac_raw,
                    "taluk": taluk or taluk_from_ac,
                    "outsideBbmp": outside,
                }
            )

    columns = list(out[0].keys())
    write_csv(SOURCES / f"{NAME}.csv", out, columns)
    write_sources(
        NAME,
        [
            {
                "key": "ktcda-lakes-2024",
                "title": "List of Lakes in Bengaluru (lakes under BBMP, BDA, Forest Department and BMRCL)",
                "publisher": "Karnataka Tank Conservation and Development Authority (KTCDA)",
                "url": PAGE,
                "license": "not stated (OpenCity's mirror, 'Bengaluru Lakes and Their Maintainers', marks it public domain)",
                "credit": "KTCDA, Government of Karnataka",
                "asOf": "2024",
                "retrieved": "2026-09-11",
            }
        ],
    )
    counts = {code: sum(r["custodian"] == code for r in out) for code in FILES}
    print(f"{NAME}: {len(out)} lakes {counts} -> data/sources/{NAME}.csv")


if __name__ == "__main__":
    build()
