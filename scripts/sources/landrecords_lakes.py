#!/usr/bin/env python3
"""
Karnataka land records lake maps for Bengaluru Urban and Bengaluru Rural districts.

Two lists on landrecords.karnataka.gov.in (Revenue Department, Survey Settlement and Land Records):
  survey   service3/lakesurvey.aspx        "Lake (Survey)"  - about 4,799 scanned Kannada sketch maps
                                                               with recorded extent, measured extent and
                                                               an encroacher table (not read here)
  digital  service3/Lakeencroachment.aspx  "Lake (Digital)" - about 334 digitised lake maps

Both are ASP.NET grids of 20 rows a page. Each row has an image button; posting it back makes the
server answer with window.open('FileDownload.aspx?file=\\\\...\\scanimages\\<mapId>.jpg'), which is the
JPEG. The file name is the site's village code followed by the survey number (ABBAGERE 75 is 18495 + 75).
For a lake on several survey numbers the site builds a name with commas ("1925248,38.jpg") that does not
exist; the same map is stored under each number, so we link the first one ("1925248.jpg").
The grid only pages forward (event validation refuses jumps), so every page is fetched in order.

Everything is cached so reruns are cheap and an interrupted run resumes where it stopped:
  data/cache/landrecords_lakes/<list>/pages/p0001.html   listing pages as downloaded
  data/raw/landrecords_lakes/<list>.json                 rows + resolved image URL, one per grid row
  data/cache/landrecords_lakes/images/<folder>/<mapId>.jpg  the map images (about 400 KB each; a few are .tif)

Output: data/sources/landrecords_lakes_survey.csv, data/sources/landrecords_lakes_digital.csv
Run with --no-images to resolve URLs and write the CSVs without downloading images.
"""

import html
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, RAW, SOURCES, clean, write_csv, write_sources  # noqa: E402

NAME = "landrecords_lakes"
BASE = "https://landrecords.karnataka.gov.in/service3/"
LISTS = {
    "digital": {"page": "Lakeencroachment.aspx", "key": "landrecords-lake-digital", "expected": 334,
                "title": "Lake (Digital) maps, Bengaluru Urban"},
    "survey": {"page": "lakesurvey.aspx", "key": "landrecords-lake-survey", "expected": 4799,
               "title": "Lake (Survey) maps, Bengaluru Urban and Bengaluru Rural"},
}
DISTRICTS = {"bengaluru": "Bengaluru Urban", "bangalore rural": "Bengaluru Rural"}
DELAY_S = 1.0
IMAGES = CACHE / NAME / "images"
# Links the site gives but whose file the server does not have (it answers with an empty page).
MISSING = RAW / NAME / "missing_images.json"


def missing():
    return set(json.loads(MISSING.read_text())) if MISSING.exists() else set()

ROW = re.compile(
    r'lblDist_(\d+)">([^<]*)<.*?lblTal_\d+">([^<]*)<.*?lblHob_\d+">([^<]*)<.*?lblVil_\d+">([^<]*)<'
    r'.*?lblsurvno_\d+">([^<]*)<.*?name="(grdMaps\$ctl\d+\$ImgPdf)"',
    re.S,
)
HIDDEN = re.compile(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"')
OPEN = re.compile(r"window\.open\('([^']+)'")

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 (LakesOfBendakaluru data project)"
_last = 0.0


def request(method, url, **kwargs):
    """Throttled request with retries. Returns the response or raises after the last try."""
    global _last
    for attempt in range(5):
        wait = DELAY_S - (time.monotonic() - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.monotonic()
        try:
            r = session.request(method, url, timeout=90, **kwargs)
            if r.status_code == 200:
                return r
            error = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            error = str(e)
        print(f"  retry {attempt + 1} {url}: {error}", flush=True)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"gave up on {url}: {error}")


def form(page_html):
    return {name: html.unescape(value) for name, value in HIDDEN.findall(page_html)}


def rows(page_html):
    return [
        {"row": int(m[0]), "district": m[1], "taluk": m[2], "hobli": m[3], "village": m[4], "survey": m[5], "button": m[6]}
        for m in ROW.findall(page_html)
    ]


def pages_in_pager(page_html):
    return {int(n) for n in re.findall(r"Page\$(\d+)&#39;", page_html)}


def fetch_pages(kind):
    """Walk the grid forward page by page, caching each page. Returns the list of page HTML."""
    url = BASE + LISTS[kind]["page"]
    folder = CACHE / NAME / kind / "pages"
    folder.mkdir(parents=True, exist_ok=True)
    pages, number = [], 1
    while True:
        path = folder / f"p{number:04d}.html"
        if path.exists():
            text = path.read_text(encoding="utf-8")
        else:
            if number == 1:
                text = request("GET", url).text
            else:
                data = {**form(pages[-1]), "__EVENTTARGET": "grdMaps", "__EVENTARGUMENT": f"Page${number}"}
                text = request("POST", url, data=data).text
            if not rows(text):
                raise RuntimeError(f"{kind} page {number} has no rows")
            path.write_text(text, encoding="utf-8")
            print(f"{kind}: page {number}", flush=True)
        pages.append(text)
        if number + 1 not in pages_in_pager(text):
            return pages
        number += 1


def resolve(kind, pages):
    """Post each row's image button and keep the JPEG URL the server opens."""
    url = BASE + LISTS[kind]["page"]
    store = RAW / NAME / f"{kind}.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["page"], r["row"]): r for r in json.loads(store.read_text())} if store.exists() else {}
    records = []
    for number, text in enumerate(pages, 1):
        fields, changed = form(text), False
        for row in rows(text):
            key = (number, row["row"])
            old = done.get(key)
            same = old and all(old[k] == row[k] for k in ("district", "taluk", "hobli", "village", "survey"))
            if same and old.get("fileUrl"):
                records.append(old)
                continue
            record = {"page": number, **{k: v for k, v in row.items() if k != "button"}, "fileUrl": None}
            data = {**fields, f"{row['button']}.x": "10", f"{row['button']}.y": "10"}
            try:
                found = OPEN.findall(request("POST", url, data=data).text)
                record["fileUrl"] = urljoin(BASE, found[0]) if found else None
            except RuntimeError as e:
                print(f"  {kind} page {number} row {row['row']}: {e}", flush=True)
            records.append(record)
            changed = True
        if changed:
            store.write_text(json.dumps(records, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
            print(f"{kind}: resolved page {number}/{len(pages)}", flush=True)
    store.write_text(json.dumps(records, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    return records


def map_id(file_url):
    """The scan's file name, e.g. 2044251 from ...%5cscanimages%5c2044251.jpg."""
    m = re.search(r"([^\\/]+)\.jpe?g$", unquote(file_url or ""), re.I)
    return m.group(1) if m else None


def image_url(file_url):
    """The site's link, repaired for lakes on several survey numbers (see the module notes)."""
    if not file_url:
        return None
    return re.sub(r"(%2c[^%]*)+(?=\.jpe?g$)", "", file_url, flags=re.I)


def village_code(mid, survey):
    first = re.split(r",", survey or "")[0].strip()
    if mid and first and mid.endswith(first) and len(mid) > len(first):
        return mid[: -len(first)]
    return None


# Most scans are JPEG; some are TIFF (or other formats) behind a .jpg name. Save each with its real type.
FORMATS = {b"\xff\xd8": ".jpg", b"II*\x00": ".tif", b"MM\x00*": ".tif", b"\x89PNG": ".png", b"%PDF": ".pdf"}


def file_type(content):
    return next((ext for magic, ext in FORMATS.items() if content.startswith(magic)), None)


def saved_image(url):
    """The cached file for a map link, whatever its format, or None."""
    path = image_path(url)
    if path is None:
        return None
    return next((p for p in (path.with_suffix(ext) for ext in set(FORMATS.values())) if p.exists()), None)


def image_path(file_url):
    """Survey scans sit in a "scanimages" folder and digital maps in "images"; keep them apart."""
    parts = re.split(r"[\\/]", unquote(file_url or ""))
    if len(parts) < 2 or not map_id(file_url):
        return None
    return IMAGES / parts[-2] / f"{map_id(file_url)}.jpg"


def download(records):
    urls = [image_url(r["fileUrl"]) for r in records]
    wanted = {image_path(u): u for u in urls if image_path(u)}
    gone = missing()
    todo = [(path, u) for path, u in wanted.items() if not saved_image(u) and u not in gone]
    for i, (path, file_url) in enumerate(todo, 1):
        mid = path.stem
        try:
            r = request("GET", file_url)
        except RuntimeError as e:
            print(f"  image {mid}: {e}", flush=True)
            continue
        ext = file_type(r.content)
        if not ext:
            print(f"  image {mid}: not an image ({len(r.content)} bytes, {r.headers.get('Content-Type')})", flush=True)
            if not r.content:
                gone.add(file_url)
                MISSING.write_text(json.dumps(sorted(gone), indent=0) + "\n", encoding="utf-8")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        tmp.write_bytes(r.content)
        tmp.rename(path.with_suffix(ext))
        if i % 50 == 0:
            print(f"images: {i}/{len(todo)}", flush=True)


def survey_numbers(text):
    return [part for part in (clean(p) for p in re.split(r"[,;&/]| and ", text or "")) if part]


def write(kind, records):
    gone = missing()
    rows_out = []
    for r in records:
        url = image_url(r["fileUrl"])
        mid = map_id(url)
        image = saved_image(url)
        district = clean(r["district"])
        rows_out.append(
            {
                "source": LISTS[kind]["key"],
                "mapId": mid,
                "villageCode": village_code(mid, r["survey"]),
                "district": district,
                "districtName": DISTRICTS.get((district or "").lower()),
                "taluk": clean(r["taluk"]),
                "hobli": clean(r["hobli"]),
                "village": clean(r["village"]),
                "surveyNumber": clean(r["survey"]),
                "surveyNumbers": survey_numbers(r["survey"]),
                "mapImageUrl": url,
                "imageFile": str(image.relative_to(CACHE.parent.parent)) if image else None,
                "imageMissing": url in gone,
                "listPage": r["page"],
                "listRow": r["row"],
            }
        )
    columns = ["source", "mapId", "villageCode", "district", "districtName", "taluk", "hobli", "village", "surveyNumber",
               "surveyNumbers", "mapImageUrl", "imageFile", "imageMissing", "listPage", "listRow"]
    write_csv(SOURCES / f"{NAME}_{kind}.csv", rows_out, columns)
    resolved = sum(1 for r in rows_out if r["mapImageUrl"])
    images = sum(1 for r in rows_out if r["imageFile"])
    absent = sum(1 for r in rows_out if r["imageMissing"])
    expected = LISTS[kind]["expected"]
    flag = "" if len(rows_out) == expected else f"  (expected {expected})"
    print(f"{NAME}_{kind}: {len(rows_out)} rows{flag}, {resolved} image URLs, {images} images on disk, {absent} missing on the server")


def main():
    with_images = "--no-images" not in sys.argv
    # Resolve and write both lists first, so the CSVs exist before the long image download.
    records = {}
    for kind in LISTS:
        records[kind] = resolve(kind, fetch_pages(kind))
        write(kind, records[kind])
    if with_images:
        for kind in LISTS:
            download(records[kind])
            write(kind, records[kind])
    write_sources(
        NAME,
        [
            {
                "key": spec["key"],
                "title": spec["title"],
                "publisher": "Department of Survey, Settlement and Land Records, Government of Karnataka",
                "url": BASE + spec["page"],
                "license": "not stated",
                "credit": "Lake maps: Survey, Settlement and Land Records Department, Karnataka",
                # The site gives no date for the lists or the maps.
                "asOf": "not stated",
                # When the cached first listing page was downloaded, not when this run happened.
                "retrieved": date.fromtimestamp((CACHE / NAME / kind / "pages" / "p0001.html").stat().st_mtime).isoformat(),
            }
            for kind, spec in LISTS.items()
        ],
    )


if __name__ == "__main__":
    main()
