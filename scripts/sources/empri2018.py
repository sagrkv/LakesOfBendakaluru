#!/usr/bin/env python3
"""
EMPRI 2018 inventory of water bodies in the Bengaluru Metropolitan Area, done for KLCDA.

Volume II has one PDF per taluk. Each holds a 64-attribute database split into four ruled tables
(morphometric, non-existing, water quality and biota, issues), then a two-page atlas sheet for
most kere. Every water body has a serial number (1-1521, unique across taluks) that ties the four
tables together, and an EMPRI code such as "BUBEVRamb_kr2-505".

Outputs:
  data/sources/empri2018.csv                one row per water body (1,521)
  data/sources/empri2018_water_quality.csv  long form, one row per sampling point and parameter
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, SOURCES, clean, write_csv, write_sources  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empri2018_atlas import ATLAS_COLUMNS, parse_atlas  # noqa: E402
from empri2018_vocab import DIRECTION_COLUMNS, LIST_COLUMNS, TEXT_COLUMNS, normalise, tidy_text  # noqa: E402

NAME = "empri2018"
DIR = CACHE / NAME
KEY = "empri-2018"
DATASET = "https://data.opencity.in/dataset/inventory-of-lakes-bengaluru-metropolitan-area"
BASE = "https://data.opencity.in/dataset/6fcbc4bc-e700-43af-b919-3d923d810a3f/resource"

# Volume II parts, in serial-number order.
VOLUMES = {
    "north": ("Bengaluru North", f"{BASE}/64147d0a-8f92-4231-b3d3-18447ab9ab5f/download/0a901419-0ec5-47cd-ac31-5e504b855ca1.pdf"),
    "east": ("Bengaluru East", f"{BASE}/976d0d35-60a4-4eba-b6b2-a6f5d05d32ec/download/1319334b-2855-4afa-bc40-3854347d4e9c.pdf"),
    "anekal": ("Anekal", f"{BASE}/69faac34-01a8-4d01-86c4-cb189f0f6317/download/d4acc208-6c89-4dd4-b281-a3805752a894.pdf"),
    "south": ("Bengaluru South", f"{BASE}/39612dd3-2599-493e-bef9-58c0ade01f71/download/aca0f147-e9e6-4ce9-bfaa-eaaf2fb1a90b.pdf"),
}
VOLUME_1 = f"{BASE}/259941c1-9700-4bf8-bcaf-939b8cd8650d/download/2f8191e1-62d1-40fa-a9de-57ef36cfcfdc.pdf"

SECTIONS = {"MORPHOMETRIC": "morph", "NON-EXISTING": "nonexist", "WATER QUALITY": "wq", "ISSUES": "issues"}
WIDTH = {"morph": 30, "nonexist": 9, "wq": 28, "issues": 16}
# Double-drawn rules and doubled glyphs split columns unless snapped and deduped.
TABLE_SETTINGS = {"snap_tolerance": 6, "join_tolerance": 6, "intersection_tolerance": 6}

# Positional columns of each table (index in the extracted row).
MORPH = {
    "no": 0, "hobli": 2, "village": 3, "name": 4, "nameOther": 5, "code": 6, "custodian": 7, "lat": 8, "lon": 9,
    "extent": 10, "survey": 11, "regime": 12, "year": 13, "elevation": 14, "depth": 15, "islands": 16,
    "inletDrains": 17, "wasteWeirs": 18, "sluiceGates": 19, "culverts": 20, "surroundingArea": 21,
    "checkDams": 22, "fenceType": 23, "presentStatus": 24, "waterUsage": 25, "visitDate": 26,
    "staff": 27, "researcher": 28, "remarks": 29,
}
NONEXIST = {"no": 0, "village": 3, "name": 4, "extent": 5, "convertedTo": 6, "convertedBy": 7, "visitDate": 8}
WQ_PARAMS = [
    # (column, parameter, unit)
    (8, "waterTemperature", "°C"),
    (9, "lightTransparency", "cm"),
    (10, "ph", ""),
    (11, "conductivity", "µS/cm"),
    (12, "tds", "mg/l"),
    (13, "tss", "mg/l"),
    (14, "turbidity", "NTU"),
    (15, "dissolvedOxygen", "mg/l"),
    (16, "cod", "mg/l"),
    (17, "bod", "mg/l"),
    (18, "totalPhosphate", "mg/l"),
    (19, "tkn", "mg/l"),
    (20, "totalColiform", "MPN/100ml"),
    (21, "sewageInflow", "cumecs"),
]
WQ = {"no": 0, "name": 4, "point": 5, "lat": 6, "lon": 7, "date": 22, "vegetationCover": 23,
      "vegetationType": 24, "aquaticFlora": 25, "fauna": 26, "visitingAnimals": 27}
ISSUES = {"no": 0, "name": 4, "encroachmentDirection": 5, "encroachedBy": 6, "encroachedFor": 7,
          "encroachmentPct": 8, "encroachmentKoliwad": 9, "dumpingDirection": 10, "dumpingType": 11,
          "sewageInflow": 12, "pollutant": 13, "weeds": 14, "otherIssues": 15}

KINDS = {"kr": "kere", "gk": "katte", "ku": "kunte"}
ATLAS_TEXT = ["atlasSourceOfWater", "atlasCatchment", "atlasRoads", "atlasDrinkingWater", "atlasWashing", "atlasBathing",
              "atlasLivestock", "atlasIrrigation", "atlasFishing", "atlasCultural", "atlasRecreation", "atlasOtherUses",
              "atlasAmphibians", "atlasReptiles", "atlasMammals", "atlasDirectPollutants", "atlasIndirectPollutants",
              "atlasEncroachment", "atlasSoilExcavation"]
HOBLIS = {
    "yelahan.": "Yelahanka", "yelahanka": "Yelahanka", "yeshwanthpura": "Yeshwanthpura", "hesarg.": "Hesaraghatta",
    "hesaraghatta": "Hesaraghatta", "dasanapura": "Dasanapura", "jala": "Jala", "kasaba": "Kasaba", "varthur": "Varthuru",
}
# Cell values that mean "this row describes a disappeared water body, nothing to measure".
DISUSED = {"disused", "non-ex", "non-existing"}

COLUMNS = [
    "empriNo", "empriCode", "name", "nameOther", "kind", "status", "statusText", "regime", "regimeText",
    "district", "taluk", "hobli", "village", "lat", "lon", "latText", "lonText", "custodian",
    "extentAcres", "extentText", "extentApprox", "extentBasis", "surveyNumbers", "surveyNoText",
    "year", "yearText", "rejuvenated", "elevationM", "maxDepthM", "islands", "inletDrains", "wasteWeirs",
    "sluiceGates", "culverts", "checkDams", "fenceType", "surroundingArea", "presentStatus", "waterUsage",
    "convertedTo", "convertedBy", "visitDate", "researcherVerified", "remarks",
    "waterSampled", "waterSampleNote", "sewageInflowCumecs", "vegetationCover", "vegetationType",
    "aquaticFlora", "fauna", "visitingAnimals",
    "encroachmentDirection", "encroachedBy", "encroachedFor", "encroachmentPct", "encroachmentKoliwadText",
    "encroachmentKoliwadAcres", "dumpingDirection", "dumpingType", "sewageInflow", "pollutant", "weeds",
    "otherIssues",

    "pdf", "pdfPage", "source",
    # Added after the first version; appended so the column order above stays stable.
    "tables", "coordProblem",
    *(c + "Text" for c in LIST_COLUMNS + DIRECTION_COLUMNS + TEXT_COLUMNS + ["custodian"]),
    *ATLAS_COLUMNS,
]
WQ_COLUMNS = ["empriNo", "empriCode", "lakeName", "samplingPoint", "lat", "lon", "sampleDate", "parameter",
              "value", "valueText", "belowDetection", "unit", "source"]


# ---------------------------------------------------------------- download and extraction


def download(name, url):
    path = DIR / name
    if not path.exists() or path.stat().st_size < 1_000_000:
        DIR.mkdir(parents=True, exist_ok=True)
        print(f"downloading {name}")
        subprocess.run(["curl", "-sSLf", "--retry", "3", "-o", str(path), url], check=True)
    return path


def extract_tables(volume, pdf_path):
    """Raw rows of the four database tables, cached because pdfplumber takes minutes per volume."""
    cache = DIR / f"tables_{volume}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    import pdfplumber

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            head = " ".join((page.extract_text() or "").split("\n")[:2])
            section = next((v for k, v in SECTIONS.items() if k in head and "EMPRI-CLC" in head), None)
            if section:
                tables = page.dedupe_chars().extract_tables(TABLE_SETTINGS)
                pages.append({"page": i + 1, "section": section, "tables": tables})
    cache.write_text(json.dumps(pages))
    return pages


# ---------------------------------------------------------------- text repair


def letterspaced(text):
    """'S e a s o n al' -> 'Season al': runs of three or more single characters are one word."""
    return re.sub(r"(?<!\S)(?:\w ){2,}\w(?!\S)", lambda m: m.group(0).replace(" ", ""), text)


def prose_words(vol1_pdf):
    """
    Word counts from Volume I's prose, split by case. Only words seen in the middle of a line count,
    because a line's first word can be the tail of a word wrapped from the line above.
    """
    from collections import Counter

    text_path = DIR / "vol1.txt"
    if not text_path.exists():
        subprocess.run(["pdftotext", str(vol1_pdf), str(text_path)], check=True)
    counts = Counter()
    for line in text_path.read_text(encoding="utf-8").split("\n"):
        counts.update(re.findall(r"(?<=\s)[A-Za-z]+(?=[\s.,;:)])", " " + line + " "))
    return counts


def build_vocabulary(volumes, prose):
    """
    Every token that appears as a whole word somewhere: after a space in a table cell, as the first
    word of a cell, or mid-line in the prose. Used to tell a wrapped word from two words.
    """
    vocab = {w.lower() for w, n in prose.items() if n >= 2}
    for pages in volumes.values():
        for page in pages:
            for table in page["tables"]:
                for row in table:
                    for cell in row:
                        lines = [letterspaced(x) for x in (cell or "").split("\n") if x.strip()]
                        for i, line in enumerate(lines):
                            for token in line.split()[0 if i == 0 else 1:]:
                                vocab.add(token.lower().strip(".,&()"))
    return vocab


# Kannada place-name endings: a wrapped "Devarabisana / halli" is always one word.
# Real two-letter words; any other one- or two-letter fragment ("al", "s", "ed") is a wrapped word's tail.
SHORT_WORDS = {"a", "an", "as", "at", "be", "by", "do", "if", "in", "is", "it", "no", "of", "on", "or", "so", "to", "up"}
PLACE_SUFFIXES = {"halli", "nahalli", "hally", "pura", "palya", "palaya", "sandra", "agrahara", "nagar", "gere"}


def join_lines(cell, vocab):
    """Undo the wrapping inside a table cell. 'Season\\nal' -> 'Seasonal', 'Eucalyptus\\nplant.' keeps its space."""
    if cell is None:
        return ""
    lines = [letterspaced(x.strip()) for x in cell.split("\n") if x.strip()]
    if not lines:
        return ""
    out = lines[0]
    for line in lines[1:]:
        head = line.split()[0]
        word = head.lower().strip(".,&()")
        glue = (
            out.endswith("-")
            or (out[-1].isalpha() and head[0].islower()
                and ((len(word) <= 2 and word not in SHORT_WORDS) or word in PLACE_SUFFIXES or word not in vocab))
            or (out[-1].isdigit() and head[0] in ".ʺ\"'ʹ")
            or (out[-1] in ".°'ʹ" and head[0].isdigit())
        )
        out = out + ("" if glue else " ") + line
    return out


def squash(cell):
    """For codes, dates and coordinates: drop every line break and space."""
    return re.sub(r"\s+", "", cell or "")


# ---------------------------------------------------------------- row assembly


def is_serial(cell):
    return bool(re.fullmatch(r"\d{1,4}", (cell or "").strip()))


def filled(row):
    return sum(1 for c in row[1:] if (c or "").strip())


def assemble(pages, section):
    """
    Turn table rows into one record per serial number, in document order.

    Wrapped cells sometimes spill into extra table rows without a serial. Those fragments join the
    record they belong to cell by cell. A record whose serial row is mostly merged cells ("split")
    also takes the fragments printed just above it. A village note row ("No water bodies") is skipped.
    Water quality rows without a serial that start with a sampling point are extra sampling points.
    """
    width = WIDTH[section]
    records, pending, orphan = [], [], None
    for page in pages:
        if page["section"] != section:
            continue
        for table in page["tables"]:
            table = fit_columns(table, width)
            if table is None:
                continue  # legends and abbreviation tables
            started = False
            for raw in table:
                row = list(raw)
                if is_serial(row[0]):
                    started = True
                    split = sum(1 for c in row[1:] if c is None) >= 3 and section == "morph"
                    if filled(row) == 0 and orphan is not None:
                        row, orphan = [row[0], *orphan[1:]], None
                    rec = {"no": int(row[0]), "page": page["page"], "cells": [[c] if c else [] for c in row], "extra": []}
                    if split and pending:
                        for frag in pending:
                            for i, c in enumerate(frag):
                                if c:
                                    rec["cells"][i].insert(len(rec["cells"][i]) - (1 if row[i] else 0), c)
                    elif pending and records:
                        attach(records[-1], pending)
                    pending = []
                    records.append(rec)
                    continue
                if not started or filled(row) == 0 and not (row[0] or "").strip():
                    continue
                text = " ".join(c for c in row if c)
                if section == "morph" and re.search(r"counted|no water ?bod|covered under|coverd", text, re.I) and filled(row) <= 4:
                    continue
                if section == "morph" and filled(row) >= 10 and not (row[0] or "").strip():
                    orphan = row  # a full record whose serial sits in the next row
                    continue
                if section == "wq" and re.match(r"(inlet|outlet|middle|centre|center|lake|bund)", (row[5] or "").strip(), re.I):
                    records[-1]["extra"].append(row)
                    continue
                pending.append(row)
    if pending and records:
        attach(records[-1], pending)
    if orphan is not None:
        raise ValueError(f"{section}: record without a serial number: {orphan}")
    return records


def fit_columns(table, width):
    """
    Some pages carry one stray ruled column. Merge the adjacent pair where every data row has at
    least one merged (None) cell, so the table has its normal width. Legend tables return None.
    """
    if len(table[0]) == width:
        return table
    if len(table[0]) != width + 1:
        return None
    data = [r for r in table if is_serial(r[0])]
    for i in range(1, width):
        if data and all(r[i] is None or r[i + 1] is None for r in data):
            return [[*r[:i], r[i] if r[i] is not None else r[i + 1], *r[i + 2:]] for r in table]
    return None


def attach(rec, fragments):
    for frag in fragments:
        for i, c in enumerate(frag):
            if c and i < len(rec["cells"]):
                rec["cells"][i].append(c)


def cells(rec, vocab):
    return [join_lines("\n".join(parts), vocab) for parts in rec["cells"]]


# ---------------------------------------------------------------- value parsing


def dms(text):
    """
    '12° 55'\n00.5ʺ' -> (12.916806, None). Returns (value, problem); value is None when unreadable.
    A line break inside a cell sometimes splits one number ('02.\n4') and sometimes separates two
    ('28\n16.1'), so try both readings and keep the one that is a valid coordinate.
    """
    t = text or ""
    if not t.strip():
        return None, None
    problem = None
    for candidate in (t.replace("\n", " "), t.replace("\n", "")):
        nums = [n.replace(" ", "") for n in re.findall(r"\d+(?:\.\s?\d+)?", candidate)]
        if len(nums) == 1 and "." in nums[0] and float(nums[0]) > 10:
            return round(float(nums[0]), 6), None
        if len(nums) not in (2, 3):
            problem = problem or f"cannot read {t!r}"
            continue
        d, m, s = float(nums[0]), float(nums[1]), float(nums[2]) if len(nums) == 3 else 0.0
        if m >= 60 or s >= 60:
            problem = f"minutes or seconds over 60 in {t!r}"
            continue
        note = None
        if d in (2, 3):
            d, note = d + 10, f"degrees read as {int(d) + 10} from {t!r}"
        return round(d + m / 60 + s / 3600, 6), note
    return None, problem.replace("\n", " ")


def acres(text):
    """
    Extent in acres-guntas ('7.09' = 7 acres 9 guntas, '2.08 3/4' = 2 acres 8.75 guntas) to decimal acres.
    Some cells lost a trailing zero ('0.2' for 0.20). Returns None for guntas of 40 or more.
    """
    t = text.replace("≈", " ").replace(",", ".")
    m = re.search(r"(\d+)(?:\.(\d{1,2})(?:\.(\d{1,2}))?)?(?:\s+(\d)/(\d))?", t)
    if not m:
        return None
    a = int(m.group(1))
    g = m.group(2) or "0"
    g = int(g) * (10 if len(g) == 1 else 1)
    if m.group(4):
        g += int(m.group(4)) / int(m.group(5))
    if m.group(3):
        g += int(m.group(3)) / 16  # annas, as in the atlas "919.38.16"
    if g >= 40:
        return None
    return round(a + g / 40, 4)


def extent_fields(text):
    t = text.strip()
    basis = re.findall(r"\(([^)]*)\)?", t)
    basis = " ".join(b for b in basis if not re.fullmatch(r"[\d/ ]*", b))
    if "SSLR" in t and "SSLR" not in basis:
        basis = (basis + " SSLR").strip()
    return {
        "extentText": t or None,
        "extentAcres": acres(re.sub(r"\([^)]*\)?", " ", t)) if t else None,
        "extentApprox": ("≈" in t) if t else None,
        "extentBasis": clean(basis.replace("Legisl ative Comm ittee", "Legislative Committee")),
    }


def survey_numbers(text):
    """'In Sy no 53' -> ['53']; '40 & 41' -> ['40', '41']; '43 (Agara), 1 (Bellandur)' keeps the village."""
    t = re.sub(r"\b(in\s+)?sy\.?\s*(no\.?)?\s*-?\s*", "", text, flags=re.I)
    out = []
    for part in re.split(r"\s*(?:,|&|\band\b)\s*(?![^()]*\))|(?<=\))\s+(?=\d)", t):
        part = part.strip(" .")
        m = re.match(r"^(\d+[A-Za-z]?(?:/\d*[A-Za-z0-9]*)?(?:\s*/\s*\([^)]*\))?)\s*(\([^)]*\)?)?$", part)
        if m:
            num = re.sub(r"\s+", "", m.group(1))
            village = m.group(2)
            out.append(f"{num} {village if village.endswith(')') else village + ')'}" if village else num)
    return out


def count(text):
    t = (text or "").strip().lower()
    if t in ("no", "nil", "n0", "0", "none"):
        return 0
    if re.fullmatch(r"\d+", t):
        return int(t)
    return None


def number(text):
    m = re.fullmatch(r"≈?\s*(\d+(?:\.\d+)?)", (text or "").strip())
    return float(m.group(1)) if m else None


def iso_date(text):
    t = squash(text)
    m = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2}|\d{4})", t)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    y = y + 2000 if y < 100 else y
    if not (1 <= mo <= 12 and 1 <= d <= 31 and 2014 <= y <= 2018):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def regime(text):
    t = re.sub(r"[^a-z]", "", text.lower())
    if not t:
        return None
    if t.startswith(("disused", "nonex")):
        return "disused"
    if "dry" in t:
        return "dry"
    if "sewage" in t and "per" in t or t.startswith(("per", "perr")):
        return "perennial"
    if t.startswith(("sea", "sean")):
        return "seasonal"
    return None


def name_key(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


# ---------------------------------------------------------------- build


def morph_row(rec, vocab, taluk, volume):
    c = cells(rec, vocab)
    g = {k: clean(c[i]) for k, i in MORPH.items()}
    code = squash(c[MORPH["code"]]) or None
    kind = re.search(r"_(kr|gk|ku)\d*-?", code or "")
    raw = ["\n".join(parts) for parts in rec["cells"]]
    lat_raw, lon_raw = raw[MORPH["lat"]], raw[MORPH["lon"]]
    spill = re.search(r"[\"ʺ]\s+(\d)$", lat_raw)
    if spill and re.match(r"\d°", lon_raw):
        # A stray column boundary moved the first digit of the longitude into the latitude cell.
        lat_raw, lon_raw = lat_raw[: spill.start(1)].strip(), spill.group(1) + lon_raw
    (lat, lat_note), (lon, lon_note) = dms(lat_raw), dms(lon_raw)
    if lat and lon and lat > 70 and lon < 20:
        lat, lon, lat_note = lon, lat, "latitude and longitude swapped"
    if lat is not None and not 12.5 <= lat <= 13.6 or lon is not None and not 77.0 <= lon <= 78.1:
        lat, lon, lat_note = None, None, f"outside Bengaluru: {c[MORPH['lat']]!r} {c[MORPH['lon']]!r}"
    regime_text = g["regime"] or ""
    year_text = g["year"] or ""
    year = re.search(r"(1[6-9]\d\d|20[01]\d)", squash(year_text))
    hobli = g["hobli"] or ""
    hobli = HOBLIS.get(hobli.lower().replace(" ", ""), hobli)
    disused = regime(regime_text) == "disused"
    survey = g["survey"] or ""
    return {
        "empriNo": rec["no"],
        "empriCode": code,
        "name": g["name"],
        "nameOther": None if (g["nameOther"] or "").lower() in ("no", "nil") else g["nameOther"],
        "kind": KINDS[kind.group(1)] if kind else None,
        "status": "disappeared" if disused else "existing",
        "statusText": regime_text or None,
        "regime": regime(regime_text),
        "regimeText": regime_text or None,
        "district": "Bengaluru Urban",
        "taluk": taluk,
        "hobli": hobli or None,
        "village": g["village"],
        "lat": lat,
        "lon": lon,
        "coordProblem": "; ".join(n for n in (lat_note, lon_note) if n) or None,
        "latText": clean(lat_raw),
        "lonText": clean(lon_raw),
        "custodian": g["custodian"],
        **extent_fields(c[MORPH["extent"]]),
        "surveyNumbers": survey_numbers(survey),
        "surveyNoText": g["survey"],
        "year": int(year.group(1)) if year else None,
        "yearText": year_text or None,
        "rejuvenated": bool(re.search(r"\(\s*R\s*\)", regime_text + year_text)) or None,
        "elevationM": number(c[MORPH["elevation"]]),
        "maxDepthM": number(c[MORPH["depth"]]),
        **{k: count(g[k]) for k in ("islands", "inletDrains", "wasteWeirs", "sluiceGates", "culverts", "checkDams")},
        **{k: None if disused and re.sub(r"\s", "", (g[k] or "").lower()) in DISUSED else g[k]
           for k in ("fenceType", "surroundingArea", "presentStatus", "waterUsage")},
        "visitDate": iso_date(c[MORPH["visitDate"]]),
        "researcherVerified": bool(g["researcher"]),
        "remarks": g["remarks"],
        "tables": ["main"],
        "pdf": f"vol2_{volume}",
        "pdfPage": rec["page"],
        "source": KEY,
    }


def wq_fields(rec, vocab):
    c = cells(rec, vocab)
    g = {k: clean(c[i]) for k, i in WQ.items()}
    measured = number(c[8]) is not None or number(c[10]) is not None
    flags = {k: None if (g[k] or "").lower() in DISUSED else g[k]
             for k in ("vegetationCover", "vegetationType", "aquaticFlora", "fauna", "visitingAnimals")}
    note = None
    if not measured:
        note = clean(" ".join(dict.fromkeys(x for x in c[5:22] if x and x not in ("NS", "-", "–"))))
    sewage = [number(c[21])] + [number(join_lines(e[21], vocab)) for e in rec["extra"]]
    sewage = [s for s in sewage if s is not None]
    return {
        "waterSampled": measured,
        "waterSampleNote": None if (note or "").lower() in DISUSED else note,
        "sewageInflowCumecs": sewage[0] if sewage else None,
        **flags,
    }


def wq_rows(rec, vocab, lake):
    """Long-form readings for every sampling point of one lake."""
    base = cells(rec, vocab)
    date = iso_date(base[WQ["date"]])
    out = []
    for cells_ in [base] + [[join_lines(x, vocab) for x in e] for e in rec["extra"]]:
        if number(cells_[10]) is None and number(cells_[8]) is None:
            continue
        lat, lon = dms(cells_[6])[0], dms(cells_[7])[0]
        for col, param, unit in WQ_PARAMS:
            text = clean(cells_[col])
            if text is None or text in ("–",):
                continue
            below = text.upper() in ("ND", "BDL")
            value = number(text.rstrip("."))
            if value is None and text[:1] in "<>":
                value = number(text[1:])  # ">1600" is the top of the scale; valueText keeps the sign
            out.append({
                "empriNo": lake["empriNo"], "empriCode": lake.get("empriCode"), "lakeName": lake["name"],
                "samplingPoint": clean(cells_[5]) if clean(cells_[5]) not in ("-", "–") else None,
                "lat": lat, "lon": lon, "sampleDate": date, "parameter": param,
                "value": value, "valueText": text, "belowDetection": below, "unit": unit, "source": KEY,
            })
    return out


def issues_fields(rec, vocab):
    c = cells(rec, vocab)
    g = {k: clean(c[i]) for k, i in ISSUES.items()}
    row = {k: g[k] for k in ISSUES if k not in ("no", "name", "encroachmentKoliwad")}
    # For a disappeared water body the issue cells say "Disused": not applicable, not a value.
    row = {k: None if (v or "").lower() in DISUSED else v for k, v in row.items()}
    koliwad = g["encroachmentKoliwad"]
    if all((v or "").lower() in DISUSED for v in row.values()) and (koliwad or "").lower() in DISUSED:
        row = {k: None for k in row}
        koliwad = None
    elif all((row[k] or "") == "" for k in list(row)[1:-1]) and row["encroachmentDirection"] and len(row["encroachmentDirection"]) > 40:
        # One merged cell across the whole row is a note, not a direction.
        row = {**{k: None for k in row}, "otherIssues": row["encroachmentDirection"]}
    if koliwad and koliwad.lower() in DISUSED:
        koliwad = None
    return {
        **row,
        "encroachmentKoliwadText": koliwad,
        "encroachmentKoliwadAcres": acres(koliwad) if koliwad and re.match(r"\d", koliwad) else None,
    }


def stub(lakes, rec, vocab, taluk, volume):
    """A serial the main table skips but a later table lists. Only names and place are known."""
    c = cells(rec, vocab)
    lakes[rec["no"]] = {**dict.fromkeys(COLUMNS),
        "empriNo": rec["no"], "name": clean(c[4]), "district": "Bengaluru Urban", "taluk": taluk,
        "hobli": HOBLIS.get((clean(c[2]) or "").lower().replace(" ", ""), clean(c[2])), "village": clean(c[3]),
        "status": None, "tables": [], "pdf": f"vol2_{volume}", "pdfPage": rec["page"], "source": KEY,
    }
    return lakes[rec["no"]]


def link_nonexisting(rows, nonexist, vocab):
    """
    The non-existing table has its own serial numbers and shortened names ("K.Agrahara kunte2"),
    but lists the same water bodies in the same order as the main table, with the same visit date
    and extent. Align the two lists per taluk keeping order, then pair any leftovers on a high score.
    """
    from difflib import SequenceMatcher

    def score(item, row):
        s = 2.0 * (item["date"] is not None and item["date"] == row["visitDate"])
        s += 2.0 * (item["extent"] is not None and item["extent"] == row["extentAcres"])
        rv, rn = name_key(row["village"]), name_key(row["name"])
        s += SequenceMatcher(None, item["village"], rv).ratio() if item["village"] and rv else 0
        s += 2 * SequenceMatcher(None, item["name"], rn).ratio() if item["name"] and rn else 0
        a, b = re.search(r"(\d+)$", item["name"]), re.search(r"(\d+)$", rn)
        if a and b and a.group(1) != b.group(1):
            s -= 2.5
        return s + (row["status"] in ("disappeared", None))

    def pair(item, row):
        row["_nonexistNo"] = item["no"]
        row["convertedTo"], row["convertedBy"] = item["convertedTo"], item["convertedBy"]
        row["tables"].append("nonExisting")

    unmatched = []
    for taluk in dict.fromkeys(rec["taluk"] for rec in nonexist):
        lakes = sorted((r for r in rows if r["taluk"] == taluk), key=lambda r: r["empriNo"])
        items = []
        for rec in (x for x in nonexist if x["taluk"] == taluk):
            c = cells(rec, vocab)
            items.append({
                "no": rec["no"], "village": name_key(c[NONEXIST["village"]]), "name": name_key(c[NONEXIST["name"]]),
                "extent": acres(c[NONEXIST["extent"]]) if c[NONEXIST["extent"]] else None,
                "date": iso_date(c[NONEXIST["visitDate"]]), "label": clean(c[NONEXIST["name"]]),
                "convertedTo": clean(c[NONEXIST["convertedTo"]]), "convertedBy": clean(c[NONEXIST["convertedBy"]]),
            })
        n, m = len(items), len(lakes)
        sc = [[score(it, lk) for lk in lakes] for it in items]
        # best[i][j]: best total aligning items[i:] with lakes[j:], counting pairs that score 3.5 or more.
        best = [[0.0] * (m + 1) for _ in range(n + 1)]
        for i in range(n - 1, -1, -1):
            for j in range(m - 1, -1, -1):
                take = sc[i][j] + best[i + 1][j + 1] if sc[i][j] >= 3.5 else float("-inf")
                best[i][j] = max(take, best[i + 1][j], best[i][j + 1])
        i = j = 0
        left = []
        while i < n and j < m:
            if sc[i][j] >= 3.5 and best[i][j] == sc[i][j] + best[i + 1][j + 1]:
                pair(items[i], lakes[j])
                i, j = i + 1, j + 1
            elif best[i][j] == best[i + 1][j]:
                left.append(items[i])
                i += 1
            else:
                j += 1
        left.extend(items[i:])
        for item in left:
            free = [lk for lk in lakes if "_nonexistNo" not in lk]
            top = max(free, key=lambda lk: score(item, lk), default=None)
            if top is not None and score(item, top) >= 4.5:
                pair(item, top)
            else:
                unmatched.append((taluk, {**item, "name": item["label"]}))
    return unmatched


def link_atlas(sheets, lakes):
    """
    Pair atlas sheets with table rows of the same taluk. The printed code is often damaged
    ("BUBEKRaby_kr1655", missing, or wrapped), so score each pair on code, name, visit date and the
    serial number the code ends with, and keep pairs one-to-one, best first.
    """
    from difflib import SequenceMatcher

    def key(code):
        return re.sub(r"[^a-z0-9]", "", (code or "").lower())

    def kind_of(name):
        m = re.search(r"\b(kere|lake|kunte|katte)", (name or "").lower())
        return {"lake": "kere"}.get(m.group(1), m.group(1)) if m else None

    def serial(code):
        m = re.search(r"-\s*(\d+)$", code or "")
        return int(m.group(1)) if m else None

    def score(sheet, row):
        a, b = key(sheet["atlasCode"]), key(row["empriCode"])
        s = 4.0 if a and a == b else 1.5 if a and b and len(a) >= 10 and (b.startswith(a) or a.startswith(b)) else 0.0
        sheet_serial = serial(sheet["atlasCode"])
        row_serial = serial(row["empriCode"]) if row["empriCode"] else row["empriNo"]
        s += 1.5 * bool(sheet_serial and sheet_serial == row_serial)
        target = name_key(sheet["atlasName"])
        names = {name_key(row["name"]), name_key(row["nameOther"]), name_key(re.sub(r"\(.*?\)", "", row["name"] or ""))}
        s += 4 * max(SequenceMatcher(None, target, n).ratio() for n in names if n) if row["name"] else 0
        s += 2.0 * (iso_date(sheet["atlasVisitDate"]) is not None and iso_date(sheet["atlasVisitDate"]) == row["visitDate"])
        n1 = re.search(r"(\d+)$", target)
        n2 = re.search(r"(\d+)$", name_key(re.sub(r"\(.*?\)", "", row["name"] or "")))
        if n1 and n2 and n1.group(1) != n2.group(1):
            s -= 3.0  # "Kunte1" is not "Kunte7"
        k1, k2 = kind_of(sheet["atlasName"]), row["kind"]
        s += (1.0 if k1 == k2 else -1.5) if k1 and k2 else 0
        return s

    pairs = sorted(((score(sh, r), i, j) for i, sh in enumerate(sheets) for j, r in enumerate(lakes)), reverse=True)
    used_sheet, used_row = set(), set()
    for s, i, j in pairs:
        if s < 3.8:  # a near-exact name alone is enough
            break
        if i in used_sheet or j in used_row:
            continue
        used_sheet.add(i)
        used_row.add(j)
        row, sheet = lakes[j], sheets[i]
        row.update({k: v for k, v in sheet.items() if k != "atlasVisitDate"})
        row["tables"].append("atlas")
        if not row["empriCode"] and sheet["atlasCode"]:
            row["empriCode"] = sheet["atlasCode"]
    return [sh for i, sh in enumerate(sheets) if i not in used_sheet]


def build():
    prose = prose_words(download("vol1.pdf", VOLUME_1))
    # Proper names: words the prose capitalises and never writes in lowercase.
    proper = {w for w, n in prose.items() if w[:1].isupper() and n >= 2 and prose[w.lower()] == 0}
    volumes, pdfs = {}, {}
    for volume, (taluk, url) in VOLUMES.items():
        pdfs[volume] = download(f"vol2_{volume}.pdf", url)
        volumes[volume] = extract_tables(volume, pdfs[volume])
    vocab = build_vocabulary(volumes, prose)

    rows, readings, nonexist = [], [], []
    for volume, (taluk, _) in VOLUMES.items():
        pages = volumes[volume]
        lakes = {rec["no"]: morph_row(rec, vocab, taluk, volume) for rec in assemble(pages, "morph")}
        for rec in assemble(pages, "wq"):
            lake = lakes.get(rec["no"]) or stub(lakes, rec, vocab, taluk, volume)
            lake["tables"].append("waterQuality")
            fields = wq_fields(rec, vocab)
            lake.update(fields)
            readings.extend(wq_rows(rec, vocab, lake))
        for rec in assemble(pages, "issues"):
            lake = lakes.get(rec["no"]) or stub(lakes, rec, vocab, taluk, volume)
            lake["tables"].append("issues")
            lake.update(issues_fields(rec, vocab))
        for rec in assemble(pages, "nonexist"):
            nonexist.append({**rec, "taluk": taluk})
        rows.extend(lakes.values())

    unmatched = link_nonexisting(rows, nonexist, vocab)
    for r in rows:
        if "main" not in r["tables"]:
            # Skipped by the main table; the non-existing table says it is gone, the name gives its kind.
            r["status"] = "disappeared" if "nonExisting" in r["tables"] else None
            kind = re.search(r"\b(kere|kunte|katte|lake)\b", (r["name"] or "").lower())
            r["kind"] = {"lake": "kere"}.get(kind.group(1), kind.group(1)) if kind else None

    unknown_terms = []
    for r in rows:
        unknown_terms.extend(normalise(r, proper))

    atlas_unmatched = []
    sheets = 0
    for volume, (taluk, _) in VOLUMES.items():
        found = parse_atlas(pdfs[volume], DIR / f"atlas_{volume}.json")
        sheets += len(found)
        atlas_unmatched += link_atlas(found, [r for r in rows if r["taluk"] == taluk])
    # Same casing and spacing clean-up as the table text; names of lakes are left as printed.
    for r in rows:
        for col in ATLAS_TEXT:
            if r.get(col):
                r[col] = tidy_text(r[col], proper)

    rows.sort(key=lambda r: r["empriNo"])
    for r in rows:
        r.pop("_nonexistNo", None)
        for col in COLUMNS:
            r.setdefault(col, None)
    write_csv(SOURCES / f"{NAME}.csv", rows, COLUMNS)
    write_csv(SOURCES / f"{NAME}_water_quality.csv", readings, WQ_COLUMNS)
    write_sources(NAME, [{
        "key": KEY,
        "title": "Inventorisation of Water Bodies in Bengaluru Metropolitan Area (BMA), Volume II: Lake Database and Atlas",
        "publisher": "Environmental Management and Policy Research Institute (EMPRI), for the Karnataka Lake Conservation and Development Authority",
        "url": DATASET,
        "license": "Public domain (as stated by OpenCity)",
        "credit": "Water body inventory: EMPRI for KLCDA, 2018",
        "asOf": "2018-03",
        "retrieved": "2026-09-11",
    }])

    report(rows, readings, nonexist, unmatched, sheets, atlas_unmatched, unknown_terms)


def report(rows, readings, nonexist, unmatched, sheets, atlas_unmatched, unknown_terms):
    from collections import Counter

    print(f"{NAME}: {len(rows)} water bodies, {len(readings)} water quality readings")
    print("  status", dict(Counter(r["status"] for r in rows)))
    print("  kind", dict(Counter(r["kind"] for r in rows)))
    print("  taluk", dict(Counter(r["taluk"] for r in rows)))
    print(f"  non-existing table rows {len(nonexist)}, linked {sum(1 for r in rows if r.get('convertedTo') or r.get('convertedBy'))}")
    for taluk, item in unmatched:
        print(f"    unlinked non-existing row {taluk} #{item['no']}: {item['name']}")
    print(f"  lakes with water quality measured {sum(1 for r in rows if r.get('waterSampled'))}")
    print(f"  atlas sheets {sheets}, linked {sheets - len(atlas_unmatched)}")
    for sheet in atlas_unmatched:
        print(f"    unlinked atlas sheet p{sheet['atlasPage']} {sheet['atlasCode']} {sheet['atlasName']}")
    missing = [r["empriNo"] for r in rows if r["lat"] is None or r["lon"] is None]
    outside = [r["empriNo"] for r in rows if r["lat"] and r["lon"] and not (12.5 <= r["lat"] <= 13.6 and 77.0 <= r["lon"] <= 78.1)]
    print(f"  missing coordinates {missing}")
    print(f"  coordinates outside Bengaluru {outside}")
    print("  list values outside the vocabulary (kept as text):")
    for (col, term), n in Counter(unknown_terms).most_common(40):
        print(f"    {col}: {term!r} x{n}")
    serials = sorted(r["empriNo"] for r in rows)
    gaps = sorted(set(range(1, serials[-1] + 1)) - set(serials))
    dups = [n for n, k in Counter(serials).items() if k > 1]
    print(f"  serial gaps {gaps} duplicates {dups}")


if __name__ == "__main__":
    build()
