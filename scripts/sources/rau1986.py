#!/usr/bin/env python3
"""
The 1986 Lakshman Rau Expert Committee report on the tanks of the Bangalore Metropolitan Area.

The report is an 82-page typewritten scan with no text layer. Three annexures list the tanks:
  Annexure 2 (PDF pages 39-50)  disused tanks in the conurbation, 46 stated, 8 columns, pages turned sideways
  Annexure 4 (PDF pages 52-64)  live tanks in the conurbation, 81 stated, 8 columns, pages turned sideways
  Annexure 5 (PDF pages 66-76)  tanks in the green belt, 262 stated, 4 columns (serial, tank number, name, hectares)

The conurbation columns are: serial, tank registration number, name, area in hectares, location and
existing condition, proposal in the 1984 Comprehensive Development Plan (the land use), proposal by the
committee (the recommendation), agency to be entrusted. Rows are grouped under road sectors; green belt
rows also under taluks.

Page images, OCR and column finding live in _rau1986_scan.py. Rows are counted in order, so the serial
is ours; a tank number or area that OCR cannot read is left empty rather than guessed.

Output: data/sources/rau1986.csv, one row per tank; `page` is the PDF page.
"""

import re
import sys
import urllib.request
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import numpy as np
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _rau1986_scan import (  # noqa: E402
    boundaries, column_layout, column_of, column_row, crop, legible_lines, line_text, lines_of, number_strips,
    ocr_words, page_image, read_band, read_decimal, refine_edges, row_edges, serial_x, top_of,
)
from common import RAW, SOURCES, read_csv, write_csv, write_sources  # noqa: E402

NAME = "rau1986"
KEY = "rau-1986"
URL = (
    "https://prod-qt-images.s3.amazonaws.com/indiawaterportal/import/sites/default/files/iwp2/"
    "report_of_the_expert_committee_for_preservation_restoration_or_otherwise_of_the_existing_tanks_in_"
    "bangalore_metropolitan_area_laxman_rau_1986.pdf"
)
PDF = RAW / NAME / "report.pdf"
CORRECTIONS = RAW / NAME / "corrections.csv"

# annexure -> (list, status, PDF pages, number of columns, tank count stated in the report)
TABLES = {
    "a2": ("city", "disused", range(39, 51), 8, 46),
    "a4": ("city", "live", range(52, 65), 8, 81),
    "a5": ("green belt", None, range(66, 77), 4, 262),
}
COLUMNS = [
    "rauId", "annexure", "list", "status", "serial", "tankNo", "name", "zone", "taluk",
    "areaHa", "condition", "landUse", "recommendation", "agency", "page", "source",
]
# Conurbation column number -> output field.
CITY_CELLS = {2: "tankNo", 3: "name", 4: "areaHa", 5: "condition", 6: "landUse", 7: "recommendation", 8: "agency"}
DECIMAL = re.compile(r"\d{1,3}[.,]\d{1,2}")
TANK_NO = re.compile(r"\d{3}(\([ab]\))?")

# The radial roads that bound each sector, in the order the report walks round the city.
RING = ["Bellary", "Madras", "Hosur", "Mysore", "Tumkur"]
TALUKS = ["Bangalore North", "Bangalore South", "Hoskote", "Anekal", "Magadi", "Nelamangala", "Devanahalli"]

# Typewriter letters tesseract misreads the same way throughout the report, checked against the scan.
WORD_FIXES = {
    "tark": "tank", "tenk": "tank", "tani": "tank", "tant": "tank", "tanic": "tank", "tanik": "tank", "Tonk": "Tank",
    "Tark": "Tank", "Tenk": "Tank", "Pank": "Tank", "Sank": "Tank",
    "Pertly": "Partly", "Forert": "Forest", "Forent": "Forest", "Forezt": "Forest", "Porest": "Forest", "Foreat": "Forest",
    "Poorest": "Forest", "Fores?": "Forest", "Rept.": "Dept.", "Depr.": "Dept.", "Dopt.": "Dept.", "Lep+.": "Dept.",
    "Tne": "The", "Tho": "The", "Phe": "The", "I+": "It", "ig": "is", "1s": "is", "towerds": "towards", "neer": "near",
    "Located": "located", "Lecatcd": "located",
}


def fetch():
    if not PDF.exists():
        PDF.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, PDF)


# ---------------------------------------------------------------- text


def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def join_words(words):
    """
    Cell text in reading order, with words broken across lines joined again. OCR reads the typed hyphen
    as a trailing "-", a separate "-" or "~", or a full stop ("Kalagondana. / hally").
    """
    out = []
    for ws in lines_of(words):
        for k, w in enumerate(ws):
            t = w["text"]
            at_line_start = k == 0 and out and re.match(r"[a-z]", t)
            if at_line_start and re.search(r"[a-z][-~_—]$", out[-1]):
                out[-1] = out[-1][:-1] + t
            elif at_line_start and len(out) >= 2 and re.fullmatch(r"[-~_—]", out[-1]) and re.search(r"[a-z]$", out[-2]):
                out[-2:] = [out[-2] + t]
            elif at_line_start and re.fullmatch(r"[A-Za-z]{4,}\.", out[-1]):
                out[-1] = out[-1][:-1] + t
            else:
                out.append(t)
    text = " ".join(WORD_FIXES.get(t, t) for t in out)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"[|‘’“”\"_«»°@®]", "", text)
    return re.sub(r"\s+", " ", text).strip(" ;:~-'.,") or None


# Letters the typewriter face loses to OCR inside tank and village names.
NAME_FIXES = [
    (r"hal\s?[il1L]{2}[it]?\b", "halli"),
    (r"\bTonk\b|\bTanke\b|\btants?\b|\btam\b", "tank"),
    (r"ker[aco]\b", "kere"),
    (r"sandxa\b", "sandra"),
    (r"\b[ZX](?=[a-z]{3})", "K"),  # the typed K reads as Z or X: "Zempambudhi", "Xodagikere"
    (r"\s*[{}]\s*", ")"),
]


def clean_name(words):
    text = join_words(words)
    if not text:
        return None
    for pattern, fix in NAME_FIXES:
        text = re.sub(pattern, fix, text)
    return re.sub(r"\s*[-~—]\s*$", "", text).strip(" .,;:*") or None


def zone_heading(text, previous):
    """
    Index k of the sector "Between RING[k] Road and RING[k+1] Road" that a heading line names, or None.
    OCR often loses one road name; "between" and one road then mean the next sector round the city.
    """
    if re.search(r"\d{3}|\d[.,]\d", text):
        return None
    words = re.findall(r"[A-Za-z]{3,}", text)
    roads = [r for r in RING if any(similar(w, r) >= 0.75 for w in words)]
    between = any(similar(w, "between") >= 0.7 for w in words)
    pairs = [{RING[k], RING[(k + 1) % len(RING)]} for k in range(len(RING))]
    if len(roads) == 2:
        return next((k for k, p in enumerate(pairs) if p == set(roads)), None)
    if between and roads:  # "Tank between Hulimavu & Arakere" names no road and is a tank
        k = 0 if previous is None else (previous + 1) % len(RING)
        return k if roads[0] in pairs[k] else None
    return None


def zone_label(k):
    return None if k is None else f"Between {RING[k]} Road and {RING[(k + 1) % len(RING)]} Road"


def taluk_heading(text):
    """The taluk a sub-heading such as "(b) Bangalore North Taluk:" names, or None."""
    if re.search(r"\d{2}", text) or len(text.split()) > 6:
        return None
    words = re.findall(r"[A-Za-z]{3,}", text)
    if not (re.match(r"\W*\(\s*\w{1,2}\s*\)", text) or any(similar(w, "taluk") >= 0.6 for w in words)):
        return None
    if any(similar(w, "bangalore") >= 0.7 for w in words):
        for side in ("North", "South"):
            if any(similar(w, side) >= 0.75 for w in words):
                return f"Bangalore {side}"
    return next((t for t in TALUKS[2:] if any(similar(w, t) >= 0.75 for w in words)), None)


def vote(readings):
    """The value most readings agree on; on a tie the first, as readings are passed best first."""
    values = [v for v in readings if v]
    if not values:
        return None
    counts = Counter(values)
    return next(v for v in values if counts[v] == max(counts.values()))


def decimal_of(text):
    m = DECIMAL.search((text or "").replace(" ", ""))
    return m.group(0).replace(",", ".") if m else None


def tank_no_of(text):
    text = re.sub(r"\s", "", text or "")
    if re.search(r"N\.?A", text):
        return "N.A."
    m = TANK_NO.search(text)
    return m.group(0) if m else None


def area_value(img, words, box):
    """
    Hectares by majority of four readings: the page OCR, the cell crop with its point found as ink, and the
    crop read at two enlargements. On 29 hand-checked cells no one reading got more than 17 right and the
    majority got 27, the other two left empty. A cell no reading sees as a decimal stays empty.
    """
    if not words:
        return None
    band = crop(img, box)
    return vote([
        decimal_of("".join(w["text"] for w in words)),
        read_decimal(band),
        decimal_of(read_band(band, 2, cv2.INTER_CUBIC, "0123456789.,-")),
        decimal_of(read_band(band, 3, cv2.INTER_NEAREST, "0123456789.,-")),
    ])


def tank_value(img, words, box):
    """Tank number by majority of the page OCR and two enlarged readings of the cell crop."""
    if not words:
        return None
    band = crop(img, box)
    whitelist = "0123456789()abNA.-"
    return vote([
        tank_no_of("".join(w["text"] for w in words)),
        tank_no_of(read_band(band, 3, cv2.INTER_NEAREST, whitelist)),
        tank_no_of(read_band(band, 2, cv2.INTER_CUBIC, whitelist)),
    ])


def smooth_tank_numbers(rows):
    """
    Tank numbers mostly run in sequence down a table. A number between n-1 and n+1 that shares n's first
    digit and differs from it in at most two digits is n misread: the typewriter's 1, 4 and 7 look alike
    (211 read as 244).
    """
    nums = [int(r["tankNo"]) if r["tankNo"] and r["tankNo"].isdigit() else None for r in rows]
    out = []
    for i, r in enumerate(rows):
        prev, nxt = (nums[i - 1] if i else None), (nums[i + 1] if i + 1 < len(nums) else None)
        want = str(prev + 1) if prev is not None and nxt is not None and nxt - prev == 2 else None
        have = r["tankNo"] or ""
        misread = want and nums[i] is not None and have != want and len(have) == len(want) and have[0] == want[0]
        if misread and sum(a != b for a, b in zip(have, want)) <= 2:
            out.append({**r, "tankNo": want})
        else:
            out.append(r)
    return out


def ocr_serial(words):
    m = re.search(r"\d{1,3}", "".join(w["text"] for w in words))
    return int(m.group(0)) if m else None


def serials_for(rows, stated):
    """1..N when every stated row was found; otherwise the printed serials, aligned."""
    if len(rows) == stated:
        return list(range(1, stated + 1))
    return printed_serials([r["serial"] for r in rows])


def printed_serials(ocr):
    """
    The report's own serial for each row. OCR misreads single serials ("54" for 51), and the scan lacks the
    page with live tanks 54-61, so a printed serial is trusted only when it and a neighbouring row agree on
    the same offset from the row count; other rows keep the offset of the last trusted serial.
    """
    offsets = [None if s is None else s - i for i, s in enumerate(ocr, 1)]
    out, current = [], 0
    for i, off in enumerate(offsets):
        near = [offsets[j] for j in (i - 1, i + 1) if 0 <= j < len(offsets)]
        if off is not None and off in near and abs(off - current) <= 12:
            current = off
        serial = i + 1 + current
        out.append(max(serial, out[-1] + 1) if out else serial)
    return out


# ---------------------------------------------------------------- conurbation tables


def page_columns(images, lines_by_page, n):
    """
    (body top, n-1 column edges) for each page. Edges come from the column-number row, with the first four
    placed by the lines that open rows. A page with no usable number row borrows the nearest good page's
    edges, moved by where its serials stand and then settled on this page's own gaps between columns.
    """
    strips = {number: number_strips(img, n) for number, img in images.items()}
    template = column_layout(strips.values(), n)
    layout = {}
    for number, img in images.items():
        head, centres = column_row(strips[number], template)
        first = row_edges(lines_by_page[number], img)
        # A number row read one column off (page 57) puts column 2's centre outside the tank-number column.
        if centres and first and not first[0] < centres[1] < first[1] + 40:
            centres = None
        body = [ws for ws in lines_by_page[number] if top_of(ws) >= (head or 0) - 4]
        edges = boundaries(body, centres, img.shape[1]) if centres else None
        if edges and first:
            edges = first + edges[4:]
        layout[number] = (head or 0, edges, first)
    found = [number for number in images if layout[number][1]]
    for number, img in images.items():
        head, edges, first = layout[number]
        if not edges:
            near = min(found, key=lambda f: abs(f - number))
            shift = serial_x(lines_by_page[number], img) - serial_x(lines_by_page[near], images[near])
            body = [ws for ws in lines_by_page[number] if top_of(ws) >= head - 4]
            edges = refine_edges(body, [e + shift for e in layout[near][1]], img.shape[1])
            if first:
                edges = first + edges[4:]
        layout[number] = (head, edges, first)
    return {number: (head, edges) for number, (head, edges, _) in layout.items()}


def parse_city(pdf, key):
    """Annexure 2 or 4: rows spanning several lines, eight columns."""
    listing, status, pages, n, stated = TABLES[key]
    images = {number: page_image(pdf, number) for number in pages}
    lines_by_page = {number: legible_lines(ocr_words(img, number)) for number, img in images.items()}
    layout = page_columns(images, lines_by_page, n)
    rows, zone, current = [], None, None
    for number in pages:
        img, (head, edges) = images[number], layout[number]
        body = [ws for ws in lines_by_page[number] if top_of(ws) >= head - 4]
        body = body[: next((i for i, ws in enumerate(body) if re.search(r"ABSTRAC", line_text(ws), re.I)), len(body))]
        for ws in body:
            text = line_text(ws)
            k = zone_heading(text, zone) if ws[0]["x0"] < edges[3] else None
            if k is not None:
                zone, current = k, None
                continue
            cols = {}
            for w in ws:
                col = column_of(w, edges)
                # A short name leaves the area left of the column edge; it is the only decimal number there.
                if col in (2, 3) and re.fullmatch(r"\d{1,3}[.,]\d{1,2}", w["text"]) and w["x0"] > edges[1] + 60:
                    col = 4
                # Tank numbers hold no words; a name typed further left (page 53) still belongs to the name column.
                elif col == 2 and re.search(r"[A-Za-z]{3}", w["text"]) and not re.search(r"\d", w["text"]):
                    col = 3
                cols.setdefault(col, []).append(w)
            if len(ws) == 1 and re.fullmatch(r"\d{1,3}\.?", ws[0]["text"]) and 1 not in cols:
                continue  # page number
            # Specks and stray letters stick to the serial (";2.", "4 Qe"); a one- or two-digit number is enough.
            serial = re.fullmatch(r"\W*\d{1,2}\W*[A-Za-z]{0,2}\W*", "".join(w["text"] for w in cols.get(1, []))) if cols.get(1) else None
            named = cols.get(2) or any(re.search(r"[A-Za-z]{3}", w["text"]) for w in cols.get(3, []))
            # A line with an area and a name opens a row even when its serial is unreadable, unless the row
            # above still lacks its area (a wrapped name carries the area on its second line).
            has_area = any(re.fullmatch(r"\d{1,3}[.,]\d{1,2}", w["text"]) for w in cols.get(4, []))
            # A wrapped name reaches its area within a line; a row already two lines into its description is done
            # even when its own area is a printed blank (K.R. Puram under Basavanapura, page 53).
            above_has_area = current is None or any(re.search(r"\d[.,]\d", w["text"]) for w in current["cells"].get(4, [])) or (
                len({w["top"] // 20 for w in current["cells"].get(5, [])}) >= 2
            )
            # Each row carries one tank number, so a second one with a name is the next row.
            tank_no = any(re.fullmatch(r"\W*\d{3}(\([ab]\))?\W*", w["text"]) for w in cols.get(2, []))
            above_has_tank_no = current is not None and any(re.search(r"\d{3}", w["text"]) for w in current["cells"].get(2, []))
            if (serial and named) or (has_area and named and above_has_area) or (tank_no and named and above_has_tank_no):
                current = {
                    "cells": {}, "page": number, "zone": zone, "img": img, "serial": ocr_serial(cols.get(1, [])), "edges": edges,
                    "line": (min(w["top"] for w in ws) - 8, max(w["bottom"] for w in ws) + 8),
                }
                rows.append(current)
            if current is not None:
                for c, cw in cols.items():
                    # The page number at the foot of the page lands in the text columns ("Regional park 58").
                    cw = [w for w in cw if not (c >= 5 and re.fullmatch(r"\d{1,3}\.?", w["text"]) and w["top"] > img.shape[0] * 0.85)]
                    if c >= 2 and cw:
                        current["cells"].setdefault(c, []).extend(cw)
    # A row whose first line lost its name (OCR read "& a") continues on the next line without a tank number.
    merged = []
    for r in rows:
        if merged and not any(re.search(r"[A-Za-z]{3}", w["text"]) for w in merged[-1]["cells"].get(3, [])) and not r["cells"].get(2):
            for c, cw in r["cells"].items():
                merged[-1]["cells"].setdefault(c, []).extend(cw)
            merged[-1]["serial"] = merged[-1]["serial"] or r["serial"]
        else:
            merged.append(r)
    rows = merged
    out = []
    for serial, r in zip(serials_for(rows, stated), rows):
        cells = {field: r["cells"].get(col, []) for col, field in CITY_CELLS.items()}
        e, (top, bottom) = r["edges"], r["line"]
        tank_words = [w for w in cells["tankNo"] if w["top"] < bottom]
        area_words = [w for w in cells["areaHa"] if w["top"] < bottom]
        area_x0 = min([e[2]] + [w["x0"] for w in area_words])
        out.append({
            "rauId": f"{key}-{serial}", "annexure": key[1:], "list": listing, "status": status, "serial": serial,
            "tankNo": tank_value(r["img"], tank_words, (e[0] + 4, e[1] - 4, top, bottom)), "name": clean_name(cells["name"]),
            "zone": zone_label(r["zone"]), "taluk": None,
            "areaHa": area_value(r["img"], area_words, (area_x0 - 10, e[3] + 10, top, bottom)),
            "condition": join_words(cells["condition"]), "landUse": join_words(cells["landUse"]),
            "recommendation": join_words(cells["recommendation"]), "agency": join_words(cells["agency"]),
            "page": r["page"], "source": KEY, "_ocrSerial": r["serial"],
        })
    return smooth_tank_numbers(out)


# ---------------------------------------------------------------- green belt table


def parse_green_belt(pdf, key="a5"):
    """
    Annexure 5: one line per tank. A line opens a row when it has anything before the name (serial or
    tank number, however garbled) or an area after it; a line with neither continues the name above.
    """
    listing, _, pages, _, _ = TABLES[key]
    rows, zone, taluk = [], None, None
    for number in pages:
        img = page_image(pdf, number)
        lines = legible_lines(ocr_words(img, number))
        clean = []
        for ws in lines:
            i = next((i for i, w in enumerate(ws) if re.search(r"[A-Za-z]{3}", w["text"])), None)
            if i and re.search(r"\d", ws[0]["text"]):
                clean.append((ws, i))
        name_x = float(np.median([ws[i]["x0"] for ws, i in clean]))
        tank_x = float(np.median([ws[i - 1]["x0"] for ws, i in clean if i >= 2]))
        area_x = float(np.median([ws[-1]["x1"] for ws, _ in clean if re.fullmatch(r"\d{1,3}[.,]\d{1,2}", ws[-1]["text"])]))
        page_rows = []
        for ws in lines:
            text = line_text(ws)
            if re.search(r"name\s+of|green\s*belt|annex|abstract|extent|hect", text, re.I):
                continue
            k = zone_heading(text, zone)
            if k is not None:
                zone = k
                continue
            if taluk_heading(text):
                taluk = taluk_heading(text)
                continue
            i = next((i for i, w in enumerate(ws) if re.search(r"[A-Za-z]{3}", w["text"]) and w["x0"] >= name_x - 40), None)
            if i is None or zone is None:  # the table starts at its first sector heading
                continue
            j = next((k for k in range(i + 1, len(ws)) if re.search(r"\d", ws[k]["text"]) and ws[k]["x1"] > area_x - 160), len(ws))
            prefix, name = ws[:i], ws[i:j]
            trail = [w for w in ws[j:] if w["x1"] <= area_x + 60 and re.search(r"\d", w["text"])]
            # A serial or tank number opens a row. So does a garbled serial with the tank column's dash
            # ("tot - Chudenapura tank"); a speck in the margin before a wrapped name ("- Yellakunte") does not.
            numbered = any(re.search(r"\d|N\.?A", w["text"]) for w in prefix)
            marked = any(w["x0"] >= tank_x - 30 for w in prefix) and any(
                tank_x - 250 <= w["x0"] < tank_x - 30 and re.search(r"[A-Za-z0-9]", w["text"]) for w in prefix
            )
            last = (page_rows or rows or [None])[-1]
            # A wrapped name can carry the area on its second line ("Kodagi Kere-Byarati / (near Geddalahalli) 9.6").
            line = (min(w["top"] for w in ws) - 8, max(w["bottom"] for w in ws) + 8)
            if numbered or marked or (trail and (last is None or last["trail"])):
                page_rows.append({
                    "tank": [w for w in prefix if w["x0"] >= tank_x - 30], "serial": ocr_serial([w for w in prefix if w["x0"] < tank_x - 30]),
                    "name": name, "trail": trail, "page": number, "zone": zone, "taluk": taluk, "img": img,
                    "line": line, "areaLine": line, "cols": (tank_x, name_x, area_x),
                })
            elif last is not None:
                last["name"] = last["name"] + name
                if trail and not last["trail"]:
                    last["trail"], last["areaLine"] = trail, line
        # The report repeats the last tank of a page at the top of the next.
        if rows and page_rows and similar(join_words(rows[-1]["name"]) or "", join_words(page_rows[0]["name"]) or "") >= 0.75:
            page_rows = page_rows[1:]
        rows += page_rows
    out = []
    for serial, r in zip(serials_for(rows, TABLES[key][4]), rows):
        tank_x, name_x, area_x = r["cols"]
        out.append({
            "rauId": f"{key}-{serial}", "annexure": key[1:], "list": listing, "status": None, "serial": serial,
            "tankNo": tank_value(r["img"], r["tank"], (tank_x - 50, name_x - 20, *r["line"])), "name": clean_name(r["name"]),
            "zone": zone_label(r["zone"]), "taluk": r["taluk"],
            "areaHa": area_value(r["img"], r["trail"], (area_x - 200, area_x + 40, *r["areaLine"])),
            "condition": None, "landUse": None, "recommendation": None, "agency": None,
            "page": r["page"], "source": KEY, "_ocrSerial": r["serial"],
        })
    return smooth_tank_numbers(out)


# ---------------------------------------------------------------- run


def apply_corrections(rows):
    """
    Cells read by hand from the scan where they were checked (data/raw/rau1986/corrections.csv; "-" is a
    printed blank, an empty cell leaves the OCR value). A correction applies only while the extracted name still
    looks like its tank, so a change in row numbering can never move it onto another tank.
    """
    if not CORRECTIONS.exists():
        return rows, 0
    fixes = {f["rauId"]: f for f in read_csv(CORRECTIONS)}
    out, applied = [], 0
    for row in rows:
        fix = fixes.get(row["rauId"])
        if not fix:
            out.append(row)
            continue
        if similar(row["name"] or "", fix["name"]) < 0.5:
            print(f"{NAME}: correction for {row['rauId']} ({fix['name']}) no longer matches the row ({row['name']}); skipped")
            out.append(row)
            continue
        changed = {k: (None if fix[k] == "-" else fix[k]) for k in ("name", "tankNo", "areaHa") if fix.get(k)}
        applied += any(row.get(k) != v for k, v in changed.items())
        out.append({**row, **changed})
    return out, applied


def build():
    fetch()
    with pdfplumber.open(PDF) as pdf:
        tables = {"a2": parse_city(pdf, "a2"), "a4": parse_city(pdf, "a4"), "a5": parse_green_belt(pdf)}
    rows = []
    for key, table in tables.items():
        listing, status, _, _, stated = TABLES[key]
        agree = sum(1 for r in table if r["_ocrSerial"] == r["serial"])
        no_area = sum(1 for r in table if not r["areaHa"])
        print(
            f"{NAME}: annexure {key[1:]} ({listing}{' ' + status if status else ''}) {len(table)} rows, report states {stated}; "
            f"printed serial read and in sequence on {agree}, no readable area on {no_area}"
        )
        rows += table
    rows, applied = apply_corrections(rows)
    print(f"{NAME}: hand corrections from the scan changed {applied} rows")
    write_csv(SOURCES / f"{NAME}.csv", [{k: r.get(k) for k in COLUMNS} for r in rows], COLUMNS)
    write_sources(NAME, [{
        "key": KEY,
        "title": "Report of the Expert Committee for Preservation, Restoration or Otherwise of the Existing Tanks in Bangalore Metropolitan Area",
        "publisher": "Government of Karnataka (Expert Committee chaired by N. Lakshman Rau)",
        "url": URL,
        "license": "not stated",
        "credit": "Lakshman Rau Expert Committee report, Government of Karnataka, 1986",
        "asOf": "1986",
        "retrieved": "2026-09-14",
    }])


if __name__ == "__main__":
    build()
