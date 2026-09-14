"""
Shared paths and helpers for the source scripts and the build.

Every source script under scripts/sources/ follows the same contract:
  - downloads go to data/raw/<source>/ (small, committed) or data/cache/<source>/ (large, ignored)
  - the cleaned table goes to data/sources/<source>.csv or .geojson
  - the citation goes to data/sources/<source>.sources.json via write_sources()
"""

import csv
import json
import math
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "cache"
SOURCES = ROOT / "data" / "sources"
OUT = ROOT / "public" / "data"

BLANK = {"", "-na-", "na", "n/a", "-", "nan", "none", "null", "<null>", "nil"}


def clean(value):
    """Normalise one text value: repair mojibake, collapse whitespace, map null spellings to None."""
    if value is None:
        return None
    text = str(value)
    # Some exports double-encoded UTF-8 through code page 437 ("Γö¼├í" for a no-break space).
    if re.search(r"[ΓöÇ├┬]", text):
        try:
            text = text.encode("cp437").decode("utf-8").encode("cp437").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
    return None if text.lower() in BLANK else text


def slugify(name):
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "lake"


# Bengaluru lake names appear with many spellings: "kere"/"lake" are the same word,
# and the same lake shows up as "Bellandur"/"Bellanduru". Strip both to compare.
NAME_NOISE = re.compile(
    r"\b(lake|kere|kere2|kunte|katte|tank|the|govt|government|new|old|big|small|dodda|chikka|upper|lower)\b"
)


def name_key(name):
    """A loose comparison key for lake names. Only ever used together with a distance check."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = NAME_NOISE.sub(" ", text)
    text = re.sub(r"(halli|hally|pura|puram|nagara|nagar|sandra|palya|palaya|u)\b", "", text)
    text = re.sub(r"(.)\1+", r"\1", text)  # "Kodigehalli"/"Kodigehali"
    return re.sub(r"\s+", "", text)


def distance_m(lon1, lat1, lon2, lat2):
    """Haversine distance in metres."""
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def write_csv(path, rows, columns):
    """Write rows (dicts) with a fixed column order. Lists are joined with ';'."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {k: ";".join(map(str, v)) if isinstance(v, list) else ("" if v is None else v) for k, v in row.items()}
            )


def read_csv(path):
    with path.open(encoding="utf-8") as f:
        return [{k: (v if v != "" else None) for k, v in row.items()} for row in csv.DictReader(f)]


def write_sources(name, entries):
    """
    Record where a source's data came from. Each entry:
      key        short id facts point at, e.g. "kspcb-2025-11"
      title      what the document or dataset is called
      publisher  who made it
      url        where a reader can see it
      license    as stated by the publisher, or "not stated"
      credit     the credit line to show, if the license needs one
      asOf       the date the data describes (YYYY or YYYY-MM or YYYY-MM-DD)
      retrieved  the date we downloaded it (YYYY-MM-DD)
    """
    required = {"key", "title", "publisher", "url", "license", "credit", "asOf", "retrieved"}
    for entry in entries:
        missing = required - entry.keys()
        if missing:
            raise ValueError(f"{name}: source {entry.get('key')} is missing {sorted(missing)}")
    path = SOURCES / f"{name}.sources.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
