#!/usr/bin/env python3
"""
Wikimedia Commons photos for each lake, found by location and by Wikidata Commons category.

For every lake outline:
  - add every file in the Commons category of the Wikidata item that sits on the lake (the item's
    point inside the outline buffered by 300 m; an item goes to its nearest lake only). Category
    redirects are followed; subcategories are not, as they drift ("Hebbal Lake" > "Manyata Tech Park").
  - add geotagged Commons files whose coordinates fall inside the outline buffered by 150 m, but only
    when the file's title or categories mention water (lake, kere, tank, pond ...). A location alone
    also catches the temple, flyover and tech park next to the lake.
Non-photos (maps, diagrams, logos, SVG, PDF, small images) and files without a free license are
dropped. At most 12 per lake: category files first, then files that mention water, then higher
resolution, then more recent.

Usage:
  scripts/sources/commons_photos.py [lakes.geojson] [--key atreeFid] [--out data/sources/commons_photos.csv]
Lakes can be polygons or points (disappeared lakes); a point is buffered the same way.
Needs data/sources/wikidata.csv (run scripts/sources/wikidata.py first).

Location search: Commons geosearch returns at most 500 files per query, and one 5 km box in central
Bengaluru already holds more than that. So instead of one search per lake, the script searches a
fixed grid of boxes (0.1 degree, split into quarters wherever a box is full), fetching only boxes
that touch a lake. Boxes are cached by grid position, so a rerun on another lake list reuses them.
This finds the same files a per-lake radius search would, without the 500-file cut-off, in far
fewer requests (Commons rate-limits anonymous clients hard).

Downloads: data/cache/commons_photos/ (API responses, reused on rerun).
"""

import argparse
import html
import json
import math
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from pyproj import Transformer
from shapely import STRtree, total_bounds
from shapely.geometry import Point, box, shape
from shapely.ops import transform

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, ROOT, SOURCES, clean, read_csv, write_csv, write_sources  # noqa: E402

DIR = CACHE / "commons_photos"
API = "https://commons.wikimedia.org/w/api.php"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "LakesOfBendakaluru/1.0 (https://filtercoffee.dev; open data project)"
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True).transform  # UTM 43N, metres

PHOTO_BUFFER_M = 150
WIKIDATA_BUFFER_M = 300
MAX_PER_LAKE = 12
GEOSEARCH_LIMIT = 500
TILE_DEG = 0.1  # base grid; Commons refuses boxes much larger than this
MIN_TILE_DEG = TILE_DEG / 2**8  # about 40 m; a box still full at this size is reported, not split
MIN_LONG_SIDE_PX = 640

PHOTO_MIMES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
NOT_A_PHOTO = re.compile(
    r"\b(maps?|mapa|locator|location map|diagrams?|charts?|graphs?|plans?|schematic|logos?|icons?|"
    r"emblems?|seals?|flags?|coat of arms|screenshots?|infographics?|satellite|landsat|sentinel-2|"
    r"topographic|openstreetmap|survey of india|documents?|scans? of)\b",
    re.I,
)
MENTIONS_WATER = re.compile(
    r"\b(lakes?|tanks?|ponds?|kunte|katte|reservoirs?|wetlands?|sarovara?)\b|kere\b|ಕೆರೆ|ಕುಂಟೆ|ಕಟ್ಟೆ|ಜಲಾಶಯ", re.I
)
FREE_LICENSE = re.compile(r"^(cc0|cc[ -]by|cc-by|public domain|pd\b|pd-|gfdl|fal\b|free art|attribution)", re.I)

EXTMETADATA = "|".join(
    [
        "Artist", "Credit", "LicenseShortName", "LicenseUrl", "AttributionRequired", "NonFree",
        "DateTimeOriginal", "Categories", "GPSLatitude", "GPSLongitude", "Restrictions",
    ]
)  # fmt: skip


def api(params):
    params = {**params, "format": "json", "formatversion": 2, "maxlag": 5}
    for attempt in range(6):
        try:
            response = SESSION.get(API, params=params, timeout=120)
        except requests.ConnectionError:
            time.sleep(5 * (attempt + 1))
            continue
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(int(response.headers.get("Retry-After", 10 * (attempt + 1))))
            continue
        response.raise_for_status()
        data = response.json()
        if data.get("error", {}).get("code") == "maxlag":
            time.sleep(int(response.headers.get("Retry-After", 5)))
            continue
        if "error" in data:
            raise RuntimeError(f"commons api: {data['error']}")
        return data
    raise RuntimeError(f"commons api: gave up on {params}")


def cached(path, fetch):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


# ---------- search ----------


def tile_bounds(level, ix, iy):
    size = TILE_DEG / 2**level
    return ix * size, iy * size, (ix + 1) * size, (iy + 1) * size  # west, south, east, north


def tile_search(level, ix, iy):
    """Files whose primary coordinate is inside one grid box."""
    west, south, east, north = tile_bounds(level, ix, iy)

    def fetch():
        time.sleep(0.2)
        data = api(
            {
                "action": "query",
                "list": "geosearch",
                "gsbbox": f"{north:.7f}|{west:.7f}|{south:.7f}|{east:.7f}",
                "gsnamespace": 6,
                "gslimit": GEOSEARCH_LIMIT,
            }
        )
        return data["query"]["geosearch"]

    return cached(DIR / "tiles" / f"{level}_{ix}_{iy}.json", fetch)


def geotagged_files(areas):
    """
    Every geotagged file in the grid boxes that touch any of the given lat/lon boxes.
    Returns {title: (lat, lon)} and the number of smallest boxes that were still full.
    """
    index = STRtree(areas)
    files, full, searched = {}, 0, 0

    def visit(level, ix, iy):
        nonlocal full, searched
        if not len(index.query(box(*tile_bounds(level, ix, iy)))):
            return
        hits = tile_search(level, ix, iy)
        searched += 1
        print(f"  searched {searched} boxes, {len(files)} files", end="\r", flush=True)
        if len(hits) < GEOSEARCH_LIMIT:
            for hit in hits:
                files[hit["title"]] = (hit["lat"], hit["lon"])
        elif TILE_DEG / 2**level <= MIN_TILE_DEG:
            full += 1
            for hit in hits:
                files[hit["title"]] = (hit["lat"], hit["lon"])
        else:
            for dx in (0, 1):
                for dy in (0, 1):
                    visit(level + 1, ix * 2 + dx, iy * 2 + dy)

    west, south, east, north = total_bounds(areas)
    for ix in range(math.floor(west / TILE_DEG), math.floor(east / TILE_DEG) + 1):
        for iy in range(math.floor(south / TILE_DEG), math.floor(north / TILE_DEG) + 1):
            visit(0, ix, iy)
    print()
    return files, full


def category_redirect(category):
    """Commons marks moved categories with {{Category redirect|...}} instead of a real redirect."""
    time.sleep(0.1)
    data = api(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": f"Category:{category}",
        }
    )
    page = data["query"]["pages"][0]
    content = page.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")
    match = re.search(r"\{\{\s*category redirect\s*\|\s*(?:category:)?([^|}]+)", content, re.I)
    return match.group(1).strip() if match else None


def category_files(category, hops=3):
    """Files directly in a category, following category redirects."""

    def fetch():
        target = category_redirect(category)
        if target and hops:
            return {"redirect": target}
        titles, cont = [], {}
        while True:
            time.sleep(0.1)
            data = api(
                {
                    "action": "query",
                    "list": "categorymembers",
                    "cmtitle": f"Category:{category}",
                    "cmtype": "file",
                    "cmlimit": 500,
                    **cont,
                }
            )
            titles += [m["title"] for m in data["query"]["categorymembers"]]
            if "continue" not in data:
                return {"files": titles}
            cont = data["continue"]

    data = cached(DIR / "categories" / f"{quote(category, safe='')}.json", fetch)
    return category_files(data["redirect"], hops - 1) if "redirect" in data else data["files"]


def file_info(titles):
    """imageinfo + coordinates per file title, cached in one growing file."""
    path = DIR / "imageinfo.json"
    known = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    missing = sorted(set(titles) - known.keys())
    for i in range(0, len(missing), 50):
        batch = missing[i : i + 50]
        time.sleep(0.2)
        data = api(
            {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "imageinfo|coordinates",
                "iiprop": "url|size|mime|extmetadata|timestamp",
                "iiurlwidth": 800,
                "iiextmetadatafilter": EXTMETADATA,
                "colimit": "max",
            }
        )
        # The API normalises titles ("File:A_b.jpg" -> "File:A b.jpg"); key the cache by what we asked.
        renamed = {n["to"]: n["from"] for n in data["query"].get("normalized", [])}
        for page in data["query"]["pages"]:
            known[renamed.get(page["title"], page["title"])] = page
        for title in batch:
            known.setdefault(title, {"missing": True})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(known, ensure_ascii=False), encoding="utf-8")
        print(f"  imageinfo {min(i + 50, len(missing))}/{len(missing)}", end="\r", flush=True)
    return {t: known[t] for t in titles}


# ---------- cleaning ----------


def plain(value):
    """extmetadata values are HTML fragments."""
    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", str(value))
    return clean(html.unescape(text))


def meta(info, key):
    return plain(info.get("extmetadata", {}).get(key, {}).get("value"))


def taken(info):
    """A date from DateTimeOriginal, at whatever precision it gives."""
    raw = meta(info, "DateTimeOriginal") or ""
    match = re.search(r"(\d{4})[-:](\d{2})[-:](\d{2})", raw)
    if match:
        return "-".join(match.groups())
    match = re.search(r"(\d{4})[-:](\d{2})\b", raw)
    if match:
        return "-".join(match.groups())
    match = re.search(r"\b(1[89]\d{2}|20\d{2})\b", raw)
    return match.group(1) if match else None


def coordinate(page, info):
    for c in page.get("coordinates", []):
        if c.get("primary", True):
            return round(c["lat"], 6), round(c["lon"], 6)
    try:
        return round(float(meta(info, "GPSLatitude")), 6), round(float(meta(info, "GPSLongitude")), 6)
    except (TypeError, ValueError):
        return None, None


def photo(title, page):
    """A clean photo record, or None if the file is not a freely licensed photo."""
    if page.get("missing") or not page.get("imageinfo"):
        return None
    info = page["imageinfo"][0]
    if info.get("mime") not in PHOTO_MIMES:
        return None
    width, height = info.get("width") or 0, info.get("height") or 0
    if max(width, height) < MIN_LONG_SIDE_PX:
        return None
    categories = (meta(info, "Categories") or "").replace("|", " ")
    if NOT_A_PHOTO.search(title) or NOT_A_PHOTO.search(categories):
        return None
    license_name = meta(info, "LicenseShortName")
    nonfree = (meta(info, "NonFree") or "").lower() in ("true", "1")
    if nonfree or not license_name or not FREE_LICENSE.search(license_name):
        return None
    author = meta(info, "Artist")
    lat, lon = coordinate(page, info)
    attribution_required = (meta(info, "AttributionRequired") or "true").lower() != "false"
    return {
        "title": title,
        "pageUrl": info.get("descriptionurl"),
        # Commons appends ?utm_source=... tracking parameters to these URLs.
        "fileUrl": (info.get("url") or "").split("?")[0] or None,
        "thumbUrl": (info.get("thumburl") or "").split("?")[0] or None,
        "width": width,
        "height": height,
        "author": author,
        "license": license_name,
        "licenseUrl": meta(info, "LicenseUrl"),
        "attributionRequired": attribution_required,
        "credit": " / ".join(x for x in (author, license_name, "Wikimedia Commons") if x),
        "dateTaken": taken(info),
        "uploaded": (info.get("timestamp") or "")[:10] or None,
        "lat": lat,
        "lon": lon,
        "mentionsWater": bool(MENTIONS_WATER.search(title) or MENTIONS_WATER.search(categories)),
    }


# ---------- lakes ----------


def load_lakes(path, key):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    lakes = []
    for f in data["features"]:
        if not f.get("geometry"):
            continue
        geom = shape(f["geometry"])
        utm = transform(TO_UTM, geom)
        minx, miny, maxx, maxy = geom.bounds
        # The buffer in degrees, generously: 150 m is under 0.0014 degrees of latitude or longitude here.
        pad = 0.002
        lakes.append(
            {
                "key": f["properties"][key],
                "utm": utm,
                "photoArea": utm.buffer(PHOTO_BUFFER_M),
                "searchBox": box(minx - pad, miny - pad, maxx + pad, maxy + pad),
            }
        )
    return lakes


def categories_by_lake(lakes):
    """Each Wikidata item with a Commons category goes to the nearest lake within 300 m."""
    path = SOURCES / "wikidata.csv"
    if not path.exists():
        sys.exit("commons_photos: data/sources/wikidata.csv is missing, run scripts/sources/wikidata.py first")
    out = {}
    for item in read_csv(path):
        if not item["commonsCategory"] or not item["lat"]:
            continue
        point = Point(TO_UTM(float(item["lon"]), float(item["lat"])))
        best = min(lakes, key=lambda lake: lake["utm"].distance(point))
        if best["utm"].distance(point) <= WIKIDATA_BUFFER_M:
            out.setdefault(best["key"], set()).add(item["commonsCategory"])
    return out


def recency(p):
    """Date taken, else upload date, as a sortable number (20190300 for "2019-03"); 0 when unknown."""
    digits = re.sub(r"\D", "", p["dateTaken"] or p["uploaded"] or "")
    return int(digits[:8].ljust(8, "0")) if digits else 0


def inside(lake, lat, lon):
    return lat is not None and lake["photoArea"].contains(Point(TO_UTM(lon, lat)))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("lakes", nargs="?", default=str(SOURCES / "atree.geojson"))
    parser.add_argument("--key", default="atreeFid", help="property that identifies a lake")
    parser.add_argument("--out", default=str(SOURCES / "commons_photos.csv"))
    args = parser.parse_args()

    lakes = load_lakes(args.lakes, args.key)
    categories = categories_by_lake(lakes)
    print(f"commons_photos: {len(lakes)} lakes, {sum(len(c) for c in categories.values())} Commons categories")

    geotagged, saturated = geotagged_files([lake["searchBox"] for lake in lakes])
    titles = list(geotagged)
    points = STRtree([Point(TO_UTM(lon, lat)) for lat, lon in geotagged.values()])

    candidates = {}
    for lake in lakes:
        found = {titles[i]: False for i in points.query(lake["photoArea"], predicate="contains")}
        for category in sorted(categories.get(lake["key"], ())):
            for title in category_files(category):
                found[title] = True
        candidates[lake["key"]] = found

    info = file_info(sorted({t for found in candidates.values() for t in found}))
    print()
    photos = {title: photo(title, page) for title, page in info.items()}

    rows = []
    for lake in lakes:
        kept = []
        for title, from_category in candidates[lake["key"]].items():
            record = photos.get(title)
            if not record:
                continue
            # A location match must mention water and still sit on the lake after the full coordinate lookup.
            if from_category or (record["mentionsWater"] and inside(lake, record["lat"], record["lon"])):
                kept.append({**record, "fromCategory": from_category})
        kept.sort(
            key=lambda p: (not p["fromCategory"], not p["mentionsWater"], -(p["width"] * p["height"]), -recency(p), p["title"])
        )
        for rank, p in enumerate(kept[:MAX_PER_LAKE], 1):
            rows.append({args.key: lake["key"], "rank": rank, **p, "source": "commons"})

    columns = [
        args.key, "rank", "title", "pageUrl", "fileUrl", "thumbUrl", "width", "height", "author", "license",
        "licenseUrl", "attributionRequired", "credit", "dateTaken", "uploaded", "lat", "lon", "fromCategory", "mentionsWater", "source",
    ]  # fmt: skip
    out = Path(args.out).resolve()
    write_csv(out, rows, columns)
    retrieved = time.strftime("%Y-%m-%d")
    write_sources(
        "commons_photos",
        [
            {
                "key": "commons",
                "title": "Wikimedia Commons photos, by location and by Wikidata Commons category",
                "publisher": "Wikimedia Commons contributors",
                "url": "https://commons.wikimedia.org/",
                "license": "per file (see the license and licenseUrl columns)",
                "credit": "Per file: author / license / Wikimedia Commons (see the credit column)",
                "asOf": retrieved,
                "retrieved": retrieved,
            }
        ],
    )
    with_photos = len({r[args.key] for r in rows})
    print(f"commons_photos: {len(rows)} photos for {with_photos} of {len(lakes)} lakes -> {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    if saturated:
        print(f"  warning: {saturated} boxes of about 40 m still hold {GEOSEARCH_LIMIT}+ files and may miss some")


if __name__ == "__main__":
    main()
