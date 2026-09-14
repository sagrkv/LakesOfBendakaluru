#!/usr/bin/env python3
"""
Our own copy of every timeline record that can be downloaded, kept next to the link to the original.

Each file is downloaded once to data/cache/archive/<id>/ (reused on rerun), uploaded to the site's
public Vercel Blob store at archive/<id>/<file>, and listed in public/data/archive.json, which the
timeline page reads. A file already in the manifest at the same size is not uploaded again.

Landsat MSS scenes are too large to keep whole, so each clear year is cut to the two districts and kept
twice: a false-colour PNG to look at (near-infrared, red and green as red, green and blue, so water is dark
and plants are red) and a GeoTIFF of the same three bands at the scene's own 60 m grid.

Not copied, because no file can be had: CORONA and HEXAGON photos (a USGS login, and $30 a scene to scan
HEXAGON), Bhuvan WBIS (no download), Dynamic World (Earth Engine only), and the 2011 SHRUG village tables
(behind a request form). Records known only by name have nothing to copy either.

Needs BLOB_READ_WRITE_TOKEN in .env.local (vercel env pull .env.local) and the Vercel CLI.
Usage: .venv/bin/python scripts/archive.py
Output: public/data/archive.json
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import rasterio
import requests
import truststore
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, OUT, ROOT  # noqa: E402

# The Census of India site sends an incomplete certificate chain; the system store completes it.
truststore.inject_into_ssl()

HEADERS = {"User-Agent": "LakesOfBendakaluru/1.0 (https://github.com/sagrkv/LakesOfBendakaluru)"}
COMMONS = "https://commons.wikimedia.org/wiki/Special:FilePath/"
OPENCITY = "https://data.opencity.in/dataset/"
CENSUS = "https://censusindia.gov.in/nada/index.php/catalog/"
DISTRICTS = (77.18, 12.66, 77.97, 13.5)  # west, south, east, north; the map's frame

# id -> (label, source address, file name). The file name's extension sets the format shown on the site.
FILES = {
    "ross-1800": [("The 1800 survey map", COMMONS + "Survey_of_the_boundaries_of_Purgunna_of_Bangalore_(1800).png", "ross-1800.png")],
    "city-plan-1843": [("The 1843 cantonment plan", COMMONS + "Plan_of_Bangalore_Cantonment_1843.jpg", "city-plan-1843.jpg")],
    "city-plan-1854": [("The 1854 city plan", COMMONS + "Bangalore_1854_Pharaoh.jpg", "city-plan-1854.jpg")],
    "soi-taluk-1878": [("The 1878 taluk map", COMMONS + "Bangalore_map_1878.png", "bangalore-taluk-1878.png")],
    "city-plan-1900": [("The city plan of about 1900", COMMONS + "Bangalore_1900.jpg", "city-plan-1900.jpg")],
    "revenue-maps-1915": [("The Singapura village map", COMMONS + "Singapura_revenue_village_map_from_1915CE.jpg", "singapura-1915.jpg")],
    "census-handbook-1961": [("The 1961 handbook", CENSUS + "28866/download/32048/24565_1961_BAN.pdf", "census-handbook-1961.pdf")],
    "census-handbook-1971": [("The 1971 handbook", CENSUS + "28865/download/32047/24902_1971_BAN.pdf", "census-handbook-1971.pdf")],
    "census-handbook-1991": [("The 1991 handbook", CENSUS + "45466/download/49670/09_41629_1991_BAN.pdf", "census-handbook-1991.pdf")],
    "ramaswamy-committee-2007": [
        (
            "The report, part 1",
            OPENCITY + "b3756019-5815-4aa6-9023-343cb249667d/resource/a4cd4765-ceab-4ece-a0c6-c33ed51834b2/download/68072efe-c62a-4d28-9943-1d9839e702af.pdf",
            "ramaswamy-2007-part-1.pdf",
        ),
        (
            "The report, part 2",
            OPENCITY + "b3756019-5815-4aa6-9023-343cb249667d/resource/caa7959f-ba93-485f-9bc6-35d0feb42301/download/ccb99415-d174-425e-93ac-e6659f028d94.pdf",
            "ramaswamy-2007-part-2.pdf",
        ),
    ],
    "patil-committee-2011": [
        (
            "The report",
            OPENCITY + "46dffdd5-1b51-4a72-bdc0-41a0ec85c31c/resource/225ab3a3-e767-4b63-a406-7048712d6b46/download/0634635f-5928-4030-aaea-d125e488aec2.pdf",
            "patil-committee-2011.pdf",
        )
    ],
    "koliwad-committee": [
        (
            "The full report",
            OPENCITY + "dab898a8-e582-4e36-ac7b-295461af12f5/resource/44fe1c87-57da-4eed-93eb-9ed20c267c24/download/32ae4efd-be63-409a-892d-0ba8213d3354.pdf",
            "koliwad-committee.pdf",
        ),
        (
            "The abstract of encroached tanks",
            OPENCITY + "dab898a8-e582-4e36-ac7b-295461af12f5/resource/b9fd1359-c24e-494f-81f2-0f3cf3065037/download/9a16556d-5b56-4687-86b2-490bd8084d4a.pdf",
            "koliwad-committee-abstract.pdf",
        ),
    ],
    "neeri-2019": [
        (
            "The report",
            OPENCITY + "30d27a06-a29e-4807-8c39-928bf823ea42/resource/1867220e-40d8-4522-b279-743fa185dfa5/download/69f09c61-6cfa-409b-a7e7-fd0704b78e11.pdf",
            "neeri-2020.pdf",
        )
    ],
    "minor-irrigation-tanks-2026": [
        (
            "The statewide tank list",
            "https://nwdp.nwic.gov.in/dataset/5ebfc603-d347-43e9-a827-ae07f47188b4/resource/52dc620d-5020-4885-a870-cd6d26064f3b/download/karnatka_minor_irregation_tank.csv",
            "karnataka-minor-irrigation-tanks.csv",
        )
    ],
}

# The clearest scene of each year that covers at least 92% of the districts (Planetary Computer search, under 10% cloud).
MSS_SCENES = [
    "LM01_L1TP_154051_19721111_02_T2",
    "LM01_L1TP_154051_19730227_02_T2",
    "LM02_L1TP_154051_19750226_02_T2",
    "LM02_L1TP_154051_19761205_02_T2",
    "LM02_L1TP_154051_19770305_02_T2",
    "LM03_L1TP_154051_19800403_02_T2",
]
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l1/items/"
SIGN = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"

FORMATS = {".pdf": "PDF", ".png": "PNG", ".jpg": "JPEG", ".csv": "CSV", ".tif": "GeoTIFF"}


def token():
    for line in (ROOT / ".env.local").read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "BLOB_READ_WRITE_TOKEN":
            return value.strip().strip('"')
    return os.environ["BLOB_READ_WRITE_TOKEN"]


def download(url, path):
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, headers=HEADERS, stream=True, timeout=300) as response:
        response.raise_for_status()
        part = path.with_suffix(path.suffix + ".part")
        with part.open("wb") as f:
            for chunk in response.iter_content(1 << 20):
                f.write(chunk)
        part.rename(path)
    print(f"archive: downloaded {path.name} ({path.stat().st_size:,} bytes)")
    return path


def mss_bands(scene):
    """Green, red and near-infrared of one scene, cut to the districts, with the cut's georeferencing."""
    item = requests.get(STAC + scene, headers=HEADERS, timeout=60).json()
    bands, profile = [], None
    for name in ("nir08", "red", "green"):
        href = requests.get(SIGN, params={"href": item["assets"][name]["href"]}, headers=HEADERS, timeout=60).json()["href"]
        with rasterio.open(href) as src:
            window = from_bounds(*transform_bounds("EPSG:4326", src.crs, *DISTRICTS), transform=src.transform)
            window = window.round_offsets().round_lengths()
            bands.append(src.read(1, window=window, boundless=True, fill_value=0))
            profile = profile or {
                "driver": "GTiff",
                "crs": src.crs,
                "transform": src.window_transform(window),
                "dtype": src.dtypes[0],
                "nodata": 0,
            }
    return np.stack(bands), profile


def mss_files(scene):
    """The PNG and GeoTIFF for one scene, built once into the cache."""
    folder = CACHE / "archive" / "landsat-mss"
    date = datetime.strptime(scene.split("_")[3], "%Y%m%d")
    stem = f"landsat-mss-{date:%Y-%m-%d}"
    png, tif = folder / f"{stem}.png", folder / f"{stem}.tif"
    if not (png.exists() and tif.exists()):
        folder.mkdir(parents=True, exist_ok=True)
        stack, profile = mss_bands(scene)
        with rasterio.open(tif, "w", **profile, count=3, width=stack.shape[2], height=stack.shape[1], compress="deflate") as dst:
            dst.write(stack)
        # Stretch each band between its 2nd and 98th percentile, ignoring the no-data edge.
        rgb = np.zeros((stack.shape[1], stack.shape[2], 3), dtype=np.uint8)
        valid = stack.min(axis=0) > 0
        for i, band in enumerate(stack.astype(np.float32)):
            lo, hi = np.percentile(band[valid], (2, 98))
            rgb[..., i] = np.clip((band - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
        rgb[~valid] = 0
        cv2.imwrite(str(png), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        print(f"archive: cut {scene}")
    day = f"{date.day} {date:%B %Y}"
    return [(f"{day}, image", png), (f"{day}, data", tif)]


def upload(path, pathname, rw_token):
    result = subprocess.run(
        ["vercel", "blob", "put", str(path), "--access", "public", "--pathname", pathname, "--allow-overwrite", "true", "--rw-token", rw_token, "--non-interactive"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    found = re.search(r"https://\S+\.blob\.vercel-storage\.com/\S+", result.stdout + result.stderr)
    if result.returncode != 0 or not found:
        raise RuntimeError(f"archive: upload of {pathname} failed:\n{result.stdout}\n{result.stderr}")
    return found.group(0).rstrip(".,)'\"")


def build():
    rw_token = token()
    manifest_path = OUT / "archive.json"
    before = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    known = {copy["href"].split("/archive/", 1)[-1]: copy for copies in before.values() for copy in copies}

    wanted = {
        source_id: [(label, download(url, CACHE / "archive" / source_id / name)) for label, url, name in files]
        for source_id, files in FILES.items()
    }
    wanted["landsat-mss"] = [pair for scene in MSS_SCENES for pair in mss_files(scene)]

    manifest = {}
    for source_id, files in wanted.items():
        manifest[source_id] = []
        for label, path in files:
            pathname = f"archive/{source_id}/{path.name}"
            size = path.stat().st_size
            old = known.get(f"{source_id}/{path.name}")
            href = old["href"] if old and old["bytes"] == size else upload(path, pathname, rw_token)
            manifest[source_id].append({"label": label, "href": href, "format": FORMATS[path.suffix], "bytes": size})

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(copy["bytes"] for copies in manifest.values() for copy in copies)
    print(f"archive: {sum(map(len, manifest.values()))} files for {len(manifest)} records, {total / 1e6:.0f} MB -> public/data/archive.json")


if __name__ == "__main__":
    build()
