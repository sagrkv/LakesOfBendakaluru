#!/usr/bin/env python3
"""
BBMP "Lakes in BBMP Custody": zone, lake, taluk, village and survey number, extent, and development status.

The CSV on OpenCity was extracted from a BBMP PDF table and is ragged:
a lake that spans several villages has one row per village parcel, and the extra rows leave
the serial number, zone and name blank. Some names were cut in half by the extraction.

We keep one row per parcel. `slNo` is carried down so the build can group parcels into a lake.
Acres and guntas are kept as given and also combined into decimal acres (40 guntas = 1 acre).

Output: data/sources/bbmp_custody.csv
"""

import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, clean, write_csv, write_sources  # noqa: E402

NAME = "bbmp_custody"
URL = (
    "https://data.opencity.in/dataset/36741bed-897a-496a-aec3-24341aec1953/resource/"
    "eb321f51-9750-4099-9362-f98e82197d0d/download/0eb79444-b763-4bd6-adf8-4f9a617fc7b3.csv"
)
RAW_FILE = RAW / NAME / "lakes_in_bbmp_custody.csv"

STATUSES = {
    "developed lake": "developed",
    "to be developed": "to be developed",
    "work in progress": "work in progress",
    "being used for other purpose": "used for other purpose",
    "tender in process": "tender in process",
}

ZONES = [
    ("mahadev", "Mahadevapura"),
    ("bommanahalli", "Bommanahalli"),
    ("rajarajeshwar", "Rajarajeshwari Nagar"),
    ("r.r.nagar", "Rajarajeshwari Nagar"),
    ("yelahanka", "Yelahanka"),
    ("dasarahalli", "Dasarahalli"),
    ("bangalore south", "South"),
    ("bangalore west", "West"),
    ("bangalore east", "East"),
    ("east", "East"),
    ("west", "West"),
    ("out side bbmp", "Outside BBMP"),
]

# Taluk text as written, in the order we look for it inside the merged "name / taluk" cell.
TALUKS = [
    (r"bangalore\s*north\s*(addl|addi|additional)\b.*", "Bangalore North (Additional)"),
    (r"bangalore\s*north.*", "Bangalore North"),
    (r"band?galore\s*south.*", "Bangalore South"),
    (r"bangalore\s*east.*", "Bangalore East"),
    (r"east\s*taluk", "Bangalore East"),
    (r"anekal", "Anekal"),
    (r"bangalore\s*$", None),
]

# Rows where the PDF extraction lost or mangled the lake name. Keyed by serial number.
PROBLEMS = {
    "18": "lake name cut off in the source; only '(Next to Brigade' survives",
    "32": "lake name cut off in the source; only 'Lake) Bangalore' survives",
    "37": "village cut off in the source; survey numbers incomplete",
    "43": "columns shifted in the source: name cell holds village-survey, village cell holds the taluk",
    "47": "lake name missing in the source; name cell holds only the taluk",
    "51": "name cell starts with a survey number",
    "126": "second parcel row has a stray 'Zone' in the zone column; serial 127 is missing and may be this row",
    "146": "village missing in the source",
    "159": "no village or survey number in the source",
}
# Of these, the ones whose name cell is only a fragment: keep it in nameTalukRaw, not as a name.
NAME_LOST = {"18", "32"}


def fetch():
    if not RAW_FILE.exists():
        RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (lakes-of-bendakaluru data build)"})
        RAW_FILE.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return RAW_FILE.read_bytes().decode("utf-8-sig")  # keep the bare CRs that mark cell wraps


def zone_of(text):
    if not text:
        return None
    low = text.lower()
    for needle, zone in ZONES:
        if needle in low:
            return zone
    return None


def split_name_taluk(text):
    """'Ambalipura Kelaginakere/ Bangalore East' and 'Yediyur LakeBangalore south' -> (name, taluk)."""
    if not text:
        return None, None
    for pattern, taluk in TALUKS:
        m = re.search(pattern, text, re.I)
        if m:
            name = text[: m.start()].strip(" /-")
            return (name or None), taluk
    return text.strip(" /-"), None


def parse_parcel(text):
    """'Kasavanalli-70', '0001, Yediyur-', 'Sompura 11, 12', 'Gunjur-301 (P)' -> (village, [survey numbers])."""
    if not text:
        return None, []
    village = " ".join(re.findall(r"[A-Za-z][A-Za-z .]*[A-Za-z]", text)).strip() or None
    if village and village.lower() in {"to", "p"}:
        village = None
    numbers = []
    for m in re.finditer(r"(\d+)\s*to\s*(\d+)|(\d+)(\s*\(P\))?", text):
        if m.group(1):
            numbers.append(f"{int(m.group(1))}-{int(m.group(2))}")
        else:
            numbers.append(f"{int(m.group(3))}{' (P)' if m.group(4) else ''}")
    # "to" and "P" are survey-number syntax, not part of the village name.
    if village:
        village = re.sub(r"\b(to|P)\b", "", village).strip() or None
    return village, numbers


# Words that start a new word after a cell wrap; any other lowercase continuation is a word cut in half.
WRAP_WORDS = {"kere", "lake", "taluk", "zone", "tanks", "nagar", "agrahara", "vaderahalli", "amanikere"}


def unwrap(cell):
    """The PDF wrapped long cells with a bare CR, sometimes mid-word ("Devarabeesanahal\\rli")."""
    cell = re.sub(r"\r(?=([a-z]+))", lambda m: " " if m.group(1) in WRAP_WORDS else "", cell)
    return cell.replace("\r", " ")


def number(text):
    text = clean(text)
    if text is None:
        return None
    return float(text) if "." in text else int(text)


def build():
    rows = list(csv.reader(io.StringIO(fetch())))
    header, body = rows[0], rows[1:]
    assert header[:7] == [
        "Sl No.", "Zone", "Name of Lake / Taluk", "Village Name & Survey No.", "Acres", "Guntas", "Other info"
    ], header

    out = []
    current = None
    for raw in body:
        sl, zone_raw, name_raw, parcel_raw, acres_raw, guntas_raw, status_raw = (clean(unwrap(c)) for c in raw[:7])
        if sl:
            name, taluk = split_name_taluk(name_raw)
            name = None if sl in NAME_LOST else name
            current = {"slNo": sl, "zoneRaw": zone_raw, "zone": zone_of(zone_raw), "nameRaw": name_raw,
                       "name": name, "taluk": taluk, "parcel": 0}
        else:
            current = {**current, "parcel": current["parcel"] + 1}
        village, surveys = parse_parcel(parcel_raw)
        acres, guntas = number(acres_raw), number(guntas_raw)
        area = None
        if acres is not None or guntas is not None:
            area = round((acres or 0) + (guntas or 0) / 40, 4)
        out.append(
            {
                "source": "bbmp-custody",
                "slNo": current["slNo"],
                "parcelIndex": current["parcel"],
                "zone": current["zone"],
                "zoneRaw": current["zoneRaw"],
                "lakeName": current["name"],
                "taluk": current["taluk"],
                "nameTalukRaw": current["nameRaw"],
                "village": village,
                "surveyNumbers": surveys,
                "villageSurveyRaw": parcel_raw,
                "acres": acres_raw,
                "guntas": guntas_raw,
                "areaAcres": area,
                "status": STATUSES.get((status_raw or "").lower(), status_raw),
                "statusRaw": status_raw,
                "problem": PROBLEMS.get(current["slNo"]),
            }
        )

    columns = list(out[0].keys())
    write_csv(SOURCES / f"{NAME}.csv", out, columns)
    write_sources(
        NAME,
        [
            {
                "key": "bbmp-custody",
                "title": "Lakes in BBMP Custody",
                "publisher": "Bruhat Bengaluru Mahanagara Palike (BBMP), via OpenCity",
                "url": "https://data.opencity.in/dataset/bengaluru-lakes-data-and-reports",
                "license": "not stated",
                "credit": "BBMP, via OpenCity",
                # Neither BBMP nor OpenCity dates the list.
                "asOf": "not stated",
                "retrieved": "2026-09-11",
            }
        ],
    )
    lakes = {r["slNo"] for r in out}
    print(f"{NAME}: {len(out)} parcel rows, {len(lakes)} lakes -> data/sources/{NAME}.csv")


if __name__ == "__main__":
    build()
