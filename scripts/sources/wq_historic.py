#!/usr/bin/env python3
"""
Older lake water quality tables from OpenCity, in one long table.

Datasets (the `dataset` column, which is also the source key):
  dmg-2011       Department of Mines and Geology lake tests, 2011: about 60 lakes, sampled at
                 inlet / middle / outlet. OCR'd CSV: "156 8" and "2:06" are decimals with the point
                 lost, "Nil" means not detected.
  lakes-2015     A one-page 2015 sheet of pH, conductivity, TDS and DO at nine lakes and one well,
                 with the water temperature written into some names ("Haralur Lake(T= 31.2)").
  jakkur-2015    Jakkur Lake monitoring, May 2015 - June 2016: eight fixed points (JK-1..JK-8),
                 from the lake itself to the raw sewage inlet and the STP outlet.
  nwmp-2021      CPCB National Water Quality Monitoring Programme 2021, lakes and ponds:
                 the yearly minimum and maximum for Karnataka stations. Station codes are the same
                 KSPCB codes as in kspcb_readings.csv.

Output: data/sources/wq_historic.csv
  dataset, stationId, stationCode, stationName, sampleLocation, date, lat, lon,
  parameter, value, qualifier, belowDetection, detectionLimit, unit, statistic, rawValue, source

  stationId       the KSPCB code (nwmp-2021), else a slug of lake name and sampling point
  sampleLocation  inlet / middle / outlet (dmg-2011) or the point's description (jakkur-2015)
  date            as precise as the source: YYYY, or YYYY-MM-DD
  parameter       same vocabulary as kspcb_readings.csv, plus eColi, aluminium, orp, colour,
                  chlorophyllA, dissolvedBod, dissolvedCod and three nitrate preservation tests
  value           the number; empty when not detected or not reported
  qualifier       ">" when printed as ">1600" (more than the test can count); "present" for a
                  coliform test reported only as present
  statistic       min / max for nwmp-2021, empty for single samples
  rawValue        the cell as printed, for checking

Run: .venv/bin/python scripts/sources/wq_historic.py
"""

import csv
import datetime
import io
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, clean, slugify, write_csv, write_sources  # noqa: E402

DIR = RAW / "wq_historic"
MANIFEST = DIR / "manifest.json"

FILES = {
    "dmg-2011": "https://data.opencity.in/dataset/c125a42f-2b5e-4664-9b87-236d615b9910/resource/08b9e909-9fae-4aa6-9e5d-43690fd8a6d3/download/3f883f14-43c1-4efc-b971-358b6ca025e1.csv",
    "lakes-2015": "https://data.opencity.in/dataset/36741bed-897a-496a-aec3-24341aec1953/resource/76774808-5caa-42bb-b3e8-15608fcb72aa/download/1fa9501f-5174-4a03-8199-5eb3f3805b44.pdf",
    "jakkur-2015": "https://data.opencity.in/dataset/36741bed-897a-496a-aec3-24341aec1953/resource/ec3af22c-a187-46dd-98c1-ece4ce2fb2e4/download/137964fe-8173-44b2-9717-5f0c4b6fa0de.pdf",
    "nwmp-2021": "https://data.opencity.in/dataset/b315fb5d-4625-457b-86e4-5fec7f7831ea/resource/60886be0-840a-44da-8c83-9823b193c8b6/download/4e742cc5-01ee-4851-ad32-8ce486bf552b.pdf",
}
EXT = {"dmg-2011": "csv"}

COLUMNS = [
    "dataset", "stationId", "stationCode", "stationName", "sampleLocation", "date", "lat", "lon",
    "parameter", "value", "qualifier", "belowDetection", "detectionLimit", "unit", "statistic", "rawValue", "source",
]


def fetch(key):
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    path = DIR / f"{key}.{EXT.get(key, 'pdf')}"
    if not path.exists() or key not in manifest:
        DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(FILES[key], headers={"User-Agent": "Mozilla/5.0 (lakes-of-bendakaluru data build)"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            path.write_bytes(resp.read())
        manifest[key] = {"url": FILES[key], "retrieved": datetime.date.today().isoformat()}
        MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    return path, manifest[key]["retrieved"]


def number(text):
    text = text.lstrip("0") or "0"
    return "0" + text if text.startswith(".") else text


def reading(raw, repair=False):
    """Printed cell -> (value, qualifier, belowDetection, detectionLimit), or None for an empty cell."""
    if raw is not None and re.fullmatch(r"\W*nil\W*", str(raw).strip(), re.I):
        return ("", "", True, "")  # "Nil": not detected
    s = clean(raw)
    if s is None:
        return None if raw is None or not str(raw).strip() else ("", "", False, "")
    s = s.strip()
    if repair:
        # OCR slips: lost decimal points ("156 8", "0 48", "5. 75", "2:06"), "0.l" for 0.1, stray "?".
        s = re.sub(r"^[?!]\s*", "", s)
        s = re.sub(r"^(\d+)(?:\s+|\.\s+|:)(\d+)$", r"\1.\2", s)
        if re.fullmatch(r"[\d.]*l[\d.l]*", s) and re.search(r"\d", s):
            s = s.replace("l", "1")
    if re.fullmatch(r"pre\s*sent", s, re.I):
        return ("", "present", False, "")
    s = s.lstrip(".")
    match = re.fullmatch(r"([<>])\s*(\d*\.?\d+)", s)
    if match:
        if match.group(1) == "<":
            return ("", "", True, number(match.group(2)))
        return (number(match.group(2)), ">", False, "")
    if re.fullmatch(r"-?\d*\.?\d+(E[+-]?\d+)?", s, re.I):
        value = float(s)
        if "e" in s.lower():
            return (str(int(value)) if value.is_integer() else repr(value), "", False, "")
        return (("-" if s.startswith("-") else "") + number(s.lstrip("-")), "", False, "")
    return ("", "", False, "")  # "-", ranges like "40-50", text: not a usable number


def row(dataset, station, parameter, unit, raw, *, repair=False, statistic="", **fields):
    parsed = reading(raw, repair)
    if parsed is None:
        return None
    value, qualifier, bdl, limit = parsed
    return {
        "dataset": dataset,
        "stationId": station["id"],
        "stationCode": station.get("code"),
        "stationName": station["name"],
        "sampleLocation": station.get("location"),
        "date": fields["date"],
        "lat": station.get("lat"),
        "lon": station.get("lon"),
        "parameter": parameter,
        "value": value,
        "qualifier": qualifier,
        "belowDetection": "true" if bdl else "false",
        "detectionLimit": limit,
        "unit": unit,
        "statistic": statistic,
        "rawValue": re.sub(r"\s+", " ", str(raw)).strip() if raw is not None else None,
        "source": dataset,
    }


# ---------- DMG 2011 ----------

DMG_PARAMS = {
    "CI": ("chloride", "mg/L"),  # "Cl" read as "CI" by the OCR
    "PO-P": ("phosphate", "mg/L as P"),
    "TSS": ("tss", "mg/L"),
    "DO": ("dissolvedOxygen", "mg/L"),
    "COD": ("cod", "mg/L"),
    "NO3": ("nitrate", "mg/L as NO3"),
    "TH": ("totalHardness", "mg/L as CaCO3"),
    "F": ("fluoride", "mg/L"),
    "pH": ("ph", ""),
    "Zn": ("zinc", "mg/L"),
    "pb": ("lead", "mg/L"),
    "Cu": ("copper", "mg/L"),
    "Mn": ("manganese", "mg/L"),
    "Al": ("aluminium", "mg/L"),
    "Cr": ("chromium", "mg/L"),
    "EC MPN/100 ml": ("eColi", "MPN/100mL"),
    "TC MPN/ 100 ml": ("totalColiform", "MPN/100mL"),
}


def dmg_2011():
    path, retrieved = fetch("dmg-2011")
    out, seen = [], {}
    for rec in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))):
        name = clean(rec["Name of the lake"])
        location = clean(rec["Sample Location"])
        if not name:
            continue
        # A few lakes list the same sampling point twice with different results: number the repeats.
        sid = f"{slugify(name)}-{slugify(location or 'unknown')}"
        seen[sid] = seen.get(sid, 0) + 1
        station = {"id": sid if seen[sid] == 1 else f"{sid}-{seen[sid]}", "name": name, "location": location}
        for column, (parameter, unit) in DMG_PARAMS.items():
            r = row("dmg-2011", station, parameter, unit, rec.get(column), repair=True, date="2011")
            if r:
                out.append(r)
    return out, retrieved


# ---------- the 2015 sheet ----------


def lakes_2015():
    path, retrieved = fetch("lakes-2015")
    out = []
    with pdfplumber.open(path) as pdf:
        table = pdf.pages[0].extract_tables()[0]
    for cells in table[1:]:
        day, source_name, ph, ec, tds, do = [clean(c) for c in cells]
        # Dates are day/month/year and the rows run in date order, so "6/9/2015" between
        # 31/05 and 16/07 cannot be 6 September; it is taken as 9 June (month/day).
        d, m, y = [int(x) for x in day.split("/")]
        if (d, m) == (6, 9):
            d, m = 9, 6
        temp = re.search(r"\(T\s*=\s*([\d.]+)\s*C?\)", source_name)
        name = clean(re.sub(r"\(T\s*=.*?\)", "", source_name))
        station = {"id": slugify(name), "name": name}
        date = f"{y:04d}-{m:02d}-{d:02d}"
        for parameter, unit, raw in (
            ("ph", "", ph),
            ("conductivity", "uS/cm", ec),
            ("tds", "mg/L", tds),
            # Values of 15-36 mg/L are far above saturation; printed as given.
            ("dissolvedOxygen", "mg/L", do),
            ("temperature", "degC", temp.group(1) if temp else None),
        ):
            r = row("lakes-2015", station, parameter, unit, raw, date=date)
            if r:
                out.append(r)
    return out, retrieved


# ---------- Jakkur 2015-16 ----------

# (parameter, unit, left edge in points) for the measurement columns of the Jakkur sheet.
JAKKUR_COLUMNS = [
    ("temperature", "degC", 244), ("colour", "Hazen", 258), ("turbidity", "NTU", 273), ("ph", "", 288),
    ("conductivity", "uS/cm", 301), ("orp", "mV", 320), ("dissolvedOxygen", "mg/L", 333),
    ("nitrate", "mg/L", 353), ("totalAlkalinity", "mg/L", 369), ("fecalColiform", "MPN/100mL", 387),
    ("tss", "mg/L", 408), ("bod", "mg/L", 439), ("dissolvedBod", "mg/L", 462), ("cod", "mg/L", 490),
    ("dissolvedCod", "mg/L", 512), ("phosphate", "mg/L", 538), ("ammoniacalNitrogen", "mg/L as N", 562),
    ("chlorophyllA", "mg/m3", 585), (None, None, 610), (None, None, 638), ("remarks", None, 655),
    ("nitrateAcidPreserved", "mg/L", 710), ("nitrateFrozen", "mg/L", 731), ("nitrateNaohNeutralised", "mg/L", 758),
]
JAKKUR_TEXT = [("code", 196), ("source", 211), ("time", 226)]


def degrees_minutes(value, low, high):
    """The sheet writes 13°05.0120' as 13.050120. Convert, and drop impossible ones (minutes > 60)."""
    deg = int(value)
    minutes = round((value - deg) * 100, 6)
    if minutes >= 60:
        return None
    result = round(deg + minutes / 60, 6)
    return result if low <= result <= high else None


def jakkur_2015():
    path, retrieved = fetch("jakkur-2015")
    edges = [(k, None, x) for k, x in JAKKUR_TEXT] + JAKKUR_COLUMNS
    lefts = [e[2] for e in edges]
    out, samples = [], 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=1.5, y_tolerance=1)
            anchors = [w for w in words if 88 < w["x0"] < 112 and re.fullmatch(r"\d{1,2}/\d{1,2}/20\d\d", w["text"])]
            if not anchors:
                continue
            ys = [w["top"] for w in anchors]
            cells = [{} for _ in anchors]
            for w in words:
                if w["x0"] < 155 or w["top"] < ys[0] - 2:
                    continue
                i = min(range(len(ys)), key=lambda k: abs(ys[k] - w["top"]))
                if abs(ys[i] - w["top"]) > 3:
                    continue
                if 155 <= w["x0"] < 177:
                    cells[i].setdefault("lat", []).append(w["text"])
                    continue
                if 177 <= w["x0"] < 196:
                    cells[i].setdefault("lon", []).append(w["text"])
                    continue
                j = max(k for k, x in enumerate(lefts) if x <= (w["x0"] + w["x1"]) / 2 or k == 0)
                cells[i].setdefault(edges[j][0], []).append(w["text"])
            for anchor, cell in zip(anchors, cells):
                d, m, y = [int(x) for x in anchor["text"].split("/")]
                code = " ".join(cell.get("code", []))
                if not re.fullmatch(r"JK-\d", code):
                    continue
                samples += 1
                remarks = re.sub(r"\s*\([^)]*\)?", "", " ".join(cell.get("remarks", [])))  # "(Green colour)" etc.
                lat = degrees_minutes(float(cell["lat"][0]), 12.8, 13.3) if cell.get("lat") else None
                lon = degrees_minutes(float(cell["lon"][0]), 77.3, 77.9) if cell.get("lon") else None
                station = {
                    "id": f"jakkur-lake-{code.lower()}",
                    "code": code,
                    "name": "Jakkur Lake",
                    "location": clean(remarks),
                    "lat": lat if lon is not None else None,
                    "lon": lon if lat is not None else None,
                }
                for parameter, unit, _ in JAKKUR_COLUMNS:
                    if parameter in (None, "remarks"):
                        continue
                    raw = " ".join(cell.get(parameter, [])) or None
                    if raw and re.search(r"[A-Za-z]{3,}", raw) and not re.fullmatch(r"\W*nil\W*", raw, re.I):
                        continue  # a long remark running on into the last columns
                    r = row("jakkur-2015", station, parameter, unit, raw, date=f"{y:04d}-{m:02d}-{d:02d}")
                    if r:
                        out.append(r)
    # The remark column adds notes to some samples ("... (More turbid water)"); name each point by its usual remark.
    usual = {}
    for r in out:
        usual.setdefault(r["stationId"], Counter())[r["sampleLocation"]] += 1
    out = [{**r, "sampleLocation": usual[r["stationId"]].most_common(1)[0][0]} for r in out]
    return out, retrieved, samples


# ---------- NWMP 2021 ----------

NWMP_PARAMS = [
    ("temperature", "degC"), ("dissolvedOxygen", "mg/L"), ("ph", ""), ("conductivity", "uS/cm"), ("bod", "mg/L"),
    ("nitrateNitrite", "mg/L as N"), ("fecalColiform", "MPN/100mL"), ("totalColiform", "MPN/100mL"),
]


def nwmp_2021():
    path, retrieved = fetch("nwmp-2021")
    out, stations = [], 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for cells in table:
                    if len(cells) != 20 or clean(cells[3]) != "KARNATAKA" or not re.fullmatch(r"\d{3,5}", clean(cells[0]) or ""):
                        continue
                    stations += 1
                    code = clean(cells[0])
                    station = {"id": code, "code": code, "name": clean(cells[1]), "location": clean(cells[2])}
                    for k, (parameter, unit) in enumerate(NWMP_PARAMS):
                        for offset, statistic in ((0, "min"), (1, "max")):
                            r = row("nwmp-2021", station, parameter, unit, cells[4 + 2 * k + offset], statistic=statistic, date="2021")
                            if r:
                                out.append(r)
    return out, retrieved, stations


def build():
    dmg, dmg_retrieved = dmg_2011()
    sheet, sheet_retrieved = lakes_2015()
    jakkur, jakkur_retrieved, jakkur_samples = jakkur_2015()
    nwmp, nwmp_retrieved, nwmp_stations = nwmp_2021()
    rows = dmg + sheet + jakkur + nwmp
    write_csv(SOURCES / "wq_historic.csv", rows, COLUMNS)
    lakes_page = "https://data.opencity.in/dataset/bengaluru-lakes-data-and-reports"
    write_sources(
        "wq_historic",
        [
            {
                "key": "dmg-2011",
                "title": "Bangalore Lakes Water Quality Results (2011)",
                "publisher": "Department of Mines and Geology, Karnataka (via India Water Portal and OpenCity)",
                "url": "https://data.opencity.in/dataset/bengaluru-lakes-water-quality-data",
                "license": "not stated",
                "credit": "Water quality 2011: Department of Mines and Geology, Karnataka",
                "asOf": "2011",
                "retrieved": dmg_retrieved,
            },
            {
                "key": "lakes-2015",
                "title": "Bangalore Lakes - Water Quality (2015)",
                "publisher": "not stated; listed on OpenCity under Bengaluru Lakes Data and Reports",
                "url": lakes_page,
                "license": "not stated",
                "credit": "Water quality 2015: Bengaluru Lakes Data and Reports, OpenCity",
                "asOf": "2015",
                "retrieved": sheet_retrieved,
            },
            {
                "key": "jakkur-2015",
                "title": "Jakkur Lake: analysis 2016",
                "publisher": "not stated; listed on OpenCity under Bengaluru Lakes Data and Reports",
                "url": lakes_page,
                "license": "not stated",
                "credit": "Jakkur Lake water analysis 2015-16: Bengaluru Lakes Data and Reports, OpenCity",
                "asOf": "2016",
                "retrieved": jakkur_retrieved,
            },
            {
                "key": "nwmp-2021",
                "title": "Water Quality Data for Lakes and Ponds - NWMP 2021",
                "publisher": "Central Pollution Control Board (CPCB)",
                "url": "https://data.opencity.in/dataset/water-quality-data-of-lakes-and-ponds-in-india",
                "license": "Other (Public Domain), as marked on OpenCity",
                "credit": "Water quality 2021: Central Pollution Control Board, NWMP",
                "asOf": "2021",
                "retrieved": nwmp_retrieved,
            },
        ],
    )
    print(
        f"wq_historic: {len(rows)} readings | dmg-2011 {len(dmg)} from {len({r['stationId'] for r in dmg})} sampling points"
        f" | lakes-2015 {len(sheet)} | jakkur-2015 {len(jakkur)} from {jakkur_samples} samples"
        f" | nwmp-2021 {len(nwmp)} from {nwmp_stations} Karnataka stations"
    )


if __name__ == "__main__":
    build()
