#!/usr/bin/env python3
"""
KSPCB monthly water quality of Bengaluru lakes, July 2023 onwards.

KSPCB publishes one PDF per month on its water monitoring page (older months as files
on its own site, newer ones as Google Drive links). OpenCity mirrors July 2023 - November 2025
as identical copies. We take every month from KSPCB and fall back to OpenCity only for a
month KSPCB does not list. November 2023 is missing from both.

Outputs:
  data/sources/kspcb_readings.csv   one row per station, month and parameter
  data/sources/kspcb_stations.csv   one row per monitoring station

Readings columns:
  stationId       our stable id: the KSPCB station code, else a slug of the cleaned name
  stationCode     the KSPCB code as printed (empty in months that print none)
  stationName     the location as printed that month
  month           YYYY-MM
  useClass        A-E, the use class KSPCB assigned that month
  parameter       see kspcb_pdf.PARAMETERS for the vocabulary and units
  value           the number; empty when below detection or not reported ("NA", "-")
  belowDetection  true when printed as "BDL" or "3(BDL)"
  detectionLimit  the number in brackets of "3(BDL)", when given
  unit
  source          kspcb-YYYY-MM

Station identity. Codes are printed in most months. July 2023 and June-July 2026 print none,
and from January 2026 reports print latitude and longitude. A row without a code takes the code
of a coded station printed at exactly the same coordinates, else of the one coded station with the
same cleaned name. Rows that still have no code use a slug of the cleaned name as their id.

Run: .venv/bin/python scripts/sources/kspcb.py [--refresh]   (--refresh re-reads the listing pages)
"""

import datetime
import hashlib
import html
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, SOURCES, clean, slugify, write_csv, write_sources  # noqa: E402
from kspcb_pdf import META, PARAMETERS, parse  # noqa: E402

KSPCB_PAGE = "https://kspcb.karnataka.gov.in/environmental-monitoring/water"
OPENCITY_API = "https://data.opencity.in/api/3/action/package_show?id=bengaluru-lake-monthly-water-quality-reports"
OPENCITY_PAGE = "https://data.opencity.in/dataset/bengaluru-lake-monthly-water-quality-reports"
DIR = CACHE / "kspcb"
MANIFEST = DIR / "manifest.json"

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

# KSPCB labels the January-March 2024 files as 2023, and the February file's own title is cut
# off at "202". The file names (Jan-24, Feb_24, March-24) and the sampling data say 2024.
MONTH_OVERRIDES = {"Feb_24.pdf": "2024-02"}

# The January and February 2025 PDFs map the letter pair "na" to "-" ("Basava-pura", "-gavara").
NA_AS_DASH = {"2025-01", "2025-02"}

# July 2023 prints names only. These four differ from every later month's name by one word or
# letter; each code below is absent from July 2023 under any other name, and the lakes are the same.
JULY_2023_NAMES = {
    "devarakere lake": "3634",  # Devarakere Tank
    "gubbalala lake": "4535",  # Gubbalal Lake
    "kogilu lake": "4511",  # Kogilu Kere
    "subramanyapura lake": "3633",  # Subramanyapura Tank
}

# Words that mark the lake itself in a location name; what follows is the spot on that lake.
LAKE_WORD = re.compile(r"\b(lake|tank|kere|kunte|katte|\w+kere)\b(\s*-\s*\d+)?", re.I)
PLACE_NOISE = re.compile(r"^(bengaluru|bangalore|bengalore)( east| south| east taluka?)?$", re.I)
CITY_SUFFIX = re.compile(r"\s*,?\s*\b(bengaluru|bangalore|bengalore)\b\s*$", re.I)


# ---------- fetch ----------


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (lakes-of-bendakaluru data build)"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def load_manifest():
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def cached(url, name, manifest, refresh=False):
    """Download once; the manifest remembers the file and the day it was retrieved."""
    path = DIR / name
    if path.exists() and not refresh and url in manifest:
        return path
    DIR.mkdir(parents=True, exist_ok=True)
    data = get(url)
    path.write_bytes(data)
    manifest[url] = {"file": name, "retrieved": datetime.date.today().isoformat(), "sha1": hashlib.sha1(data).hexdigest()}
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    return path


def drive_download(url):
    match = re.search(r"/d/([\w-]+)", url)
    return f"https://drive.google.com/uc?export=download&id={match.group(1)}" if match else url


def kspcb_documents(manifest, refresh):
    """Every 'Water Quality Data of Bengaluru Lakes' link on the KSPCB page: (label, link, download url)."""
    page = cached(KSPCB_PAGE, "kspcb-water.html", manifest, refresh).read_text(encoding="utf-8", errors="replace")
    docs = []
    for href, inner in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
        if not re.search(r"Ben\w*galuru\s+Lakes\s+for\s+the\s+month", label, re.I):
            continue
        link = href.strip()
        if link.startswith("/"):
            link = "https://kspcb.karnataka.gov.in" + link
        docs.append((label, link, drive_download(link)))
    return docs


def opencity_documents(manifest, refresh):
    meta = json.loads(cached(OPENCITY_API, "opencity-package.json", manifest, refresh).read_text())
    return [(r["name"], r["url"], r["url"]) for r in meta["result"]["resources"] if r["format"].upper() == "PDF"]


def month_from(text):
    match = re.search(r"(?:month\s+of|report)\s+([A-Za-z]+)[\s,\-–]*(\d{4})", text or "", re.I)
    if match and match.group(1)[:3].lower() in MONTHS:
        return f"{match.group(2)}-{MONTHS[match.group(1)[:3].lower()]:02d}"
    return None


def file_name(link):
    match = re.search(r"/d/([\w-]+)", link)
    if match:
        return f"drive-{match.group(1)}.pdf"
    return re.sub(r"[^\w.-]+", "_", urllib.request.unquote(link.rsplit("/", 1)[-1]))


def collect(refresh):
    """month -> report, for every month either publisher has."""
    manifest = load_manifest()
    reports = {}
    for publisher, docs in (("KSPCB", kspcb_documents(manifest, refresh)), ("OpenCity", opencity_documents(manifest, refresh))):
        for label, link, url in docs:
            label_month = month_from(label)
            if publisher == "OpenCity" and label_month in reports:
                continue  # KSPCB already has it; the OpenCity copies are byte-identical
            name = ("opencity-" if publisher == "OpenCity" else "") + file_name(link)
            path = cached(url, name, manifest)
            title, keys, rows = parse(path)
            if not rows:
                print(f"  skip {label!r}: no data table (a summary chart)")
                continue
            base = urllib.request.unquote(link.rsplit("/", 1)[-1])
            month = MONTH_OVERRIDES.get(base) or month_from(title) or label_month
            if month in reports:
                raise ValueError(f"two reports for {month}: {reports[month]['link']} and {link}")
            reports[month] = {
                "month": month,
                "label": label,
                "title": title,
                "link": link,
                "publisher": publisher,
                "retrieved": manifest[url]["retrieved"],
                "keys": keys,
                "rows": rows,
            }
    return dict(sorted(reports.items()))


# ---------- cleaning ----------


def parse_value(raw):
    """Printed cell -> (value, belowDetection, detectionLimit), or None for an empty cell."""
    s = re.sub(r"\s+", "", raw or "")
    if not s:
        return None
    if s.upper() in ("NA", "-", "_", "--", "#VALUE!", "ND", "NR"):
        return ("", False, "")
    # "BDL", "3(BDL)", "0.5 (BDL)", "(BDL)", "1.BDL" and, where text overflows its cell, "3(BDL".
    match = re.fullmatch(r"(\d*\.?\d+)?\.?\(?BDL\)?", s, re.I)
    if match:
        return ("", True, number(match.group(1)) if match.group(1) else "")
    match = re.fullmatch(r"<(\d*\.?\d+)", s)
    if match:
        return ("", True, number(match.group(1)))
    if re.fullmatch(r"\d*\.?\d+(E[+-]?\d+)?", s, re.I):
        return (number(s), False, "")
    raise ValueError(f"unreadable value {raw!r}")


def number(text):
    value = float(text)
    if "e" in text.lower():
        return str(int(value)) if value.is_integer() else repr(value)
    text = text.lstrip("0") or "0"
    return "0" + text if text.startswith(".") else text


def name_key(name):
    """Exact-name comparison key: case, punctuation and spacing ignored."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def split_name(name):
    """'Ulsoor Lake Training Centre Of Fish Breeding' -> ('Ulsoor Lake', 'Training Centre Of Fish Breeding')."""
    # "(S)", "( Kr Puram Lake )" are other names, kept in stationName. "Hoodi (Rajapalya Lake) Itpl..."
    # has no lake word outside the brackets, so there the bracket is the lake.
    first = re.split(r",", name)[0]
    if re.search(r"\(", first) and not LAKE_WORD.search(re.sub(r"\([^)]*\)?", " ", first)):
        name = re.sub(r"\)", ")|", name, count=1)
        head, _, tail = name.partition("|")
        parts = [head.strip()] + [p.strip(" .-") for p in re.split(r",", tail) if p.strip(" .-")]
        return head.strip(), ", ".join(CITY_SUFFIX.sub("", p) for p in parts[1:] if not PLACE_NOISE.match(p)) or None
    text = re.sub(r"\([^)]*\)?", " ", name)
    parts = [CITY_SUFFIX.sub("", p).strip(" .-") for p in re.split(r",", text)]
    parts = [p for p in parts if p]
    head = re.sub(r"\s+", " ", parts[0]) if parts else name
    rest = [p for p in parts[1:] if not PLACE_NOISE.match(p)]
    matches = list(LAKE_WORD.finditer(head))
    if matches:
        end = matches[-1].end()
        lake, spot = head[:end].strip(), head[end:].strip(" .-")
        rest = ([spot] if spot else []) + rest
    else:
        lake = head
    if lake.isupper():
        lake = lake.title()
    return lake, ", ".join(rest) or None


def use_class(text):
    match = re.match(r"\s*([A-E])\b", text or "")
    return match.group(1) if match else None


def coordinate(text, low, high):
    try:
        value = float(re.sub(r"[^\d.]", "", text or ""))
    except ValueError:
        return None
    return value if low <= value <= high else None


def printed_rows(reports):
    """Flatten reports into one record per printed station row."""
    out = []
    for month, report in reports.items():
        for i, row in enumerate(report["rows"]):
            name = clean(re.sub("[\u00c2\u00e2](?=\\s|$)", "", row.get("name") or ""))  # a stray "â" after "Mahadevpura"
            if month in NA_AS_DASH and name:
                name = re.sub(r"-(?=[a-z]|\s)", "na", re.sub(r"(?<![A-Za-z])-(?=[a-z])", "Na", name))
            code = clean(row.get("code"))
            klass = use_class(row.get("useClass"))
            # July 2023 prints one name so long that the class runs on from it: "...(SWARANA KUNTE)D (Propagation...)".
            spill = re.search(r"(?<=[)\s])([A-E])(\s*\((?:propagation|irrigation|drinking|out|bath)[^)]*\)?)?$", name or "", re.I)
            if klass is None and spill:
                klass, name = spill.group(1).upper(), name[: spill.start()].strip()
            if not name:
                raise ValueError(f"{month} row {i}: no station name")
            if code and not re.fullmatch(r"\d{3,5}", code):
                raise ValueError(f"{month} row {i}: odd station code {code!r}")
            out.append(
                {
                    "month": month,
                    "code": code,
                    "name": name,
                    "lat": coordinate(row.get("lat"), 11.5, 14.5),
                    "lon": coordinate(row.get("lon"), 76.5, 78.5),
                    "useClass": klass,
                    "sampled": clean(row.get("sampled")),
                    "row": row,
                    "source": f"kspcb-{month}",
                }
            )
    return out


def assign_ids(records):
    """Give every printed row a stationId. Returns counts of how rows were linked."""
    by_coord, by_name = defaultdict(set), defaultdict(set)
    for r in records:
        if r["code"]:
            by_name[name_key(r["name"])].add(r["code"])
            if r["lat"] is not None and r["lon"] is not None:
                by_coord[(r["lat"], r["lon"])].add(r["code"])
    how = Counter()
    for r in records:
        if r["code"]:
            r["stationId"], method = r["code"], "printed code"
        elif len(by_coord.get((r["lat"], r["lon"]), ())) == 1:
            r["stationId"], method = next(iter(by_coord[(r["lat"], r["lon"])])), "same coordinates"
        elif len(by_name.get(name_key(r["name"]), ())) == 1:
            r["stationId"], method = next(iter(by_name[name_key(r["name"])])), "same name"
        elif r["month"] == "2023-07" and name_key(r["name"]) in JULY_2023_NAMES:
            r["stationId"], method = JULY_2023_NAMES[name_key(r["name"])], "reviewed name"
        else:
            r["stationId"], method = slugify(name_key(r["name"])), "name slug"
        how[method] += 1
    # Two uncoded rows of one month on the same id are two stations with one name
    # (July 2023 lists "PUTTENAHALLI LAKE" twice: codes 3614 and 3624, but which is which is not
    # printed). They get the name slug plus their order in the report.
    seen = Counter((r["stationId"], r["month"]) for r in records)
    order = Counter()
    for r in records:
        key = (r["stationId"], r["month"])
        if seen[key] > 1 and not r["code"]:
            order[key] += 1
            r["stationId"] = f"{slugify(name_key(r['name']))}-{order[key]}"
    dupes = Counter((r["stationId"], r["month"]) for r in records)
    for (sid, month), n in dupes.items():
        if n > 1:
            raise ValueError(f"{n} rows for station {sid} in {month}")
    return how


def readings(records):
    rows, problems = [], []
    for r in records:
        for key, raw in r["row"].items():
            if key in META:
                continue
            try:
                parsed = parse_value(raw)
            except ValueError as e:
                problems.append(f"{r['month']} {r['stationId']} {key}: {e}")
                continue
            if parsed is None:
                continue
            value, bdl, limit = parsed
            rows.append(
                {
                    "stationId": r["stationId"],
                    "stationCode": r["code"],
                    "stationName": r["name"],
                    "month": r["month"],
                    "useClass": r["useClass"],
                    "parameter": key,
                    "value": value,
                    "belowDetection": "true" if bdl else "false",
                    "detectionLimit": limit,
                    "unit": PARAMETERS[key],
                    "source": r["source"],
                }
            )
    return rows, problems


def stations(records):
    groups = defaultdict(list)
    for r in records:
        groups[r["stationId"]].append(r)
    # Coordinates: printed for the station itself, else carried from a same-named station.
    # Only names that belong to one station can carry coordinates.
    ids_by_name = defaultdict(set)
    for r in records:
        ids_by_name[name_key(r["name"])].add(r["stationId"])
    coords_by_name = {}
    for r in sorted(records, key=lambda r: r["month"]):
        if r["lat"] is not None and r["lon"] is not None and len(ids_by_name[name_key(r["name"])]) == 1:
            coords_by_name[name_key(r["name"])] = (r["lat"], r["lon"], r["source"])
    out = []
    for sid, rows in groups.items():
        rows.sort(key=lambda r: r["month"])
        latest = rows[-1]
        located = [r for r in rows if r["lat"] is not None and r["lon"] is not None]
        if located:
            lat, lon, coord_source = located[-1]["lat"], located[-1]["lon"], located[-1]["source"]
        else:
            lat, lon, coord_source = next(
                (coords_by_name[name_key(r["name"])] for r in reversed(rows) if name_key(r["name"]) in coords_by_name),
                (None, None, None),
            )
        codes = sorted({r["code"] for r in rows if r["code"]})
        lake, spot = split_name(latest["name"])
        out.append(
            {
                "stationId": sid,
                "stationCode": ";".join(codes) or None,
                "stationName": latest["name"],
                "lakeName": lake,
                "subLocation": spot,
                "lat": lat,
                "lon": lon,
                "coordSource": coord_source,
                "firstMonth": rows[0]["month"],
                "lastMonth": latest["month"],
                "monthsReported": len({r["month"] for r in rows}),
                "source": latest["source"],
            }
        )
    out.sort(key=lambda s: (not s["stationId"].isdigit(), int(s["stationId"]) if s["stationId"].isdigit() else 0, s["stationId"]))
    return out


def check_months(records):
    """The sampling-month column, where printed, should agree with the report month."""
    for r in records:
        sampled = (r["sampled"] or "")[:3].lower()
        if sampled in MONTHS and MONTHS[sampled] != int(r["month"][5:]):
            print(f"  warning: {r['month']} {r['name']!r} says sampled in {r['sampled']!r}")


def build(refresh=False):
    reports = collect(refresh)
    records = printed_rows(reports)
    check_months(records)
    how = assign_ids(records)
    reading_rows, problems = readings(records)
    station_rows = stations(records)

    write_csv(
        SOURCES / "kspcb_readings.csv",
        reading_rows,
        ["stationId", "stationCode", "stationName", "month", "useClass", "parameter", "value",
         "belowDetection", "detectionLimit", "unit", "source"],
    )
    write_csv(
        SOURCES / "kspcb_stations.csv",
        station_rows,
        ["stationId", "stationCode", "stationName", "lakeName", "subLocation", "lat", "lon", "coordSource",
         "firstMonth", "lastMonth", "monthsReported", "source"],
    )
    write_sources(
        "kspcb",
        [
            {
                "key": f"kspcb-{month}",
                "title": r["title"] or r["label"],
                "publisher": "Karnataka State Pollution Control Board (KSPCB)",
                "url": r["link"] if r["publisher"] == "KSPCB" else OPENCITY_PAGE,
                "license": "not stated" if r["publisher"] == "KSPCB" else "Other (Public Domain), as marked on OpenCity",
                "credit": "Water quality: Karnataka State Pollution Control Board",
                "asOf": month,
                "retrieved": r["retrieved"],
            }
            for month, r in reports.items()
        ],
    )
    for month, r in reports.items():
        print(f"  {month}: {len(r['rows'])} stations, {len([k for k in r['keys'] if k not in META])} parameters ({r['publisher']})")
    print(f"  station ids: {dict(how)}")
    for p in problems:
        print(f"  unread: {p}")
    print(f"kspcb: {len(reports)} months, {len(station_rows)} stations, {len(reading_rows)} readings")


if __name__ == "__main__":
    build(refresh="--refresh" in sys.argv)
