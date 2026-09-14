#!/usr/bin/env python3
"""
Citizen Matters directory of Bengaluru lake groups (July 2022 PDF).

The PDF is an Excel sheet printed across pages: pages 1-5 hold the first five columns
(name, type, work description, contacts, Twitter) and pages 31-35 the last two (Facebook, website)
for the same rows; the pages in between are blank. We read it cell by cell from the grid lines.
Long descriptions overflow into the next row's cell, so each text line is given to the row whose
first line it lines up with (lines are 13 pt apart and every row's text starts 3 pt below its top line).

We keep only organisations, and only their name, type, the lakes they name, and public links.
Rows for individuals (politicians, officials, activists) are dropped, as are all contact details
and the free-text description, which names people. The PDF has no area column.

Output: data/sources/lake_groups.csv
"""

import collections
import re
import sys
import urllib.request
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, clean, write_csv, write_sources  # noqa: E402

NAME = "lake_groups"
URL = "https://citizenmatters.in/wp-content/uploads/2022/07/Lake-groups-Shilpa-190722.pdf"
RAW_FILE = RAW / NAME / "Lake-groups-Shilpa-190722.pdf"
LINE_PITCH = 13.0
TEXT_OFFSET = 3.1
SPILL_PAGE_OFFSET = 30  # page n's rows continue on page n + 30
EXPECTED_ROWS = 49

# A row is kept only if its name reads as an organisation; individuals' names match none of these.
ORG_WORDS = re.compile(
    r"trust|group|foundation|samiti|samithi|society|federation|rwa|association|committee|matters|rising|"
    r"lake|trees|bharat|watch|milaap|uthkarsh|agastya|united way|institute|bengaluru|india|monitoring",
    re.I,
)
HONORIFIC = re.compile(r"^(mr|ms|mrs|dr)\b", re.I)
NO_VALUE = {"-----", "nil"}

# Words that can sit right before "lake" in a description without being part of a lake's name.
NOT_A_NAME = {
    "the", "of", "in", "on", "to", "and", "for", "many", "better", "bengaluru", "bengauru", "around",
    "revive", "maintain", "restore", "adopted", "beside", "especially", "these", "specific", "state", "have",
}
NAME_SUFFIXES = {"agrahara", "palya", "ambalipura"}  # "pattandur agrahara lake", "lower ambalipura lake"


def fetch():
    if not RAW_FILE.exists():
        RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (lakes-of-bendakaluru data build)"})
        RAW_FILE.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return RAW_FILE


def merged(values, gap=2):
    out = []
    for v in sorted(values):
        if not out or v - out[-1] > gap:
            out.append(v)
    return out


def page_cells(page):
    """Rows x columns of text lines, using the thin black grid rectangles."""
    rules = [r for r in page.rects if r["non_stroking_color"] == 0.0]
    tops = merged(round(r["top"]) for r in rules if r["height"] < 3 and r["width"] > 200)
    lefts = merged(round(r["x0"]) for r in rules if r["width"] < 3 and r["height"] > 20)
    if "Name of Trusts" in (page.extract_text() or "") or "Alternative social" in (page.extract_text() or ""):
        tops = tops[1:]  # drop the header row
    columns = list(zip(lefts, lefts[1:]))
    rows = [[[] for _ in columns] for _ in tops[:-1]]
    for ci, (x0, x1) in enumerate(columns):
        lines = collections.defaultdict(list)
        for ch in page.chars:
            if x0 <= ch["x0"] < x1 and ch["top"] > tops[0]:
                lines[round(ch["top"], 1)].append(ch)
        for top in sorted(lines):
            text = "".join(c["text"] for c in sorted(lines[top], key=lambda c: c["x0"])).strip()
            owner = None
            for ri in range(len(tops) - 1):
                start = tops[ri] + TEXT_OFFSET
                steps = (top - start) / LINE_PITCH
                if top >= start - 0.6 and abs(steps - round(steps)) * LINE_PITCH < 0.6:
                    owner = ri
            if owner is None:
                raise ValueError(f"page {page.page_number}: line at {top} fits no row: {text!r}")
            rows[owner][ci].append(text)
    return rows


def text(lines):
    return clean(" ".join(lines))


def link(lines):
    value = clean("".join(lines).replace(" ", ""))
    return None if value is None or value.lower() in NO_VALUE else value


def lakes_named(name, description):
    found = []
    m = re.match(r"^(?:save\s+)?([a-z]+)\s+(?:neighbourhood\s+)?(?:lake|environs)\b", name, re.I)
    if m:
        found.append(f"{m.group(1)} lake")
    for m in re.finditer(r"([\w-]+)(?:\s+([\w-]+))?\s+(lakes?|kere)\b", description or "", re.I):
        before, word, kind = m.group(1), m.group(2), m.group(3)
        if word is None:
            word, before = before, None
        if word.lower() in NOT_A_NAME or not word[0].isalpha():
            continue
        words = [before, word] if before and word.lower() in NAME_SUFFIXES and before.lower() not in NOT_A_NAME else [word]
        found.append(" ".join([*words, kind]))
    seen, out = set(), []
    for lake in found:
        key = re.sub(r"[^a-z]", "", lake.lower().replace("lakes", "lake"))
        if key not in seen:
            seen.add(key)
            out.append(lake)
    return out


def build():
    pdf = pdfplumber.open(fetch())
    records = []
    for index in range(len(pdf.pages)):
        page = pdf.pages[index]
        if index >= SPILL_PAGE_OFFSET or not page.chars:
            continue
        left, right = page_cells(page), page_cells(pdf.pages[index + SPILL_PAGE_OFFSET])
        assert len(left) == len(right), f"page {index + 1}: {len(left)} rows vs {len(right)} on its spill page"
        for a, b in zip(left, right):
            records.append({"name": a[0], "type": a[1], "work": a[2], "twitter": a[4], "facebook": b[0], "website": b[1]})
    assert len(records) == EXPECTED_ROWS, len(records)

    out, dropped = [], 0
    for r in records:
        name = text(r["name"])
        if not name or HONORIFIC.match(name) or not ORG_WORDS.search(name):
            dropped += 1
            continue
        name = re.sub(r"\s+Managing Trustee$", "", name).rstrip(".")  # a role that spilled into the name cell
        kind = text(r["type"])
        out.append(
            {
                "source": "citizenmatters-lake-groups-2022",
                "groupName": name,
                "groupType": None if kind and kind.lower() in NO_VALUE else kind,
                "lakes": lakes_named(name, text(r["work"])),
                "website": link(r["website"]),
                "facebook": link(r["facebook"]),
                "twitter": link(r["twitter"]),
            }
        )

    write_csv(SOURCES / f"{NAME}.csv", out, list(out[0].keys()))
    write_sources(
        NAME,
        [
            {
                "key": "citizenmatters-lake-groups-2022",
                "title": "Lake groups in Bengaluru (directory)",
                "publisher": "Citizen Matters",
                "url": URL,
                "license": "not stated",
                "credit": "Citizen Matters",
                "asOf": "2022-07",
                "retrieved": "2026-09-11",
            }
        ],
    )
    print(f"{NAME}: {len(out)} groups kept, {dropped} individuals dropped, of {len(records)} rows -> data/sources/{NAME}.csv")


if __name__ == "__main__":
    build()
